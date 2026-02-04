# FastF1 Integration Tests

Integration tests that make **real API calls** to FastF1 and the Ergast API to verify the library integration works correctly.

## Overview

These tests differ from the unit tests in the main `tests/` directory:

- **Unit tests** (in `tests/scripts/`, etc.) use mocks and run quickly
- **Integration tests** (here) make real API calls and can be slow

Integration tests verify that:
- FastF1 library integration works correctly
- Real F1 data is retrieved and processed properly
- Session loading, event schedules, and Ergast API calls function as expected
- Temporal analysis works with real schedule data

## Running Integration Tests

### Run all integration tests

```bash
cd packages/pitlane-agent
uv run pytest -m integration -v
```

### Run specific integration test file

```bash
uv run pytest tests/integration/test_fastf1_event_schedule.py -v
uv run pytest tests/integration/test_fastf1_ergast_api.py -v
uv run pytest tests/integration/test_fastf1_session_loading.py -v
uv run pytest tests/integration/test_fastf1_temporal.py -v
```

### Run integration tests with timeout

Some tests (especially session loading with telemetry) can be slow:

```bash
uv run pytest -m integration -v --timeout=300
```

### Skip integration tests (default for development)

```bash
# Run only fast unit tests
uv run pytest -m "not integration"
```

## Test Organization

| File | Purpose | Speed |
|------|---------|-------|
| `test_fastf1_event_schedule.py` | Event schedule retrieval (`get_event_schedule()`) | Fast |
| `test_fastf1_ergast_api.py` | Ergast API driver info (`fastf1.ergast`) | Fast |
| `test_fastf1_session_loading.py` | Session loading, lap data, telemetry | Slow |
| `test_fastf1_temporal.py` | Temporal analyzer with real schedules | Medium |

## Test Data Strategy

Integration tests use **2025 season data** as the primary test dataset:

- **2025 season**: Most recent complete season with stable, finalized data
- **Monaco GP**: Classic race used for testing
- **Bahrain GP**: First race of 2025, used for "recent" data tests
- **Session-scoped cache**: Shared across all tests to reduce API calls

### Why 2025?

- Complete season with all results finalized
- Won't change or become incomplete (unlike current/future seasons)
- Provides stable, predictable data for tests

## Fixtures

Integration tests use special fixtures defined in `conftest.py`:

### `fastf1_cache_dir`
- Session-scoped temporary cache directory
- Shared across all integration tests
- Reduces API calls by caching responses

### `stable_test_data`
- Provides 2025 season test parameters
- Includes year, test GP (Monaco), drivers, round count

### `recent_race_data`
- Provides 2025 Bahrain GP (round 1) data
- Used for testing with recent but complete race data

### `skip_if_no_internet`
- Gracefully skips tests if no internet connection
- Useful for offline development

## CI Behavior

Integration tests are **skipped in CI by default** to keep builds fast and avoid network dependencies.

### Regular CI (PR checks)
```bash
pytest -m "not integration"  # Skips integration tests
```

### Manual Integration Test Runs

To run integration tests in CI, include `[run-integration]` in your commit message:

```bash
git commit -m "Add new FastF1 feature [run-integration]"
```

Or manually trigger the integration test workflow (if configured).

## Adding New Integration Tests

When adding new integration tests:

1. **Mark with `@pytest.mark.integration`**
   ```python
   @pytest.mark.integration
   def test_my_integration(self, fastf1_cache_dir):
       # test code
   ```

2. **Use `@pytest.mark.slow` for slow operations**
   ```python
   @pytest.mark.integration
   @pytest.mark.slow
   def test_slow_operation(self):
       # test code
   ```

3. **Use session-scoped cache**
   ```python
   def test_something(self, fastf1_cache_dir, stable_test_data):
       # fastf1_cache_dir enables caching
       # stable_test_data provides 2025 season parameters
   ```

4. **Add timeout for very slow tests**
   ```python
   @pytest.mark.integration
   @pytest.mark.timeout(300)  # 5 minutes
   def test_telemetry_loading(self):
       # slow test code
   ```

5. **Use stable historical data (2025 season)**
   - Avoid using current/future seasons which may be incomplete
   - Use `stable_test_data` fixture for consistent test parameters

## Troubleshooting

### Tests are very slow
- First run downloads and caches data (slow)
- Subsequent runs use cache (much faster)
- Consider running specific test files instead of all tests

### Network errors
- Ensure internet connection is available
- FastF1/Ergast APIs may occasionally be down
- Tests will fail if APIs are unreachable

### Cache issues
- Cache is session-scoped and temporary
- Each test session gets a fresh cache directory
- Old cache is automatically cleaned up

### Data changes
- F1 data occasionally gets corrected (e.g., penalties)
- If tests start failing, data may have been updated
- Update test assertions to match current reality

## Best Practices

1. **Run integration tests before major releases** to verify FastF1 integration
2. **Don't run integration tests on every code change** (too slow)
3. **Use unit tests for rapid development** (fast, mocked)
4. **Use integration tests for verification** (slow, real API)
5. **Keep integration tests focused** on critical FastF1 operations
6. **Use session cache** to avoid redundant API calls

## Example Output

```bash
$ uv run pytest -m integration -v

tests/integration/test_fastf1_event_schedule.py::TestEventScheduleIntegration::test_get_full_season_schedule PASSED
tests/integration/test_fastf1_event_schedule.py::TestEventScheduleIntegration::test_get_specific_round PASSED
tests/integration/test_fastf1_ergast_api.py::TestErgastAPIIntegration::test_get_driver_by_code PASSED
...

====== 18 passed in 45.23s ======
```

## See Also

- Main test suite: `tests/` directory
- FastF1 documentation: https://docs.fastf1.dev/
- Ergast API: http://ergast.com/mrd/
