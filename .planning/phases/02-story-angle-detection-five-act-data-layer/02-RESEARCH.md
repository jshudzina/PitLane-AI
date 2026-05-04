# Phase 2: Story Angle Detection + Five-Act Data Layer — Research

**Researched:** 2026-05-03
**Domain:** Python service layer — ELO signal aggregation, Anthropic SDK, FastF1 data access, Pydantic BaseModel
**Confidence:** HIGH (all critical findings verified directly from codebase source files)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Signal Sources (ANGL-01 — expanded)**
- D-01: `AngleService` ingests both ELO signals (`detect_stories()` from `pitlane_elo.studio_api`) AND three race-level signals: wildness score (from `season_summary.get_season_summary(year)`), championship standings shift (from `get_driver_standings(year, round)` vs `get_driver_standings(year, round-1)`), and lap-1 chaos (from `pitlane_agent.commands.analyze.position_changes`). ANGL-01 in REQUIREMENTS.md should be updated to reflect this expanded signal set.
- D-02: All signals compete together in a single pool; sorted by confidence (normalized 0–1), top 6 taken as candidates (minimum 4). No reserved ELO slots — non-ELO signals can surface if their magnitude warrants it.

**AngleCandidate Schema**
- D-03: `AngleService.get_angles(year, round)` returns `list[AngleCandidate]`. `AngleCandidate` is a new Pydantic `BaseModel` with fields: `angle_id: str`, `name: str`, `signal_type: str` (8 values), `confidence: float`, `data_rationale: str`, `dnf_suppressed: bool`.
- D-04: `data_rationale` is `StorySignal.narrative` for ELO signals; equivalent narrative string for non-ELO signals.

**Ranking and Filtering (ANGL-02)**
- D-05: Top 2 per ELO signal_type cap; non-ELO signals not capped (max 1 each by nature). Sort all candidates by `confidence` descending, take top 6 (minimum 4).
- D-06: Novelty filter: suppress if same `(driver_id, signal_type)` appeared in either of the two preceding rounds. Implementation: recompute `detect_stories()` for `(year, round-1)` and `(year, round-2)`.

**DNF Cross-Check (ANGL-03)**
- D-07: Only `slump` and `surprise_under` signal types trigger a DNF cross-check.
- D-08: Cross-check via targeted Claude API call using `anthropic` SDK (not claude-agent-sdk) with web search tool. Returns `{"dnf": true/false, "reason": "..."}`.
- D-09: In-memory cache per `AngleService` instance: `dict[(year, round, driver_id), bool]`.

**Data Completeness Gate (ANGL-04)**
- D-10: Gate blocks if session < 2 hours old OR lap count < 90% scheduled. Uses `get_session_info()` for session metadata.
- D-11: `get_angles()` raises `DataNotReadyError` with `message: str` attribute. FastAPI route returns 422 with structured JSON.

**Five-Act Mapper (ACT-01, ACT-02)**
- D-12: `ACT_CONFIG` is a module-level constant dict mapping acts 1–5 to command callables and act metadata.
- D-13: `FiveActMapper.fetch_act_data(year, round, act_number)` caches results in in-memory dict keyed by `(year, round, act_number)`.

### Claude's Discretion

- Exact command function signatures for non-ELO signals (position_changes, race_control) — follow the established pattern for calling pitlane-agent commands directly.
- Narrative string templates for non-ELO `AngleCandidate.data_rationale` — Claude picks reasonable phrasing.
- Model choice for DNF check API call — use a fast/cheap model (e.g., Haiku) since it's a binary classification task.

### Deferred Ideas (OUT OF SCOPE)

- Lap-1 chaos as a standalone ACT-02 data source vs. signal source: it plays both roles (angle signal in ANGL-01 and act 2 data in ACT-01). Both uses are in scope; deconfliction is an implementation detail.
- Five-act SQLite persistence — in-memory cache; revisit in v2 if restart latency becomes an issue.
- Additional non-ELO signals (e.g., fastest lap shifts, team constructor battle) — not discussed.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANGL-01 | User can load any completed race and receive 4–6 story angle candidates derived from ELO signals AND three race-level signals (expanded per D-01) | `detect_stories()` signature verified; `get_season_summary()`, `get_driver_standings()`, and `generate_position_changes_chart()` signatures verified |
| ANGL-02 | Angle candidates are ranked by field-relative significance (top 2 per ELO signal type) and filtered for novelty (suppress same driver + same signal type if it appeared in the prior 2 races) | `detect_stories()` recomputation for prior rounds verified as feasible; `StorySignal` fields `driver_id` and `signal_type` confirmed available |
| ANGL-03 | Driver crisis angles (slump, underperformance) cross-checked against web search for DNF/retirement events before surfacing | `anthropic` SDK not yet in pitlane-studio deps — must be added; `StorySignal.context.dnf_category` field exists but is unreliable (per known issue) |
| ANGL-04 | Angle generation blocked with user-facing message if session < 2 hours old or lap count is incomplete | `SessionInfo.total_laps` and `SessionInfo.date` confirmed in `get_session_info()` return; `session.date` is a date-only string (not datetime) — see Pitfall 1 |
| ACT-01 | Static ACT_CONFIG dict mapping acts 1–5 to pitlane-agent command callables | All target functions verified; four of five act-data commands are chart-generating and require `workspace_dir: Path` — see Pitfall 2 |
| ACT-02 | System fetches and caches act-specific data on race load; data available as grounding context | In-memory dict cache on FiveActMapper instance confirmed as the implementation approach; workspace_dir strategy documented |
</phase_requirements>

