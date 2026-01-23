# PitLane-AI
Bringing AI agents to F1 data analysis - interactive telemetry exploration, race strategy insights, and results analysis

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python package management in a monorepo workspace.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

## Development

### Code Quality

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Run linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Running the Web App

```bash
uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload
```
