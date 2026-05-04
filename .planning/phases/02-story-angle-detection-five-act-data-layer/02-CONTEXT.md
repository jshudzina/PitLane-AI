# Phase 2: Story Angle Detection + Five-Act Data Layer - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the data intelligence layer for story angle detection: `AngleService` ingests ELO signals (from `pitlane_elo.studio_api`) plus three race-level signals (wildness score, championship standings shift, lap-1 chaos) to produce 4–6 ranked `AngleCandidate` objects per race; `FiveActMapper` provides a static act→command config with on-demand data fetching. Phase delivers no UI — this is pure service layer that Phase 3 builds on.

Requirements in scope: ANGL-01 (expanded), ANGL-02, ANGL-03, ANGL-04, ACT-01, ACT-02.

</domain>

<decisions>
## Implementation Decisions

### Signal Sources (ANGL-01 — expanded)

- **D-01:** `AngleService` ingests both ELO signals (`detect_stories()` from `pitlane_elo.studio_api`) **and** three race-level signals: wildness score (from `season_summary.get_season_summary(year)`), championship standings shift (from `get_driver_standings(year, round)` vs `get_driver_standings(year, round-1)`), and lap-1 chaos (from `pitlane_agent.commands.analyze.position_changes`). ANGL-01 in REQUIREMENTS.md should be updated to reflect this expanded signal set.
- **D-02:** All signals compete together in a single pool; sorted by confidence (normalized 0–1), top 6 taken as candidates (minimum 4). No reserved ELO slots — non-ELO signals can surface if their magnitude warrants it.

### AngleCandidate Schema