---

## Summary

Phase 2 builds the pure-Python service layer that Phase 3's UI will consume. It introduces two new modules under `packages/pitlane-studio/src/pitlane_studio/services/`: `angles.py` (containing `AngleService`, `AngleCandidate`, and `DataNotReadyError`) and `five_act.py` (containing `FiveActMapper` and the module-level `ACT_CONFIG` dict).

All signal sources for `AngleService` have been verified against the actual source code. The `StorySignal` dataclass is confirmed to have the fields needed for mapping to `AngleCandidate`. The `detect_stories()` function is the sole public entry point via `pitlane_elo.studio_api` and returns a `list[StorySignal]`. Non-ELO signals come from three pitlane-agent commands that require no `workspace_dir` argument.

Two architectural issues require explicit planning attention. First, the `get_session_info()` function returns `date` as a date-only string (e.g., `"2026-03-16"`) and `total_laps` as a count of laps completed — it does not return a session end timestamp. The data gate logic must derive session age using the race date plus the expected race duration (approximately 2 hours), not a direct end-time comparison. Second, the four chart-generating commands used in `ACT_CONFIG` (tyre strategy, lap times, qualifying results, position changes) require a `workspace_dir: Path` argument with no safe default — `FiveActMapper.fetch_act_data()` must supply a platform-appropriate temporary directory (e.g., `~/.pitlane/studio/charts/`).

The `anthropic` SDK is not installed in pitlane-studio and must be added as a direct dependency via `uv add --directory packages/pitlane-studio anthropic`.

**Primary recommendation:** Implement `AngleService` and `FiveActMapper` as specified in CONTEXT.md decisions D-01 through D-13, adding `anthropic` as a direct pitlane-studio dependency and supplying `~/.pitlane/studio/charts/` as the workspace_dir for chart-generating ACT_CONFIG commands.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ELO signal detection | pitlane-elo (studio_api) | — | Already implemented; AngleService is a consumer, not owner |
| Race-level signal computation | pitlane-agent commands layer | pitlane-studio (AngleService wraps calls) | FastF1 access lives in pitlane-agent; studio only normalizes results |
| Signal ranking and deduplication | pitlane-studio (AngleService) | — | Business logic for story angle selection belongs to the studio layer |
| DNF cross-check (web search + LLM) | pitlane-studio (AngleService) | anthropic SDK | Binary classification step in angle filtering pipeline |
| Five-act data fetching | pitlane-studio (FiveActMapper) | pitlane-agent commands layer | Dispatch logic in studio; data access in agent |
| Data completeness gate | pitlane-studio (AngleService) | pitlane-agent (session_info) | Gate decision in studio; raw metadata from agent |
| Chart output storage | Filesystem (~/.pitlane/studio/charts/) | — | Chart commands write PNGs; studio must own the path |

---

## Standard Stack

### Core (verified from source files)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0 (already in pyproject.toml) | `AngleCandidate` BaseModel schema | Matches Phase 1 pattern for `ArticleRecord` [VERIFIED: pyproject.toml] |
| anthropic | >=0.92.0 (latest on PyPI) | DNF cross-check via Claude API with web search tool | Direct SDK call (not claude-agent-sdk) per D-08; must be added to pitlane-studio deps [VERIFIED: pypi.org] |
| pitlane-elo | workspace | `detect_stories()` ELO signals | Already declared in pitlane-studio pyproject.toml [VERIFIED: pyproject.toml] |
| pitlane-agent | workspace | All pitlane-agent command imports | Already declared in pitlane-studio pyproject.toml [VERIFIED: pyproject.toml] |
| hashlib (stdlib) | stdlib | Deterministic `angle_id` hash per D-03 | Standard library; no install needed |
| datetime (stdlib) | stdlib | UTC comparison for 2-hour data gate | Standard library; `datetime.now(UTC)` pattern used in `article_store.py` |

**Installation command (one new dep):**
```bash
uv add --directory packages/pitlane-studio anthropic
```

---

## Architecture Patterns

### System Architecture Diagram

```
                    AngleService.get_angles(year, round)
                               │
                    ┌──────────▼──────────┐
                    │  DataNotReadyError  │◄── session age < 2h
                    │  gate check         │◄── total_laps < 90% scheduled
                    └──────────┬──────────┘
                               │ (gate passes)
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    detect_stories()    get_season_summary()  get_driver_standings()×2
    (ELO signals)       (wildness score)      (standings shift)
    pitlane_elo.         pitlane_agent         pitlane_agent
    studio_api           commands.fetch        commands.fetch
              │                │                ▼
              │                │        position_changes stats
              │                │        (lap-1 chaos signal)
              └────────────────┴────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Single signal pool  │
                    │  (all signals merged)│
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  ELO cap: top 2 per │
                    │  ELO signal_type    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Novelty filter:     │
                    │  suppress if same    │
                    │  (driver, type) in   │◄── detect_stories(round-1)
                    │  prior 2 rounds     │◄── detect_stories(round-2)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  DNF cross-check:   │
                    │  slump/surprise_    │◄── anthropic SDK (Haiku)
                    │  under only         │    web_search_tool
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Sort by confidence │
                    │  take top 4–6       │
                    └──────────┬──────────┘
                               ▼
                    list[AngleCandidate]


FiveActMapper.fetch_act_data(year, round, act_number)
                               │
              ┌────────────────▼────────────────┐
              │        ACT_CONFIG lookup          │
              └────────────────┬────────────────┘
                               │
          ┌────────┬───────────┼───────────┬────────┐
          ▼        ▼           ▼           ▼        ▼
        Act 1    Act 2       Act 3       Act 4    Act 5
    session_info race_control  tyre_    lap_times  driver_
    qualifying_  position_     strategy race_      standings
    results      changes*      race_    control*
                               control*

        * requires workspace_dir → ~/.pitlane/studio/charts/
```

