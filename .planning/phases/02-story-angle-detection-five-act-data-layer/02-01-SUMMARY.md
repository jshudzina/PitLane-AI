---
phase: 02-story-angle-detection-five-act-data-layer
plan: "01"
subsystem: pitlane-studio/services
tags: [test-stubs, wave-0, angle-service, five-act-mapper, anthropic, xfail]
dependency_graph:
  requires: []
  provides:
    - pitlane_studio.services package marker (services/__init__.py)
    - xfail test stubs for ANGL-01..04 (test_angle_service.py)
    - xfail test stubs for ACT-01..02 (test_five_act_mapper.py)
    - anthropic>=0.97.0 direct dependency in pitlane-studio
  affects:
    - packages/pitlane-studio/pyproject.toml
    - packages/pitlane-studio/tests/
tech_stack:
  added:
    - anthropic==0.97.0 (direct dep; DNF cross-check via Claude API)
    - pytest-mock>=3.15.1 (optional test dep; mocker fixture)
  patterns:
    - pytestmark xfail at module scope for stubs targeting non-existent modules
    - lazy imports inside test functions (exception to CLAUDE.md top-imports rule — required for collection-safe xfail stubs)
    - class-per-requirement grouping (matches test_article_store.py pattern)
key_files:
  created:
    - packages/pitlane-studio/src/pitlane_studio/services/__init__.py
    - packages/pitlane-studio/tests/test_angle_service.py
    - packages/pitlane-studio/tests/test_five_act_mapper.py
  modified:
    - packages/pitlane-studio/pyproject.toml (anthropic dep + pytest-mock test dep)
    - uv.lock (updated for worktree venv)
decisions:
  - Lazy imports inside test function bodies (not at module top) required for collection-safe xfail stubs targeting non-existent modules — documented CLAUDE.md exception
  - anthropic==0.97.0 resolved (plan specified >=0.92.0; latest is 0.97.0)
  - pytest-mock was already in worktree venv via workspace sync; added to pyproject.toml optional test deps for explicitness
metrics:
  duration: "~6 minutes"
  completed_date: "2026-05-04"
  tasks_completed: 3
  files_created: 3
  files_modified: 2
---

# Phase 2 Plan 01: Wave 0 Test Scaffold Summary

Wave 0 scaffold for Phase 2: anthropic dependency added, services/ package created, xfail test stubs for all ANGL-*/ACT-* requirements in place before any service implementation lands.

---

## Files Created and Modified

### Created

| File | Purpose |
|------|---------|
| `packages/pitlane-studio/src/pitlane_studio/services/__init__.py` | Services package marker; docstring declares Phase 2 contents |
| `packages/pitlane-studio/tests/test_angle_service.py` | 6 test classes, 13 tests, xfail stubs for ANGL-01..04 |
| `packages/pitlane-studio/tests/test_five_act_mapper.py` | 2 test classes, 13 tests (12 xfail + 1 skipif), stubs for ACT-01..02 |

### Modified

| File | Change |
|------|--------|
| `packages/pitlane-studio/pyproject.toml` | Added `anthropic>=0.97.0` to `[project.dependencies]`; added `pytest-mock>=3.15.1` to `[project.optional-dependencies.test]` |
| `uv.lock` | Updated for worktree venv (anthropic 0.97.0 + 5 transitive deps: distro, docstring-parser, jiter, sniffio) |

---

## Anthropic Version

```
anthropic==0.97.0
```

Verified: `uv run --directory packages/pitlane-studio python -c "import anthropic; print(anthropic.__version__)"` → `0.97.0`

Plan specified `>=0.92.0`; resolved to `0.97.0` (latest stable).

---

## Pytest Collection Verification

Both new test files collect cleanly with zero collection errors:

```
tests/test_angle_service.py  — 13 tests collected
tests/test_five_act_mapper.py — 13 tests collected (12 + 1 skipif)
```

Full suite result:
```
16 passed, 1 skipped, 25 xfailed in 34.52s
```

