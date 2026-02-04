# Code Quality

PitLane-AI maintains high code quality through automated tooling and conventions.

## Linting and Formatting

### Ruff

We use [ruff](https://docs.astral.sh/ruff/) for both linting and formatting:

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check formatting (CI)
uv run ruff format --check .
```

### Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
]

[tool.ruff.lint.isort]
known-first-party = ["pitlane_agent", "pitlane_web"]
```

## Type Checking

### MyPy (Optional)

```bash
# Run type checking
uv run mypy packages/pitlane-agent/src
uv run mypy packages/pitlane-web/src
```

### Type Hints

Use type hints for function signatures:

```python
from typing import AsyncIterator

async def chat(self, message: str) -> AsyncIterator[str]:
    """Process chat message."""
    ...
```

## Code Style Guidelines

### Python Style

- **Line length**: 120 characters max
- **Imports**: Grouped by stdlib, third-party, first-party (enforced by ruff)
- **Naming**:
  - `snake_case` for functions, variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Docstrings

Use Google-style docstrings:

```python
def create_workspace(session_id: str | None = None) -> dict:
    """Create a new workspace directory.

    Args:
        session_id: Session identifier. Auto-generated if None.

    Returns:
        Dictionary with workspace information.

    Raises:
        ValueError: If workspace already exists.

    Example:
        >>> info = create_workspace("my-session")
        >>> print(info["workspace_path"])
    """
```

### Comments

```python
# Good: Explain WHY, not WHAT
# Use batch processor for production to reduce overhead
span_processor = BatchSpanProcessor(exporter)

# Bad: Redundant comment
# Set span processor to batch
span_processor = BatchSpanProcessor(exporter)
```

## Testing Standards

- Maintain **>80% code coverage**
- Write tests for new features
- Include both success and error cases
- Use descriptive test names

```python
def test_agent_initialization_with_explicit_session_id():
    """Agent should use provided session ID."""
    agent = F1Agent(session_id="test-123")
    assert agent.session_id == "test-123"
```

## Error Handling

### Specific Exceptions

```python
# Good: Specific exception
if not workspace_exists(session_id):
    raise ValueError(f"Workspace not found: {session_id}")

# Bad: Generic exception
if not workspace_exists(session_id):
    raise Exception("Workspace not found")
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log with context
logger.info("Creating workspace", extra={"session_id": session_id})
logger.error("Failed to fetch data", exc_info=True)
```

## Security Best Practices

### Path Validation

```python
# Always validate user input
from pathlib import Path

def is_within_workspace(file_path: str, workspace: str) -> bool:
    file_resolved = Path(file_path).resolve()
    workspace_resolved = Path(workspace).resolve()
    return str(file_resolved).startswith(str(workspace_resolved))
```

### Timing-Safe Comparison

```python
import secrets

# Use timing-safe comparison for secrets
def validate_session(cookie_session: str, expected: str) -> bool:
    return secrets.compare_digest(cookie_session, expected)
```

## Performance Considerations

### Async Operations

```python
# Good: Use async for I/O
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# Bad: Blocking I/O in async function
async def fetch_data_bad(url: str) -> str:
    response = requests.get(url)  # Blocks event loop
    return response.text
```

### Caching

```python
# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(x: int) -> int:
    return x ** 2
```

## CI/CD Checks

All pull requests must pass:

1. **Linting**: `ruff check .`
2. **Formatting**: `ruff format --check .`
3. **Tests**: `pytest`
4. **Coverage**: `pytest --cov --cov-fail-under=80`

## Pre-commit Hooks (Optional)

```bash
# Install pre-commit
uv pip install pre-commit

# Set up hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Related Documentation

- [Setup](setup.md) - Development environment
- [Testing](testing.md) - Writing tests
- [Contributing](contributing.md) - Contribution workflow