### Recommended Project Structure

```
packages/pitlane-studio/src/pitlane_studio/
├── services/                        # New in Phase 2
│   ├── __init__.py
│   ├── angles.py                    # AngleService, AngleCandidate, DataNotReadyError
│   └── five_act.py                  # FiveActMapper, ACT_CONFIG
├── store/
│   └── article_store.py             # Phase 1 — reference pattern
├── filters.py                       # Phase 1
├── app.py                           # Phase 1 — Phase 3 will add routes
└── cli.py                           # Phase 1
```

### Pattern 1: AngleCandidate as Pydantic BaseModel

Follows the exact same pattern as `ArticleRecord` in `article_store.py`. No SQLAlchemy table is needed — `AngleCandidate` is an in-memory data object only.

```python
# Source: packages/pitlane-studio/src/pitlane_studio/store/article_store.py (verified)
from __future__ import annotations
import hashlib
from pydantic import BaseModel

class AngleCandidate(BaseModel):
    """Ranked story angle candidate derived from ELO and race-level signals."""

    angle_id: str            # deterministic hash of (year, round, signal_type, driver_id)
    name: str                # human-readable angle title
    signal_type: str         # hot_streak|slump|surprise_over|surprise_under|teammate_shift|
                             # wildness|standings_shift|lap1_chaos
    confidence: float        # 0–1 normalized signal magnitude
    data_rationale: str      # narrative string (StorySignal.narrative for ELO; built for non-ELO)
    dnf_suppressed: bool     # True if removed by DNF check (excluded from results; for logging)
```

### Pattern 2: StorySignal Fields (ELO signals)

`StorySignal` (verified from `pitlane_elo.stories.signals`):

| Field | Type | Notes |
|-------|------|-------|
| `signal_type` | `str` | `hot_streak`, `slump`, `surprise_over`, `surprise_under`, `teammate_shift` |
| `driver_id` | `str` | Ergast driverId slug (e.g., `"hamilton"`) |
| `year` | `int` | |
| `round` | `int` | |
| `value` | `float` | Raw signal magnitude (ΔR̂ for trend, SurpriseScore for outlier, gap for teammate) |
| `threshold` | `float` | The threshold crossed |
| `narrative` | `str` | Ready-to-use story angle string; maps directly to `AngleCandidate.data_rationale` |
| `context` | `dict` | Extra data (e.g., lookback_races, current_rating, expected/actual positions) |

ELO confidence normalization: `min(abs(signal.value) / signal.threshold, 1.0)` — uses the threshold already stored on the signal.

### Pattern 3: Non-ELO Signal Sources

**Wildness signal** — `get_season_summary(year: int) -> SeasonSummary`:
- Returns `SeasonSummary["races"]` — a `list[SeasonRaceSummary]`, sorted by `wildness_score` descending.
- Each entry has `SeasonRaceSummary["round"]: int` and `SeasonRaceSummary["wildness_score"]: float` (0–1 already; normalized during computation).
- To get the wildness score for `round`: filter `races` list for matching round number.
- Signal uses `driver_id = "race"` (no driver; race-level angle).
- Confidence = `wildness_score` directly (already 0–1).
- No `workspace_dir` required. [VERIFIED: season_summary.py]

**Championship standings shift** — `get_driver_standings(year: int, round_number: int | None = None) -> dict`:
- Returns `{"year", "round", "total_standings", "filters", "standings": list[dict]}`.
- Each standings entry: `{"position", "points", "wins", "driver_id", "driver_code", "given_name", "family_name", ...}`.
- To compute shift: call for `round` and `round-1`; compute point delta per driver; normalize by largest delta in field.
- Signal uses `driver_id` from standings (Ergast driverId format).
- No `workspace_dir` required. [VERIFIED: driver_standings.py + ergast.py]

**Lap-1 chaos signal** — `generate_position_changes_chart(year, gp, session_type, ...) -> dict`:
- `gp` accepts `int` (round number) directly — `fastf1.get_session(year, gp, ...)` signature is `gp: str | int`.
- Returns `{"statistics": {"total_position_changes", "total_overtakes", "average_volatility", "drivers": [...]}}`.
- For lap-1 chaos, the key metric is `total_position_changes` from lap 0 (grid) to lap 1; but the `statistics` dict covers the full race. See Pitfall 3 — there is no built-in "lap 1 only" filter.
- Requires `workspace_dir: Path` — must provide `Path.home() / ".pitlane" / "studio" / "charts"`.
- Confidence: normalize `total_position_changes` at lap 1 by grid size (20 drivers = max 20 changes).
- Signal uses `driver_id = "race"` (race-level angle). [VERIFIED: position_changes.py]

