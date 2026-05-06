"""AngleService — story angle detection pipeline for completed F1 races.

Per CONTEXT.md:
  D-01/D-02: ELO + 3 race-level signals in one pool; top 6 by confidence.
  D-03: AngleCandidate is a Pydantic BaseModel (in-memory only; no SQLite).
  D-05: Top 2 per ELO signal_type cap; non-ELO not capped.
  D-06: Novelty filter: suppress (driver_id, signal_type) in prior 2 rounds.
  D-07/D-08: DNF cross-check only for slump/surprise_under via anthropic SDK.
  D-09: DNF results cached in self._dnf_cache per instance.
  D-10/D-11: Data gate raises DataNotReadyError before any signal computation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import anthropic
from pydantic import BaseModel

from pitlane_agent.commands.analyze.position_changes import generate_position_changes_chart
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.fetch.season_summary import get_season_summary
from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_elo.studio_api import detect_stories

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ELO signal types (from StorySignal.signal_type in pitlane_elo.stories.signals)
# Used to distinguish ELO signals (subject to top-2 cap) from non-ELO signals.
# ---------------------------------------------------------------------------
_ELO_SIGNAL_TYPES: frozenset[str] = frozenset(
    ["hot_streak", "slump", "surprise_over", "surprise_under", "teammate_shift"]
)

# Signal types that trigger a DNF cross-check (D-07).
_DNF_CHECK_TYPES: frozenset[str] = frozenset(["slump", "surprise_under"])

# Chart directory for position_changes command (requires workspace_dir).
_CHART_DIR: Path = Path.home() / ".pitlane" / "studio" / "charts"

# Conservative race-end estimate: races typically end by 16:00 UTC.
# Used for the 2-hour gate when session.date is a date-only string (Pitfall 1).
_RACE_END_UTC_HOUR: int = 16


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class AngleCandidate(BaseModel):
    """Ranked story angle candidate derived from ELO and race-level signals.

    Per D-03: Pydantic BaseModel (in-memory only; no corresponding SQLite table).
    """

    angle_id: str          # deterministic hash: sha256(f"{year}:{round}:{signal_type}:{driver_id}")[:16]
    name: str              # human-readable angle title
    signal_type: str       # hot_streak|slump|surprise_over|surprise_under|teammate_shift|
                           # wildness|standings_shift|lap1_chaos
    confidence: float      # 0–1 normalized signal magnitude
    data_rationale: str    # narrative string (StorySignal.narrative for ELO; built for non-ELO)
    dnf_suppressed: bool   # True if removed by DNF check (excluded from results; for logging)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class DataNotReadyError(Exception):
    """Raised by AngleService.get_angles() when session data is not yet reliable.

    Per D-11: FastAPI route returns this as HTTP 422 with structured JSON.

    Attributes:
        message: User-facing explanation suitable for the 422 response body.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _make_angle_id(year: int, round_num: int, signal_type: str, driver_id: str) -> str:
    """Deterministic 16-char hex ID for an angle candidate (D-03)."""
    hash_input = f"{year}:{round_num}:{signal_type}:{driver_id}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def _check_data_gate(year: int, round_num: int) -> None:
    """Gate check: raise DataNotReadyError if session data is unreliable.

    Per D-10:
      - Blocks if session is less than ~2 hours old (conservative estimate).
      - Blocks if total_laps < 90% of scheduled distance.

    Per Pitfall 1: session.date is a date-only string — construct a conservative
    race-end datetime estimate using _RACE_END_UTC_HOUR.

    Per Pitfall 4: session_info has no scheduled_laps field.
    Use get_season_summary() races[round].total_laps as the scheduled proxy.
    Fallback: derive from 305 km FIA standard / circuit_length_km.
    Final fallback: 58 laps (F1 average).
    """
    if not isinstance(year, int) or not isinstance(round_num, int):
        raise TypeError(
            f"year and round_num must be int, got {type(year).__name__} and {type(round_num).__name__}"
        )
    if year < 2023:
        raise ValueError(f"year {year} predates supported data range (2023+)")
    if round_num < 1 or round_num > 30:
        raise ValueError(f"round_num {round_num} out of valid range 1–30")
    info = get_session_info(year, str(round_num), "R")

    # --- Gate 1: session age < 2 hours ---
    session_date_str: str | None = info.get("date")
    if session_date_str:
        try:
            session_date = date.fromisoformat(session_date_str)
            # Conservative race-end: session_date at _RACE_END_UTC_HOUR UTC.
            # If race started at ~14:00 UTC and ran 1h30m, it ended by 16:00 UTC.
            race_end_estimate = datetime(
                session_date.year,
                session_date.month,
                session_date.day,
                _RACE_END_UTC_HOUR,
                0,
                tzinfo=UTC,
            )
            two_hours_after = race_end_estimate + timedelta(hours=2)
            if datetime.now(UTC) < two_hours_after:
                raise DataNotReadyError(
                    f"Race data for {year} R{round_num} is less than 2 hours old. "
                    "Please wait before loading angle candidates."
                )
        except ValueError:
            logger.warning("Could not parse session date %r — skipping age gate", session_date_str)

    # --- Gate 2: incomplete lap count ---
    actual_laps: int | None = info.get("total_laps")
    if actual_laps is not None:
        # Determine scheduled laps (Pitfall 4 resolution):
        # Try season_summary first; fall back to FIA 305km / circuit_length_km; then 58.
        scheduled_laps = _get_scheduled_laps(year, round_num, info)
        threshold = int(scheduled_laps * 0.90)
        if actual_laps < threshold:
            raise DataNotReadyError(
                f"Race at {year} R{round_num} appears incomplete: "
                f"{actual_laps} laps completed, expected at least {threshold} "
                f"(90% of {scheduled_laps} scheduled). Data may be from a red-flagged race."
            )


