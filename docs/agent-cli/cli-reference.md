# CLI Reference

!!! warning "Agent-Only Tool"
    This CLI is designed for agent use only, not direct user interaction.
    End users should use the [Web Interface](../user-guide/web-interface.md) instead.

The `pitlane` CLI provides workspace-based access to F1 data analysis tools. All commands operate within session-scoped workspaces for data isolation and concurrent usage.

## Installation

```bash
# Install from PyPI
pip install pitlane-agent

# Or use with uvx (no installation)
uvx pitlane-agent <command>
```

## Command Structure

```
pitlane <command> [subcommand] [options]
```

**Available Commands:**
- `workspace` - Manage session workspaces
- `fetch` - Fetch F1 data (sessions, drivers, schedules)
- `analyze` - Analyze and visualize F1 data
- `temporal-context` - Show current F1 calendar context

## Workspace Commands

Manage session-based workspaces for data isolation.

### `pitlane workspace create`

Create a new workspace for analysis.

**Usage:**
```bash
pitlane workspace create [--workspace-id ID] [--description TEXT]
```

**Options:**
- `--workspace-id` - Explicit workspace ID (auto-generated if omitted)
- `--description` - Optional workspace description

**Examples:**
```bash
# Auto-generated workspace ID
pitlane workspace create
# Output: {"session_id": "abc123-...", "workspace_path": "~/.pitlane/workspaces/abc123-..."}

# Explicit workspace ID
pitlane workspace create --workspace-id monaco-2024 --description "Monaco Grand Prix analysis"

# Use in scripts
SESSION_ID=$(pitlane workspace create | jq -r '.session_id')
```

**Output:**
```json
{
  "session_id": "abc123-def456-...",
  "workspace_path": "/Users/alice/.pitlane/workspaces/abc123-...",
  "created_at": "2024-05-23T14:30:00Z"
}
```

### `pitlane workspace list`

List all workspaces (10 most recent by default).

**Usage:**
```bash
pitlane workspace list [--show-all]
```

**Options:**
- `--show-all` - Show all workspaces (default: 10 most recent)

**Examples:**
```bash
# List recent workspaces
pitlane workspace list

# List all workspaces
pitlane workspace list --show-all
```

**Output:**
```json
{
  "total": 3,
  "workspaces": [
    {
      "session_id": "abc123-...",
      "created_at": "2024-05-23T14:30:00Z",
      "last_accessed": "2024-05-23T15:45:00Z",
      "description": "Monaco 2024 analysis",
      "workspace_path": "~/.pitlane/workspaces/abc123-...",
      "data_files": ["session_info.json"],
      "chart_files": ["lap_times.png"]
    }
  ]
}
```

### `pitlane workspace info`

Show detailed workspace information.

**Usage:**
```bash
pitlane workspace info --workspace-id SESSION_ID
```

**Options:**
- `--workspace-id` (required) - Workspace ID to inspect

**Examples:**
```bash
pitlane workspace info --workspace-id abc123
```

**Output:**
```json
{
  "session_id": "abc123",
  "workspace_path": "~/.pitlane/workspaces/abc123",
  "created_at": "2024-05-23T14:30:00Z",
  "last_accessed": "2024-05-23T15:45:00Z",
  "data_files": ["session_info.json", "drivers.json"],
  "chart_files": ["lap_times.png", "strategy.png"]
}
```

### `pitlane workspace clean`

Remove old workspaces to free disk space.

**Usage:**
```bash
pitlane workspace clean --older-than DAYS [--yes]
pitlane workspace clean --all [--yes]
```

**Options:**
- `--older-than` - Remove workspaces not accessed in N days
- `--all` - Remove all workspaces
- `--yes`, `-y` - Skip confirmation prompt

**Examples:**
```bash
# Remove workspaces older than 7 days
pitlane workspace clean --older-than 7

# Remove all workspaces (with confirmation)
pitlane workspace clean --all

# Remove all workspaces (skip confirmation)
pitlane workspace clean --all --yes
```

**Output:**
```json
{
  "removed_count": 3,
  "removed_sessions": ["abc123", "def456", "ghi789"]
}
```

### `pitlane workspace remove`

Remove a specific workspace.

