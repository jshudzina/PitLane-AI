# Codebase Concerns

Codebase is well-structured overall; key risks concentrate in data quality (DNF classification), error-message leakage, and Python 3.14 / Numba incompatibility.

**Analysis Date:** 2026-05-02

---

## Security

### MEDIUM — Error message leakage to end users

- **File:** `packages/pitlane-web/src/pitlane_web/app.py:214`
- **Issue:** The `/api/chat` exception handler returns `f"An error occurred: {e}"` directly as `response_text`, which is then rendered into the HTML response. Raw exception messages (stack frames, file paths, internal state) can leak to the browser.
- **Current mitigation:** None.
- **Fix:** Replace with a generic user-facing message and log the full exception server-side only.

### MEDIUM — LLM response rendered as `| safe` HTML without sanitization

- **File:** `packages/pitlane-web/src/pitlane_web/templates/partials/message.html:136`
- **Issue:** The filter chain `content | rewrite_paths(session_id) | html_charts_to_iframes | markdown | safe` calls Jinja2's `| safe` on LLM-generated content converted from Markdown. The `markdown` library does not strip potentially injected HTML (e.g., `<script>` tags in a crafted response). If the underlying LLM or tool output were ever adversarially influenced, this is a stored-XSS path.
- **Current mitigation:** `sandbox="allow-scripts allow-same-origin"` on iframes only; no sanitization of the main response body.
- **Fix:** Use `markdown.markdown(..., extensions=["fenced_code","tables"], output_format="html")` with `bleach.clean()` or equivalent before calling `| safe`.

### MEDIUM — No CSRF protection on state-mutating POST routes

- **Files:** `packages/pitlane-web/src/pitlane_web/app.py` routes `/api/chat`, `/api/conversations/new`, `/api/conversations/{id}/resume`
- **Issue:** The web app has no CSRF token mechanism. POST endpoints rely on session cookie (`SameSite=lax`) which mitigates cross-site form submission for most browsers but is not a complete defense (lax does not cover all navigation-triggered POSTs, and some older browsers ignore it).
- **Current mitigation:** `SameSite=lax` cookie; `httponly=True`.
- **Fix:** Add CSRF double-submit cookie or synchronizer token for state-mutating endpoints.

### LOW — No input length limit on `/api/chat` question field

- **File:** `packages/pitlane-web/src/pitlane_web/app.py:151`
- **Issue:** `question: str = Form(...)` accepts unlimited-length input. Oversized inputs are forwarded to the Claude Agent SDK, potentially consuming API budget or triggering upstream errors.
- **Fix:** Add `question: Annotated[str, Form(max_length=4096)] = Form(...)`.

### LOW — Rate limiter state is in-process memory only

- **File:** `packages/pitlane-web/src/pitlane_web/app.py:76` (`storage_uri="memory://"`)
- **Issue:** If the app is run with multiple uvicorn workers (e.g., `--workers 4`), each process maintains a separate rate-limit counter. Effective per-IP limit is multiplied by the worker count. A single-worker deployment is unaffected, but horizontal scaling silently defeats the limit.
- **Fix:** Switch to a Redis-backed `storage_uri` when running multi-worker, or document the single-worker constraint.

### LOW — F-string SQL construction with file paths in DuckDB queries

- **Files:** `packages/pitlane-agent/src/pitlane_agent/utils/elo_db.py:296`, `packages/pitlane-agent/src/pitlane_agent/utils/stats_db.py:112`, `packages/pitlane-agent/scripts/review_mechanical_dnfs.py:263`
- **Issue:** Parquet paths are interpolated into SQL strings via f-strings (e.g., `f"SELECT * FROM read_parquet('{parquet_path}')`). These paths are generated internally from the data directory and year, not from user input, so the practical injection risk is low. However if the path ever contains a single quote (e.g., a home directory with `'`) it would break or could be exploited.
- **Fix:** Use DuckDB's `read_parquet(?)`-style parameter binding for paths, or escape the path. As a minimum, assert that paths do not contain single quotes before interpolating.

---

## Performance

### MEDIUM — DuckDB connection opened per-driver inside `detect_trend_signals`

