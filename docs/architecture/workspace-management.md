# Workspace Management

PitLane-AI uses **workspaces** to isolate agent data, ensuring clean separation between conversations and enabling concurrent multi-user deployments.

## Overview

Each F1Agent operates in its own workspace directory, providing:

- **Data Isolation**: Workspace data never conflicts or mixes
- **Concurrent Access**: Multiple agents can run simultaneously
- **Resource Management**: Old workspaces can be cleaned up
- **Reproducibility**: Workspace data persists for debugging

## Workspace Structure

### Directory Layout

```
~/.pitlane/
├── workspaces/
│   ├── <workspace-id-1>/
│   │   ├── .metadata.json
│   │   ├── data/
│   │   │   ├── session_info.json
│   │   │   ├── drivers.json
│   │   │   └── schedule.json
│   │   └── charts/
│   │       ├── lap_times.png
│   │       └── strategy.png
│   └── <workspace-id-2>/
│       └── ...
└── cache/
    ├── fastf1/              # Shared FastF1 cache
    └── temporal/            # Temporal context cache
```

### Workspace Components

**`.metadata.json`**: Workspace metadata
```json
{
  "workspace_id": "abc123-def456-...",
  "created_at": "2024-05-23T14:30:00Z",
  "last_accessed": "2024-05-23T15:45:00Z",
  "description": "Monaco 2024 analysis"  // optional
}
```

**`data/`**: Workspace-specific data files
- JSON outputs from CLI commands
- Query results (drivers, schedules, session info)
- Intermediate analysis data

**`charts/`**: Generated visualizations
- PNG images from matplotlib
- Lap time distributions
- Strategy visualizations
- Telemetry plots

## Workspace Lifecycle

### 1. Creation

Workspaces are created automatically when F1Agent is initialized:

```python
agent = F1Agent()  # Auto-generates workspace ID and creates workspace
```

Or with explicit workspace ID:

```python
agent = F1Agent(workspace_id="my-workspace-123")
```

**Creation Process**:
1. Generate UUID workspace ID (if not provided)
2. Check for collision (retry up to 3 times for auto-generated IDs)
3. Create directory structure (`workspace/`, `data/`, `charts/`)
4. Write `.metadata.json` with timestamp
5. Ensure shared cache directories exist

**Collision Handling**: Auto-generated UUIDs handle collisions gracefully:
```python
create_workspace(workspace_id=None, max_retries=3)
# Retries UUID generation if workspace already exists
```

Explicit workspace IDs fail immediately if workspace exists:
```python
create_workspace(workspace_id="explicit-id")
# Raises ValueError if workspace exists
```

### 2. Access

On each agent initialization:
- `last_accessed` timestamp updated in `.metadata.json`
- Atomic write using tempfile + rename (POSIX guarantee)
- Missing metadata recreated if needed

### 3. Cleanup

Old workspaces can be removed:

```bash
# Remove workspaces older than 7 days
pitlane workspace clean --older-than-days 7

# Remove all workspaces
pitlane workspace clean --all
```

**Cleanup Logic**:
1. Iterate through workspace directories
2. Read `.metadata.json` to check `last_accessed`
3. Calculate age from current time
4. Remove if age exceeds threshold
5. Return cleanup stats (count, workspace IDs)

## Workspace ID Propagation

The workspace ID flows through the system via **environment variable**:

```python
# F1Agent sets workspace ID for skills
os.environ["PITLANE_WORKSPACE_ID"] = self.workspace_id

# Skills access workspace ID
workspace_id = os.environ["PITLANE_WORKSPACE_ID"]

# CLI commands use workspace ID
pitlane fetch session-info --workspace-id $PITLANE_WORKSPACE_ID --year 2024
```

This enables:
- Skills to access the correct workspace
- CLI commands to save data in the right location
- Tool permissions to validate workspace paths

## Workspace API

