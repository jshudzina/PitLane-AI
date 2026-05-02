# Testing Patterns

Pytest-based test suite split across three packages with unit, integration, and async test types; no coverage enforcement threshold.

**Analysis Date:** 2026-05-02

## Test Framework

**Runner:**
- pytest 9.x
- Root config: `/pyproject.toml` (workspace-level)
- Package-level overrides: `packages/pitlane-agent/pyproject.toml`, `packages/pitlane-elo/pyproject.toml`

**Plugins:**
- `pytest-asyncio>=0.24` — async test support
- `pytest-cov>=4.1` — coverage reporting
- `pytest-mock>=3.12` — monkeypatch + MagicMock integration
- `pytest-timeout>=2.2.0` — test timeout enforcement

**Assertion Library:**
- pytest built-in `assert` statements (no separate assertion library)

**Run Commands:**
```bash
# Run all non-integration tests for pitlane-agent (from package dir)
cd packages/pitlane-agent && uv run pytest -m "not integration"

# Run all tests for pitlane-web (from package dir)
cd packages/pitlane-web && uv run pytest

# Run with coverage (XML + terminal output)
cd packages/pitlane-agent && uv run pytest -m "not integration" --cov --cov-report=xml --cov-report=term

# Run the full workspace test suite (from repo root)
uv run pytest

# Run only integration tests (requires FastF1 network access)
cd packages/pitlane-agent && uv run pytest -m integration

# Run with verbose output showing all results including passes
cd packages/pitlane-agent && uv run pytest -ra
```

## Test File Organization

**Location:**
- Separate `tests/` directory inside each package (not co-located with source)
- `packages/pitlane-agent/tests/`
- `packages/pitlane-elo/tests/`
- `packages/pitlane-web/tests/`

**Naming:**
- All test files named `test_<feature>.py`: `test_agent.py`, `test_snapshots.py`, `test_app.py`
- No `*_test.py` files observed in practice (only `test_*.py` pattern used)

**Structure:**
```
packages/pitlane-agent/tests/
├── __init__.py
├── conftest.py                          # shared fixtures
├── test_agent.py
├── test_cli.py
├── test_cli_stories.py
├── test_permission_hooks.py
├── test_tracing.py
├── test_webfetch_permissions.py
├── test_workspace.py
├── temporal/
│   ├── __init__.py
│   ├── test_cache.py
│   ├── test_context.py
│   └── test_formatter.py
└── integration/
    ├── __init__.py
    ├── conftest.py
    ├── test_fastf1_ergast_api.py
    ├── test_fastf1_event_schedule.py
    ├── test_fastf1_gear_shifts_map.py
    ├── test_fastf1_race_control.py
    ├── test_fastf1_season_summary.py
    ├── test_fastf1_session_loading.py
    ├── test_fastf1_temporal.py
    └── test_fastf1_track_map.py

packages/pitlane-elo/tests/
├── __init__.py
├── conftest.py
├── test_calibration.py
├── test_cli_stories.py
├── test_config.py
├── test_data.py
├── test_integration.py
├── test_snapshots.py

packages/pitlane-web/tests/
├── __init__.py
├── conftest.py
├── test_agent_manager.py
├── test_agent_manager_concurrency.py
├── test_app.py
├── test_config.py
├── test_filters.py
├── test_security.py
└── test_session.py
```

## Test Structure

**Suite Organization:**
```python
class TestF1AgentInitialization:
    """Tests for F1Agent initialization."""

    def test_init_default_workspace(self, tmp_path):
        """Test initialization creates workspace with auto-generated workspace ID."""
        with patch("pitlane_agent.agent.get_workspace_path", return_value=tmp_path / "workspace"):
            agent = F1Agent()
            assert agent.workspace_id is not None
```

- Class-based grouping: `Test<FeatureName>` or `Test<ClassName><Aspect>` (e.g., `TestF1AgentInitialization`, `TestStoriesDetectCommand`)
- Each test method has a one-sentence docstring stating the expected behavior
- `tmp_path` pytest built-in used for all temporary file system needs

**Async tests:**
```python
@pytest.mark.asyncio
async def test_chat_yields_text_chunks(self):
    """Test that chat yields text chunks from assistant messages."""
    ...
```
`asyncio_mode = "auto"` set at workspace level — `@pytest.mark.asyncio` is still used explicitly in some tests; both styles coexist.

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) + `pytest-mock` (`monkeypatch`)

**Patterns:**
```python
# Context manager patch for module-level functions
with patch("pitlane_agent.agent.get_workspace_path", return_value=tmp_path / "workspace"):
    agent = F1Agent()

# monkeypatch for env vars and attribute replacement
monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))

# AsyncMock for async methods
agent.chat_full = AsyncMock(return_value="Mocked agent response")
mock_cache.get_or_create = AsyncMock(return_value=mock_agent)
```

**What to mock:**
- FastF1 sessions (use `MagicMock` with explicit attribute assignment)
- External API calls (FastF1 cache, network requests)
- Workspace filesystem functions when testing agent logic
- The agent cache (`_agent_cache`) when testing web routes

**What NOT to mock:**
- DuckDB in-memory operations — real DuckDB connections are used with `tmp_path`-backed Parquet files in `pitlane-elo` tests
- Standard library file I/O when using `tmp_path`