**Usage:**
```bash
pitlane workspace remove --workspace-id SESSION_ID [--yes]
```

**Options:**
- `--workspace-id` (required) - Workspace ID to remove
- `--yes`, `-y` - Skip confirmation prompt

**Examples:**
```bash
# Remove with confirmation
pitlane workspace remove --workspace-id abc123

# Remove without confirmation
pitlane workspace remove --workspace-id abc123 --yes
```

## Fetch Commands

Fetch F1 data from FastF1 and Ergast API.

### `pitlane fetch session-info`

Fetch session information and driver list.

**Usage:**
```bash
pitlane fetch session-info --workspace-id ID --year YEAR --gp GP_NAME --session SESSION_TYPE
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year (e.g., 2024)
- `--gp` (required) - Grand Prix name (e.g., Monaco, Silverstone)
- `--session` (required) - Session type (R, Q, FP1, FP2, FP3, S, SQ)

**Examples:**
```bash
pitlane fetch session-info --workspace-id abc123 --year 2024 --gp Monaco --session R
pitlane fetch session-info --workspace-id abc123 --year 2024 --gp Silverstone --session Q
```

**Output:**
```json
{
  "event_name": "Monaco Grand Prix",
  "session_type": "Race",
  "date": "2024-05-26",
  "drivers": ["VER", "HAM", "LEC", ...],
  "saved_to": "~/.pitlane/workspaces/abc123/data/session_info.json"
}
```

### `pitlane fetch drivers`

Fetch driver information for a season.

**Usage:**
```bash
pitlane fetch drivers --workspace-id ID --year YEAR [--team TEAM]
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--team` (optional) - Filter by team (e.g., "Ferrari", "Mercedes")

**Examples:**
```bash
pitlane fetch drivers --workspace-id abc123 --year 2024
pitlane fetch drivers --workspace-id abc123 --year 2024 --team Ferrari
```

### `pitlane fetch schedule`

Fetch season calendar with race dates.

**Usage:**
```bash
pitlane fetch schedule --workspace-id ID --year YEAR
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year

**Examples:**
```bash
pitlane fetch schedule --workspace-id abc123 --year 2024
```

## Analyze Commands

Analyze and visualize F1 data.

### `pitlane analyze lap-times`

Analyze lap time distributions with visualizations.

**Usage:**
```bash
pitlane analyze lap-times --workspace-id ID --year YEAR --gp GP_NAME --session SESSION_TYPE --drivers DRIVER [--drivers DRIVER2 ...]
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--gp` (required) - Grand Prix name
- `--session` (required) - Session type (R, Q, FP1, etc.)
- `--drivers` (required, repeatable) - Driver codes (VER, HAM, etc.)

**Examples:**
```bash
# Compare two drivers
pitlane analyze lap-times --workspace-id abc123 --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM

# Compare multiple drivers
pitlane analyze lap-times --workspace-id abc123 --year 2024 --gp Silverstone --session R --drivers VER --drivers HAM --drivers LEC
```

**Output:**
```json
{
  "chart_saved_to": "~/.pitlane/workspaces/abc123/charts/lap_times.png",
  "statistics": {
    "VER": {"mean": "1:12.345", "median": "1:12.234", "std": "0.234"},
    "HAM": {"mean": "1:12.456", "median": "1:12.345", "std": "0.321"}
  }
}
```

### `pitlane analyze tyre-strategy`

Visualize tyre strategy and pit stops.

**Usage:**
```bash
pitlane analyze tyre-strategy --workspace-id ID --year YEAR --gp GP_NAME --session R
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--gp` (required) - Grand Prix name
- `--session` (required) - Must be 'R' (Race only)

**Examples:**
```bash
pitlane analyze tyre-strategy --workspace-id abc123 --year 2024 --gp Monaco --session R
```

**Output:**
```json
{
  "chart_saved_to": "~/.pitlane/workspaces/abc123/charts/strategy.png",
  "strategy_summary": {
    "VER": ["SOFT-20", "MEDIUM-38"],
    "HAM": ["MEDIUM-25", "HARD-33"]
  }
}
```

### `pitlane analyze qualifying-results`

Generate a horizontal bar chart showing each driver's gap to pole position.