### Pattern 4: Data Completeness Gate

`get_session_info(year, gp, session_type) -> SessionInfo` returns:
- `SessionInfo["date"]: str | None` — date-only string: `"2026-03-16"` (NO time component).
- `SessionInfo["total_laps"]: int | None` — actual laps completed.

**Critical:** `date` is date-only, not a session end timestamp. The 2-hour gate must be implemented as:
```python
from datetime import UTC, date, datetime, timedelta

session_date = date.fromisoformat(info["date"])  # "2026-03-16" → date object
# F1 races average 1h30m; add 2h buffer from assumed race start at session_date + 14:00 UTC
# OR: use a conservative "assume race started at noon UTC on session_date"
# Simple safe approach: block if session_date == today (race day or same day)
session_datetime_estimate = datetime(
    session_date.year, session_date.month, session_date.day, 16, 0, tzinfo=UTC
)  # 16:00 UTC is a conservative race-end estimate
```

**Scheduled laps:** `get_session_info()` returns `total_laps` (actual completed) but NOT scheduled laps. The scheduled distance is available from `get_season_summary(year)["races"]` where each entry has `race_summary["total_laps"]`. Alternative: hardcode 305 km / circuit length. See Pitfall 4.

### Pattern 5: ACT_CONFIG Module-Level Dict

```python
# Source: CONTEXT.md D-12 (locked design decision)
# All imports at top of file per CLAUDE.md

from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_agent.commands.fetch.race_control import get_race_control_messages
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.analyze.tyre_strategy import generate_tyre_strategy_chart
from pitlane_agent.commands.analyze.lap_times import generate_lap_times_chart
from pitlane_agent.commands.analyze.qualifying_results import generate_qualifying_results_chart
from pitlane_agent.commands.analyze.position_changes import generate_position_changes_chart

ACT_CONFIG: dict[int, dict] = {
    1: {
        "label": "Qualifying / Grid",
        "commands": [get_session_info, generate_qualifying_results_chart],
    },
    2: {
        "label": "Lap 1 Chaos",
        "commands": [get_race_control_messages, generate_position_changes_chart],
    },
    3: {
        "label": "Pit Window",
        "commands": [generate_tyre_strategy_chart, get_race_control_messages],
    },
    4: {
        "label": "Final Stint",
        "commands": [generate_lap_times_chart, generate_position_changes_chart],
    },
    5: {
        "label": "Championship Implications",
        "commands": [get_driver_standings],
    },
}
```

### Pattern 6: DNF Cross-Check via Anthropic SDK

```python
# Source: CONTEXT.md D-08 (locked); anthropic 0.92.0 on PyPI
import anthropic  # direct dep; NOT claude-agent-sdk

def _check_dnf(self, year: int, round_num: int, driver_id: str, race_name: str) -> bool:
    cache_key = (year, round_num, driver_id)
    if cache_key in self._dnf_cache:
        return self._dnf_cache[cache_key]

    client = anthropic.Anthropic()
    # Use claude-haiku-4-5 for fast binary classification
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": (
                f'Did {driver_id} DNF or retire in the {race_name} {year}? '
                f'Respond with only valid JSON: {{"dnf": true/false, "reason": "brief explanation"}}'
            ),
        }],
    )
    # parse response.content for JSON...
    result = ...  # bool parsed from JSON
    self._dnf_cache[cache_key] = result
    return result
```

Note: The `web_search` tool type must match the current Anthropic API naming (`web_search_20250305` as of the current SDK). [ASSUMED — exact tool type string; verify against anthropic SDK docs on install]

### Anti-Patterns to Avoid

- **Lazy imports:** All imports must be at the top of the file — no `from pitlane_agent.commands.X import Y` inside function bodies. This is a hard project rule (CLAUDE.md + project memory feedback).
- **subprocess invocation of pitlane commands:** All pitlane-agent functions are called as Python imports, never via subprocess or CLI.
- **Using F1Agent or workspace system:** AngleService does not use the workspace system; it calls command functions directly.
- **Re-using claude-agent-sdk for DNF check:** D-08 explicitly specifies the `anthropic` SDK directly. The claude-agent-sdk is constrained to `<0.2.0` and carries different interface assumptions.
- **Treating `StorySignal.dnf_category` as reliable:** Known issue logged in STATE.md — 2025 DNFs all classified as "retired". Do not use `dnf_category` for the DNF gate. Web search cross-check is the required approach.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pydantic model validation | Custom dataclass + `__post_init__` validators | `pydantic.BaseModel` | Phase 1 precedent; free validation, serialization, `model_validate()` |
| JSON parsing of DNF response | Manual string search for `true/false` | `json.loads()` on isolated JSON block | Anthropic responses may include explanation text before JSON |
| ELO signal detection | Custom rating delta calculations | `pitlane_elo.studio_api.detect_stories()` | Already implemented, tested, with proper thresholds from design doc §7 |
| FastF1 session loading | Direct `fastf1.get_session()` calls in services | `pitlane_agent.commands.fetch.session_info.get_session_info()` | session_info wraps error handling, caching, and data extraction |
| Champion standings shift | Custom points-delta calculation | `get_driver_standings(year, round)` called twice | Ergast client already handles pagination, data normalization |

