---
phase: 1
slug: package-scaffold-prerequisites
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured in root pyproject.toml) |
| **Config file** | Root `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["packages/*/tests"]` |
| **Quick run command** | `uv run pytest packages/pitlane-studio/tests/ -x` |
| **Full suite command** | `uv run pytest` (from repo root, covers all packages) |
| **Estimated runtime** | ~15 seconds |

Note: Wave 0 commands invoke pytest by path (`uv run pytest packages/pitlane-studio/tests/ ...`) because `packages/pitlane-studio/pyproject.toml` does not exist until Plan 01-02 (Wave 1). Pytest discovers tests by path without requiring the package to be installed. From Wave 1 onward, `uv run --directory packages/pitlane-studio pytest ...` is also valid.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/pitlane-studio/tests/ -x` (or `--directory` form once package exists)
- **After every plan wave:** Run `uv run pytest` (full suite from root)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | PKG-01,02,03,04 | — | N/A | wave0 | `uv run pytest packages/pitlane-studio/tests/ --collect-only` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | PKG-01,02,03,04 | — | N/A | wave0 | `uv run pytest packages/pitlane-studio/tests/ --collect-only` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | PKG-03 | T-1-04-T1 | bleach.clean() sanitizes `<script>` tags | unit | `uv run --directory packages/pitlane-studio pytest tests/test_filters.py -x` | ✅ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | PKG-04 | T-1-04-T3 | ValueError on illegal transitions | integration | inline python -c smoke + tests/test_article_store.py | ✅ W0 | ⬜ pending |
| 1-04-03 | 04 | 2 | PKG-04 | — | conftest tmp_store fixture (import at top) | unit | grep + `uv run pytest packages/pitlane-studio/tests/conftest.py --collect-only` | ✅ W0 | ⬜ pending |
| 1-04-04 | 04 | 2 | PKG-04 | T-1-04-T3 | full suite green, zero xfail markers | integration | `uv run --directory packages/pitlane-studio pytest -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `packages/pitlane-studio/tests/__init__.py` — required for pytest discovery (Plan 01-01 Task 1.1)
- [x] `packages/pitlane-studio/tests/conftest.py` — `tmp_db_path` fixture (Plan 01-01 Task 1.1); `tmp_store` fixture added by Plan 01-04 Task 4.3 with top-of-file import
- [x] `packages/pitlane-studio/tests/test_app.py` — PKG-01 smoke test stub xfail (Plan 01-01 Task 1.2)
- [x] `packages/pitlane-studio/tests/test_studio_api.py` — PKG-02 integration stub xfail (Plan 01-01 Task 1.2)
- [x] `packages/pitlane-studio/tests/test_filters.py` — PKG-03 unit test stub xfail (Plan 01-01 Task 1.2)
- [x] `packages/pitlane-studio/tests/test_article_store.py` — PKG-04 integration stub xfail (Plan 01-01 Task 1.2)
- [x] pitlane-studio package itself — created in Plan 01-02 (Wave 1) before any tests run for real

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `uv sync --all-packages` completes with no dep conflicts | PKG-01 | Install-time check, not runtime | Run from repo root; confirm no error output |
| `pitlane-studio` CLI starts uvicorn on port 8001 | PKG-01 | Process management | Run `uv run --directory packages/pitlane-studio pitlane-studio`; confirm server starts |
| `claude-agent-sdk<0.2.0` pin reflected in lock file | PKG-03 | Lock file inspection | `grep "claude-agent-sdk" uv.lock` — confirm version is `<0.2.0` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test files exist; `tmp_store` fixture wired in Plan 04 with top-of-file import)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Wave 0 commands use repo-root path invocation (pyproject.toml not yet present); Wave 1+ may use `--directory` form

**Approval:** approved
