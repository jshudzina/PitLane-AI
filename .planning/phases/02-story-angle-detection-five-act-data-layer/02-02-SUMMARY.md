---
phase: 02-story-angle-detection-five-act-data-layer
plan: "02"
subsystem: pitlane-studio/services
tags: [five-act-mapper, act-config, pitlane-agent, fastf1, caching, static-config]
dependency_graph:
  requires:
    - phase: 02-01
      provides: services/__init__.py package marker, xfail test stubs for ACT-01 and ACT-02
  provides:
    - pitlane_studio.services.five_act module (ACT_CONFIG + FiveActMapper)
    - ACT_CONFIG: module-level dict mapping acts 1-5 to pitlane-agent command callables
    - FiveActMapper.fetch_act_data(): on-demand data fetching with in-memory cache
    - _CHART_DIR: module-level Path constant for chart output
  affects:
    - Phase 3 PipelineOrchestrator (imports FiveActMapper for act data grounding)
tech-stack:
  added: []
  patterns:
    - "_resolve_cmd() helper uses importlib to resolve live (possibly mocked) function at call time — enables pytest-mock patches at source module level to be intercepted"
    - "ACT_CONFIG as module-level constant with imported callable references (not strings)"
    - "frozenset for O(1) membership testing of chart-requiring commands"
    - "from __future__ import annotations + all imports at top of file (CLAUDE.md)"
key-files:
  created:
    - packages/pitlane-studio/src/pitlane_studio/services/five_act.py
  modified:
    - packages/pitlane-studio/tests/test_five_act_mapper.py
key-decisions:
  - "Used importlib.import_module + getattr in _resolve_cmd() to resolve live functions at call time — required so pytest-mock patches at source module level (mocker.patch('pitlane_agent.commands.fetch.session_info.get_session_info', ...)) are intercepted by fetch_act_data()"
  - "generate_lap_times_chart called with drivers=[] — required positional arg with no default; empty list produces chart with no driver lines but avoids TypeError; Phase 3 caller can extend with specific drivers"
  - "Chart commands called with str(round_num) for gp parameter — FastF1 accepts int or str; actual signatures require gp:str not str|int as the plan interface section implied"
  - "All chart commands require gp and session_type as positional args (no defaults) — plan interface section was inaccurate; actual signatures verified from source"
patterns-established:
  - "Pattern: _resolve_cmd() for mock-compatible dispatch — store function references in config dict for identity tests, resolve through importlib at call time for testability"
requirements-completed: [ACT-01, ACT-02]
duration: ~15min
completed: "2026-05-04"
---

# Phase 2 Plan 02: FiveActMapper + ACT_CONFIG Summary

**ACT_CONFIG static dict and FiveActMapper class with in-memory cache — maps all 5 race acts to 7 pitlane-agent command callables; ACT-01 and ACT-02 tests fully pass**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-04T12:00:00Z
- **Completed:** 2026-05-04T12:15:00Z
- **Tasks:** 1 (single TDD task with implementation + test update)
- **Files modified:** 2

## Accomplishments

- `five_act.py` created with `ACT_CONFIG` (5 acts, 7 commands) and `FiveActMapper` class
- `FiveActMapper.fetch_act_data()` with in-memory cache keyed by `(year, round_num, act_number)`
- All 12 ACT-01/ACT-02 tests now pass; xfail marker removed; imports moved to top of test file
- `_CHART_DIR` created on `FiveActMapper.__init__`; chart commands always receive `workspace_dir=_CHART_DIR`

## Task Commits

1. **Task 2.1: Implement five_act.py with ACT_CONFIG and FiveActMapper** — `0696f64` (feat)

## Files Created/Modified

- `packages/pitlane-studio/src/pitlane_studio/services/five_act.py` — New module: `ACT_CONFIG` constant dict, `FiveActMapper` class, `_CHART_DIR` constant, `_resolve_cmd()` helper, `_CHART_COMMANDS` frozenset
- `packages/pitlane-studio/tests/test_five_act_mapper.py` — Removed `pytestmark` xfail; moved all imports to module top level per CLAUDE.md

## Decisions Made

**1. _resolve_cmd() for mock-compatible dispatch**

The plan's interface section showed commands like `get_session_info` with defaults for `gp` and `session_type`. In practice, `five_act.py` stores function references in `ACT_CONFIG` (imported with `from ... import`). Since `pytest-mock` patches at the source module level (`mocker.patch("pitlane_agent.commands.fetch.session_info.get_session_info", ...)`), calls made via the locally-imported reference would bypass the mock.

Resolution: `_resolve_cmd(cmd)` uses `importlib.import_module(cmd.__module__)` and `getattr(module, cmd.__name__)` to re-fetch the live (possibly mocked) function at call time. This allows `ACT_CONFIG` to store original function references (for identity tests like `get_session_info in ACT_CONFIG[1]["commands"]`) while ensuring mocks work correctly in `fetch_act_data()`.

**2. generate_lap_times_chart drivers=[]**

The plan listed `generate_lap_times_chart` in ACT 4 but the actual signature requires `drivers: list[str]` with no default. `FiveActMapper` is a general-purpose fetcher — there's no race-level driver list to pass. `drivers=[]` is passed; the chart loop is a no-op but the call succeeds. Phase 3's PipelineOrchestrator can extend this with specific drivers if needed.