**Key insight:** The pitlane-agent `commands/` layer already wraps all FastF1 complexity. Never bypass it to call `fastf1.*` directly from pitlane-studio.

---

## Common Pitfalls

### Pitfall 1: session.date is Date-Only, Not a Datetime

**What goes wrong:** `get_session_info()` returns `"date": str | None` which is a date-only string like `"2026-03-16"`, not a session start or end timestamp. Code that tries to parse it as a datetime will fail or produce a midnight UTC timestamp that is wrong for race-time comparisons.

**Why it happens:** `session_info.py` line 326: `str(session.date.date())` — `.date()` strips the time component.

**How to avoid:** For the 2-hour gate, use `date.fromisoformat()` to get a date object, then construct a conservative datetime estimate (e.g., add 16:00 UTC as a race-end upper bound). If the race_date is today or session_date + timedelta(hours=18) > datetime.now(UTC), block with `DataNotReadyError`. [VERIFIED: session_info.py line 326]

**Warning signs:** Gate never triggers because midnight UTC comparison makes all races appear "2 hours old immediately."

### Pitfall 2: Chart-Generating Commands Require workspace_dir

**What goes wrong:** Four of the five-act command functions (`generate_tyre_strategy_chart`, `generate_lap_times_chart`, `generate_qualifying_results_chart`, `generate_position_changes_chart`) require a `workspace_dir: Path` argument. The parameter appears optional in `position_changes.py` (default `None`) but the function immediately dereferences it as `workspace_dir / "charts"` — this will raise `TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'` if `None` is passed.

**Why it happens:** These commands were designed for the workspace-based CLI workflow; they write chart PNG files to disk.

**How to avoid:** `FiveActMapper.fetch_act_data()` must supply `workspace_dir = Path.home() / ".pitlane" / "studio" / "charts"` and call `workspace_dir.mkdir(parents=True, exist_ok=True)` before invoking chart commands. This path should be a constant in `five_act.py`.

**Warning signs:** `TypeError` on first call to any act that uses chart commands.

[VERIFIED: position_changes.py line 201; tyre_strategy.py; lap_times.py; qualifying_results.py]

### Pitfall 3: Lap-1 Chaos Signal Requires Filtered Data

**What goes wrong:** `generate_position_changes_chart()` returns aggregate statistics for the entire race, not just lap 1. Using `total_position_changes` as the lap-1 chaos signal produces a season-chaos signal, not a lap-1 signal.

**Why it happens:** The position changes command is a visualization command; it has no "first lap only" mode in its public interface.

**How to avoid:** For the lap-1 chaos signal specifically, use `race_summary["total_position_changes"]` from `get_session_info()` as a proxy (it includes all race position changes), OR use the `lap_start=1, lap_end=1` filter parameters available on `get_race_control_messages()` for act 2 data. For the AngleService signal, a simpler approach is to compute lap-1 position changes directly: the number of drivers whose position at lap 1 differs from their grid position (available from `SessionInfo["drivers"]` grid_position and position fields). [VERIFIED: position_changes.py signature; session_info.py DriverInfo TypedDict]

**Warning signs:** Wildness confidence and lap-1 chaos confidence are nearly identical every race.

### Pitfall 4: Scheduled Laps Not in session_info

**What goes wrong:** `get_session_info()` returns `total_laps: int | None` which is the laps actually completed — there is no `scheduled_laps` field. Using `total_laps` as both actual and scheduled produces a ratio of 1.0 always.

**Why it happens:** FastF1 `session.total_laps` reflects what was driven, not what was scheduled.

**How to avoid:** Use `get_season_summary(year)["races"]` to find the matching round's `race_summary["total_laps"]` as the "expected" lap count (it's pre-computed from the full session). Or hardcode 305 km / circuit_length_km as a fallback. The `SessionInfo["circuit_length_km"]` field can derive an estimate. [VERIFIED: session_info.py line 314–316; season_summary.py SeasonRaceSummary TypedDict]

**Warning signs:** Data gate never blocks for "incomplete lap count" even for red-flagged races.

### Pitfall 5: detect_stories() for Novelty Filter is Slow

**What goes wrong:** Calling `detect_stories(year, round-1)` and `detect_stories(year, round-2)` for the novelty filter involves DuckDB parquet queries. If ELO snapshots are large, these two extra calls could add seconds of latency to `get_angles()`.

**Why it happens:** `detect_stories()` queries all ELO snapshot parquet files for each call. Three total calls (current + 2 prior) means three DuckDB scan operations.

**How to avoid:** The calls are deterministic and do not change for a given (year, round) pair after ELO snapshots are built. Consider caching the prior-round signals on the `AngleService` instance (same in-memory dict pattern as the DNF cache). [VERIFIED: signals.py — uses `duckdb.connect()` per call; no built-in caching]

**Warning signs:** `get_angles()` takes 10+ seconds due to three sequential DuckDB scans.

### Pitfall 6: anthropic SDK Tool Name Version Mismatch

