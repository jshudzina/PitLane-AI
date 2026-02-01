# PitLane-AI

AI-powered Formula 1 data analysis - from lap times and tyre strategy to race telemetry and historical insights. Built with [Claude's Agent SDK](https://github.com/anthropics/anthropic-sdk-python) to demonstrate practical applications of AI agents in domain-specific analysis. This project explores the intersection of motorsport data and modern agent architectures.

## What It Analyzes

- **Lap Time Analysis** - Compare driver performance with visual lap time distributions
- **Tyre Strategy** - Visualize pit stop patterns and compound usage across races
- **Race Telemetry** - Access detailed session data for qualifying, practice, and race sessions
- **Driver Information** - Query F1 driver rosters, codes, and metadata from 1950 to present
- **Event Schedules** - Browse complete season calendars with session timings and locations

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

> If pitlane_web is not found run  `uv sync --all-packages --reinstall` and retry

### Tracing

Enable OpenTelemetry tracing to observe agent behavior in the web app:

```bash
# Local development (sets secure cookie flag to false for HTTP)
PITLANE_ENV=development uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload

# Enable tracing to see tool calls, permission checks, and decision flows
PITLANE_ENV=development PITLANE_TRACING_ENABLED=1 uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload

# Use batch processor for production workloads
PITLANE_TRACING_ENABLED=1 PITLANE_SPAN_PROCESSOR=batch uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload
```

Trace output is written to stderr and shows how the agent reasons through F1 analysis requests.

## How It Works

PitLane-AI demonstrates key features of Claude's Agent SDK through a skills-based architecture:

### Agent Architecture

The agent uses specialized **skills** to handle different F1 analysis domains:
- **f1-analyst** - Lap time and tyre strategy analysis with visualizations
- **f1-drivers** - Driver information queries via the Ergast API
- **f1-schedule** - Event calendars and session schedules

Each skill invokes Python scripts through the agent's tool system, using FastF1 for data access and matplotlib for visualizations.

### Tool Permissions

The agent demonstrates **tool permission controls** through domain-restricted web access. The WebFetch tool is limited to F1-related domains (`wikipedia.org`, `ergast.com`, `formula1.com`) - showing how agents can be safely constrained to approved data sources. See [tool_permissions.py](packages/pitlane-agent/src/pitlane_agent/tool_permissions.py) for configuration.

### Observable Agent Behavior

Optional OpenTelemetry tracing shows how the agent works under the hood - which tools it calls, permission checks, and decision flows. This makes the agent's reasoning transparent and debuggable. See the Development section below for tracing configuration.
