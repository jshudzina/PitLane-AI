# PitLane-AI

<div align="center">
  <img src="https://img.shields.io/pypi/v/pitlane-web" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/pitlane-web" alt="Python versions">
  <img src="https://img.shields.io/github/license/jshudzina/PitLane-AI" alt="License">
</div>

!!! info "Claude Agent SDK Demonstration"
    PitLane-AI demonstrates practical patterns for building AI agents:

    - **Skills** - Composable, domain-specific agent capabilities
    - **Progressive Disclosure** - Just-in-time context via temporal awareness
    - **Tool Permissions** - Layered restrictions for safe agent behavior

AI-powered Formula 1 data analysis built with [Claude's Agent SDK](https://github.com/anthropics/anthropic-sdk-python). Uses [FastF1](https://docs.fastf1.dev/) for telemetry and [jolpica-f1](https://github.com/jolpica/jolpica-f1) for historical data.

## What It Analyzes

- **Lap Time Analysis** - Compare driver performance with visual lap time distributions
- **Tyre Strategy** - Visualize pit stop patterns and compound usage across races
- **Race Telemetry** - Access detailed session data for qualifying, practice, and race sessions
- **Driver Information** - Query F1 driver rosters, codes, and metadata from 1950 to present
- **Event Schedules** - Browse complete season calendars with session timings and locations

## Quick Start

!!! tip "Before you begin"
    PitLane-AI requires an Anthropic API key. Get one at [console.anthropic.com](https://console.anthropic.com) and set it in your environment:

    ```bash
    export ANTHROPIC_API_KEY=sk-ant-...
    ```

=== "CLI"

    ```bash
    # Install
    pip install pitlane-agent

    # Create workspace
    pitlane workspace create --workspace-id my-analysis

    # Analyze Monaco qualifying
    pitlane analyze lap-times --workspace-id my-analysis \
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

| | |
|---|---|
| **[Getting Started](getting-started/installation.md)** | Install PitLane-AI and run your first analysis |
| **[Architecture](architecture/overview.md)** | Understand the agent system, skills, and temporal context |
| **[User Guide](user-guide/web-interface.md)** | Learn how to use the web interface |
| **[Developer Guide](developer-guide/setup.md)** | Contribute and build custom skills |

## Key Features

**Skills** - Three specialized skills handle different F1 domains: `f1-analyst` (lap times, strategy), `f1-drivers` (driver info), and `f1-schedule` (calendars). Each skill has its own tool restrictions. [Learn more →](architecture/skills.md)

**Temporal Context** - The agent knows "where we are" in the F1 season. Queries like "analyze the last race" work without specifying which race. [Learn more →](architecture/temporal-context.md)

**Tool Permissions** - Demonstrates layered security: WebFetch limited to F1 domains, Bash restricted to `pitlane` CLI, file access constrained to workspace. [Learn more →](architecture/tool-permissions.md)

## License

PitLane-AI is licensed under the Apache License 2.0. See the [License](license.md) page for details.