**What goes wrong:** The web search tool name in the Anthropic SDK changes between API versions (e.g., `"web_search"` vs `"web_search_20250305"`). Passing the wrong tool type string results in a 400 error from the API.

**Why it happens:** Anthropic uses date-stamped tool names for versioned APIs.

**How to avoid:** After installing `anthropic`, verify the correct tool type string from the current SDK docs or by checking `anthropic.__version__` and consulting the changelog. [ASSUMED — exact tool type string; verify on install against current anthropic SDK documentation]

---

## Code Examples

### Verified: StorySignal to AngleCandidate Mapping (ELO signals)

```python
# Source: signals.py (verified StorySignal fields)
import hashlib

def _elo_signal_to_candidate(signal: StorySignal) -> AngleCandidate:
    hash_input = f"{signal.year}:{signal.round}:{signal.signal_type}:{signal.driver_id}"
    angle_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    confidence = min(abs(signal.value) / signal.threshold, 1.0)
    return AngleCandidate(
        angle_id=angle_id,
        name=signal.narrative,
        signal_type=signal.signal_type,
        confidence=confidence,
        data_rationale=signal.narrative,
        dnf_suppressed=False,
    )
```

### Verified: Wildness Score Extraction from SeasonSummary

```python
# Source: season_summary.py (verified SeasonRaceSummary TypedDict)
from pitlane_agent.commands.fetch.season_summary import get_season_summary

def _get_wildness_signal(year: int, round_num: int) -> AngleCandidate | None:
    summary = get_season_summary(year)
    race = next((r for r in summary["races"] if r["round"] == round_num), None)
    if race is None:
        return None
    wildness = race["wildness_score"]  # already 0–1 normalized
    hash_input = f"{year}:{round_num}:wildness:race"
    angle_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    return AngleCandidate(
        angle_id=angle_id,
        name=f"Chaotic race — wildness score {wildness:.2f}",
        signal_type="wildness",
        confidence=wildness,
        data_rationale=(
            f"Race wildness score {wildness:.2f} — "
            f"{race['race_summary']['num_safety_cars'] if 'num_safety_cars' in race else ''} "
            f"safety car(s), {race['race_summary']['total_overtakes']} overtakes"
        ),
        dnf_suppressed=False,
    )
```

### Verified: get_driver_standings Call Pattern for Standings Shift

```python
# Source: driver_standings.py + ergast.py (verified return shape)
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings

def _get_standings_shift_signals(year: int, round_num: int) -> list[AngleCandidate]:
    current = get_driver_standings(year, round_num)
    prior = get_driver_standings(year, round_num - 1) if round_num > 1 else None
    if prior is None:
        return []

    current_pts = {s["driver_id"]: s["points"] for s in current["standings"]}
    prior_pts = {s["driver_id"]: s["points"] for s in prior["standings"]}
    deltas = {
        d: current_pts.get(d, 0) - prior_pts.get(d, 0)
        for d in current_pts
    }
    max_delta = max(abs(v) for v in deltas.values()) if deltas else 1
    # Build AngleCandidate(s) for largest gainers/losers...
```

### Verified: FiveActMapper workspace_dir Setup