- **Files:** `packages/pitlane-elo/src/pitlane_elo/stories/signals.py:161-180`, `packages/pitlane-elo/src/pitlane_elo/stories/signals.py:87-125`
- **Issue:** `detect_trend_signals` creates one DuckDB connection per driver when no `con` is passed, because it calls `_get_recent_snapshots(con=_con)` correctly — but `detect_upset_signals` and `detect_supremacy_signals` each independently open their own top-level connections for their internal loops. With 20 drivers per race, this creates 40+ short-lived DuckDB in-memory connections per `detect_stories` call. The test at `packages/pitlane-elo/tests/stories/test_signals.py:640` now passes for `detect_trend_signals` (fixed in commit `e3aeb26`) but analogous patterns in other detectors remain.
- **Impact:** Slow story detection at scale; connection overhead on every CLI invocation.
- **Fix:** Accept and thread a shared `con` through all detector functions; open one connection in `detect_stories` and pass it down.

### MEDIUM — Full parquet glob scan on every `_get_recent_snapshots` call

- **File:** `packages/pitlane-elo/src/pitlane_elo/stories/signals.py:105-116`
- **Issue:** Every call reads `elo_snapshots/*.parquet` in full and filters in DuckDB. For 50+ seasons of data this glob grows large. No incremental index or pre-filtered view is used.
- **Impact:** Increasing latency as historical data grows.
- **Fix:** Partition the parquet files by year and push the `year < ?` predicate to file-level selection, or maintain a DuckDB persistent file for snapshots.

### LOW — FastF1 session data loaded per-request with no shared cache between agent instances

- **Files:** `packages/pitlane-agent/src/pitlane_agent/agent.py`, `packages/pitlane-agent/commands/workspace/operations.py:35`
- **Issue:** FastF1 caches to `~/.pitlane/cache/fastf1/` on disk, so repeated loads of the same session are fast. However, when the LRU agent cache evicts an agent (`agent_manager.py:64`), any in-process DataFrame objects held by that agent are GC'd. If the same session is requested again from a new agent, FastF1 re-deserializes from disk. This is a moderate cost, not a correctness issue.
- **Impact:** Slightly slower first response after cache eviction.

---

## Tech Debt

### HIGH — DNF classification disabled for 2023+ data

- **Files:** `packages/pitlane-elo/src/pitlane_elo/config.py:56-59`, `packages/pitlane-elo/src/pitlane_elo/config.py:74,86`
- **Issue:** `exclude_mechanical_dnf=False` is set on all production configs with the comment: _"2025 data classifies all DNFs as 'retired' so we can't distinguish mechanical failures from crashes. Re-enable once the DNF classification pipeline is fixed."_ This means the ELO model does not exclude mechanical DNFs from rating updates, subtly penalizing drivers for car failures they had no control over. The `review_mechanical_dnfs.py` script exists to LLM-reclassify them, but it is a manual, per-year process.
- **Impact:** Model accuracy degraded for post-2022 seasons; the calibrated holdout period (2022–2025) is evaluated with the same broken classification.
- **Fix:** Either automate the reclassification pipeline and re-enable `exclude_mechanical_dnf=True`, or document the degradation quantitatively.

### MEDIUM — Bayesian model (Van Kesteren) retained but excluded from default test run

- **Files:** `packages/pitlane-elo/src/pitlane_elo/bayesian/van_kesteren.py`, `packages/pitlane-elo/pyproject.toml:63` (`--ignore=tests/bayesian`)
- **Issue:** The Bayesian model is an optional extra (`pymc>=5.0`) and its tests are ignored by default. Per project memory, the model had poor log-likelihood and metrics and is not used for driver performance prediction. The code is maintained but untested in CI.
- **Impact:** Dead weight that adds maintenance surface and import complexity; `type: ignore` comments throughout `van_kesteren.py` indicate ongoing friction with PyMC's type stubs.
- **Fix:** Either promote the Bayesian model to active use or archive/remove it to reduce maintenance burden.

### MEDIUM — Hardcoded `end_year=2026` defaults in CLI and snapshot functions

- **Files:** `packages/pitlane-elo/src/pitlane_elo/cli.py:52`, `packages/pitlane-elo/src/pitlane_elo/snapshots.py:167`
- **Issue:** The default `--end-year` is hardcoded to `2026`. This will silently stop including data for 2027+ without a code change.
- **Fix:** Default to `datetime.now().year` or a configuration constant.