## Fixtures and Factories

**Shared fixtures in conftest.py:**

`packages/pitlane-agent/tests/conftest.py`:
- `tmp_output_dir` — temporary workspace dir
- `mock_fastf1_session` — `MagicMock` session with realistic F1 data
- `mock_fastf1_cache` — monkeypatched FastF1 cache
- `sample_driver_data` — simple dict of driver abbreviations + race metadata
- `enable_tracing` / `disable_tracing` — reset global tracing state around tests

`packages/pitlane-elo/tests/conftest.py`:
- `tmp_db` — empty `tmp_path` directory for Parquet-backed DuckDB tests
- `populated_db` — `tmp_path` pre-populated with 1 season, 5 drivers
- `multi_race_db` — `tmp_path` with 2 seasons, 3 rounds each, includes DNF scenarios
- `cancelled_rounds_db` — `tmp_path` simulating a cancelled race round

`packages/pitlane-web/tests/conftest.py`:
- `test_session_id` — valid UUID string
- `invalid_session_ids` — list of boundary cases (empty, path traversal, non-UUID, wrong length)
- `tmp_workspace` — temp dir with `charts/` and `data/` subdirs plus `.metadata.json`
- `sample_chart_file` — minimal valid PNG bytes written to disk
- `mock_agent` — `MagicMock` F1Agent with `AsyncMock` for `chat_full`
- `app_client` — `fastapi.testclient.TestClient` with agent cache mocked

**Factory helpers (module-level in conftest or test files):**
```python
def make_race_entry(driver_id, finish, *, dnf_category="none", laps=57) -> RaceEntry:
    """Build a minimal RaceEntry dict for unit tests."""
    ...

def _make_signal(driver_id="VER", value=0.8, signal_type="hot_streak", ...) -> StorySignal:
    ...
```

**Test data:** DuckDB Parquet files written via `_write_race_parquet()` / `_write_qual_parquet()` helpers in `packages/pitlane-elo/tests/conftest.py`. Real DuckDB connections used (not mocked).

## Coverage

**Requirements:** No minimum threshold enforced — `--cov` flags present in CI but no `--cov-fail-under` setting.

**Coverage reports generated:**
- XML: `--cov-report=xml` (for CI artifact upload)
- Terminal: `--cov-report=term`

**View Coverage:**
```bash
cd packages/pitlane-agent && uv run pytest -m "not integration" --cov --cov-report=term
cd packages/pitlane-web && uv run pytest --cov --cov-report=term
```

**Gap:** `pitlane-elo` is not run with `--cov` in CI (`pr-checks.yml` only covers `pitlane-agent` and `pitlane-web`).

## Test Types

**Unit Tests:**
- Scope: individual functions/classes with all external dependencies mocked
- Location: `tests/test_*.py` (top-level in each package's `tests/`)
- Examples: `test_agent.py`, `test_snapshots.py`, `test_filters.py`

**Integration Tests (pitlane-agent):**
- Scope: real FastF1 API calls against live data
- Location: `packages/pitlane-agent/tests/integration/`
- Marker: `@pytest.mark.integration`
- Excluded from CI by default: `-m "not integration"` in `pr-checks.yml`
- To run locally: `uv run pytest -m integration` from `packages/pitlane-agent`

**End-to-End Tests:**
- Not present. No browser/HTTP-level E2E framework (no Playwright, no Selenium).

**CLI Tests:**
- Use `click.testing.CliRunner` to invoke CLI commands in-process
- Found in `test_cli.py`, `test_cli_stories.py` in both `pitlane-agent` and `pitlane-elo`

**Concurrency Tests:**
- `packages/pitlane-web/tests/test_agent_manager_concurrency.py` — tests concurrent agent cache access

## Markers

**pitlane-agent markers** (defined in `packages/pitlane-agent/pyproject.toml`):
- `integration` — real FastF1 API calls; deselect with `-m "not integration"` in CI
- `slow` — slow running tests

**pitlane-elo markers** (defined in `packages/pitlane-elo/pyproject.toml`):
- `slow` — slow running tests
- `bayesian` — PyMC-dependent tests; entire `tests/bayesian/` directory ignored by default (`--ignore=tests/bayesian`)

`--strict-markers` is enforced in both `pitlane-agent` and `pitlane-elo` — unregistered markers fail the test run.

## CI Test Execution

From `.github/workflows/pr-checks.yml`:
- Matrix: Python 3.12, 3.13, 3.14
- `pitlane-agent`: `pytest -m "not integration" --cov --cov-report=xml --cov-report=term`
- `pitlane-web`: `pytest --cov --cov-report=xml --cov-report=term`
- `pitlane-elo`: **not run in CI** (no test step for it in `pr-checks.yml`)

## Known Gaps

- `pitlane-elo` tests are not executed in CI (`pr-checks.yml`)
- No coverage minimum threshold — coverage could silently drop
- Integration tests require network access and real FastF1 data — must be run manually
- Bayesian tests (`tests/bayesian/`) are excluded by default in `pitlane-elo` due to Python 3.14 compatibility issues with PyMC/Numba

---

*Testing analysis: 2026-05-02*