```python
# Source: Pitfall 2 resolution
from pathlib import Path

_CHART_DIR = Path.home() / ".pitlane" / "studio" / "charts"

class FiveActMapper:
    def __init__(self) -> None:
        self._cache: dict[tuple[int, int, int], dict] = {}
        _CHART_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_act_data(self, year: int, round_num: int, act_number: int) -> dict:
        cache_key = (year, round_num, act_number)
        if cache_key in self._cache:
            return self._cache[cache_key]
        config = ACT_CONFIG[act_number]
        results = {}
        for cmd in config["commands"]:
            # Chart commands receive workspace_dir; data-only commands do not
            # Caller is responsible for matching kwargs to each command signature
            ...
        self._cache[cache_key] = results
        return results
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ergast REST API (direct HTTP) | FastF1 Ergast client via `fastf1.ergast.Ergast()` | FastF1 3.x | Already abstracted in pitlane-agent; no change needed |
| Single monolithic signal score | Multiple typed `StorySignal` with `signal_type` enum | Phase 1 design | Enables per-type caps (D-05) |
| DNF from FastF1 classification | Web search + Claude binary check | Known issue (2025 data) | Required by ANGL-03; FastF1 `dnf_category` unreliable |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `web_search_20250305` is the correct tool type string for web search in anthropic SDK 0.92.0 | Pattern 6, Pitfall 6 | DNF check API call returns 400; must look up correct tool name on install |
| A2 | Lap-1 chaos can be computed from `SessionInfo["drivers"]` grid_position vs position fields | Pitfall 3 | If `grid_position` is None for most drivers, signal will be uncomputable; fall back to race_summary aggregate |
| A3 | `fastf1.get_session(year, gp=int, ...)` accepts round number as `gp` argument | Pattern 3 (position changes) | If FastF1 rejects int for gp, chart commands called with round number will fail; must look up event name first |

---

## Open Questions

1. **Scheduled laps for data gate**
   - What we know: `session_info.total_laps` is actual laps completed; `get_season_summary()` has `race_summary["total_laps"]` which is also actual.
   - What's unclear: There is no "scheduled laps" field in any current command output.
   - Recommendation: Define "scheduled" as the laps count from a fully completed reference race of the same event, or use 305 km / `circuit_length_km` as the FIA standard. The 90% threshold from D-10 is forgiving enough that using "all laps FastF1 knows about" as the expected count is a viable proxy — a red-flagged 30-lap race won't have 90% of 57 laps.

2. **Lap-1 chaos signal granularity**
   - What we know: `generate_position_changes_chart()` aggregates the full race; `SessionInfo["drivers"]` has per-driver `grid_position` and `position` (final position).
   - What's unclear: Position after lap 1 specifically is not directly exposed in `session_info`; it would require loading laps data.
   - Recommendation: Compute lap-1 chaos as "count of drivers whose lap-1 position differs from grid position" using the race_control messages on lap 1 as a proxy for chaos events, OR accept that the signal represents "race chaos broadly" not strictly "lap 1." The ACT-02 usage of position_changes for act 2 data covers lap-1 specifically when `lap_end=1` is passed to race control.

3. **anthropic SDK web search tool name**
   - What we know: pypi shows anthropic 0.92.0 as latest; the SDK has web search tool support.
   - What's unclear: Exact tool type string (`"web_search"` vs `"web_search_20250305"`) for current SDK.
   - Recommendation: After running `uv add anthropic`, check `python -c "import anthropic; print(dir(anthropic))"` and consult the web search tool docs in the anthropic SDK. This is a Wave 0 verification step in the plan.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python >=3.12 | All code | ✓ | system | — |
| uv | Package management | ✓ | system | — |
| pitlane-elo (workspace) | `detect_stories()`, `get_race_entries()` | ✓ | workspace member | — |
| pitlane-agent (workspace) | All command imports | ✓ | workspace member | — |
| anthropic SDK | DNF cross-check (ANGL-03) | ✗ | not installed in pitlane-studio | Must add via `uv add --directory packages/pitlane-studio anthropic` |
| FastF1 cache | All pitlane-agent commands | ✓ | disk cache at `~/.fastf1/` (assumed standard path) | Commands work without cache; first call is slow |
| ANTHROPIC_API_KEY env var | DNF cross-check | [ASSUMED] | — | If absent, `anthropic.Anthropic()` raises `AuthenticationError` — catch and log, suppress DNF check |

**Missing dependencies with no fallback:**
- `anthropic` SDK in pitlane-studio — must install before Wave 1.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing in pitlane-studio) |
| Config file | `packages/pitlane-studio/pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py tests/test_five_act_mapper.py -x` |
| Full suite command | `uv run --directory packages/pitlane-studio pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANGL-01 | `get_angles()` returns 4–6 `AngleCandidate` instances with correct schema | integration (real ELO data) | `pytest tests/test_angle_service.py::test_get_angles_returns_candidates -x` | ❌ Wave 0 |
| ANGL-01 | `AngleCandidate` Pydantic schema validates required fields | unit | `pytest tests/test_angle_service.py::test_angle_candidate_schema -x` | ❌ Wave 0 |
| ANGL-02 | Top 2 per ELO signal_type cap applied | unit | `pytest tests/test_angle_service.py::test_elo_type_cap -x` | ❌ Wave 0 |
| ANGL-02 | Novelty filter suppresses repeated (driver_id, signal_type) | unit (mocked prior rounds) | `pytest tests/test_angle_service.py::test_novelty_filter -x` | ❌ Wave 0 |
| ANGL-03 | DNF check only triggers for `slump` and `surprise_under` | unit (mocked anthropic) | `pytest tests/test_angle_service.py::test_dnf_check_only_for_crisis_types -x` | ❌ Wave 0 |
| ANGL-03 | DNF cache prevents duplicate API calls | unit (mocked anthropic) | `pytest tests/test_angle_service.py::test_dnf_cache -x` | ❌ Wave 0 |
| ANGL-04 | `DataNotReadyError` raised for session < 2 hours old | unit (mocked session_info) | `pytest tests/test_angle_service.py::test_data_gate_too_fresh -x` | ❌ Wave 0 |
| ANGL-04 | `DataNotReadyError` raised for incomplete lap count | unit (mocked session_info) | `pytest tests/test_angle_service.py::test_data_gate_incomplete_laps -x` | ❌ Wave 0 |
| ACT-01 | `ACT_CONFIG` maps all 5 acts with correct command callables | unit | `pytest tests/test_five_act_mapper.py::test_act_config_structure -x` | ❌ Wave 0 |
| ACT-02 | `fetch_act_data()` returns dict and caches subsequent calls | integration (real FastF1 data, skippable) | `pytest tests/test_five_act_mapper.py::test_fetch_act_data_caches -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py tests/test_five_act_mapper.py -x`
- **Per wave merge:** `uv run --directory packages/pitlane-studio pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_angle_service.py` — covers ANGL-01 through ANGL-04
- [ ] `tests/test_five_act_mapper.py` — covers ACT-01, ACT-02
- [ ] `src/pitlane_studio/services/__init__.py` — package init file
- [ ] `src/pitlane_studio/services/angles.py` — `AngleService`, `AngleCandidate`, `DataNotReadyError`
- [ ] `src/pitlane_studio/services/five_act.py` — `FiveActMapper`, `ACT_CONFIG`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in this phase (personal tool) |
| V3 Session Management | no | No sessions in this phase |
| V4 Access Control | no | Single-user local tool |
| V5 Input Validation | yes | Pydantic BaseModel validates `AngleCandidate` fields; `year` and `round` are int bounds (validated at FastAPI route layer in Phase 3) |
| V6 Cryptography | no | `hashlib.sha256` for deterministic ID generation (not security-critical) |

