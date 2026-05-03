---
phase: 01-package-scaffold-prerequisites
plan: "01"
subsystem: pitlane-studio/tests
tags: [pytest, scaffold, xfail, nyquist, wave-0]
dependency_graph:
  requires: []
  provides: [test-scaffold, nyquist-gate]
  affects: [01-02, 01-03, 01-04]
tech_stack:
  added: [pytest-xfail-markers]
  patterns: [module-level-pytestmark, tmp_path-fixture, class-based-test-organization]
key_files:
  created:
    - packages/pitlane-studio/tests/__init__.py
    - packages/pitlane-studio/tests/conftest.py
    - packages/pitlane-studio/tests/test_app.py
    - packages/pitlane-studio/tests/test_studio_api.py
    - packages/pitlane-studio/tests/test_filters.py
    - packages/pitlane-studio/tests/test_article_store.py
    - packages/pitlane-studio/pyproject.toml
    - packages/pitlane-studio/README.md
  modified:
    - uv.lock
decisions:
  - "Wave 0 conftest contains only tmp_db_path — no production imports until Plan 04 adds tmp_store with top-of-file import per CLAUDE.md imports-at-top rule"
  - "pyproject.toml created in this plan (Rule 3 fix) because uv workspace requires it for package discovery and pytest collection"
metrics:
  duration_seconds: 204
  completed_date: "2026-05-03T14:32:14Z"
  tasks_completed: 2
  files_created: 8
  files_modified: 1
---

# Phase 1 Plan 01: Wave 0 Test Scaffold Summary

**One-liner:** Six pytest xfail stub files establishing the Nyquist gate for Phase 1 — every implementation plan has a pre-existing target test file.

---

## What Was Built

Wave 0 test scaffold for Phase 1. All four PKG-* requirement tests exist as collectable pytest files before any implementation lands. This satisfies the Nyquist sampling rule: every implementation task in Waves 1 and 2 has a pre-existing automated verify target.

### Files Created

| File | Role |
|------|------|
| `packages/pitlane-studio/tests/__init__.py` | Empty marker; enables pytest discovery under workspace |
| `packages/pitlane-studio/tests/conftest.py` | Wave 0 conftest with `tmp_db_path` fixture only; zero production imports |
| `packages/pitlane-studio/tests/test_app.py` | PKG-01 health endpoint smoke test (xfail until Plan 02) |
| `packages/pitlane-studio/tests/test_studio_api.py` | PKG-02 cross-package `detect_stories` integration test (xfail until Plan 03) |
| `packages/pitlane-studio/tests/test_filters.py` | PKG-03 bleach `safe_html` XSS sanitization unit tests (xfail until Plan 04) |
| `packages/pitlane-studio/tests/test_article_store.py` | PKG-04 ArticleStore SQLite state machine integration tests (xfail until Plan 04) |
| `packages/pitlane-studio/pyproject.toml` | Package config; required by uv workspace discovery (Rule 3 fix) |
| `packages/pitlane-studio/README.md` | Minimal readme; required by hatchling build backend (Rule 3 fix) |

### Test Collection Result

```
14 tests collected (0 errors)
```

All 14 tests are marked `@pytest.mark.xfail(strict=False, run=True)` at module scope. They will XFAIL (not ERROR) because the production modules they import do not yet exist.

---

## Key Decisions

- **Wave 0 conftest scope:** `tmp_db_path` only. The `tmp_store` fixture that depends on `ArticleStore` is intentionally deferred to Plan 04. When Plan 04 adds it, the import will live at the top of conftest.py — per CLAUDE.md's imports-at-top rule (no lazy imports inside functions).

- **xfail strategy:** `strict=False, run=True` — tests run and are expected to fail. This gives honest signal: if a production module accidentally lands early, the test will pass (unexpected pass with `strict=False` is still a pass, not an error).

- **Module-level pytestmark vs. per-test decorator:** Module-level mark is the correct pattern for stub files where all tests in the file are expected to fail until a single plan lands.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created pyproject.toml and README.md to unblock pytest collection**

- **Found during:** Task 1.2 verification
- **Issue:** `uv run pytest packages/pitlane-studio/tests/ --collect-only` failed with `error: Workspace member is missing a pyproject.toml`. The uv workspace uses `members = ["packages/*"]` glob — any directory under `packages/` must have a `pyproject.toml` to be a valid workspace member.
- **Fix:** Created `packages/pitlane-studio/pyproject.toml` (from the PATTERNS.md template, which already specified this file's exact content) and `packages/pitlane-studio/README.md` (minimal, required by hatchling build backend). Then ran `uv sync --all-packages` to update `uv.lock`.
- **Files modified:** `packages/pitlane-studio/pyproject.toml`, `packages/pitlane-studio/README.md`, `uv.lock`
- **Commit:** `0a91173`
- **Impact:** pyproject.toml was already specified in the PATTERNS.md file (plan 01 was about test scaffold; pyproject.toml is intended for a later plan in the phase). Its early creation has no negative consequences — the package spec is identical to what PATTERNS.md specifies.

---

## Known Stubs

All test files are intentional stubs (xfail). No unintentional stubs exist.

- `test_app.py` — stub for `pitlane_studio.app:app` (Plan 02)
- `test_studio_api.py` — stub for `pitlane_elo.studio_api` (Plan 03)
- `test_filters.py` — stub for `pitlane_studio.filters.safe_html` (Plan 04)
- `test_article_store.py` — stub for `pitlane_studio.store.article_store.ArticleStore` (Plan 04)

---

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Wave 0 produces test stubs only — no runtime code paths, no input handling, no persistence.

---

## Self-Check

### Created files exist

- [x] `packages/pitlane-studio/tests/__init__.py` — FOUND
- [x] `packages/pitlane-studio/tests/conftest.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_app.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_studio_api.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_filters.py` — FOUND
- [x] `packages/pitlane-studio/tests/test_article_store.py` — FOUND
- [x] `packages/pitlane-studio/pyproject.toml` — FOUND
- [x] `packages/pitlane-studio/README.md` — FOUND

### Commits exist

- [x] `93294da` — feat(01-01): create tests/ directory with __init__ and minimal conftest fixtures
- [x] `0a91173` — feat(01-01): write four xfail test stubs and scaffold package pyproject.toml

### pytest collection

- [x] 14 tests collected, 0 errors

## Self-Check: PASSED