def _get_scheduled_laps(year: int, round_num: int, session_info: dict) -> int:
    """Derive expected lap count for the gate check (Pitfall 4 resolution)."""
    try:
        summary = get_season_summary(year)
        race = next(
            (r for r in summary.get("races", []) if r.get("round") == round_num),
            None,
        )
        if race and race.get("total_laps"):
            return int(race["total_laps"])
    except Exception:
        logger.debug("get_season_summary failed — using FIA 305km fallback")

    # FIA 305km standard fallback
    circuit_km: float | None = session_info.get("circuit_length_km")
    if circuit_km and circuit_km > 0:
        return round(305 / circuit_km)

    return 58  # F1 average fallback


# ---------------------------------------------------------------------------
# AngleService
# ---------------------------------------------------------------------------


class AngleService:
    """Detects and ranks story angle candidates for a completed race.

    Pipeline order (D-10, D-09, RESEARCH.md critical findings):
      1. Data gate check (raises DataNotReadyError if blocked)
      2. ELO signals via detect_stories()
      3. Non-ELO signals (wildness, standings shift, lap-1 chaos)
      4. ELO top-2-per-type cap (D-05)
      5. Novelty filter (D-06)
      6. DNF cross-check on slump/surprise_under (D-07/D-08)
      7. Sort by confidence; return top 4–6 (D-02)
    """

    def __init__(self) -> None:
        # DNF check cache: (year, round, driver_id) -> bool (D-09)
        self._dnf_cache: dict[tuple[int, int, str], bool] = {}
        # Signal cache: (year, round) -> list[StorySignal]
        # Avoids triple DuckDB scan for novelty filter (Pitfall 5)
        self._signal_cache: dict[tuple[int, int], list] = {}
        # Ensure chart dir exists for position_changes signal
        _CHART_DIR.mkdir(parents=True, exist_ok=True)

    def get_angles(self, year: int, round_num: int) -> list[AngleCandidate]:
        """Run the full pipeline; raises DataNotReadyError if gate blocks.

        Returns:
            4–6 ranked AngleCandidate instances, sorted by confidence descending.
            Minimum 4 returned; maximum 6 (per D-02).

        Raises:
            DataNotReadyError: If session data is less than 2 hours old or
                lap count is below 90% of scheduled distance.
        """
        # Step 1: Gate check (FIRST — before any expensive computation)
        _check_data_gate(year, round_num)

        # Step 2: ELO signals
        elo_candidates, driver_id_map = self._get_elo_candidates(year, round_num)

        # Step 3: Non-ELO signals
        non_elo_candidates, non_elo_driver_ids = self._get_non_elo_candidates(year, round_num)
        driver_id_map.update(non_elo_driver_ids)

        # Step 4: ELO cap (top 2 per ELO signal_type)
        capped_elo = self._apply_elo_type_cap(elo_candidates)

        # Merge all candidates
        all_candidates = capped_elo + non_elo_candidates

        # Step 5: Novelty filter
        filtered = self._apply_novelty_filter(all_candidates, year, round_num, driver_id_map)

        # Step 6: DNF cross-check (slump/surprise_under only)
        # Get race name for web search query
        race_name = self._get_race_name(year, round_num)
        checked = self._apply_dnf_filter(filtered, year, round_num, race_name, driver_id_map)

        # Step 7: Sort by confidence desc; return top 4–6
        checked.sort(key=lambda c: c.confidence, reverse=True)
        result = checked[:6]

        if len(result) < 4:
            # Not enough candidates after filtering — return what we have with a warning
            logger.warning(
                "get_angles() produced only %d candidates for %d R%d (expected 4–6)",
                len(result), year, round_num,
            )
        return result

    def _get_elo_candidates(
        self, year: int, round_num: int
    ) -> tuple[list[AngleCandidate], dict[str, str]]:
        """Convert ELO StorySignals to AngleCandidate instances.

        Returns:
            (candidates, driver_id_map) where driver_id_map maps angle_id -> driver_id.
        """
        signals = self._get_signals_cached(year, round_num)
        candidates: list[AngleCandidate] = []
        driver_id_map: dict[str, str] = {}

        for signal in signals:
            confidence = min(abs(signal.value) / signal.threshold, 1.0) if signal.threshold else 0.0
            angle_id = _make_angle_id(year, round_num, signal.signal_type, signal.driver_id)
            candidate = AngleCandidate(
                angle_id=angle_id,
                name=signal.narrative,
                signal_type=signal.signal_type,
                confidence=confidence,
                data_rationale=signal.narrative,
                dnf_suppressed=False,
            )
            candidates.append(candidate)
            driver_id_map[angle_id] = signal.driver_id

        return candidates, driver_id_map

    def _get_non_elo_candidates(
        self, year: int, round_num: int
    ) -> tuple[list[AngleCandidate], dict[str, str]]:
        """Build AngleCandidate instances from wildness, standings shift, and lap-1 chaos.

        Returns:
            (candidates, driver_id_map). Non-ELO signals use driver_id="race"
            (wildness, lap1_chaos) or actual driver_id (standings_shift).
        """
        candidates: list[AngleCandidate] = []
        driver_id_map: dict[str, str] = {}

        # --- Wildness signal ---
        wildness_candidate = self._get_wildness_candidate(year, round_num)
        if wildness_candidate:
            candidates.append(wildness_candidate)
            driver_id_map[wildness_candidate.angle_id] = "race"

        # --- Championship standings shift ---
        standings_candidates, standings_driver_ids = self._get_standings_shift_candidates(year, round_num)
        candidates.extend(standings_candidates)
        driver_id_map.update(standings_driver_ids)

        # --- Lap-1 chaos signal ---
        lap1_candidate = self._get_lap1_chaos_candidate(year, round_num)
        if lap1_candidate:
            candidates.append(lap1_candidate)
            driver_id_map[lap1_candidate.angle_id] = "race"

        return candidates, driver_id_map

    def _get_wildness_candidate(self, year: int, round_num: int) -> AngleCandidate | None:
        """Build wildness AngleCandidate from season_summary wildness_score (D-01)."""
        try:
            summary = get_season_summary(year)
            race = next(
                (r for r in summary.get("races", []) if r.get("round") == round_num),
                None,
            )
            if race is None:
                return None
            wildness: float = race.get("wildness_score", 0.0)
            if wildness <= 0:
                return None

            race_summary = race.get("race_summary", {})
            safety_cars = race_summary.get("num_safety_cars", "")
            overtakes = race_summary.get("total_overtakes", "")
            rationale_parts = [f"Race wildness score {wildness:.2f}"]
            if safety_cars != "":
                rationale_parts.append(f"{safety_cars} safety car(s)")
            if overtakes != "":
                rationale_parts.append(f"{overtakes} overtakes")
            data_rationale = " — ".join(rationale_parts)

            angle_id = _make_angle_id(year, round_num, "wildness", "race")
            return AngleCandidate(
                angle_id=angle_id,
                name=f"Chaotic race — wildness score {wildness:.2f}",
                signal_type="wildness",
                confidence=wildness,  # already 0–1 normalized (season_summary.py)
                data_rationale=data_rationale,
                dnf_suppressed=False,
            )
        except Exception:
            logger.debug("Wildness signal unavailable for %d R%d", year, round_num)
            return None

    def _get_standings_shift_candidates(
        self, year: int, round_num: int
    ) -> tuple[list[AngleCandidate], dict[str, str]]:
        """Build standings shift AngleCandidates (D-01).

        Computes point delta per driver between round and round-1.
        Normalizes by max delta in field. Returns top gainer.
        """
        if round_num <= 1:
            return [], {}
        try:
            current = get_driver_standings(year, round_num)
            prior = get_driver_standings(year, round_num - 1)
        except Exception:
            logger.debug("Standings data unavailable for %d R%d", year, round_num)
            return [], {}

        current_pts = {s["driver_id"]: s.get("points", 0) for s in current.get("standings", [])}
        prior_pts = {s["driver_id"]: s.get("points", 0) for s in prior.get("standings", [])}

        deltas: dict[str, float] = {
            d: current_pts.get(d, 0) - prior_pts.get(d, 0)
            for d in current_pts
        }
        if not deltas:
            return [], {}

        max_abs_delta = max(abs(v) for v in deltas.values()) or 1.0
        candidates: list[AngleCandidate] = []
        driver_id_map: dict[str, str] = {}

        # Top gainer — largest positive delta
        top_gainer = max(deltas, key=lambda d: deltas[d])
        gainer_delta = deltas[top_gainer]
        if gainer_delta > 0:
            confidence = min(abs(gainer_delta) / max_abs_delta, 1.0)
            angle_id = _make_angle_id(year, round_num, "standings_shift", top_gainer)
            candidates.append(AngleCandidate(
                angle_id=angle_id,
                name=f"{top_gainer.capitalize()} gained {gainer_delta:.0f} championship points",
                signal_type="standings_shift",
                confidence=confidence,
                data_rationale=(
                    f"{top_gainer.capitalize()} gained {gainer_delta:.0f} points this race, "
                    f"the largest single-race gain in the field"
                ),
                dnf_suppressed=False,
            ))
            driver_id_map[angle_id] = top_gainer

        return candidates, driver_id_map

    def _get_lap1_chaos_candidate(self, year: int, round_num: int) -> AngleCandidate | None:
        """Build lap-1 chaos AngleCandidate from position changes (D-01).

        Per Pitfall 3: position_changes command covers full race; confidence is
        normalized by total position changes (proxy for chaos). workspace_dir
        must be supplied to avoid TypeError at line 201.
        """
        try:
            result = generate_position_changes_chart(
                year, str(round_num), "R", workspace_dir=_CHART_DIR
            )
            stats = result.get("statistics", {})
            total_changes = stats.get("total_position_changes", 0)
            if total_changes == 0:
                return None
            # Normalize: 20 drivers × ~57 laps = theoretical max ~1000+ changes.
            # Use 60 as a practical "high chaos" reference (3 changes per driver).
            confidence = min(total_changes / 60.0, 1.0)
            angle_id = _make_angle_id(year, round_num, "lap1_chaos", "race")
            return AngleCandidate(
                angle_id=angle_id,
                name=f"Race chaos — {total_changes} position changes across the race",
                signal_type="lap1_chaos",
                confidence=confidence,
                data_rationale=(
                    f"{total_changes} position changes recorded — "
                    f"{'high' if total_changes > 40 else 'moderate'} race chaos"
                ),
                dnf_suppressed=False,
            )
        except Exception:
            logger.debug("Lap-1 chaos signal unavailable for %d R%d", year, round_num)
            return None

    def _apply_elo_type_cap(self, candidates: list[AngleCandidate]) -> list[AngleCandidate]:
        """Keep at most 2 candidates per ELO signal_type (D-05).

        Non-ELO signals (wildness, standings_shift, lap1_chaos) pass through uncapped.
        Within each ELO type, top 2 by confidence are kept.
        """
        elo_by_type: dict[str, list[AngleCandidate]] = defaultdict(list)
        non_elo: list[AngleCandidate] = []

        for candidate in candidates:
            if candidate.signal_type in _ELO_SIGNAL_TYPES:
                elo_by_type[candidate.signal_type].append(candidate)
            else:
                non_elo.append(candidate)

        capped: list[AngleCandidate] = []
        for signal_type, type_candidates in elo_by_type.items():
            type_candidates.sort(key=lambda c: c.confidence, reverse=True)
            capped.extend(type_candidates[:2])

        return capped + non_elo

    def _get_signals_cached(self, year: int, round_num: int) -> list:
        """Return detect_stories() result, using instance cache to avoid triple DuckDB scan."""
        key = (year, round_num)
        if key not in self._signal_cache:
            self._signal_cache[key] = detect_stories(year, round_num)
        return self._signal_cache[key]

    def _apply_novelty_filter(
        self,
        candidates: list[AngleCandidate],
        year: int,
        round_num: int,
        driver_id_map: dict[str, str],
    ) -> list[AngleCandidate]:
        """Suppress candidates whose (driver_id, signal_type) appeared in prior 2 rounds (D-06).

        Per D-06: recomputes detect_stories() for (year, round-1) and (year, round-2).
        Uses instance signal cache to avoid triple DuckDB scan (Pitfall 5).
        """
        prior_pairs: set[tuple[str, str]] = set()
        for prior_round in [round_num - 1, round_num - 2]:
            if prior_round < 1:
                continue
            try:
                prior_signals = self._get_signals_cached(year, prior_round)
                for s in prior_signals:
                    prior_pairs.add((s.driver_id, s.signal_type))
            except Exception:
                logger.debug("Novelty filter: could not load signals for %d R%d", year, prior_round)

        result: list[AngleCandidate] = []
        for candidate in candidates:
            driver_id = driver_id_map.get(candidate.angle_id, "race")
            if (driver_id, candidate.signal_type) in prior_pairs:
                logger.debug(
                    "Novelty filter suppressed: driver=%s signal_type=%s",
                    driver_id, candidate.signal_type,
                )
            else:
                result.append(candidate)
        return result

    def _apply_dnf_filter(
        self,
        candidates: list[AngleCandidate],
        year: int,
        round_num: int,
        race_name: str,
        driver_id_map: dict[str, str],
    ) -> list[AngleCandidate]:
        """Suppress slump/surprise_under candidates for confirmed DNF drivers (D-07).

        Only slump and surprise_under signal types are checked (D-07).
        Per ANGL-03: FastF1 DNF classification is NOT used.
        """
        result: list[AngleCandidate] = []
        for candidate in candidates:
            if candidate.signal_type not in _DNF_CHECK_TYPES:
                result.append(candidate)
                continue
            driver_id = driver_id_map.get(candidate.angle_id, "")
            if not driver_id or driver_id == "race":
                result.append(candidate)
                continue
            dnf = self._check_dnf(year, round_num, driver_id, race_name)
            if dnf:
                logger.info(
                    "DNF filter suppressed: driver=%s signal_type=%s (confirmed DNF)",
                    driver_id, candidate.signal_type,
                )
                # Excluded from results (suppressed candidates are not returned)
            else:
                result.append(candidate)
        return result

    def _check_dnf(self, year: int, round_num: int, driver_id: str, race_name: str) -> bool:
        """Check via web search whether the driver DNF'd in the given race.

        Tries tool type "web_search_20250305" first; on BadRequestError falls back
        to "web_search".  On AuthenticationError (no API key) returns False
        conservatively.  All other exceptions default to False with a logged trace.

        Per Pitfall 6: web search tool type string may vary by SDK version.
        Initial attempt: "web_search_20250305". On 400 error, fall back to "web_search".
        """
        cache_key = (year, round_num, driver_id)
        if cache_key in self._dnf_cache:
            return self._dnf_cache[cache_key]

        result = False
        client = anthropic.Anthropic()
        prompt = (
            f'Did {driver_id} DNF or retire in the {race_name} {year} Formula 1 race? '
            f'Respond with ONLY valid JSON: {{"dnf": true, "reason": "brief"}} '
            f'or {{"dnf": false, "reason": "finished"}}'
        )
        tool_types = ["web_search_20250305", "web_search"]
        for tool_type in tool_types:
            try:
                response = client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=150,
                    tools=[{"type": tool_type, "name": "web_search"}],
                    messages=[{"role": "user", "content": prompt}],
                )
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        text = block.text.strip()
                        start = text.find("{")
                        end = text.rfind("}") + 1
                        if start >= 0 and end > start:
                            parsed = json.loads(text[start:end])
                            result = bool(parsed.get("dnf", False))
                        break
                break  # success — stop trying tool types
            except anthropic.BadRequestError:
                logger.warning("web_search tool type %r rejected — trying fallback", tool_type)
                continue
            except anthropic.AuthenticationError:
                logger.warning(
                    "ANTHROPIC_API_KEY not set — skipping DNF check for %s %d R%d",
                    driver_id, year, round_num,
                )
                break
            except Exception:
                logger.exception(
                    "DNF check failed for %s %d R%d — defaulting to False",
                    driver_id, year, round_num,
                )
                break

        self._dnf_cache[cache_key] = result
        return result

    def _get_race_name(self, year: int, round_num: int) -> str:
        """Get a human-readable race name for the DNF web search query."""
        try:
            info = get_session_info(year, str(round_num), "R")
            return info.get("event_name") or info.get("circuit_name") or f"Round {round_num}"
        except Exception:
            return f"Round {round_num}"


__all__ = ["AngleCandidate", "AngleService", "DataNotReadyError"]
