---
phase: 03-plan-then-write-pipeline-co-authoring-ui
plan: "01"
subsystem: database
tags: [sqlalchemy, sqlite, pydantic, pytest, beat-store]

# Dependency graph
requires:
  - phase: 02-angle-detection-five-act-mapper
    provides: ArticleStore pattern (SQLAlchemy Core, composite PK, upsert)
provides:
  - BeatStore class with outline_beats and beats tables (composite PK)
  - OutlineBeatRecord and BeatRecord Pydantic models
  - 8 CRUD/upsert integration tests for BeatStore
  - 10 xfail stub tests establishing Phase 3 test contract (pipeline + routes)
affects:
  - 03-02 (PipelineOrchestrator depends on BeatStore)
  - 03-03 (Router tests fill in test_routes.py xfail stubs)
  - 03-04 (SSE streaming fills in test_pipeline.py xfail stubs)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Composite PK via SQLAlchemy Core Column(primary_key=True) on article_id AND beat_number"
    - "INSERT OR REPLACE upsert via table.insert().prefix_with('OR REPLACE').values(...)"
    - "xfail stubs with strict=True to establish Phase 3 test contracts before implementation"

key-files:
  created:
    - packages/pitlane-studio/src/pitlane_studio/store/beat_store.py
    - packages/pitlane-studio/tests/test_beat_store.py
    - packages/pitlane-studio/tests/test_pipeline.py
    - packages/pitlane-studio/tests/test_routes.py
  modified: []

key-decisions:
  - "INSERT OR REPLACE (prefix_with) chosen over ON CONFLICT for SQLite upsert — matches existing article_store.py pattern"
  - "xfail stubs are sync-only — pytest-asyncio not yet installed (Plan 03-04 adds it)"

patterns-established:
  - "BeatStore follows ArticleStore pattern exactly: get_engine, _now_iso, engine.begin() for writes, engine.connect() for reads"
  - "Composite PK declared on both article_id and beat_number columns — prevents silent duplicate rows"

requirements-completed:
  - PTW-02
  - PTW-03
  - PTW-04

# Metrics
duration: 8min
completed: 2026-05-05
---

# Phase 3 Plan 01: BeatStore + Phase 3 Test Contracts Summary

**SQLAlchemy Core BeatStore with composite-PK outline_beats and beats tables, 8 passing CRUD tests, and 10 xfail stubs establishing the Phase 3 pipeline and router test contracts**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-05T00:00:00Z
- **Completed:** 2026-05-05T00:08:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `beat_store.py` with `BeatStore` class, two SQLAlchemy Core tables (`outline_beats`, `beats`), composite PKs, and `INSERT OR REPLACE` upsert pattern
- Wrote `test_beat_store.py` with 8 integration tests (CRUD + upsert idempotency) against real SQLite — all passing
- Created `test_pipeline.py` and `test_routes.py` with 10 xfail stubs (strict=True) establishing test contracts for PipelineOrchestrator and router endpoints

## Task Commits

1. **Task 1: Create beat_store.py** — `32e7d7f` (feat)
2. **Task 2: Write test files** — `c0c749a` (test)

## Files Created/Modified

- `packages/pitlane-studio/src/pitlane_studio/store/beat_store.py` — BeatStore with outline_beats + beats tables, composite PK, upsert, Pydantic record models
- `packages/pitlane-studio/tests/test_beat_store.py` — 8 CRUD/upsert integration tests (TestBeatStoreOutlineBeats, TestBeatStoreBeats)
- `packages/pitlane-studio/tests/test_pipeline.py` — 5 xfail stubs for PipelineOrchestrator (Plans 02-03)
- `packages/pitlane-studio/tests/test_routes.py` — 5 xfail stubs for FastAPI router endpoints (Plans 03-05)

## Decisions Made

- Used `INSERT OR REPLACE` (prefix_with pattern) for upsert — consistent with existing codebase patterns and explicit about SQLite behavior
- xfail stubs are sync-only because `pytest-asyncio` is not yet installed — Plan 03-04 will add it and replace stubs with real async tests

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `BeatStore` is ready for `PipelineOrchestrator` to import and use (Plan 03-02)
- `test_pipeline.py` and `test_routes.py` stubs define the exact test signatures Plans 03-03 and 03-04 must satisfy
- Full test suite: 50 passed, 2 skipped (live data), 10 xfailed — all pre-existing tests intact

---
*Phase: 03-plan-then-write-pipeline-co-authoring-ui*
*Completed: 2026-05-05*

## Self-Check: PASSED

- `packages/pitlane-studio/src/pitlane_studio/store/beat_store.py` — FOUND
- `packages/pitlane-studio/tests/test_beat_store.py` — FOUND
- `packages/pitlane-studio/tests/test_pipeline.py` — FOUND
- `packages/pitlane-studio/tests/test_routes.py` — FOUND
- Commit `32e7d7f` — FOUND
- Commit `c0c749a` — FOUND
- Test suite: 50 passed, 2 skipped, 10 xfailed — VERIFIED