### MEDIUM — `cli_analyze.py` uses broad `except Exception` on every command

- **File:** `packages/pitlane-agent/src/pitlane_agent/cli_analyze.py:101,151,200,264,368,428,469,518,565,665,753,811,884,957,1001`
- **Issue:** Every CLI command wraps its core logic in `except Exception as e: raise click.ClickException(str(e))`. This collapses all failures (missing data, type errors, API errors) into a single generic error with no differentiated handling or recovery. Stack traces are suppressed.
- **Impact:** Difficult to diagnose failures; no distinction between transient (retry-able) and permanent errors.
- **Fix:** Catch specific exception types and provide typed error messages; log the full traceback before wrapping.

### LOW — `_upsert_parquet_table` builds SQL table name by string parsing

- **File:** `packages/pitlane-agent/src/pitlane_agent/utils/elo_db.py:304-309`
- **Issue:** `_table_name()` extracts the table name by splitting the CREATE TABLE SQL and skipping keywords. This is fragile: it will break if schema has comments, IF NOT EXISTS casing changes, or quoted identifiers are used.
- **Fix:** Pass the table name explicitly as a parameter rather than parsing SQL.

### LOW — `load_elo_history.py` default `--end-year` is hardcoded to 2025

- **File:** `packages/pitlane-agent/scripts/load_elo_history.py:28`
- **Issue:** The orchestrator script for bulk history loading has `default=2025` for `--end-year`, one year behind the ELO CLI default of 2026. The two defaults are inconsistent.
- **Fix:** Align defaults or derive from a shared constant.

---

## Dependencies

### HIGH — Numba incompatible with Python 3.14 (free-threaded)

- **File:** `packages/pitlane-elo/src/pitlane_elo/ratings/endure_elo.py:21` (`import numba as nb`)
- **Issue:** All three packages declare `requires-python = ">=3.12,<3.15"`, meaning Python 3.14 is nominally supported. However Numba (required by `pitlane-elo`) does not support Python 3.14 as of this writing. The project workaround (noted in commit `2b29da8`) redirects the Numba cache to `/tmp` and skips Bayesian tests on 3.14. If a user installs on Python 3.14 and attempts to use the ELO model, Numba will fail to JIT-compile.
- **Impact:** Silent breakage on Python 3.14; `pitlane-elo` is effectively Python 3.12/3.13 only.
- **Fix:** Either restrict `pitlane-elo` to `<3.14` until Numba adds 3.14 support, or add a runtime check with a clear error message.

### MEDIUM — `claude-agent-sdk>=0.1.40` is an internal/pre-release package with no upper bound

- **File:** `packages/pitlane-agent/pyproject.toml`
- **Issue:** The Claude Agent SDK has no upper-bound pin (`>=0.1.40` only). Breaking changes in a minor release of a pre-1.0 SDK could silently break the agent without a lockfile catching it.
- **Impact:** Potential breakage on fresh installs if the SDK introduces breaking changes.
- **Fix:** Pin to a tested minor version range (e.g., `>=0.1.40,<0.2.0`) until the SDK stabilizes at 1.0.

### MEDIUM — Ergast API dependency via FastF1 (service sunset risk)

- **Files:** `packages/pitlane-agent/tests/integration/conftest.py:56`, `packages/pitlane-agent/scripts/update_elo_data.py:62,103,159`
- **Issue:** The DNF classification pipeline and some integration tests reference Ergast. Ergast shut down its public API in late 2024 (now proxied via Jolpica/OpenF1). FastF1 internally redirects, but the codebase has comments acknowledging Ergast as the data source. If FastF1's Jolpica proxy changes behavior, DNF extraction may break silently.
- **Impact:** Data pipeline fragility; 2023+ DNF classification already degraded (see Tech Debt: DNF classification).

### LOW — `slowapi` is a community-maintained library with low release cadence

- **File:** `packages/pitlane-web/pyproject.toml` (`slowapi>=0.1.9`)
- **Issue:** `slowapi` is a thin wrapper around `limits` for FastAPI. It is lightly maintained. The import of the private name `_rate_limit_exceeded_handler` in `app.py:23` is fragile and may break on minor `slowapi` upgrades.
- **Fix:** Copy or re-implement the handler locally to remove the private import dependency.

