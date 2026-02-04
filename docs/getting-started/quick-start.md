# Quick Start

Get up and running with PitLane-AI in minutes. This guide will walk you through your first F1 analysis using both the CLI and web interface.

## CLI Quick Start

### 1. Install

```bash
pip install pitlane-agent
```

### 2. Create a Workspace

Workspaces isolate your analysis sessions and store generated charts:

```bash
pitlane workspace create --session-id monaco-analysis
```

### 3. Fetch Driver Information

Get information about F1 drivers:

```bash
pitlane fetch driver-info --season 2024 --limit 10
```

### 4. View Event Schedule

Check the race calendar:

```bash
pitlane fetch event-schedule --year 2024 --no-testing
```

### 5. Analyze Lap Times

Compare lap times between drivers at a specific race:

```bash
pitlane analyze lap-times \
  --session-id monaco-analysis \
  --year 2024 \
  --gp Monaco \
  --session Q \
  --drivers VER \
  --drivers HAM
```

This generates a lap time comparison chart saved in `~/.pitlane/workspaces/monaco-analysis/charts/`.

### 6. Analyze Tyre Strategy

Visualize pit stop and tyre compound usage:

```bash
pitlane analyze tyre-strategy \
  --session-id monaco-analysis \
  --year 2024 \
  --gp Monaco \
  --session R
```

### 7. Check Temporal Context

See what the agent knows about the current F1 season:

```bash
pitlane temporal-context
```

## Web Interface Quick Start

### 1. Install

```bash
pip install pitlane-web
```

### 2. Start the Server

```bash
uvx pitlane-web --env development
```

Or with tracing enabled:

```bash
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development
```

### 3. Open in Browser

Navigate to [http://localhost:8000](http://localhost:8000) in your web browser.

### 4. Create a Session

On the home page, create a new analysis session with a descriptive name.

### 5. Ask Questions

Try these example queries in the chat interface:

- "Show me lap time distributions for the Monaco 2024 qualifying session"
- "Compare Verstappen and Hamilton's tyre strategies at Monaco"
- "What are the upcoming races this season?"
- "Give me information about driver VER"

### 6. View Generated Charts

Charts are automatically displayed in the chat interface and saved to your workspace.

## Python API Quick Start

For programmatic access:

```python
import asyncio
from pitlane_agent import F1Agent

async def main():
    # Create an agent
    agent = F1Agent(session_id="my-analysis")

    # Stream a response
    async for chunk in agent.chat("Compare lap times for VER and HAM at Monaco 2024 qualifying"):
        print(chunk, end="", flush=True)

    print()  # New line after response

# Run the async function
asyncio.run(main())
```

## Workspace Management

### List Workspaces

```bash
pitlane workspace list
```

### View Workspace Info

```bash
pitlane workspace info --session-id monaco-analysis
```

### Clean Old Workspaces

Remove workspaces older than 7 days:

```bash
pitlane workspace clean --older-than 7 --yes
```

### Remove a Specific Workspace

```bash
pitlane workspace remove --session-id monaco-analysis --yes
```

## Common Session Types

When using the `--session` parameter, these are the valid session types:

- `FP1` - Free Practice 1
- `FP2` - Free Practice 2
- `FP3` - Free Practice 3
- `Q` - Qualifying
- `SQ` - Sprint Qualifying
- `S` - Sprint Race
- `R` - Race

## Example Workflows

### Analyzing a Complete Race Weekend

```bash
# Create workspace
pitlane workspace create --session-id silverstone-2024

# Analyze qualifying
pitlane analyze lap-times \
  --session-id silverstone-2024 \
  --year 2024 --gp "Great Britain" --session Q \
  --drivers VER --drivers NOR

# Analyze race tyre strategy
pitlane analyze tyre-strategy \
  --session-id silverstone-2024 \
  --year 2024 --gp "Great Britain" --session R

# View all generated charts
ls -lh ~/.pitlane/workspaces/silverstone-2024/charts/
```

### Comparing Multiple Drivers

```bash
pitlane analyze lap-times \
  --session-id multi-driver \
  --year 2024 --gp Monaco --session R \
  --drivers VER \
  --drivers HAM \
  --drivers LEC \
  --drivers NOR
```

## Tips

!!! tip "Grand Prix Names"
    Use the official race names or country names for the `--gp` parameter. Examples:

    - `Monaco`, `"Great Britain"`, `Italy`, `Singapore`
    - Multi-word names should be quoted: `"Saudi Arabia"`, `"United States"`

!!! tip "Session IDs"
    Use descriptive session IDs that indicate the race or analysis type:

    - `monaco-quali-analysis`
    - `bahrain-2024-strategy`
    - `verstappen-performance`

!!! tip "View Charts"
    Charts are saved in `~/.pitlane/workspaces/<session-id>/charts/` with timestamps in the filenames for easy organization.

## Next Steps

- [Configuration](configuration.md) - Configure environment variables and settings
- [CLI Reference](../user-guide/cli-reference.md) - Complete CLI command reference
- [Web Interface](../user-guide/web-interface.md) - Learn more about the web interface
- [Analysis Types](../user-guide/analysis-types.md) - Detailed guide to analysis capabilities
