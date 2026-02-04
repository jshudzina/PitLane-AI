# Development Setup

Set up your local development environment for contributing to PitLane-AI.

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) package manager
- Git

## Installation

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### 2. Clone Repository

```bash
git clone https://github.com/jshudzina/PitLane-AI.git
cd PitLane-AI
```

### 3. Install Dependencies

```bash
# Install all workspace dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

This installs both `pitlane-agent` and `pitlane-web` packages with development dependencies.

## Project Structure

```
PitLane-AI/
├── pyproject.toml          # Workspace configuration
├── uv.lock                 # Dependency lockfile
├── packages/
│   ├── pitlane-agent/      # Core agent library
│   │   ├── pyproject.toml
│   │   ├── src/pitlane_agent/
│   │   └── tests/
│   └── pitlane-web/        # Web interface
│       ├── pyproject.toml
│       ├── src/pitlane_web/
│       └── tests/
└── docs/                   # Documentation (this site)
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific package tests
uv run --directory packages/pitlane-agent pytest
uv run --directory packages/pitlane-web pytest

# Run with coverage
uv run pytest --cov=pitlane_agent --cov=pitlane_web

# Run integration tests only
uv run pytest -m integration

# Run unit tests only (exclude integration)
uv run pytest -m "not integration"
```

## Code Quality

### Linting and Formatting

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Type Checking

```bash
# Run mypy
uv run mypy packages/pitlane-agent/src
uv run mypy packages/pitlane-web/src
```

## Running Locally

### CLI

```bash
# Run pitlane CLI
uv run pitlane --help

# Run agent in interactive mode
uv run pitlane-agent
```

### Web Interface

```bash
# Development mode with auto-reload
uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload

# Or using the CLI
uvx pitlane-web --env development
```

Visit [http://localhost:8000](http://localhost:8000)

## Environment Configuration

Create `.env` file (optional):

```bash
# Tracing
PITLANE_TRACING_ENABLED=1
PITLANE_SPAN_PROCESSOR=simple

# API Keys (if needed for extensions)
ANTHROPIC_API_KEY=sk-ant-...

# Cache directory (optional)
PITLANE_CACHE_DIR=~/.pitlane/cache
```

## Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**
   ```bash
   # Edit code
   vim packages/pitlane-agent/src/pitlane_agent/agent.py
   ```

3. **Run tests**
   ```bash
   uv run pytest
   ```

4. **Format code**
   ```bash
   uv run ruff format .
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

## Troubleshooting

### Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'pitlane_agent'`

**Solution:**
```bash
uv sync --all-packages --reinstall
```

### Test Failures

**Problem:** Tests fail with import errors

**Solution:** Ensure you're using `uv run` to execute tests:
```bash
uv run pytest  # Not: pytest
```

### Cache Issues

**Problem:** Stale test cache

**Solution:**
```bash
# Clear pytest cache
rm -rf .pytest_cache
rm -rf packages/*/.pytest_cache

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

## Next Steps

- [Project Structure](project-structure.md) - Detailed codebase layout
- [Contributing](contributing.md) - Contribution guidelines
- [Testing](testing.md) - Writing and running tests
- [Code Quality](code-quality.md) - Code standards
