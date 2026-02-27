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

### `pitlane analyze telemetry`

Generate an interactive telemetry chart (speed, RPM, gear, throttle, brake, super clipping) comparing drivers on their fastest laps.

**Usage:**
```bash
pitlane analyze telemetry --workspace-id ID --year YEAR
  [--gp GP_NAME | --test N --day N]
  [--session SESSION_TYPE]
  --drivers DRIVER [--drivers DRIVER2 ...]
  [--annotate-corners]
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--gp` - Grand Prix name (mutually exclusive with `--test`/`--day`)
- `--session` - Session type (R, Q, FP1, FP2, FP3, S, SQ)
- `--test` - Pre-season testing event number (e.g., 1 or 2)
- `--day` - Day/session within testing event (1–3)
- `--drivers` (required, 2–5 times) - Driver abbreviations to compare
- `--annotate-corners` - Add corner number markers to the distance axis

**Examples:**
```bash
# Compare two drivers in qualifying
pitlane analyze telemetry --workspace-id abc123 --year 2024 --gp Monaco --session Q \
  --drivers VER --drivers NOR

# With corner annotations
pitlane analyze telemetry --workspace-id abc123 --year 2024 --gp Monaco --session Q \
  --drivers VER --drivers NOR --annotate-corners

# Pre-season testing session
pitlane analyze telemetry --workspace-id abc123 --year 2024 --test 1 --day 2 \
  --drivers VER --drivers HAM
```

**Output:**
```json
{
  "chart_path": "~/.pitlane/workspaces/abc123/charts/telemetry_2024_monaco_Q.html",
  "statistics": {
    "VER": {
      "lap_time": "1:10.270",
      "sector_1": "18.456",
      "sector_2": "36.123",
      "sector_3": "15.691",
      "speed_trap_kmh": 287.3,
      "finish_speed_kmh": 210.4,
      "lift_coast_zones": 3,
      "super_clipping_zones": 2
    }
  },
  "workspace_id": "abc123"
}
```

The chart is an interactive HTML file rendered as an iframe in the web interface. All six subplots (Speed, RPM, Gear, Throttle, Brake, Super Clipping) share a zoom/pan axis. Hover over any point to see per-driver values and deltas.

### `pitlane analyze multi-lap`

Compare multiple laps for a single driver within one session. Useful for analyzing qualifying run differences, stint pace evolution, or any lap-to-lap comparison.

**Usage:**
```bash
pitlane analyze multi-lap --workspace-id ID --year YEAR
  [--gp GP_NAME | --test N --day N]
  [--session SESSION_TYPE]
  --driver DRIVER
  --lap SPEC [--lap SPEC ...]
  [--annotate-corners]
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--gp` - Grand Prix name (mutually exclusive with `--test`/`--day`)
- `--session` - Session type (R, Q, FP1, FP2, FP3, S, SQ)
- `--test` - Pre-season testing event number
- `--day` - Day/session within testing event
- `--driver` (required) - Single driver abbreviation
- `--lap` (required, 2–6 times) - Lap specifier: `best` for fastest lap, or an integer lap number
- `--annotate-corners` - Add corner number markers

**Examples:**
```bash
# Compare fastest lap vs lap 3 in qualifying
pitlane analyze multi-lap --workspace-id abc123 --year 2024 --gp Monaco --session Q \
  --driver VER --lap best --lap 3

# Compare multiple race laps to analyze stint pace
pitlane analyze multi-lap --workspace-id abc123 --year 2024 --gp Bahrain --session R \
  --driver LEC --lap 5 --lap 20 --lap 45

# Pre-season testing session
pitlane analyze multi-lap --workspace-id abc123 --year 2024 --test 1 --day 2 \
  --driver VER --lap best --lap 5
```

**Output:**
```json
{
  "chart_path": "~/.pitlane/workspaces/abc123/charts/multi_lap_VER_2024_monaco_Q.html",
  "statistics": {
    "Lap 1 (best)": {"lap_time": "1:10.270", "sector_1": "18.456", ...},
    "Lap 3": {"lap_time": "1:10.589", "sector_1": "18.712", ...}
  },
  "workspace_id": "abc123"
}
```

### `pitlane analyze year-compare`

Compare a driver's fastest lap at the same circuit across multiple seasons. Useful for visualizing the impact of regulation changes on braking, speed profiles, and driving technique.

**Usage:**
```bash
pitlane analyze year-compare --workspace-id ID
  [--gp GP_NAME | --test N --day N]
  [--session SESSION_TYPE]
  --driver DRIVER
  --years YEAR [--years YEAR ...]
  [--annotate-corners]
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--gp` - Grand Prix name (must exist in all specified years; mutually exclusive with `--test`/`--day`)
- `--session` - Session type (R, Q, FP1, FP2, FP3, S, SQ)
- `--test` - Pre-season testing event number
- `--day` - Day/session within testing event
- `--driver` (required) - Single driver abbreviation
- `--years` (required, 2–6 times) - Seasons to include (note: `--years` not `--year`)
- `--annotate-corners` - Add corner number markers

**Examples:**
```bash
# Compare VER's best qualifying lap at Monza across two seasons
pitlane analyze year-compare --workspace-id abc123 --gp Monza --session Q \
  --driver VER --years 2022 --years 2024

# Three-season comparison for regulation impact analysis
pitlane analyze year-compare --workspace-id abc123 --gp Silverstone --session Q \
  --driver HAM --years 2021 --years 2022 --years 2024
```

**Output:**
```json
{
  "chart_path": "~/.pitlane/workspaces/abc123/charts/year_compare_VER_monza_Q.html",
  "statistics": {
    "2022": {"lap_time": "1:20.161", "sector_1": "25.347", ...},
    "2024": {"lap_time": "1:18.927", "sector_1": "24.815", ...}
  },
  "workspace_id": "abc123"
}
```

### `pitlane analyze driver-laps`

Fetch per-lap data for a single driver without generating a chart. Returns structured JSON covering all laps in the session — useful for identifying which lap numbers are worth comparing before running `multi-lap`.

**Usage:**
```bash
pitlane analyze driver-laps --workspace-id ID --year YEAR
  [--gp GP_NAME | --test N --day N]
  [--session SESSION_TYPE]
  --driver DRIVER
```

**Options:**
- `--workspace-id` (required) - Workspace ID
- `--year` (required) - Season year
- `--gp` - Grand Prix name (mutually exclusive with `--test`/`--day`)
- `--session` - Session type (R, Q, FP1, FP2, FP3, S, SQ)
- `--test` - Pre-season testing event number
- `--day` - Day/session within testing event
- `--driver` (required) - Single driver abbreviation

**Examples:**
```bash
# List all race laps for VER to find which laps to compare
pitlane analyze driver-laps --workspace-id abc123 --year 2024 --gp Monaco --session R \
  --driver VER

# Testing session lap data
pitlane analyze driver-laps --workspace-id abc123 --year 2024 --test 1 --day 2 \
  --driver VER
```

**Output:**
```json
{
  "driver": "VER",
  "session": "Race",
  "laps": [
    {
      "lap_number": 1,
      "lap_time": "1:32.456",
      "sector_1": "28.123",
      "sector_2": "42.456",
      "sector_3": "21.877",
      "compound": "SOFT",
      "stint": 1,
      "pit_in": false,
      "pit_out": false,
      "position": 1,
      "is_accurate": true
    }
  ],
  "workspace_id": "abc123"
}
```

The `is_accurate` flag indicates whether FastF1 considers the lap race-representative (excludes pit in/out laps, safety car laps, and formation laps).

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