---

## Reliability

### HIGH — No automatic workspace disk cleanup in production

- **Files:** `packages/pitlane-agent/src/pitlane_agent/cli.py:103`, `packages/pitlane-agent/src/pitlane_agent/commands/workspace/operations.py:312`
- **Issue:** Workspaces in `~/.pitlane/workspaces/` accumulate indefinitely. The `pitlane clean` CLI command exists but requires manual invocation. The web app has no lifecycle hook (FastAPI lifespan, cron, or background task) to evict old workspaces. Each workspace can contain chart images and conversation JSON files. With 100 sessions/day and no cleanup, disk use grows without bound.
- **Impact:** Production disk exhaustion over days to weeks.
- **Fix:** Add a FastAPI lifespan startup task or background `asyncio` task to prune workspaces older than N days on startup/periodically.

### MEDIUM — `AgentCache` LRU eviction drops agent without workspace cleanup

- **File:** `packages/pitlane-web/src/pitlane_web/agent_manager.py:64`
- **Issue:** When the LRU cache evicts an agent (`del self._cache[oldest_workspace]`), only the in-memory `F1Agent` object is removed. The corresponding workspace directory and charts on disk remain. Over time, all 100 LRU slots may be evicted many times while workspaces grow unboundedly on disk.
- **Impact:** Compounds the disk accumulation concern above.

### MEDIUM — `build_snapshots` always re-runs from `start_year`, no incremental resumption

- **File:** `packages/pitlane-elo/src/pitlane_elo/snapshots.py:165-238`
- **Issue:** The docstring states: _"Always re-runs from start_year because ELO ratings at race N depend on all prior races."_ For a full history rebuild (1970–2026, ~1,000 races), this is a multi-minute blocking operation. There is no checkpoint to resume a partially-failed run; if the process is interrupted, it must restart from scratch.
- **Impact:** Fragile long-running data pipeline; slow to recover from errors.
- **Fix:** Checkpoint model state more aggressively (which `save_checkpoint` partially does), or verify that `add_race_snapshot` incremental path is always preferred in production scripts.

### LOW — `update_elo_data.py` swallows all exceptions for individual rounds

- **File:** `packages/pitlane-agent/scripts/update_elo_data.py:415,421,477`
- **Issue:** Multiple `except Exception` clauses in the data update script continue processing on failure without re-raising. A failed round may be silently skipped and the database left with a gap.
- **Impact:** Silent data gaps in the ELO history; difficult to detect until downstream metrics are wrong.

### LOW — Rate limiter resets on app restart (in-memory storage)

- **File:** `packages/pitlane-web/src/pitlane_web/app.py:76`
- **Issue:** Because `storage_uri="memory://"`, all rate-limit counters reset when the process restarts. A client hitting the limit could trigger a restart (via an admin action or crash) to reset their quota.
- **Fix:** Use persistent storage (Redis or file-based) for rate-limit state in production.

---

## Test Coverage Gaps

### MEDIUM — No test coverage for workspace disk-space exhaustion or cleanup interaction

- **What's not tested:** The interaction between `AgentCache` LRU eviction and workspace disk accumulation. No test verifies that old workspaces are pruned in production scenarios.
- **Files:** `packages/pitlane-web/src/pitlane_web/agent_manager.py`, `packages/pitlane-agent/src/pitlane_agent/commands/workspace/operations.py`
- **Risk:** Silent disk exhaustion in production.
- **Priority:** Medium

### MEDIUM — No integration test for the full chat-to-response HTML rendering path

- **What's not tested:** The complete pipeline from `POST /api/chat` through agent execution, markdown rendering, path rewriting, and `| safe` output. `test_app.py` mocks the agent, so the Jinja2 filter chain is never exercised against real LLM output.
- **Files:** `packages/pitlane-web/tests/test_app.py`
- **Risk:** XSS or rendering regressions undetected until production.
- **Priority:** Medium

### LOW — Bayesian model tests excluded from CI (`--ignore=tests/bayesian`)

- **Files:** `packages/pitlane-elo/pyproject.toml:63`, `packages/pitlane-elo/tests/bayesian/`
- **Risk:** Regressions in the Bayesian code path are undetected.
- **Priority:** Low (model not in production use)

---

*Concerns audit: 2026-05-02*
