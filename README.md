# PitLane-AI

AI-powered Formula 1 data analysis - from lap times and tyre strategy to race telemetry and historical insights. Built with [Claude's Agent SDK](https://github.com/anthropics/anthropic-sdk-python) to demonstrate practical applications of AI agents in domain-specific analysis. This project explores the intersection of motorsport data and modern agent architectures.

## What It Analyzes

- **Lap Time Analysis** - Compare driver performance with visual lap time distributions
- **Tyre Strategy** - Visualize pit stop patterns and compound usage across races
- **Race Telemetry** - Access detailed session data for qualifying, practice, and race sessions
- **Driver Information** - Query F1 driver rosters, codes, and metadata from 1950 to present
- **Event Schedules** - Browse complete season calendars with session timings and locations

## Prerequisites

PitLane-AI uses [Claude](https://www.anthropic.com/claude) as its AI backbone. You'll need an Anthropic API key to run the agent.

1. Get an API key at [console.anthropic.com](https://console.anthropic.com)
2. Set it in your environment:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

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

#### Quick Start (Recommended)

```bash
# Development mode with auto-reload
uvx pitlane-web --env development

# With tracing enabled
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development

# Custom port
uvx pitlane-web --port 3000

# See all options
uvx pitlane-web --help
```

#### Alternative: Direct uvicorn (for workspace development)

```bash
uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload
```

> If pitlane_web is not found run `uv sync --all-packages --reinstall` and retry

### Tracing

Enable OpenTelemetry tracing to observe agent behavior:

```bash
# Enable tracing to see tool calls, permission checks, and decision flows
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development

# Use batch processor for production workloads
PITLANE_TRACING_ENABLED=1 PITLANE_SPAN_PROCESSOR=batch uvx pitlane-web --env development
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
