# PitLane-AI

<div align="center">
  <img src="https://img.shields.io/pypi/v/pitlane-ai" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/pitlane-ai" alt="Python versions">
  <img src="https://img.shields.io/github/license/jshudzina/PitLane-AI" alt="License">
</div>

AI-powered Formula 1 data analysis - from lap times and tyre strategy to race telemetry and historical insights. Built with [Claude's Agent SDK](https://github.com/anthropics/anthropic-sdk-python) to demonstrate practical applications of AI agents in domain-specific analysis.

## What It Analyzes

- **Lap Time Analysis** - Compare driver performance with visual lap time distributions
- **Tyre Strategy** - Visualize pit stop patterns and compound usage across races
- **Race Telemetry** - Access detailed session data for qualifying, practice, and race sessions
- **Driver Information** - Query F1 driver rosters, codes, and metadata from 1950 to present
- **Event Schedules** - Browse complete season calendars with session timings and locations

## Quick Start

=== "CLI"

    ```bash
    # Install
    pip install pitlane-agent

    # Create workspace
    pitlane workspace create --session-id my-analysis

    # Analyze Monaco qualifying
    pitlane analyze lap-times --session-id my-analysis \
      --year 2024 --gp Monaco --session Q \
      --drivers VER --drivers HAM
    ```

=== "Web Interface"

    ```bash
    # Install
    pip install pitlane-web

    # Run web server
    uvx pitlane-web --env development

    # Visit http://localhost:8000
    ```

=== "Python API"

    ```python
    from pitlane_agent import F1Agent

    agent = F1Agent(session_id="my-analysis")

    async for chunk in agent.chat("Compare Verstappen and Hamilton lap times at Monaco 2024"):
        print(chunk, end="")
    ```

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install PitLane-AI and run your first analysis

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-architecture:{ .lg .middle } **Architecture**

    ---

    Understand the agent system, skills, and temporal context

    [:octicons-arrow-right-24: Architecture Overview](architecture/overview.md)

-   :material-book-open:{ .lg .middle } **User Guide**

    ---

    Learn how to use the web interface for F1 data analysis

    [:octicons-arrow-right-24: Web Interface](user-guide/web-interface.md)

-   :material-code-braces:{ .lg .middle } **Developer Guide**

    ---

    Contribute to PitLane-AI and build custom skills

    [:octicons-arrow-right-24: Setup](developer-guide/setup.md)

</div>

## Key Features

### Skills-Based Architecture

The agent uses specialized **skills** to handle different F1 analysis domains:

- **f1-analyst** - Lap time and tyre strategy analysis with visualizations
- **f1-drivers** - Driver information queries via the Ergast API
- **f1-schedule** - Event calendars and session schedules

Each skill invokes Python scripts through the agent's tool system, using FastF1 for data access and matplotlib for visualizations.

### Temporal Context Awareness

PitLane-AI includes a sophisticated temporal context system that provides real-time awareness of the F1 calendar:

- Knows the current season, phase (pre/in/post/off-season), and race weekend
- Detects live or recent sessions automatically
- Intelligently caches data based on temporal state
- Ensures queries like "latest race results" use the correct year and race

Learn more about the [Temporal Context System](architecture/temporal-context.md).

### Tool Permissions

The agent demonstrates **tool permission controls** through domain-restricted web access. The WebFetch tool is limited to F1-related domains (`wikipedia.org`, `ergast.com`, `formula1.com`) - showing how agents can be safely constrained to approved data sources.

See [Tool Permissions](architecture/tool-permissions.md) for details.

### Observable Behavior

Optional OpenTelemetry tracing shows how the agent works under the hood - which tools it calls, permission checks, and decision flows. This makes the agent's reasoning transparent and debuggable.

## Project Structure

PitLane-AI is a monorepo containing three tightly integrated Python packages:

- **pitlane-ai** - Meta-package bundling both agent and web interface
- **pitlane-agent** - Core AI agent for F1 data analysis with CLI
- **pitlane-web** - Web interface (FastAPI) for interactive F1 analysis

Learn more about the [Project Structure](developer-guide/project-structure.md).

## License

PitLane-AI is licensed under the Apache License 2.0. See the [License](license.md) page for details.