- **16 passed** — pre-existing tests (app, article_store, filters, studio_api) all green
- **25 xfailed** — all new stubs xfail as expected (modules not yet implemented)
- **1 skipped** — `test_fetch_act1_real_data` marked `skipif(True)` by design (requires live FastF1 cache)

---

## Xfail Stub Coverage

All 6 ANGL-*/ACT-* requirements have stub test coverage:

| Requirement | Test Class | Tests | Status |
|-------------|------------|-------|--------|
| ANGL-01 | `TestAngleCandidateSchema` | 2 unit | xfail |
| ANGL-01 | `TestGetAnglesIntegration` | 1 integration | xfail |
| ANGL-02 | `TestEloTypeCap` | 2 unit | xfail |
| ANGL-02 | `TestNoveltyFilter` | 2 unit (mocked) | xfail |
| ANGL-03 | `TestDnfCheck` | 3 unit (mocked anthropic) | xfail |
| ANGL-04 | `TestDataGate` | 3 unit (mocked session_info) | xfail |
| ACT-01 | `TestActConfigStructure` | 9 unit | xfail |
| ACT-02 | `TestFetchActData` | 3 unit (mocked) + 1 skipif | xfail |

---

## pytest-mock

pytest-mock was already available in the worktree venv (installed via workspace sync). Added explicitly to `[project.optional-dependencies.test]` in pyproject.toml for declaration completeness.

---

## Notes for Wave 1

- All new stubs are xfail until Wave 1 plans land production modules:
  - `test_five_act_mapper.py` xfail reason: `"pitlane_studio.services.five_act not yet implemented (lands in Plan 02)"`
  - `test_angle_service.py` xfail reason: `"pitlane_studio.services.angles not yet implemented (lands in Plan 03)"`
- Wave 1 plans (02 and 03) each have a pre-existing target test file as required by the Nyquist rule
- The `test_fetch_act1_real_data` integration test is explicitly `skipif(True)` — it must be manually activated after FastF1 cache is available (or when elo_data_available() is implemented)

---

## Deviations from Plan

### Auto-applied Exceptions

**1. [CLAUDE.md Exception] Lazy imports inside test function bodies**

- **Found during:** Task 1.2 (writing test_angle_service.py)
- **Issue:** CLAUDE.md mandates all imports at the top of the file. However, top-level imports of `pitlane_studio.services.angles` (which does not yet exist) would cause an `ImportError` at collection time, making the file uncollectable. The plan's acceptance criteria explicitly require zero collection errors.
- **Resolution:** Lazy imports inside test function bodies are used exclusively in these two xfail stub test files. The `pytestmark = pytest.mark.xfail(run=True)` marker only applies at test execution time, not at import/collection time.
- **Precedent:** The plan's docstring and pattern (as specified in 02-01-PLAN.md) explicitly called for this approach.
- **Scope:** Only `test_angle_service.py` and `test_five_act_mapper.py` — both xfail stub files targeting non-existent modules. All production code and all other test files must follow CLAUDE.md top-imports rule.
- **Files modified:** `tests/test_angle_service.py`, `tests/test_five_act_mapper.py`

---

## Known Stubs

None that affect plan goals. All stubs are intentional xfail markers awaiting Wave 1 implementation. The stub pattern is the deliverable of this plan.

---

## Threat Flags

None. Wave 0 produces only test stubs and package setup — no runtime code paths, no network calls, no user input surfaces.

---

## Self-Check: PASSED

Files verified:

- [x] `packages/pitlane-studio/src/pitlane_studio/services/__init__.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_angle_service.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_five_act_mapper.py` — FOUND

Commits verified:

- [x] `81f9152` — feat(02-01): add anthropic dependency and create services/ package init
- [x] `6b42e2e` — test(02-01): add xfail stubs for AngleService — ANGL-01 through ANGL-04
- [x] `f44e614` — test(02-01): add xfail stubs for FiveActMapper — ACT-01 and ACT-02