- **D-03:** `AngleService.get_angles(year, round)` returns `list[AngleCandidate]`. `AngleCandidate` is a new Pydantic `BaseModel` (consistent with Phase 1's `ArticleStore` pattern) with fields:
  - `angle_id: str` — deterministic hash of (year, round, signal_type, driver_id or "race")
  - `name: str` — human-readable angle title (from `StorySignal.narrative` for ELO signals; built narrative string for non-ELO signals)
  - `signal_type: str` — one of: `hot_streak | slump | surprise_over | surprise_under | teammate_shift | wildness | standings_shift | lap1_chaos`
  - `confidence: float` — 0–1 normalized signal magnitude (ELO: `min(|value|/threshold, 1.0)`; wildness: `wildness_score` directly; standings shift: normalize by points gap; lap-1 chaos: positions changed / grid size)
  - `data_rationale: str` — `StorySignal.narrative` for ELO signals; equivalent narrative string for non-ELO signals
  - `dnf_suppressed: bool` — True if this angle was suppressed due to a confirmed DNF (for logging/debugging; suppressed angles are excluded from results)
- **D-04:** `data_rationale` is the `StorySignal.narrative` string as-is for ELO signals. For non-ELO signals, `AngleService` builds an equivalent narrative string (e.g. "Race wildness score 0.82 — among the most chaotic of the season").

### Ranking and Filtering (ANGL-02)

- **D-05:** From the full ELO signal pool, apply "top 2 per ELO signal_type" to prevent one ELO signal dominating all 6 slots. Non-ELO signals are not capped (max 1 each by nature). Then sort all candidates by `confidence` descending, take top 6 (minimum 4).
- **D-06:** Novelty filter: suppress an `AngleCandidate` if the same `(driver_id, signal_type)` combination appeared in either of the two preceding rounds. Implementation: recompute `detect_stories()` for `(year, round-1)` and `(year, round-2)` and check for overlapping driver+signal_type pairs. Do NOT track historically surfaced angles — use raw signal recomputation (deterministic, no extra state).

### DNF Cross-Check (ANGL-03)

- **D-07:** Only `slump` and `surprise_under` signal types trigger a DNF cross-check — these are the "driver crisis angles" per ANGL-03.
- **D-08:** Cross-check mechanism: make a targeted Claude API call (using `anthropic` SDK, not claude-agent-sdk) with a web search tool enabled. Prompt asks Claude to return structured JSON: `{"dnf": true/false, "reason": "..."}`. Query: `"{driver} {race_name} {year} DNF retirement result"`.
- **D-09:** In-memory cache per `AngleService` instance: `dict[(year, round, driver_id), bool]` keyed to DNF verdict. Avoids duplicate API calls within a session. No persistence needed.

### Data Completeness Gate (ANGL-04)

- **D-10:** Gate logic runs before any signal detection. Two conditions block angle generation:
  1. Session age < 2 hours: compare race session end time (from FastF1 session info) to `datetime.now(UTC)`. Use `pitlane_agent.commands.fetch.session_info.get_session_info()` to get session metadata.
  2. Incomplete lap count: compare `session.total_laps` to expected race distance. "Incomplete" = total laps < 90% of scheduled race distance (handles shortened races that completed classification, but not abandoned races).
- **D-11:** When blocked, `get_angles()` raises a `DataNotReadyError` (new exception class in `pitlane_studio.services.angles`) with a user-facing message string as the `message` attribute. The FastAPI route returns this message to the frontend as a 422 with structured JSON.

### Five-Act Mapper (ACT-01, ACT-02)

- **D-12:** `FiveActMapper` is a static Python dict (module-level constant, not a class method) mapping act numbers 1–5 to pitlane-agent command callables and act metadata:
  ```python
  ACT_CONFIG = {
      1: {"label": "Qualifying / Grid", "commands": [get_session_info, get_qualifying_results], ...},
      2: {"label": "Lap 1 Chaos", "commands": [get_race_control_messages, get_position_changes], ...},
      3: {"label": "Pit Window", "commands": [get_tyre_strategy, get_race_control_messages], ...},
      4: {"label": "Final Stint", "commands": [get_lap_times, get_position_changes], ...},
      5: {"label": "Championship Implications", "commands": [get_driver_standings], ...},
  }
  ```
- **D-13:** `FiveActMapper.fetch_act_data(year, round, act_number)` calls the configured commands and returns a `dict` keyed by act number. Results cached in an **in-memory dict** on the `FiveActMapper` instance, keyed by `(year, round, act_number)`. Cache is per-process; lost on restart. This is acceptable since FastF1 data itself is cached on disk.

### Claude's Discretion

- Exact command function signatures for non-ELO signals (position_changes, race_control) — follow the established pattern for calling pitlane-agent commands directly.
- Narrative string templates for non-ELO `AngleCandidate.data_rationale` — Claude picks reasonable phrasing.
- Model choice for DNF check API call — use a fast/cheap model (e.g., Haiku) since it's a binary classification task.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, and requirements (ANGL-01 through ACT-02)
- `.planning/REQUIREMENTS.md` — Full v1 requirements; ANGL-01 needs updating to include non-ELO signals

### ELO Signal Layer
- `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` — `StorySignal` dataclass; `detect_stories(year, round_num)` — entry point for ELO signals
- `packages/pitlane-elo/src/pitlane_elo/studio_api.py` — Public `detect_stories(year, round)` boundary used by AngleService

### Non-ELO Signal Sources
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/season_summary.py` — `get_season_summary(year)` returns races with `wildness_score` field; `_compute_wildness_score()` documents the formula
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/driver_standings.py` — `get_driver_standings(year, round_number)` for championship standings shift
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/position_changes.py` — lap-1 position changes signal
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/session_info.py` — session metadata for data completeness gate (ANGL-04)

### Five-Act Command Mapping (ACT-01)
- `packages/pitlane-agent/src/pitlane_agent/commands/fetch/race_control.py` — acts 2 and 3
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/tyre_strategy.py` — act 3
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/lap_times.py` — act 4
- `packages/pitlane-agent/src/pitlane_agent/commands/analyze/qualifying_results.py` — act 1

### Phase 1 Foundation
- `packages/pitlane-studio/src/pitlane_studio/store/` — ArticleStore pattern; Pydantic BaseModel convention to follow for AngleCandidate
- `.planning/phases/01-package-scaffold-prerequisites/01-CONTEXT.md` — Phase 1 decisions (import style, Pydantic BaseModel, SQLAlchemy Core)

### Architecture Constraints
- `CLAUDE.md` — Monorepo rules, import rules (all imports at top of file), test commands

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pitlane_elo.studio_api.detect_stories(year, round)` — already tested, returns `list[StorySignal]` sorted by `|value|` desc
- `pitlane_elo.data.get_race_entries(year)` — find race entries to support novelty filter (prior 2 rounds lookup)
- `pitlane_agent.commands.fetch.season_summary.get_season_summary(year)` — returns `SeasonSummary` with per-race `wildness_score: float` (0–1)
- `pitlane_agent.commands.fetch.driver_standings.get_driver_standings(year, round_number)` — already exists for championship standings shift
- `packages/pitlane-studio/src/pitlane_studio/store/` — Pydantic BaseModel + SQLAlchemy Core pattern to follow for `AngleCandidate`

### Established Patterns
- **Direct Python imports, not subprocess** — all pitlane-agent commands are called as `from pitlane_agent.commands.X import Y; Y(year, round)` — not via CLI
- **All imports at top of file** — per project feedback rule; no lazy imports inside functions
- **Pydantic BaseModel** for data classes (confirmed in Phase 1 for ArticleStore)
- **`StorySignal.signal_type`** string literals: `hot_streak | slump | surprise_over | surprise_under | teammate_shift`

### Integration Points
- `AngleService` imports from `pitlane_elo.studio_api` and multiple `pitlane_agent.commands.*`
- `FiveActMapper` imports from `pitlane_agent.commands.*` (fetch + analyze layers)
- New module location: `packages/pitlane-studio/src/pitlane_studio/services/angles.py` and `services/five_act.py`
- DNF check uses `anthropic` SDK directly (not claude-agent-sdk) — add `anthropic` as a direct dep in pitlane-studio's pyproject.toml if not already present

</code_context>

<specifics>
## Specific Ideas

- `AngleService.get_angles(year, round)` is the primary public method; it runs the full pipeline (gate check → ELO signals → non-ELO signals → DNF cross-check → novelty filter → rank → return top 4–6)
- `FiveActMapper` is a lightweight module with a module-level `ACT_CONFIG` dict and a `fetch_act_data(year, round, act_number)` function — not a heavy class
- Non-ELO `data_rationale` example: `"Race wildness score 0.82 — heavy safety car activity and 14 position swaps"` (use the season_summary context dict for specifics)
- DNF check uses a fast model (Haiku) for the binary JSON classification — keep it cheap
- `DataNotReadyError` is a custom exception with a `message: str` attribute for the journalist-facing blocking message

</specifics>

<deferred>
## Deferred Ideas

- Lap-1 chaos as a *standalone* ACT-02 data source vs. signal source: it plays both roles (angle signal in ANGL-01 and act 2 data in ACT-01). Both uses are in scope; deconfliction is an implementation detail.
- Five-act SQLite persistence — user opted for in-memory cache; revisit in v2 if restart latency becomes an issue.
- Additional non-ELO signals (e.g., fastest lap shifts, team constructor battle) — not discussed; could be added in a future iteration if the 3 chosen signals prove insufficient.

</deferred>

---

*Phase: 2-Story Angle Detection + Five-Act Data Layer*
*Context gathered: 2026-05-03*