### Known Threat Patterns for Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Anthropic API key exposure in logs | Information Disclosure | Never log API key; use env var `ANTHROPIC_API_KEY`; catch `AuthenticationError` without logging key |
| JSON injection in DNF check response | Tampering | Use `json.loads()` on isolated JSON block; do not `eval()` response; treat parse failure as `dnf=False` |
| Path traversal via workspace_dir | Tampering | Use hardcoded `Path.home() / ".pitlane" / "studio" / "charts"` — not user-controlled |
| XSS via narrative strings in HTML context | XSS | Phase 2 is pure service layer with no HTML rendering; Phase 3 must apply `bleach.clean()` per PKG-03 when narrative strings are rendered |

---

## Sources

### Primary (HIGH confidence)

- `packages/pitlane-elo/src/pitlane_elo/studio_api.py` — `detect_stories()` signature verified
- `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` — `StorySignal` dataclass fields, all signal_types, `threshold` field confirmed
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/season_summary.py` — `get_season_summary()` signature and `SeasonRaceSummary` TypedDict with `wildness_score: float`
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/driver_standings.py` — `get_driver_standings(year, round_number)` signature
- `packages/pitlane-agent/src/pitlane_agent/utils/ergast.py` — `parse_driver_standings_response()` return shape including `standings[*].points`
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/session_info.py` — `SessionInfo` TypedDict; `date` is date-only string; `total_laps` is int|None; no scheduled_laps
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/race_control.py` — `get_race_control_messages()` signature and `RaceControlData` return type
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/tyre_strategy.py` — `generate_tyre_strategy_chart()` requires `workspace_dir: Path`
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/lap_times.py` — `generate_lap_times_chart()` requires `workspace_dir: Path`
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/qualifying_results.py` — `generate_qualifying_results_chart()` requires `workspace_dir: Path`
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/position_changes.py` — `generate_position_changes_chart()` workspace_dir=None crashes; confirmed line 201
- `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` — `ArticleRecord` Pydantic pattern to follow
- `packages/pitlane-studio/pyproject.toml` — confirmed `anthropic` not in dependencies
- `packages/pitlane-studio/tests/conftest.py` — `tmp_db_path`, `tmp_store` fixture patterns
- `packages/pitlane-studio/tests/test_article_store.py` — integration test pattern with real SQLite

### Secondary (MEDIUM confidence)

- PyPI `anthropic` version check — 0.92.0 confirmed as latest [VERIFIED: pypi.org curl]
- FastF1 `get_session(year, gp: str | int, ...)` accepts int for gp [VERIFIED: Python help() introspection]

### Tertiary (LOW confidence)

- Anthropic web search tool type string (`web_search_20250305`) — training knowledge; not verified against installed SDK

---

## Project Constraints (from CLAUDE.md)

The following CLAUDE.md directives apply to Phase 2 implementation:

| Directive | Applies To | Compliance Requirement |
|-----------|------------|----------------------|
| `uv` only — never `pip` directly | Adding `anthropic` dep | Use `uv add --directory packages/pitlane-studio anthropic` |
| All imports at top of file — no lazy imports | `angles.py`, `five_act.py`, test files | All `from pitlane_agent.commands.*` imports at module top |
| Direct Python imports, not subprocess | AngleService, FiveActMapper | Call `get_driver_standings(year, round)` directly, never `subprocess.run(["pitlane", ...])` |
| Do NOT use F1Agent, workspace system, or Bash tool sandboxing | AngleService, FiveActMapper | No `F1Agent` instantiation; no workspace path lookup |
| Cross-package integration test must call `detect_stories()` with real data (no mocks) | test_angle_service.py | At least one integration test uses real ELO data, skipable if no snapshots |
| ArticleStore integration test must hit a real SQLite file (no mocks) | Not applicable to Phase 2 (no new SQLite) | N/A |
| DNF cross-check: web search NOT FastF1 classification | AngleService._check_dnf() | Use anthropic SDK + web search tool; never read `StorySignal.context["dnf_category"]` |
| Plan-then-write — always 5 separate API calls | Phase 3 | Not applicable to Phase 2 |
| Hard approval gate | Phase 3 | Not applicable to Phase 2 |
| SDK pin: `claude-agent-sdk<0.2.0` | pitlane-agent/pyproject.toml | Already in place; Phase 2 adds `anthropic` directly — these are separate packages |
| XSS: Jinja2 `| safe` outputs through `bleach.clean()` | Phase 3 HTML rendering | Phase 2 service layer has no HTML output; flag for Phase 3 consumption of `data_rationale` |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all source files read directly from codebase; pyproject.toml confirmed
- Architecture: HIGH — all command signatures verified from source; one ASSUMED (anthropic tool type string)
- Pitfalls: HIGH — Pitfalls 1–5 verified directly from source code; Pitfall 6 ASSUMED from training

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 (stable codebase; anthropic SDK tool names may change faster)