See [`commands/workspace/`](https://github.com/jshudzina/PitLane-AI/blob/main/packages/pitlane-agent/src/pitlane_agent/commands/workspace/) for the full API:

### Create Workspace

```python
from pitlane_agent.commands.workspace import create_workspace

# Auto-generated workspace ID
workspace_info = create_workspace()
# Returns: {
#   "workspace_id": "abc123-...",
#   "workspace_path": "/Users/alice/.pitlane/workspaces/abc123-...",
#   "created_at": "2024-05-23T14:30:00Z"
# }

# Explicit workspace ID
workspace_info = create_workspace(
    workspace_id="my-workspace",
    description="Monaco 2024 analysis"
)

# Collision retry (auto-generated IDs only)
workspace_info = create_workspace(max_retries=5)
```

### Get Workspace Info

```python
from pitlane_agent.commands.workspace import get_workspace_info

info = get_workspace_info(workspace_id="abc123")
# Returns: {
#   "workspace_id": "abc123",
#   "workspace_path": "~/.pitlane/workspaces/abc123",
#   "created_at": "2024-05-23T14:30:00Z",
#   "last_accessed": "2024-05-23T15:45:00Z",
#   "description": "Monaco 2024 analysis",
#   "data_files": ["session_info.json", "drivers.json"],
#   "chart_files": ["lap_times.png"]
# }
```

### List Workspaces

```python
from pitlane_agent.commands.workspace import list_workspaces

# Recent workspaces (10 most recent)
workspaces = list_workspaces()

# All workspaces
workspaces = list_workspaces(show_all=True)

# Returns list sorted by last_accessed (newest first)
```

### Remove Workspace

```python
from pitlane_agent.commands.workspace import remove_workspace

remove_workspace(workspace_id="abc123")
# Raises ValueError if workspace doesn't exist
```

### Clean Workspaces

```python
from pitlane_agent.commands.workspace import clean_workspaces

# Remove workspaces older than 7 days
result = clean_workspaces(older_than_days=7)
# Returns: {
#   "removed_count": 3,
#   "removed_workspaces": ["abc123", "def456", "ghi789"]
# }

# Remove all workspaces
result = clean_workspaces(remove_all=True)
```

## Shared Cache

Some data is **shared across all workspaces** to avoid redundant downloads:

### FastF1 Cache

Location: `~/.pitlane/cache/fastf1/`

**Contents**:
- Downloaded race data (lap times, telemetry, etc.)
- Event schedules
- Session metadata

**Benefits**:
- Faster analysis (no re-downloads)
- Reduced API load
- Shared across all workspaces

### Temporal Context Cache

Location: `~/.pitlane/cache/temporal/`

**Contents**:
- F1 calendar context (current/last/next races)
- Session timings
- Live event status

**Benefits**:
- Single source of truth for calendar
- Adaptive TTL (5min-24h depending on proximity to events)
- All agents see consistent temporal context

## Concurrency

Workspaces enable **concurrent agent operations**:

```python
# Workspace 1: Monaco 2024 analysis
agent1 = F1Agent(workspace_id="monaco-2024")
await agent1.chat("Analyze Verstappen lap times")

# Workspace 2: Silverstone 2023 analysis (concurrent)
agent2 = F1Agent(workspace_id="silverstone-2023")
await agent2.chat("Show Hamilton strategy")
```

**Isolation Guarantees**:
- Each workspace has its own directory
- File I/O restricted to workspace paths (via tool permissions)
- No cross-workspace data leakage
- Shared cache uses thread-safe FastF1 implementation

## CLI Integration

The `pitlane workspace` CLI provides management commands:

```bash
# List workspaces
pitlane workspace list
pitlane workspace list --all

# Get workspace info
pitlane workspace info --workspace-id abc123

# Remove workspace
pitlane workspace remove --workspace-id abc123

# Clean old workspaces
pitlane workspace clean --older-than-days 7
pitlane workspace clean --all
```

See [User Guide: CLI Reference](../agent-cli/cli-reference.md) for details.

## Benefits

### 1. Data Isolation

Each workspace is completely isolated:
- No accidental data mixing
- No file path conflicts
- Clean slate for each conversation

### 2. Multi-User Support

Web deployments can serve multiple users:
- Each user gets a unique workspace ID
- Concurrent analysis sessions
- No user-to-user data leakage

### 3. Debugging

Persistent workspaces enable:
- Post-mortem analysis of agent behavior
- Inspection of generated charts
- Review of CLI command outputs

### 4. Resource Management

Automatic cleanup prevents disk bloat:
- Configurable retention policies
- Last-accessed tracking
- Bulk cleanup operations

## Related Documentation

- [Agent System](agent-system.md) - How workspaces integrate with F1Agent
- [Tool Permissions](tool-permissions.md) - Workspace path restrictions
- [User Guide: CLI Reference](../agent-cli/cli-reference.md) - Workspace CLI commands
