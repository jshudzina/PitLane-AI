# Configuration

PitLane-AI can be configured using environment variables, command-line flags, and programmatic parameters. This guide covers all configuration options.

## Environment Variables

### General Settings

#### PITLANE_TRACING_ENABLED

Enable OpenTelemetry tracing to observe agent behavior.

- **Type**: Boolean (`1`, `true`, `yes` for enabled)
- **Default**: Disabled
- **Example**:
  ```bash
  export PITLANE_TRACING_ENABLED=1
  ```

#### PITLANE_SPAN_PROCESSOR

Configure the OpenTelemetry span processor mode.

- **Type**: String (`simple` or `batch`)
- **Default**: `simple`
- **Values**:
  - `simple` - Immediate export (good for testing)
  - `batch` - Batched export (good for production)
- **Example**:
  ```bash
  export PITLANE_SPAN_PROCESSOR=batch
  ```

### Temporal Context Settings

These variables are automatically set by the temporal context system but can be referenced in your scripts:

#### PITLANE_CURRENT_SEASON

The current F1 season year.

- **Type**: Integer
- **Example**: `2026`

#### PITLANE_SEASON_PHASE

The current phase of the F1 season.

- **Type**: String
- **Values**: `pre_season`, `in_season`, `post_season`, `off_season`

#### PITLANE_CURRENT_RACE

The current race event name (if any).

- **Type**: String
- **Example**: `Monaco Grand Prix`

#### PITLANE_CURRENT_ROUND

The current round number (if any).

- **Type**: Integer

### Web Interface Settings

These are used when running `pitlane-web`:

#### PITLANE_WEB_HOST

The host address for the web server.

- **Type**: String
- **Default**: `0.0.0.0`
- **Example**:
  ```bash
  export PITLANE_WEB_HOST=127.0.0.1
  ```

#### PITLANE_WEB_PORT

The port for the web server.

- **Type**: Integer
- **Default**: `8000`
- **Example**:
  ```bash
  export PITLANE_WEB_PORT=3000
  ```

#### PITLANE_WEB_ENV

The environment mode.

- **Type**: String
- **Values**: `development`, `production`
- **Default**: `production`
- **Example**:
  ```bash
  export PITLANE_WEB_ENV=development
  ```

## CLI Configuration

### Global Flags

Most CLI commands accept these common flags:

#### --session-id

Specify the workspace/session ID for analysis.

```bash
pitlane analyze lap-times --session-id my-analysis ...
```

#### --help

Show help information for any command.

```bash
pitlane --help
pitlane workspace --help
pitlane analyze lap-times --help
```

### Command-Specific Options

#### Temporal Context

```bash
# Format: text, json, prompt
pitlane temporal-context --format json

# Verbosity: minimal, normal, detailed
pitlane temporal-context --verbosity detailed

# Force refresh from FastF1
pitlane temporal-context --refresh
```

#### Workspace Management

```bash
# Create with description
pitlane workspace create --session-id my-session --description "Monaco 2024 analysis"

# List all workspaces
pitlane workspace list --show-all

# Clean old workspaces
pitlane workspace clean --older-than 7 --yes
```

#### Analysis Commands

```bash
# Specify drivers (can be used multiple times)
pitlane analyze lap-times --drivers VER --drivers HAM --drivers LEC

# Specify year, grand prix, and session
pitlane analyze tyre-strategy --year 2024 --gp Monaco --session R
```

## Python API Configuration

When using the Python API, you can configure the agent programmatically:

```python
from pitlane_agent import F1Agent

# Create agent with temporal context injection
agent = F1Agent(
    session_id="my-analysis",
    inject_temporal_context=True  # Default: True
)

# Disable temporal context
agent = F1Agent(
    session_id="my-analysis",
    inject_temporal_context=False
)
```

## FastF1 Cache Configuration

PitLane-AI uses FastF1 for data access, which caches data locally.

### Cache Location

By default, FastF1 cache is stored in:

```
~/.pitlane/cache/fastf1/
```

### Clearing Cache

To clear the FastF1 cache:

```bash
rm -rf ~/.pitlane/cache/fastf1/
```

!!! warning
    Clearing the cache will require re-downloading data from FastF1 servers, which can take time for race sessions.

## Workspace Configuration

### Workspace Directory

Workspaces are stored in:

```
~/.pitlane/workspaces/<session-id>/
```

Each workspace contains:

- `metadata.json` - Session metadata
- `data/` - Fetched session and driver data
- `charts/` - Generated visualizations

### Workspace Lifecycle

Workspaces are created automatically when you run analysis commands with a `--session-id` parameter, or manually using:

```bash
pitlane workspace create --session-id my-session
```

## Tracing Configuration

### Console Tracing (Development)

For local development, traces are written to stderr:

```bash
PITLANE_TRACING_ENABLED=1 pitlane analyze lap-times ...
```

### Batch Tracing (Production)

For production workloads, use batch processing:

```bash
PITLANE_TRACING_ENABLED=1 PITLANE_SPAN_PROCESSOR=batch pitlane-web
```

### Trace Output

Traces show:

- Tool calls made by the agent
- Permission checks and validation
- Decision flows and reasoning
- Timing information

Example trace output:

```
[TRACE] Tool called: Bash(command="pitlane fetch driver-info --season 2024")
[TRACE] Permission check: ALLOWED - pitlane command
[TRACE] Tool result: Success (127 bytes)
```

## Configuration Precedence

Settings are applied in this order (last wins):

1. Default values (in code)
2. Environment variables
3. Command-line flags
4. Programmatic parameters (Python API)

Example:

```bash
# Environment variable sets default
export PITLANE_WEB_PORT=3000

# CLI flag overrides environment variable
pitlane-web --port 8080  # Uses port 8080, not 3000
```

## Advanced Configuration

### Custom Agent Configuration

For advanced use cases, you can customize the agent's behavior:

```python
from pitlane_agent.agent import F1Agent
from pitlane_agent.tool_permissions import get_tool_permission_callback

agent = F1Agent(
    session_id="custom-session",
    inject_temporal_context=True,
    # Add custom configuration here
)
```

### Custom Tool Permissions

See [Tool Permissions](../architecture/tool-permissions.md) for details on customizing allowed domains and tool restrictions.

## Troubleshooting

### Workspace Not Found

If you get "workspace not found" errors:

```bash
# List all workspaces
pitlane workspace list

# Create the workspace manually
pitlane workspace create --session-id your-session-id
```

### Cache Issues

If you experience data issues:

```bash
# Clear and refresh temporal context cache
pitlane temporal-context --refresh

# Clear FastF1 cache
rm -rf ~/.pitlane/cache/fastf1/
```

### Port Already in Use

If the web server port is already in use:

```bash
# Use a different port
pitlane-web --port 8080

# Or set via environment variable
export PITLANE_WEB_PORT=8080
pitlane-web
```

## Next Steps

- [CLI Reference](../user-guide/cli-reference.md) - Complete command reference
- [Architecture Overview](../architecture/overview.md) - Learn how PitLane-AI works
- [Temporal Context](../architecture/temporal-context.md) - Deep dive into temporal awareness