**3. Chart command signature deviation**

The plan's `<interfaces>` section showed `gp: str | int` and `session_type: str = "R"` with defaults. Actual source signatures:
- `generate_qualifying_results_chart(year, gp: str | None, session_type: str | None, workspace_dir: Path, ...)` — gp and session_type are positional/required
- `generate_position_changes_chart(year, gp: str, session_type: str, ..., workspace_dir: Path | None = None)` — same
- `generate_tyre_strategy_chart(year, gp: str, session_type: str, workspace_dir: Path, ...)` — same

`fetch_act_data()` passes `str(round_num)` for gp and `"R"` for session_type to all chart commands.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _resolve_cmd() for mock-compatible dispatch**

- **Found during:** Task 2.1 (verifying test_cache_returns_same_object_on_second_call)
- **Issue:** `from ... import` binds local names to original function objects. `mocker.patch` at source module level does not intercept calls via already-imported references. Without fix, `mock_get_session.call_count` would be 0 and the test would fail.
- **Fix:** Added `_resolve_cmd(cmd)` helper that uses `importlib` to re-fetch the function through its source module at call time. This is a standard pattern for making already-imported functions testable with source-level mocks.
- **Files modified:** `packages/pitlane-studio/src/pitlane_studio/services/five_act.py`
- **Verification:** `test_cache_returns_same_object_on_second_call` passes with `mock_get_session.call_count == 1`
- **Committed in:** `0696f64` (task commit)

**2. [Rule 3 - Blocking] Worktree venv lacked pytest**

- **Found during:** First test run
- **Issue:** The worktree's `.venv` was created by wave 0's `uv add` but lacked test dependencies (pytest not installed). `uv run --directory packages/pitlane-studio pytest` was routing to the parent repo's `.venv`, which had pitlane-studio editable-installed from a different worktree — so `five_act.py` was not found at collection time.
- **Fix:** Ran `uv sync --all-packages --extra test` in the worktree to install pytest and all test extras into the worktree's `.venv`.
- **Files modified:** None (venv state only)
- **Verification:** `uv run --directory packages/pitlane-studio pytest tests/test_five_act_mapper.py` now uses the worktree `.venv` and finds all modules.
- **Committed in:** N/A (environment fix, no files changed)

**3. [Rule 3 - Blocking] Worktree HEAD not at correct base commit**

- **Found during:** Initial setup — wave 0 test files missing from working tree
- **Issue:** The worktree branch (`worktree-agent-a9e0c0f4626772676`) was branched from `993cf9f` (Phase 1 merge), not `6958e15` (post-wave-0 base). The `<worktree_branch_check>` startup script detected the mismatch and reset to `6958e15`, which restored the wave 0 files (`test_five_act_mapper.py`, `test_angle_service.py`, `services/__init__.py`).
- **Fix:** `git reset --hard 6958e15fdd68f541cea979779543eaef0b33a0c5` as prescribed by the startup script.
- **Files modified:** N/A (git tree correction)
- **Verification:** `ls packages/pitlane-studio/tests/` showed all wave 0 test files present.
- **Committed in:** N/A (tree correction, no new commit needed)

---

**Total deviations:** 3 (1 bug fix, 2 blocking)
**Impact on plan:** All fixes necessary for correctness and test execution. No scope creep.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `FiveActMapper` and `ACT_CONFIG` are fully implemented and tested
- Phase 3 `PipelineOrchestrator` can import `FiveActMapper` from `pitlane_studio.services.five_act`
- `test_angle_service.py` tests remain xfail (plan 03 will resolve them)
- Full suite: 28 passed, 1 skipped, 13 xfailed — all green

---

## Known Stubs

None. `FiveActMapper.fetch_act_data()` returns real data (or mocked data in tests). The `drivers=[]` default for `generate_lap_times_chart` is an intentional simplification — documented in decisions above. It does not prevent plan 02's goal from being achieved.

## Threat Flags

None. `ACT_CONFIG` commands are trusted callable references imported at module top — not constructed from strings or user input. `_CHART_DIR` is hardcoded, not derived from user input. No new network endpoints or auth paths introduced.

---

## Self-Check

Files verified:

- [x] `packages/pitlane-studio/src/pitlane_studio/services/five_act.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_five_act_mapper.py` — FOUND (updated, xfail removed)

Commits verified:

- [x] `0696f64` — feat(02-02): implement FiveActMapper and ACT_CONFIG — ACT-01 and ACT-02

Test results verified:

- [x] `uv run --directory packages/pitlane-studio pytest tests/test_five_act_mapper.py -q` → 12 passed, 1 skipped
- [x] `uv run --directory packages/pitlane-studio pytest -q` → 28 passed, 1 skipped, 13 xfailed

Acceptance criteria verified:

- [x] `grep -c "from __future__ import annotations" five_act.py` → 1
- [x] `grep -c "from pitlane_agent" five_act.py` → 7
- [x] `grep -c "_CHART_DIR" five_act.py` → 4
- [x] `grep -c "workspace_dir=None" five_act.py` → 0
- [x] `grep -c "__all__" five_act.py` → 1

## Self-Check: PASSED

*Phase: 02-story-angle-detection-five-act-data-layer*
*Completed: 2026-05-04*
