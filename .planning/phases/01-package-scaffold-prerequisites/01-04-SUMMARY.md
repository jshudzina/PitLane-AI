---
phase: 01-package-scaffold-prerequisites
plan: "04"
subsystem: pitlane-studio/filters, pitlane-studio/store
tags: [bleach, sqlalchemy, sqlite, state-machine, security, xss, pydantic]
dependency_graph:
  requires: [01-01, 01-02, 01-03]
  provides: [PKG-03, PKG-04, safe_html-filter, ArticleStore, pitlane-studio-full-suite]
  affects: [Phase-2-AngleService, Phase-2-PipelineOrchestrator, Phase-3-templates]
tech_stack:
  added:
    - bleach>=6.0 (two-pass XSS sanitization with regex pre-pass + bleach.clean)
    - sqlalchemy>=2.0 Core (Table/Column/MetaData — no ORM layer)
    - pydantic>=2.0 (ArticleRecord BaseModel)
    - markupsafe (Markup return type for Jinja2 filter)
  patterns:
    - two-pass XSS sanitization (regex pre-pass strips script content + inner text, bleach strips remaining tags)
    - SQLAlchemy Core only — engine.begin()/connect(), parameterized expressions
    - strict state machine via _TRANSITIONS dict + ValueError on mismatch
    - Pitfall 5 mitigation: path.parent.mkdir(parents=True, exist_ok=True) in get_engine before create_engine
    - Jinja2 filter registration via templates.env.filters dict
key_files:
  created:
    - packages/pitlane-studio/src/pitlane_studio/filters.py
    - packages/pitlane-studio/src/pitlane_studio/store/__init__.py
    - packages/pitlane-studio/src/pitlane_studio/store/article_store.py
  modified:
    - packages/pitlane-studio/tests/conftest.py
    - packages/pitlane-studio/tests/test_filters.py
    - packages/pitlane-studio/tests/test_article_store.py
decisions:
  - "Two-pass XSS sanitization: regex pre-pass strips script/style/iframe tags AND their inner content (bleach strip=True keeps inner text), then bleach.clean() handles remaining disallowed tags"
  - "ArticleStore uses SQLAlchemy Core throughout — no Session, no DeclarativeBase, no mapped_column"
  - "tmp_store fixture import placed at top of conftest.py per CLAUDE.md imports-at-top rule"
  - "ArticleRecord is Pydantic v2 BaseModel; datetime stored as ISO8601 string (SQLite has no native datetime)"
metrics:
  duration_seconds: 2453
  completed_date: "2026-05-03T15:24:00Z"
  tasks_completed: 4
  files_created: 3
  files_modified: 3
---

# Phase 1 Plan 04: bleach filter + ArticleStore Summary

**One-liner:** Two-pass XSS-sanitizing safe_html Jinja2 filter and SQLAlchemy Core ArticleStore with strict draft→published state machine — Phase 1 all four PKG-* requirements closed, 16 tests green, zero xfail markers.

---

## What Was Built

### Task 4.1 — safe_html filter (commit: 026fbac)

Created `packages/pitlane-studio/src/pitlane_studio/filters.py` implementing the PKG-03 bleach sanitization requirement.

Key implementation detail: bleach `strip=True` strips HTML tags but preserves their inner text — meaning `<script>alert(1)</script>` becomes `alert(1)`. To meet the test requirement that `alert(1)` is not in the output, a regex pre-pass (`_STRIP_CONTENT_PATTERN`) removes script/style/iframe/object/embed/applet/form/input/button blocks including their inner content before bleach runs. bleach then handles all remaining disallowed tags.

Allowed markdown tags: `a abbr acronym b blockquote br code em h1-h6 hr i li ol p pre s strong table tbody td th thead tr ul` — covers all markdown-to-HTML output including table family.

`register_filters(templates)` wires the filter into a Jinja2Templates instance for use as `{{ content | safe_html }}`.

Activated `test_filters.py` — removed pytestmark xfail, added `test_javascript_protocol_anchor_stripped` and `test_table_tags_preserved`. All 6 tests pass.

### Task 4.2 — ArticleStore (commit: 3af5cd9)

Created `store/__init__.py` and `store/article_store.py` implementing PKG-04.

State machine transitions: `_TRANSITIONS = {"draft": "outline_generated", "outline_generated": "outline_approved", "outline_approved": "published"}`. `published` is terminal. Any call to `transition_status` that does not match `_TRANSITIONS.get(current)` raises `ValueError("Invalid transition: <current> -> <target>. Expected: <expected>")`. This is the hard approval gate that Phase 3's PTW-02 depends on.

SQLAlchemy Core only: `Table`, `Column`, `MetaData`, `create_engine`, `engine.begin()`, `engine.connect()`. No ORM constructs. All queries use parameterized SQLAlchemy expressions — no string concatenation.

Pitfall 5 mitigated: `path.parent.mkdir(parents=True, exist_ok=True)` in `get_engine()` before `create_engine()` call.

### Task 4.3 — conftest.py tmp_store fixture (commit: bea8791)

