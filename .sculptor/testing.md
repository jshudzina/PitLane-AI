# Testing

## Branch Naming
- **Bug-fix branches:** `fix/<short-description>`
- **Feature branches:** `feat/<short-description>`
- **Test-only branches:** `test/<short-description>`
- **Example:** `fix/cli-stories-error-handling`

## Test Strategy
Write unit tests for all behavioral changes. Use `pytest` with `click.testing.CliRunner` for CLI commands. Mock external dependencies (filesystem, database, workspace functions) using `unittest.mock.patch`. Integration tests that write real parquet files (like `test_signals.py`) are acceptable for core signal logic. Prefer testing the public API; only test private helpers when they contain non-trivial logic. No manual testing infrastructure exists — verify all changes via the test suite.

## Test Framework
- **Framework:** pytest
- **Run a test file:** `uv run pytest packages/pitlane-elo/tests/test_cli_stories.py -v`
- **Run a single test:** `uv run pytest packages/pitlane-elo/tests/test_cli_stories.py::TestDetectOutput::test_no_snapshots_exits_zero_with_empty_signals -v`
- **Run all tests:** `uv run pytest -v`
- **Test location:**
  - `pitlane-elo` tests: `packages/pitlane-elo/tests/`
  - `pitlane-agent` tests: `packages/pitlane-agent/tests/`
- **Conventions:** Test classes prefixed `Test`, test functions prefixed `test_`. See `packages/pitlane-elo/tests/test_cli_stories.py` and `packages/pitlane-agent/tests/test_cli_stories.py` as CLI test references.
