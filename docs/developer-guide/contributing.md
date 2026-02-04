# Contributing

Thank you for considering contributing to PitLane-AI! This guide will help you get started.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the project

## Getting Started

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/PitLane-AI.git
   cd PitLane-AI
   ```
3. **Set up development environment:**
   ```bash
   uv sync
   ```
4. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### 1. Make Changes

Edit code in `packages/pitlane-agent/` or `packages/pitlane-web/`:

```bash
vim packages/pitlane-agent/src/pitlane_agent/agent.py
```

### 2. Run Tests

```bash
# Run all tests
uv run pytest

# Run specific tests
uv run pytest packages/pitlane-agent/tests/test_agent.py

# Run with coverage
uv run pytest --cov
```

### 3. Format Code

```bash
# Format with ruff
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

### 4. Commit Changes

Use [conventional commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat: add new skill for race predictions"
git commit -m "fix: resolve session timeout issue"
git commit -m "docs: update CLI reference"
```

**Commit Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a Pull Request on GitHub with:
- Clear title and description
- Reference related issues (#123)
- Include screenshots/examples if applicable

## Contribution Types

### Bug Fixes

1. Create an issue describing the bug
2. Reference the issue in your PR
3. Include a test case demonstrating the fix

### New Features

1. Discuss the feature in an issue first
2. Get approval before implementing
3. Include tests and documentation
4. Update relevant docs/

### Documentation

- Fix typos and improve clarity
- Add missing examples
- Update API references
- Improve getting started guides

### Tests

- Add missing test coverage
- Improve test reliability
- Add integration tests

## Code Standards

### Python Style

- Follow PEP 8 (enforced by ruff)
- Maximum line length: 120 characters
- Use type hints where helpful
- Write descriptive docstrings

**Example:**
```python
def fetch_lap_times(
    session_id: str,
    year: int,
    gp_name: str,
    session_type: str,
) -> dict[str, Any]:
    """Fetch lap times for a session.

    Args:
        session_id: Workspace session ID.
        year: Season year.
        gp_name: Grand Prix name (e.g., "Monaco").
        session_type: Session code (R, Q, FP1, etc.).

    Returns:
        Dictionary with lap time data and statistics.

    Raises:
        ValueError: If session not found.
    """
    ...
```

### Testing Standards

- Write tests for new features
- Maintain >80% code coverage
- Use descriptive test names
- Include both positive and negative cases

**Example:**
```python
def test_agent_initialization_with_explicit_session_id():
    """Agent should use provided session ID."""
    agent = F1Agent(session_id="test-123")
    assert agent.session_id == "test-123"

def test_agent_initialization_generates_session_id():
    """Agent should generate UUID if no session ID provided."""
    agent = F1Agent()
    assert len(agent.session_id) == 36  # UUID format
```

## Documentation Standards

### Docstrings

Use Google-style docstrings:

```python
def create_workspace(session_id: str | None = None) -> dict:
    """Create a new workspace.

    Args:
        session_id: Session identifier. Auto-generated if None.

    Returns:
        Dictionary with workspace information:
        {
            "session_id": str,
            "workspace_path": str,
            "created_at": str,
        }

    Raises:
        ValueError: If workspace already exists.

    Example:
        >>> info = create_workspace(session_id="my-session")
        >>> print(info["workspace_path"])
        ~/.pitlane/workspaces/my-session
    """
```

### MkDocs Pages

Follow existing structure:
- Use clear headings
- Include code examples
- Link to related pages
- Add diagrams where helpful

## Review Process

### What We Look For

1. **Code Quality:**
   - Clean, readable code
   - Proper error handling
   - Type hints where helpful

2. **Tests:**
   - New tests for new features
   - Tests pass locally
   - Good coverage

3. **Documentation:**
   - Docstrings updated
   - User docs updated if needed
   - Changelog entry (for features/fixes)

4. **Style:**
   - Passes ruff checks
   - Follows project conventions

### Review Timeline

- Initial review within 3-5 days
- Follow-up reviews within 1-2 days
- Merge after approval from maintainer

## Getting Help

- **Questions:** Open a GitHub issue with the "question" label
- **Bugs:** Open a GitHub issue with the "bug" label
- **Features:** Open a GitHub issue with the "enhancement" label

## Related Documentation

- [Setup](setup.md) - Development environment
- [Testing](testing.md) - Writing tests
- [Code Quality](code-quality.md) - Code standards
- [Adding Skills](adding-skills.md) - Creating new skills
