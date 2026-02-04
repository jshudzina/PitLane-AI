# Workspace Management

PitLane-AI uses **session-based workspaces** to isolate agent data, ensuring clean separation between conversations and enabling concurrent multi-user deployments.

## Overview

Each F1Agent session operates in its own workspace directory, providing:

- **Data Isolation**: Session data never conflicts or mixes
- **Concurrent Access**: Multiple agents can run simultaneously
- **Resource Management**: Old workspaces can be cleaned up
- **Reproducibility**: Session data persists for debugging

## Workspace Structure

### Directory Layout

```
~/.pitlane/
├── workspaces/
│   ├── <session-id-1>/
│   │   ├── .metadata.json
│   │   ├── data/
│   │   │   ├── session_info.json
│   │   │   ├── drivers.json
│   │   │   └── schedule.json
│   │   └── charts/
│   │       ├── lap_times.png
│   │       └── strategy.png
│   └── <session-id-2>/
│       └── ...
└── cache/
    ├── fastf1/              # Shared FastF1 cache
    └── temporal/            # Temporal context cache
```

### Workspace Components

**`.metadata.json`**: Session metadata
```json
{
  "session_id": "abc123-def456-...",
  "created_at": "2024-05-23T14:30:00Z",
  "last_accessed": "2024-05-23T15:45:00Z",
  "description": "Monaco 2024 analysis"  // optional
}
```

**`data/`**: Session-specific data files
- JSON outputs from CLI commands
- Query results (drivers, schedules, session info)
- Intermediate analysis data

**`charts/`**: Generated visualizations
- PNG images from matplotlib
- Lap time distributions
- Strategy visualizations
- Telemetry plots

## Session Lifecycle

### 1. Creation

Workspaces are created automatically when F1Agent is initialized:

```python
agent = F1Agent()  # Auto-generates session ID and creates workspace
```

Or with explicit session ID:

```python
agent = F1Agent(session_id="my-session-123")
```

**Creation Process**:
1. Generate UUID session ID (if not provided)
2. Check for collision (retry up to 3 times for auto-generated IDs)
3. Create directory structure (`workspace/`, `data/`, `charts/`)
4. Write `.metadata.json` with timestamp
5. Ensure shared cache directories exist

**Collision Handling**: Auto-generated UUIDs handle collisions gracefully:
```python
create_workspace(session_id=None, max_retries=3)
# Retries UUID generation if workspace already exists
```

Explicit session IDs fail immediately if workspace exists:
```python
create_workspace(session_id="explicit-id")
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
5. Return cleanup stats (count, session IDs)

## Session ID Propagation

The session ID flows through the system via **environment variable**:

```python
# F1Agent sets session ID for skills
os.environ["PITLANE_SESSION_ID"] = self.session_id

# Skills access session ID
session_id = os.environ["PITLANE_SESSION_ID"]

# CLI commands use session ID
pitlane fetch session-info --session-id $PITLANE_SESSION_ID --year 2024
```

This enables:
- Skills to access the correct workspace
- CLI commands to save data in the right location
- Tool permissions to validate workspace paths

## Workspace API

See [`scripts/workspace.py`](../../packages/pitlane-agent/src/pitlane_agent/scripts/workspace.py) for the full API:

### Create Workspace

```python
from pitlane_agent.scripts.workspace import create_workspace

# Auto-generated session ID
workspace_info = create_workspace()
# Returns: {
#   "session_id": "abc123-...",
#   "workspace_path": "/Users/alice/.pitlane/workspaces/abc123-...",
#   "created_at": "2024-05-23T14:30:00Z"
# }

# Explicit session ID
workspace_info = create_workspace(
    session_id="my-session",
    description="Monaco 2024 analysis"
)

# Collision retry (auto-generated IDs only)
workspace_info = create_workspace(max_retries=5)
```

### Get Workspace Info

```python
from pitlane_agent.scripts.workspace import get_workspace_info

info = get_workspace_info(session_id="abc123")
# Returns: {
#   "session_id": "abc123",
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
from pitlane_agent.scripts.workspace import list_workspaces

# Recent workspaces (10 most recent)
workspaces = list_workspaces()

# All workspaces
workspaces = list_workspaces(show_all=True)

# Returns list sorted by last_accessed (newest first)
```

### Remove Workspace

```python
from pitlane_agent.scripts.workspace import remove_workspace

remove_workspace(session_id="abc123")
# Raises ValueError if workspace doesn't exist
```

### Clean Workspaces

```python
from pitlane_agent.scripts.workspace import clean_workspaces

# Remove workspaces older than 7 days
result = clean_workspaces(older_than_days=7)
# Returns: {
#   "removed_count": 3,
#   "removed_sessions": ["abc123", "def456", "ghi789"]
# }

# Remove all workspaces
result = clean_workspaces(remove_all=True)
```

## Shared Cache

Some data is **shared across all sessions** to avoid redundant downloads:

### FastF1 Cache

Location: `~/.pitlane/cache/fastf1/`

**Contents**:
- Downloaded race data (lap times, telemetry, etc.)
- Event schedules
- Session metadata

**Benefits**:
- Faster analysis (no re-downloads)
- Reduced API load
- Shared across all sessions

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

Workspaces enable **concurrent agent sessions**:

```python
# Session 1: Monaco 2024 analysis
agent1 = F1Agent(session_id="monaco-2024")
await agent1.chat("Analyze Verstappen lap times")

# Session 2: Silverstone 2023 analysis (concurrent)
agent2 = F1Agent(session_id="silverstone-2023")
await agent2.chat("Show Hamilton strategy")
```

**Isolation Guarantees**:
- Each session has its own workspace directory
- File I/O restricted to workspace paths (via tool permissions)
- No cross-session data leakage
- Shared cache uses thread-safe FastF1 implementation

## CLI Integration

The `pitlane workspace` CLI provides management commands:

```bash
# List workspaces
pitlane workspace list
pitlane workspace list --all

# Get workspace info
pitlane workspace info --session-id abc123

# Remove workspace
pitlane workspace remove --session-id abc123

# Clean old workspaces
pitlane workspace clean --older-than-days 7
pitlane workspace clean --all
```

See [User Guide: CLI Reference](../user-guide/cli-reference.md) for details.

## Benefits

### 1. Data Isolation

Each session is completely isolated:
- No accidental data mixing
- No file path conflicts
- Clean slate for each conversation

### 2. Multi-User Support

Web deployments can serve multiple users:
- Each user gets unique session ID
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
- [User Guide: CLI Reference](../user-guide/cli-reference.md) - Workspace CLI commands
