---
phase: 01-package-scaffold-prerequisites
plan: "02"
subsystem: pitlane-studio/scaffold
tags: [uv, fastapi, scaffold, packaging, click, uvicorn, sqlalchemy, bleach]
dependency_graph:
  requires: [01-01]
  provides: [PKG-01, fastapi-app-scaffold, pitlane-studio-package]
  affects: [01-03, 01-04]
tech_stack:
  added:
    - fastapi>=0.115
    - uvicorn[standard]>=0.30
    - click>=8.1.0
    - sqlalchemy>=2.0
    - bleach>=6.0
    - pydantic>=2.0
    - httpx>=0.27
    - pitlane-elo (workspace dep)
  patterns:
    - src layout (packages/pitlane-studio/src/pitlane_studio/)
    - PEP 561 py.typed marker
    - click CLI wrapping uvicorn.run on port 8001
    - FastAPI app with /health endpoint returning {"status": "ok"}
    - hatchling build backend
key_files:
  created:
    - packages/pitlane-studio/src/pitlane_studio/__init__.py
    - packages/pitlane-studio/src/pitlane_studio/py.typed
    - packages/pitlane-studio/src/pitlane_studio/cli.py
    - packages/pitlane-studio/src/pitlane_studio/app.py
  modified:
    - packages/pitlane-studio/pyproject.toml
    - pyproject.toml
    - uv.lock
    - packages/pitlane-studio/tests/test_app.py
decisions:
  - "FastAPI app is intentionally minimal in Plan 02 — no templates, no slowapi, no StaticFiles; those land in Plan 04"
  - "httpx added to main dependencies (not just optional-dependencies.test) for simplicity — it is a standard transitive of FastAPI anyway"
  - "cli.py mirrors pitlane-web CLI pattern but uses port 8001 (distinct from pitlane-web port 8000) per CLAUDE.md constraint"
  - "Default host 127.0.0.1 (loopback) satisfies threat T-1-02-S1: operator must opt into 0.0.0.0"
metrics:
  duration_seconds: 373
  completed_date: "2026-05-03T14:37:05Z"
  tasks_completed: 3
  files_created: 4
  files_modified: 4
---

# Phase 1 Plan 02: pitlane-studio Package Scaffold Summary

**One-liner:** pitlane-studio FastAPI package installed as uv workspace member — click CLI on port 8001, `/health` returns 200, PKG-01 closed.

---

## What Was Built

The `pitlane-studio` package is now a fully installable uv workspace member with src layout. Every downstream Phase 2/3 service (AngleService, FiveActMapper, PipelineOrchestrator) attaches to this FastAPI app. PKG-01 is closed.

### Package Directory Structure

```
packages/pitlane-studio/
  pyproject.toml          (updated: added httpx, optional-deps.test)
  README.md               (pre-existing from Plan 01 Rule 3 fix)
  src/
    pitlane_studio/
      __init__.py         (NEW: __version__ = "0.1.0")
      py.typed            (NEW: PEP 561 empty marker)
      cli.py              (NEW: click command, uvicorn.run, port 8001)
      app.py              (NEW: FastAPI app, /health endpoint)
  tests/
    test_app.py           (MODIFIED: removed pytestmark xfail — now green)
```

### Root Workspace Changes

- `pyproject.toml`: `pitlane-studio` added to `[project] dependencies` and `[tool.uv.sources]`
- `uv.lock`: regenerated to include pitlane-studio, sqlalchemy 2.0.49, bleach, httpx

### Verification Results

| Check | Result |
|-------|--------|
| `uv sync --all-packages` | Resolved 228 packages, 0 conflicts |
| `pytest tests/test_app.py -x` | 1 passed |
| `TestClient GET /health` | HTTP 200 `{"status": "ok"}` |
| `pitlane-studio --help` shows `--port` default 8001 | Confirmed |
| `grep 'name = "pitlane-studio"' uv.lock` | 3 entries (package + its deps) |
| `grep 'name = "sqlalchemy"' uv.lock` | 3 entries |

---

## Deviations from Plan

None — plan executed exactly as written.

The pyproject.toml already existed from Plan 01 (Rule 3 auto-fix for workspace discovery). This plan's Task 2.1 updated it by adding `httpx>=0.27` and `[project.optional-dependencies]`, and created the src layout files.

---

## Known Stubs

None. The `/health` endpoint is fully wired and returning real data. No placeholder text, no hardcoded empty values flowing to UI.

---

## Threat Surface Scan

Per plan threat register:
- **T-1-02-S1** (Spoofing): Mitigated — `--host` default is `127.0.0.1` (loopback only).
- **T-1-02-I1** (Info Disclosure): Mitigated — `debug` flag not set on `FastAPI(...)`.
- **T-1-02-T1, T-1-02-D1, T-1-02-E1**: Accepted per plan rationale (static dict response, personal-use loopback, operator-controlled flag).

No new threat surface beyond what the plan's threat register accounts for.

---

## Self-Check

### Created files exist

- [x] `packages/pitlane-studio/src/pitlane_studio/__init__.py` — FOUND
- [x] `packages/pitlane-studio/src/pitlane_studio/py.typed` — FOUND
- [x] `packages/pitlane-studio/src/pitlane_studio/cli.py` — FOUND
- [x] `packages/pitlane-studio/src/pitlane_studio/app.py` — FOUND

### Commits exist

- [x] `e584b07` — feat(01-02): create pitlane-studio src layout, __init__.py, py.typed; add httpx dep
- [x] `06511c0` — feat(01-02): create cli.py (click+uvicorn port 8001) and app.py (FastAPI /health)
- [x] `f26d5f6` — feat(01-02): register pitlane-studio in root workspace; remove test_app xfail marker

### pytest verification

- [x] `tests/test_app.py` — 1 passed, 0 xfail

## Self-Check: PASSED
