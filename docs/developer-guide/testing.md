# Testing

PitLane-AI uses pytest for unit and integration testing with async support.

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific package
uv run --directory packages/pitlane-agent pytest
uv run --directory packages/pitlane-web pytest

# Run with coverage
uv run pytest --cov=pitlane_agent --cov=pitlane_web --cov-report=html

# Run integration tests only
uv run pytest -m integration

# Exclude integration tests
uv run pytest -m "not integration"

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

## Test Organization

### Unit Tests

Located in `packages/*/tests/`:

```python
# packages/pitlane-agent/tests/test_agent.py
def test_agent_creates_workspace(tmp_path):
    agent = F1Agent(workspace_dir=tmp_path)
    assert agent.workspace_dir.exists()

async def test_agent_chat_streaming():
    agent = F1Agent(session_id="test")
    chunks = []
    async for chunk in agent.chat("Hello"):
        chunks.append(chunk)
    assert len(chunks) > 0
```

### Integration Tests

Marked with `@pytest.mark.integration`:

```python
# packages/pitlane-agent/tests/integration/test_fastf1_temporal.py
import pytest

@pytest.mark.integration
async def test_temporal_context_fetches_live_data():
    """Test temporal context with live FastF1 API."""
    ctx = get_temporal_context(force_refresh=True)
    assert ctx.current_season >= 2024
```

## Fixtures

### Common Fixtures

```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def temp_workspace(tmp_path):
    """Temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "data").mkdir()
    (workspace / "charts").mkdir()
    return workspace

@pytest.fixture
def mock_session_id():
    """Fixed session ID for testing."""
    return "test-session-123"
```

### Agent Fixtures

```python
@pytest.fixture
async def agent(temp_workspace):
    """F1Agent instance with temp workspace."""
    agent = F1Agent(
        session_id="test",
        workspace_dir=temp_workspace,
        inject_temporal_context=False,  # Skip for speed
    )
    yield agent
```

## Writing Tests

### Test Structure

```python
def test_function_name():
    """Test description.

    Tests should:
    - Have clear, descriptive names
    - Include docstrings explaining what is tested
    - Test one behavior per test
    - Use arrange-act-assert pattern
    """
    # Arrange
    workspace = Path("/tmp/test")

    # Act
    result = create_workspace("test-id")

    # Assert
    assert result["session_id"] == "test-id"
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_agent_chat():
    agent = F1Agent(session_id="test")
    response = await agent.chat_full("Hello")
    assert isinstance(response, str)
```

### Mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_with_mock_claude():
    with patch("pitlane_agent.agent.ClaudeSDKClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.query = AsyncMock()
        agent = F1Agent(session_id="test")
        await agent.chat("Test")
        mock_client.return_value.__aenter__.return_value.query.assert_called_once()
```

## Test Markers

```python
# Mark integration tests
@pytest.mark.integration
def test_live_api():
    pass

# Mark slow tests
@pytest.mark.slow
def test_expensive_operation():
    pass

# Skip tests conditionally
@pytest.mark.skipif(os.getenv("CI"), reason="Skip in CI")
def test_local_only():
    pass
```

## Coverage

```bash
# Generate coverage report
uv run pytest --cov=pitlane_agent --cov=pitlane_web --cov-report=html

# Open coverage report
open htmlcov/index.html

# Check coverage threshold
uv run pytest --cov --cov-fail-under=80
```

## Best Practices

1. **Test isolation**: Each test should be independent
2. **Clear names**: `test_agent_raises_error_when_session_invalid()`
3. **Fast tests**: Mock external APIs, use temp directories
4. **Assertions**: Be specific (not just `assert result`)
5. **Edge cases**: Test both success and failure paths

## Related Documentation

- [Setup](setup.md) - Development environment
- [Contributing](contributing.md) - Contribution workflow
- [Code Quality](code-quality.md) - Code standards
