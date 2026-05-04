---
phase: 02-story-angle-detection-five-act-data-layer
plan: "04"
subsystem: angle-service-gap-closure
tags: [gap-closure, dnf-check, retry-loop, import-cleanup, requirements-update]
dependency_graph:
  requires: [02-03-PLAN.md]
  provides: [ANGL-03-closed, ACT-01-closed, CR-02-closed]
  affects: [angles.py, test_angle_service.py, test_five_act_mapper.py, REQUIREMENTS.md]
tech_stack:
  added: []
  patterns: [BadRequestError-retry-loop, pytest-importorskip-at-module-scope, _FakeDatetime-subclass-for-mocking]
key_files:
  modified:
    - packages/pitlane-studio/src/pitlane_studio/services/angles.py
    - packages/pitlane-studio/tests/test_angle_service.py
    - packages/pitlane-studio/tests/test_five_act_mapper.py
    - .planning/REQUIREMENTS.md
decisions:
  - "ANGL-03: _check_dnf retries with web_search fallback on BadRequestError; confirmed bounded to exactly 2 tool types (T-02gc-02 DoS mitigation)"
  - "ACT-01: REQUIREMENTS.md updated to reflect qualifying-results for act 1; implementation was correct, spec was stale"
  - "CR-02: lazy datetime imports replaced with _FakeDatetime subclass pattern to make test_data_gate_too_fresh time-of-day independent"
metrics:
  duration_minutes: 7
  completed_date: "2026-05-04"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 02 Plan 04: Gap Closure — ANGL-03 DNF Fallback + ACT-01 Spec Alignment Summary

**One-liner:** DNF check gains BadRequestError retry loop with web_search fallback; ACT-01 spec aligned to qualifying_results; all 4 lazy imports moved to module top.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace _check_dnf with retry loop + fix lazy imports | 56df044 | angles.py, test_angle_service.py |
| 2 | Update REQUIREMENTS.md ACT-01 + add act 1 assertion | 900e437 | REQUIREMENTS.md, test_five_act_mapper.py |

## Verification

Full phase 2 test suite after both tasks: **26 passed, 2 skipped**

```
tests/test_angle_service.py    13 passed, 1 skipped
tests/test_five_act_mapper.py  13 passed, 1 skipped
```

Both skipped tests are integration tests requiring live FastF1/ELO data — expected.

## Decisions Made

1. **ACT-01 resolution: update spec, not implementation.** The implementation (`generate_qualifying_results_chart` in act 1) was intentional per CONTEXT.md D-12 decision. The REQUIREMENTS.md spec was stale. Updated spec with rationale referencing D-12 rather than reverting the implementation.

2. **_FakeDatetime subclass pattern.** The `test_data_gate_too_fresh` test was time-of-day dependent — it used `date.today()` as the race date but the gate window closed before 18:00 UTC. Fixed using a `_FakeDatetime(datetime)` subclass with overridden `now()` to make the test deterministic. This is the correct pattern for mocking `datetime.now()` when the code also uses `datetime(...)` constructor.

3. **pytest.importorskip at module scope.** The `from pitlane_elo.data import get_race_entries` lazy import inside `test_get_angles_returns_candidates` was replaced with `pytest.importorskip` at module scope, which causes the entire module to be skipped if `pitlane_elo.data` is unavailable — a more correct approach than catching ImportError inside the test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed time-of-day dependent test_data_gate_too_fresh**
- **Found during:** Task 1 verification
- **Issue:** `test_data_gate_too_fresh` used `date.today()` as race date; the gate window (race end 16:00 UTC + 2h = 18:00 UTC) had already passed by test execution time (23:09 UTC), so `DataNotReadyError` was never raised
- **Fix:** Used `_FakeDatetime(datetime)` subclass with `now()` returning 17:00 UTC on a fixed date, patched into `pitlane_studio.services.angles.datetime`
- **Files modified:** `tests/test_angle_service.py`
- **Commit:** 56df044

**2. [Rule 3 - Blocking] Installed pytest in worktree venv**
- **Found during:** Task 1 verification
- **Issue:** The worktree's `.venv` did not have pytest installed (only `uv sync` without `--extra test` was run during venv creation). uv fell back to the main repo's `.venv/bin/python3`, which had the main repo's unmodified source on its path. Tests were running against stale code.
- **Fix:** Ran `uv sync --directory packages/pitlane-studio --extra test` to install pytest into the worktree venv
- **Files modified:** None (venv setup only)
- **Commit:** N/A (runtime fix)

## Known Stubs

None — all changes are concrete implementations or spec documentation.

## Threat Flags

No new threat surface introduced. The retry loop is bounded to 2 tool types (T-02gc-02 DoS mitigation confirmed implemented).

## Self-Check

### Files

- [x] `packages/pitlane-studio/src/pitlane_studio/services/angles.py` — exists
- [x] `packages/pitlane-studio/tests/test_angle_service.py` — exists
- [x] `packages/pitlane-studio/tests/test_five_act_mapper.py` — exists
- [x] `.planning/REQUIREMENTS.md` — exists

### Commits

- [x] 56df044 — Task 1
- [x] 900e437 — Task 2

## Self-Check: PASSED
