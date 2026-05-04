---
phase: 01-package-scaffold-prerequisites
verified: 2026-05-03T00:00:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 1: Package Scaffold + Prerequisites Verification Report

**Phase Goal:** Stand up the pitlane-studio package skeleton — all deps installed, tests stubs in place, health endpoint live, studio_api boundary wired, ArticleStore persisting to SQLite, bleach filter sanitizing HTML.
**Verified:** 2026-05-03
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All four phase test files exist as importable stubs before any implementation begins | VERIFIED | `test_app.py`, `test_studio_api.py`, `test_filters.py`, `test_article_store.py` all present in `packages/pitlane-studio/tests/` |
| 2 | pytest can discover and collect the test stubs (xfail markers removed, all 16 pass) | VERIFIED | `uv run --directory packages/pitlane-studio pytest -q` → `16 passed in 0.49s` |
| 3 | Developer can install pitlane-studio via `uv sync --all-packages` as a workspace member | VERIFIED | `pyproject.toml` (root) lists `"pitlane-studio"` in dependencies + `[tool.uv.sources]`; `uv.lock` has 3 entries for `name = "pitlane-studio"` |
| 4 | GET /health returns HTTP 200 with `{"status": "ok"}` | VERIFIED | `packages/pitlane-studio/src/pitlane_studio/app.py` has `@app.get("/health")` returning `{"status": "ok"}`; `test_app.py` TestClient smoke test passes |
| 5 | pitlane-studio pyproject.toml declares pitlane-elo, sqlalchemy>=2.0, bleach>=6.0, pydantic>=2.0 | VERIFIED | All four deps confirmed in `packages/pitlane-studio/pyproject.toml` |
| 6 | `pitlane_elo.studio_api` exports `detect_stories(year, round)` and `StorySignal` in `__all__` | VERIFIED | `studio_api.py` has `def detect_stories(year: int, round: int)`, positional pass-through to `_detect_stories`, and `__all__ = ["StorySignal", "detect_stories"]` |
| 7 | Cross-package integration test (`test_studio_api_exports`) passes unconditionally | VERIFIED | 16 tests passed including both studio_api tests |
| 8 | claude-agent-sdk is pinned with upper bound `<0.2.0` in pitlane-agent | VERIFIED | `packages/pitlane-agent/pyproject.toml` line 22: `"claude-agent-sdk>=0.1.40,<0.2.0"` |
| 9 | uv.lock resolves claude-agent-sdk to a version satisfying `<0.2.0` | VERIFIED | `uv.lock` shows `version = "0.1.47"` |
| 10 | `safe_html('<script>alert(1)</script>hello')` returns `Markup` with no `<script>` or `alert(1)`, "hello" preserved | VERIFIED | `filters.py` uses two-pass approach: regex strips script content entirely, then `bleach.clean(..., strip=True)` with `_MARKDOWN_TAGS`; returns `Markup(cleaned)`; 6 filter unit tests pass |
| 11 | ArticleStore creates articles in `draft`, persists to SQLite, and enforces the state machine | VERIFIED | `article_store.py` implements `_TRANSITIONS`, `create()`, `get()`, `transition_status()`; `mkdir(parents=True, exist_ok=True)` in `get_engine()`; 7 lifecycle + persistence tests pass |
| 12 | Zero xfail markers remain across all test files | VERIFIED | `grep -rc "pytestmark = pytest.mark.xfail" packages/pitlane-studio/tests/` returns 0 for every file |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/pitlane-studio/tests/__init__.py` | pytest discovery marker | VERIFIED | Exists |
| `packages/pitlane-studio/tests/conftest.py` | `tmp_db_path` + `tmp_store` fixtures; `ArticleStore` import at top-level | VERIFIED | Both fixtures present; `from pitlane_studio.store.article_store import ArticleStore` is top-level import, not lazy |
| `packages/pitlane-studio/tests/test_app.py` | PKG-01 health smoke test | VERIFIED | No pytestmark; passes via TestClient |
| `packages/pitlane-studio/tests/test_studio_api.py` | PKG-02 integration test | VERIFIED | No pytestmark; exports test passes unconditionally; data test skips or passes |
| `packages/pitlane-studio/tests/test_filters.py` | PKG-03 bleach unit tests (6+) | VERIFIED | No pytestmark; 6 tests pass |
| `packages/pitlane-studio/tests/test_article_store.py` | PKG-04 lifecycle + persistence (7+) | VERIFIED | No pytestmark; 7 tests pass |
| `packages/pitlane-studio/pyproject.toml` | Workspace metadata, deps, CLI entry | VERIFIED | `name = "pitlane-studio"`, all required deps, `pitlane-studio = "pitlane_studio.cli:main"` |
| `packages/pitlane-studio/src/pitlane_studio/__init__.py` | `__version__` marker | VERIFIED | Exists |
| `packages/pitlane-studio/src/pitlane_studio/py.typed` | PEP 561 marker | VERIFIED | Exists |
| `packages/pitlane-studio/src/pitlane_studio/cli.py` | click + uvicorn on port 8001 | VERIFIED | `import uvicorn`, `default=8001`, `"pitlane_studio.app:app"` |
| `packages/pitlane-studio/src/pitlane_studio/app.py` | FastAPI + `/health` endpoint | VERIFIED | `app = FastAPI(...)`, `@app.get("/health")` returning `{"status": "ok"}` |
| `packages/pitlane-studio/src/pitlane_studio/filters.py` | `safe_html`, `register_filters`, bleach-backed | VERIFIED | `bleach.clean(...)` with `_MARKDOWN_TAGS`, `strip=True`, returns `Markup`; `__all__` exports both names |
| `packages/pitlane-studio/src/pitlane_studio/store/__init__.py` | Re-exports `ArticleRecord`, `ArticleStore` | VERIFIED | Top-level import and `__all__` confirmed |
| `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` | SQLAlchemy Core, Pydantic, state machine | VERIFIED | No ORM, `_TRANSITIONS` dict, `mkdir(parents=True, exist_ok=True)`, `raise ValueError` on bad transitions |
| `packages/pitlane-elo/src/pitlane_elo/studio_api.py` | `detect_stories(year, round)` + `StorySignal` in `__all__` | VERIFIED | Positional pass-through, `__all__ = ["StorySignal", "detect_stories"]` |
| `packages/pitlane-agent/pyproject.toml` | `claude-agent-sdk>=0.1.40,<0.2.0` | VERIFIED | Confirmed at line 22 |
| `pyproject.toml` (root) | `pitlane-studio` in dependencies and `[tool.uv.sources]` | VERIFIED | Both entries confirmed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `packages/pitlane-studio/pyproject.toml [project.scripts]` | `pitlane_studio.cli:main` | `pitlane-studio = "pitlane_studio.cli:main"` | WIRED | Confirmed in pyproject.toml |
| `cli.py` | `app.py` | `uvicorn.run("pitlane_studio.app:app", ...)` | WIRED | Module string `"pitlane_studio.app:app"` in cli.py |
| `filters.safe_html` | `bleach.clean` | `bleach.clean(pre_cleaned, tags=_MARKDOWN_TAGS, ..., strip=True)` | WIRED | Confirmed in filters.py; two-pass approach validated by 6 passing tests |
| `ArticleStore.transition_status` | `_TRANSITIONS` + `ValueError` | `_TRANSITIONS.get(current) != target_status → raise ValueError` | WIRED | Confirmed in article_store.py; validated by 4 error-path tests |
| `ArticleStore.__init__` | `Path.parent.mkdir(parents=True, exist_ok=True)` | `get_engine()` calls mkdir before `create_engine` | WIRED | `path.parent.mkdir(parents=True, exist_ok=True)` in `get_engine()` |
| `tests/test_studio_api.py` | `pitlane_elo.studio_api` | `from pitlane_elo.studio_api import StorySignal, detect_stories` | WIRED | Import resolves; tests pass |
| `pitlane_elo.studio_api.detect_stories` | `pitlane_elo.stories.signals.detect_stories` | `_detect_stories(year, round)` positional call | WIRED | Confirmed in studio_api.py |

### Data-Flow Trace (Level 4)

N/A for Phase 1 — all artifacts are infrastructure (API skeleton, SQLite layer, utility filter). No dynamic data rendering to trace.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite green (16 tests) | `uv run --directory packages/pitlane-studio pytest -q` | `16 passed in 0.49s` | PASS |
| claude-agent-sdk version satisfies `<0.2.0` | `uv.lock` version check | `version = "0.1.47"` | PASS |
| No xfail markers remain | `grep -rc "pytestmark = pytest.mark.xfail" tests/` | All files return 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PKG-01 | 01-02 | pitlane-studio installable uv workspace package with FastAPI skeleton, uvicorn entry point, `pitlane-studio` CLI | SATISFIED | Package installs; CLI entry `pitlane_studio.cli:main` wired; `/health` endpoint returns 200; 16 tests pass |
| PKG-02 | 01-03 | `pitlane_elo.studio_api` with `detect_stories()` integration test against real data (no mocks) | SATISFIED | `studio_api.py` exists; `test_studio_api_exports` passes unconditionally; data test passes or skips per A2 semantics |
| PKG-03 | 01-03, 01-04 | claude-agent-sdk pinned `<0.2.0`; Jinja2 `\| safe` sanitized via `bleach.clean()` | SATISFIED | SDK pin confirmed in pyproject.toml and uv.lock; `safe_html` filter backed by bleach; 6 XSS unit tests pass |
| PKG-04 | 01-04 | SQLite ArticleStore at `~/.pitlane/studio/articles.db` with `draft → outline_generated → outline_approved → published` state machine | SATISFIED | `article_store.py` uses SQLAlchemy Core; `_TRANSITIONS` enforces strict machine; `mkdir(parents=True)` handles missing dirs; 7 tests pass including persistence test |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `filters.py` | 40-46 | Regex pre-pass before bleach (deviation from plan spec) | Info | Two-pass approach is a conscious security improvement — regex removes script/style/iframe content (not just tags); bleach handles remaining disallowed tags. Tests validate XSS payloads are stripped. Not a stub or regression. |

No blockers found. The two-pass filter is more defensive than the plan spec, not less.

### Human Verification Required

None. All phase-1 behaviors are fully automatable:
- Test suite run confirmed programmatically (16 passed)
- File structure and content verified via grep and file reads
- SDK pin verified in both pyproject.toml and uv.lock
- State machine correctness proven by 7 test cases including all illegal-transition paths

### Gaps Summary

No gaps. All 12 observable truths are VERIFIED, all 17 required artifacts exist with substantive content, all 7 key links are wired, and all 4 requirement IDs (PKG-01 through PKG-04) are satisfied with passing tests.

---

_Verified: 2026-05-03_
_Verifier: Claude (gsd-verifier)_
