# PitLane Agent

AI agent for F1 data analysis using Claude Agent SDK and FastF1.

## Quick Start

```bash
# Install with pip/uv
pip install pitlane-agent

# Create a workspace
pitlane workspace create --session-id my-analysis

# Fetch session data
pitlane fetch session-info --session-id my-analysis --year 2024 --gp Monaco --session R

# Analyze lap times
pitlane analyze lap-times --session-id my-analysis --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
```

## Features

- **F1 Data Analysis** - Lap times, tyre strategy, race telemetry, and more
- **Skills-Based Architecture** - Specialized skills for different analysis domains
- **Workspace Management** - Isolated analysis sessions with persistent data
- **FastF1 Integration** - Direct access to comprehensive F1 data
- **Chart Generation** - Matplotlib-based visualizations
- **Tool Permissions** - Domain-restricted web access for safe agent operation

## Skills

### f1-analyst
Lap time and tyre strategy analysis with visualizations.

**Examples:**
```bash
pitlane analyze lap-times --session-id my-session --year 2024 --gp Monaco --session Q
pitlane analyze tyre-strategy --session-id my-session --year 2024 --gp Monaco --session R
```

### f1-drivers
Driver information queries via the Ergast API.

**Examples:**
```bash
pitlane fetch drivers --year 2024
pitlane fetch driver-info --driver-code VER
```

### f1-schedule
Event calendars and session schedules.

**Examples:**
```bash
pitlane fetch schedule --year 2024
pitlane fetch event-info --year 2024 --round 6
```

## Workspace Management

```bash
# Create workspace
pitlane workspace create --session-id my-analysis

# List workspaces
pitlane workspace list

# Get workspace info
pitlane workspace info --session-id my-analysis

# Clean old workspaces (older than 7 days)
pitlane workspace clean --older-than 7

# Remove specific workspace
pitlane workspace remove --session-id my-analysis
```

## Requirements

- Python 3.11 or higher (up to 3.13)
- Claude API key (for AI agent functionality)

## Dependencies

- **Claude Agent SDK** - AI agent orchestration
- **FastF1** - F1 data access and telemetry
- **Matplotlib** - Chart generation
- **Click** - CLI framework
- **OpenTelemetry** - Optional tracing support

## Architecture

The agent uses a skills-based architecture where each skill handles a specific F1 analysis domain:
- Skills invoke Python scripts through the agent's tool system
- FastF1 provides data access and telemetry processing
- Matplotlib generates visualizations
- Tool permissions restrict web access to approved F1 data sources

## License

Apache-2.0

## Links

- [GitHub Repository](https://github.com/jshudzina/PitLane-AI)
- [Documentation](https://github.com/jshudzina/PitLane-AI#readme)
- [Issues](https://github.com/jshudzina/PitLane-AI/issues)