**Usage:**
```bash
pitlane analyze qualifying-results --workspace-id ID --year YEAR --gp GP_NAME [--session SESSION_TYPE]
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--gp` (required) - Grand Prix name (e.g., Monaco, Silverstone)
- `--session` - Session type: `Q` (Qualifying), `SQ` (Sprint Qualifying), or `SS` (Sprint Shootout). Defaults to `Q` when `--gp` is used.

**Examples:**
```bash
# Standard qualifying
pitlane analyze qualifying-results --workspace-id abc123 --year 2024 --gp Monaco --session Q

# Sprint shootout
pitlane analyze qualifying-results --workspace-id abc123 --year 2024 --gp China --session SS
```

**Output:**
```json
{
  "chart_path": "~/.pitlane/workspaces/abc123/charts/qualifying_results_2024_monaco_Q.png",
  "pole_driver": "VER",
  "pole_time_str": "1:10.270",
  "statistics": [
    {
      "position": 1,
      "abbreviation": "VER",
      "team": "Red Bull Racing",
      "phase": "Q3",
      "best_time_s": 70.27,
      "best_time_str": "1:10.270",
      "gap_to_pole_s": 0.0
    }
  ],
  "workspace_id": "abc123"
}
```

Drivers are colored by qualifying phase: Q3 finishers use their team color, Q2 eliminees use a dimmed team color, and Q1 eliminees appear in gray. Automatically handles both 20-car (≤2025) and 22-car (2026+) qualifying formats.

## Temporal Context Command

Show current F1 calendar context.

### `pitlane temporal-context`

Display the current state of the F1 season.

**Usage:**
```bash
pitlane temporal-context [--format FORMAT] [--refresh] [--verbosity LEVEL]
```

**Options:**
- `--format` - Output format: `text` (default), `json`, `prompt`
- `--refresh` - Force refresh from FastF1 (ignore cache)
- `--verbosity` - Detail level: `minimal`, `normal` (default), `detailed`

**Examples:**
```bash
# Human-readable text (default)
pitlane temporal-context

# JSON output
pitlane temporal-context --format json

# System prompt format (for agent integration)
pitlane temporal-context --format prompt --verbosity detailed

# Force refresh cache
pitlane temporal-context --refresh
```

**Output (text format):**
```
F1 Temporal Context (2024-05-23 14:30 UTC)

Season Status: 2024 Season - In Progress
- Races completed: 7/24
- Races remaining: 17

Current Race Weekend: Monaco Grand Prix (Round 8)
- Location: Monaco, Monaco
- Event Date: 2024-05-26
- Phase: Practice
- Current Session: FP1 (Live - Started 15 minutes ago)
- Next Session: FP2 (in 2 hours 15 minutes)

Last Completed Race: Emilia Romagna Grand Prix
- Completed: 3 days ago

Next Race: Monaco Grand Prix (in 3 days)
```

## Session Types

| Code | Session Name |
|------|-------------|
| `R` | Race |
| `Q` | Qualifying |
| `S` | Sprint Race |
| `SQ` | Sprint Qualifying |
| `SS` | Sprint Shootout |
| `FP1` | Free Practice 1 |
| `FP2` | Free Practice 2 |
| `FP3` | Free Practice 3 |

## Common Driver Codes (2024)

| Code | Driver | Team |
|------|--------|------|
| VER | Max Verstappen | Red Bull |
| PER | Sergio Perez | Red Bull |
| HAM | Lewis Hamilton | Mercedes |
| RUS | George Russell | Mercedes |
| LEC | Charles Leclerc | Ferrari |
| SAI | Carlos Sainz | Ferrari |
| NOR | Lando Norris | McLaren |
| PIA | Oscar Piastri | McLaren |
| ALO | Fernando Alonso | Aston Martin |
| STR | Lance Stroll | Aston Martin |

See [Ergast API](https://ergast.com/mrd/) for complete driver codes.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (with JSON error message on stderr) |

## Related Documentation

- [Analysis Types](../user-guide/analysis-types.md) - Detailed analysis workflows
- [Skills Usage](skills-usage.md) - Using skills in agent mode
- [Architecture: Workspace Management](../architecture/workspace-management.md) - Workspace internals
