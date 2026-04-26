"""Story angle detection signals.

Translates ELO rating trajectories into narrative triggers:
- Trend detection (short-term momentum, long-term trajectory)
- Outlier detection (surprise scores, probability uplift)
- Car/driver performance decoupling
- Teammate battle tracking

See docs/F1_ELO_Story_Detection_System_Design.md §7 for thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from pitlane_elo.data import RaceEntry, get_data_dir, get_race_entries
from pitlane_elo.snapshots import EloSnapshot, get_race_snapshot

# ---------------------------------------------------------------------------
# Thresholds — from design doc §7
# ---------------------------------------------------------------------------

_TREND_3_HOT_THRESHOLD = 0.5  # ΔR̂_3race > 0.5 → hot streak
_TREND_3_COLD_THRESHOLD = -0.5  # ΔR̂_3race < -0.5 → slump
_SURPRISE_THRESHOLD = 2.0  # |SurpriseScore| > 2.0 → story candidate
_TEAMMATE_DELTA_RACES = 3  # Consecutive races confirming teammate shift
_TEAMMATE_GAP_MIN = 0.1  # Minimum ELO gap to flag a consistent lead
_TREND_TOP_N = 3  # Top/bottom N drivers flagged for momentum

_SNAPSHOT_SELECT = (
    "year, round, session_type, driver_id, pre_race_rating, pre_race_k, "
    "win_probability, podium_probability, finish_position, dnf_category"
)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class StorySignal:
    """A detected narrative signal from ELO data."""

    signal_type: str
    """hot_streak | slump | surprise_over | surprise_under | teammate_shift"""
    driver_id: str
    year: int
    round: int
    value: float
    """Raw signal value — ΔR̂ for trend, SurpriseScore for outlier, gap for teammate."""
    threshold: float
    """The threshold value that was crossed."""
    narrative: str
    """Human-readable story angle suitable for agent prompting."""
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type,
            "driver_id": self.driver_id,
            "year": self.year,
            "round": self.round,
            "value": round(self.value, 4),
            "threshold": self.threshold,
            "narrative": self.narrative,
            "context": self.context,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rows_to_snapshots(rows: list[tuple], columns: list[str]) -> list[EloSnapshot]:
    result = []
    for row in rows:
        d = dict(zip(columns, row, strict=True))
        result.append(EloSnapshot(**d))
    return result


def _get_recent_snapshots(
    driver_id: str,
    before_year: int,
    before_round: int,
    n: int,
    *,
    session_type: str = "R",
    data_dir: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> list[EloSnapshot]:
    """Return up to N snapshots for driver_id in races strictly before (before_year, before_round).

    Results are ordered newest-first.
    """
    d = data_dir or get_data_dir()
    snapshots_dir = d / "elo_snapshots"
    if not snapshots_dir.exists() or not list(snapshots_dir.glob("*.parquet")):
        return []
    glob_pattern = str(snapshots_dir / "*.parquet").replace("'", "''")

    _con = con or duckdb.connect()
    _close = con is None
    try:
        cursor = _con.execute(
            f"SELECT {_SNAPSHOT_SELECT} FROM read_parquet('{glob_pattern}') "
            "WHERE driver_id = ? AND session_type = ? "
            "AND (year < ? OR (year = ? AND round < ?)) "
            "ORDER BY year DESC, round DESC "
            "LIMIT ?",
            [driver_id, session_type, before_year, before_year, before_round, n],
        )
        rows = cursor.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cursor.description]
    finally:
        if _close:
            _con.close()
    return _rows_to_snapshots(rows, columns)


def _expected_positions(snapshots: list[EloSnapshot]) -> dict[str, int]:
    """Map driver_id → expected finishing position by win-probability rank."""
    ranked = sorted(snapshots, key=lambda s: s.win_probability, reverse=True)
    return {s.driver_id: i + 1 for i, s in enumerate(ranked)}


def _sigma_position(k_factor: float) -> float:
    """Positional uncertainty as a function of k-factor.

    Higher k (less established rating) → wider band → harder to register a surprise.
    """
    return max(3.0, 3.0 + k_factor * 5.0)


# ---------------------------------------------------------------------------
# Signal detectors
# ---------------------------------------------------------------------------


def detect_trend_signals(
    race_snapshots: list[EloSnapshot],
    year: int,
    round_num: int,
    *,
    n: int = 3,
    session_type: str = "R",
    data_dir: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> list[StorySignal]:
    """Detect momentum: trailing N-race ΔR̂, flagging top/bottom N drivers."""
    current = {s.driver_id: s.pre_race_rating for s in race_snapshots}
    deltas: list[tuple[str, float]] = []

    _con = con or duckdb.connect()
    _close = con is None
    try:
        for driver_id, current_rating in current.items():
            history = _get_recent_snapshots(
                driver_id,
                year,
                round_num,
                n,
                session_type=session_type,
                data_dir=data_dir,
                con=_con,
            )
            if len(history) < n:
                continue
            oldest = history[n - 1]  # history is newest-first, oldest is index n-1
            deltas.append((driver_id, current_rating - oldest.pre_race_rating))
    finally:
        if _close:
            _con.close()

    if not deltas:
        return []

    deltas.sort(key=lambda x: x[1], reverse=True)
    signals: list[StorySignal] = []

    for driver_id, delta in deltas[:_TREND_TOP_N]:
        if delta > _TREND_3_HOT_THRESHOLD:
            signals.append(
                StorySignal(
                    signal_type="hot_streak",
                    driver_id=driver_id,
                    year=year,
                    round=round_num,
                    value=delta,
                    threshold=_TREND_3_HOT_THRESHOLD,
                    narrative=(
                        f"{driver_id} has gained {delta:+.3f} ELO over the last {n} races"
                        " — hottest momentum in the field"
                    ),
                    context={"lookback_races": n, "current_rating": round(current[driver_id], 4)},
                )
            )

    for driver_id, delta in deltas[-_TREND_TOP_N:]:
        if delta < _TREND_3_COLD_THRESHOLD:
            signals.append(
                StorySignal(
                    signal_type="slump",
                    driver_id=driver_id,
                    year=year,
                    round=round_num,
                    value=delta,
                    threshold=_TREND_3_COLD_THRESHOLD,
                    narrative=(
                        f"{driver_id} has lost {abs(delta):.3f} ELO over the last {n} races"
                        " — deepest slump in the field"
                    ),
                    context={"lookback_races": n, "current_rating": round(current[driver_id], 4)},
                )
            )

    return signals


def detect_surprise_signals(
    race_snapshots: list[EloSnapshot],
    year: int,
    round_num: int,
) -> list[StorySignal]:
    """Detect outlier results via SurpriseScore = (actual_pos − expected_pos) / σ."""
    if not race_snapshots:
        return []

    expected = _expected_positions(race_snapshots)
    signals: list[StorySignal] = []

    for snap in race_snapshots:
        if snap.finish_position is None:
            continue
        exp_pos = expected[snap.driver_id]
        sigma = _sigma_position(snap.pre_race_k)
        score = (snap.finish_position - exp_pos) / sigma

        if score < -_SURPRISE_THRESHOLD:
            signals.append(
                StorySignal(
                    signal_type="surprise_over",
                    driver_id=snap.driver_id,
                    year=year,
                    round=round_num,
                    value=score,
                    threshold=-_SURPRISE_THRESHOLD,
                    narrative=(
                        f"{snap.driver_id} massively overperformed: expected P{exp_pos},"
                        f" finished P{snap.finish_position} (SurpriseScore {score:.2f})"
                    ),
                    context={
                        "expected_position": exp_pos,
                        "actual_position": snap.finish_position,
                        "win_probability": round(snap.win_probability, 4),
                        "pre_race_rating": round(snap.pre_race_rating, 4),
                    },
                )
            )
        elif score > _SURPRISE_THRESHOLD:
            signals.append(
                StorySignal(
                    signal_type="surprise_under",
                    driver_id=snap.driver_id,
                    year=year,
                    round=round_num,
                    value=score,
                    threshold=_SURPRISE_THRESHOLD,
                    narrative=(
                        f"{snap.driver_id} massively underperformed: expected P{exp_pos},"
                        f" finished P{snap.finish_position} (SurpriseScore {score:.2f})"
                    ),
                    context={
                        "expected_position": exp_pos,
                        "actual_position": snap.finish_position,
                        "win_probability": round(snap.win_probability, 4),
                        "pre_race_rating": round(snap.pre_race_rating, 4),
                    },
                )
            )

    return signals


def detect_teammate_delta(
    race_snapshots: list[EloSnapshot],
    race_entries: list[RaceEntry],
    year: int,
    round_num: int,
    *,
    session_type: str = "R",
    data_dir: Path | None = None,
    lookback: int = _TEAMMATE_DELTA_RACES,
    con: duckdb.DuckDBPyConnection | None = None,
) -> list[StorySignal]:
    """Detect teammate battles via within-team ΔR̂ over recent races."""
    team_drivers: dict[str, list[str]] = {}
    for entry in race_entries:
        team = entry.get("team", "")
        driver = entry.get("driver_id", "")
        if team and driver and driver not in team_drivers.get(team, []):
            team_drivers.setdefault(team, []).append(driver)

    current = {s.driver_id: s.pre_race_rating for s in race_snapshots}
    signals: list[StorySignal] = []

    _con = con or duckdb.connect()
    _close = con is None
    try:
        for team, drivers in team_drivers.items():
            if len(drivers) < 2:
                continue
            a, b = drivers[0], drivers[1]
            if a not in current or b not in current:
                continue

            history_a = _get_recent_snapshots(
                a, year, round_num, lookback, session_type=session_type, data_dir=data_dir, con=_con
            )
            history_b = _get_recent_snapshots(
                b, year, round_num, lookback, session_type=session_type, data_dir=data_dir, con=_con
            )
            if not history_a or not history_b:
                continue

            a_by_race = {(s.year, s.round): s.pre_race_rating for s in history_a}
            b_by_race = {(s.year, s.round): s.pre_race_rating for s in history_b}
            common = sorted(set(a_by_race) & set(b_by_race), reverse=True)[:lookback]

            if len(common) < lookback:
                continue

            historical_deltas = [a_by_race[r] - b_by_race[r] for r in common]
            current_delta = current[a] - current[b]

            all_positive = all(d > 0 for d in historical_deltas)
            all_negative = all(d < 0 for d in historical_deltas)
            # Gap flipped relative to the historical trend
            gap_flipped = (current_delta > 0 and all_negative) or (current_delta < 0 and all_positive)

            if gap_flipped:
                leader, trailer = (a, b) if current_delta > 0 else (b, a)
                signals.append(
                    StorySignal(
                        signal_type="teammate_shift",
                        driver_id=leader,
                        year=year,
                        round=round_num,
                        value=abs(current_delta),
                        threshold=0.0,
                        narrative=(
                            f"{leader} has taken the upper hand over {trailer} at {team}"
                            f" — internal gap has reversed over the last {lookback} races"
                        ),
                        context={
                            "team": team,
                            "teammate": trailer,
                            "current_delta": round(current_delta, 4),
                            "historical_deltas": [round(d, 4) for d in historical_deltas],
                        },
                    )
                )
            elif (all_positive or all_negative) and abs(current_delta) > _TEAMMATE_GAP_MIN:
                leader, trailer = (a, b) if current_delta > 0 else (b, a)
                gap = abs(current_delta)
                signals.append(
                    StorySignal(
                        signal_type="teammate_shift",
                        driver_id=leader,
                        year=year,
                        round=round_num,
                        value=gap,
                        threshold=_TEAMMATE_GAP_MIN,
                        narrative=(
                            f"{leader} holds a consistent {gap:.3f} ELO advantage over {trailer}"
                            f" at {team} across {lookback} races"
                        ),
                        context={
                            "team": team,
                            "teammate": trailer,
                            "current_delta": round(current_delta, 4),
                            "historical_deltas": [round(d, 4) for d in historical_deltas],
                        },
                    )
                )
    finally:
        if _close:
            _con.close()

    return signals


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def detect_stories(
    year: int,
    round_num: int,
    *,
    session_type: str = "R",
    data_dir: Path | None = None,
    trend_lookback: int = 3,
) -> list[StorySignal]:
    """Run all story detectors for a race and return signals sorted by |value| desc.

    Requires ELO snapshots built via ``pitlane-elo snapshot``. Returns an empty
    list if no snapshots exist for the given race.
    """
    race_snapshots = get_race_snapshot(year, round_num, session_type=session_type, data_dir=data_dir)
    if not race_snapshots:
        return []

    year_entries = get_race_entries(year, data_dir=data_dir, session_type=session_type)
    race_entries: list[RaceEntry] = []
    if year_entries:
        race_entries = [e for e in year_entries if e.get("round") == round_num]

    signals: list[StorySignal] = []
    con = duckdb.connect()
    try:
        signals.extend(
            detect_trend_signals(
                race_snapshots,
                year,
                round_num,
                n=trend_lookback,
                session_type=session_type,
                data_dir=data_dir,
                con=con,
            )
        )
        signals.extend(detect_surprise_signals(race_snapshots, year, round_num))
        signals.extend(
            detect_teammate_delta(
                race_snapshots,
                race_entries,
                year,
                round_num,
                session_type=session_type,
                data_dir=data_dir,
                con=con,
            )
        )
    finally:
        con.close()

    signals.sort(key=lambda s: abs(s.value), reverse=True)
    return signals


__all__ = [
    "StorySignal",
    "detect_stories",
    "detect_surprise_signals",
    "detect_teammate_delta",
    "detect_trend_signals",
]