Replaced Wave 0 conftest (tmp_db_path only) with full fixtures module. `from pitlane_studio.store.article_store import ArticleStore` is a top-level import (CLAUDE.md imports-at-top rule). `tmp_store` fixture body contains only the constructor call.

### Task 4.4 — Activate test_article_store.py (commit: 8e641c2)

Removed pytestmark xfail block. All 7 tests pass:
- `test_create_returns_draft` — creates draft with correct fields
- `test_full_lifecycle_draft_to_published` — full state machine traversal
- `test_skip_to_published_raises_value_error` — skip-forward blocked
- `test_skip_to_outline_approved_raises_value_error` — skip-forward blocked
- `test_reverse_transition_raises_value_error` — reverse transition blocked
- `test_unknown_id_raises_value_error` — missing article raises ValueError
- `test_articles_db_file_created_in_db_path` — SQLite file created at configured path

Full pitlane-studio suite: **16 passed, 0 xfail markers remaining**.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two-pass XSS sanitization for script inner content**

- **Found during:** Task 4.1 verification
- **Issue:** `bleach.clean('<script>alert(1)</script>hello', tags=frozenset(), strip=True)` returns `'alert(1)hello'` — bleach strips the `<script>` tag but preserves its inner text. The test `assert "alert(1)" not in str(result)` fails.
- **Fix:** Added a regex pre-pass `_STRIP_CONTENT_PATTERN` that removes `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<applet>`, `<form>`, `<input>`, `<button>` blocks including their inner content before calling `bleach.clean()`.
- **Files modified:** `packages/pitlane-studio/src/pitlane_studio/filters.py`
- **Commit:** `026fbac`

**2. [Rule 1 - Bug] Comment text triggering ORM grep false positive**

- **Found during:** Task 4.2 acceptance criteria verification
- **Issue:** The docstring comment "D-03: SQLAlchemy Core only (no ORM, no Session, no DeclarativeBase)" caused `grep -c "DeclarativeBase\|mapped_column\|Session\b"` to return 1 instead of 0.
- **Fix:** Rewrote comment to "D-03: SQLAlchemy Core only — Table/Column/MetaData; no ORM layer" which conveys the same intent without triggering the grep.
- **Files modified:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py`
- **Commit:** `3af5cd9`

**3. [Rule 3 - Blocking] Worktree .venv missing pytest**

- **Found during:** Task 4.1 initial test run
- **Issue:** The worktree's `.venv` was freshly created by `uv run --directory packages/pitlane-studio` with only the package's direct dependencies — pytest was not included. The main `.venv` at the repo root has pytest but its editable pitlane-studio pth points to the original repo path, not the worktree.
- **Fix:** Ran `uv sync --all-packages` from the worktree root to install all workspace packages including dev dependencies (pytest, pytest-asyncio, etc.) into the worktree's `.venv`.
- **Impact:** All subsequent `uv run pytest` calls use the worktree `.venv` with both pytest and the worktree's pitlane-studio code.

---

## Known Stubs

None. All implementations are fully wired with no placeholder values, hardcoded empty returns, or TODO comments.

---

## Threat Surface Scan

Per plan threat register — all mitigations implemented:

- **T-1-04-T1 (XSS):** Mitigated — two-pass sanitization strips script inner content (regex pre-pass) + all remaining disallowed tags (bleach). `test_script_tag_is_stripped` and `test_javascript_protocol_anchor_stripped` validate both attack vectors.
- **T-1-04-T2 (XSS bypass via `| safe`):** Convention enforced via CLAUDE.md. No pitlane-studio templates exist in Phase 1; Phase 3 templates will use `| safe_html`.
- **T-1-04-T3 (state-machine bypass):** Mitigated — `_TRANSITIONS.get(current) != target_status` is the single gate. Three skip/reverse tests prove all illegal paths raise ValueError.
- **T-1-04-T4 (path traversal):** Mitigated — default path is fixed; `db_path` kwarg is test-only.
- **T-1-04-E1 (SQL injection):** Mitigated — all SQLAlchemy parameterized expressions, no string concat.

No new threat surface beyond what the plan's threat register accounts for.

---

## Self-Check

### Created files exist

- [x] `packages/pitlane-studio/src/pitlane_studio/filters.py` — FOUND
- [x] `packages/pitlane-studio/src/pitlane_studio/store/__init__.py` — FOUND
- [x] `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` — FOUND

### Commits exist

- [x] `026fbac` — feat(01-04): implement safe_html bleach filter + activate test_filters.py
- [x] `3af5cd9` — feat(01-04): implement ArticleStore with SQLAlchemy Core and strict state machine
- [x] `bea8791` — feat(01-04): extend conftest.py with tmp_store fixture (top-level import)
- [x] `8e641c2` — feat(01-04): activate test_article_store.py — remove xfail, all 7 tests pass

### Test verification

- [x] `packages/pitlane-studio/tests/test_filters.py` — 6 passed
- [x] `packages/pitlane-studio/tests/test_article_store.py` — 7 passed
- [x] Full pitlane-studio suite — 16 passed, 0 xfail markers

## Self-Check: PASSED
