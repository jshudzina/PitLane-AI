# Standings Analysis

Analyze championship standings, driver/constructor performance across the season, and title fight scenarios.

## Available Analysis Types

### 1. Championship Possibilities

Calculate which drivers or constructors can still mathematically win their respective championship based on current standings and remaining races.

**Command:**
```bash
# Current standings
pitlane analyze championship-possibilities \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --championship drivers

# Historical "what if" analysis after a specific round
pitlane analyze championship-possibilities \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --championship drivers \
  --after-round 10
```

**Parameters:**
- `--workspace-id`: Workspace ID (required)
- `--year`: Championship year (required)
- `--championship`: Type - "drivers" or "constructors" (default: drivers)
- `--after-round`: Optional round number for historical "what if" analysis

**Returns:**
- `chart_path`: Path to visualization (includes round number in filename for historical analysis)
- `workspace`: Workspace directory
- `year`: Championship year
- `championship_type`: "drivers" or "constructors"
- `analysis_round`: Round number being analyzed (current or specified with --after-round)
- `remaining_races`: Number of races remaining after the analysis round
- `remaining_sprints`: Number of sprint races remaining after the analysis round
- `max_points_available`: Maximum points available in remaining races
- `leader`: Current championship leader details (name, points, position)
- `statistics`:
  - `total_competitors`: Total in standings
  - `still_possible`: Count who can mathematically win
  - `eliminated`: Count who are mathematically eliminated
  - `competitors`: Per-competitor breakdown with:
    - `name`: Driver/constructor name
    - `position`: Current championship position
    - `current_points`: Current championship points
    - `max_possible_points`: Maximum theoretical points
    - `points_behind`: Points deficit to leader
    - `can_win`: Boolean - mathematically possible to win
    - `required_scenario`: Description of what's needed to win

**Example Questions:**
- "Who can still win the drivers' championship?"
- "How many points does Norris need to catch Verstappen?"
- "Is the constructors' championship still possible for Ferrari?"
- "Is the title race still open?"
- "Show me who's mathematically eliminated from the championship"
- "What were the championship possibilities after round 10?" (historical analysis)
- "Could Ferrari have won the constructors' title after the summer break?" (historical analysis)
- "Show me the title fight situation after Singapore" (historical analysis)

**Example Analysis Response:**
"Based on the standings after round [analysis_round] with [X] races remaining, [Y] drivers can still mathematically win the championship. [Leader name] leads with [Z] points. [Driver 2] needs to outscore [Leader] by at least [points_behind + 1] points across the remaining races to take the title. [Driver 3] is mathematically eliminated as their maximum possible points ([max]) is less than the leader's current total."

**Note:** You can use the `--after-round` parameter to perform "what if" analysis on any past round in the season, allowing you to see how championship possibilities looked at different points in time.

**Interpretation:**
- Filled bars show current championship points
- Extended hatched bars show maximum possible points
- Green bars indicate the driver/constructor can still mathematically win
- Gray bars indicate mathematical elimination
- The visualization accounts for both standard race points and sprint race points
- Chart title shows "(After Round X)" when analyzing historical data
- Filename includes round number (e.g., `championship_possibilities_2024_drivers_round_10.png`) for historical analysis

---

### 2. Season Summary — Championship Heatmap (Analyze)

Visualize championship points scored per competitor at each round of the season as an interactive Plotly heatmap. Covers both driver and constructor championships.

**Command:**
```bash
# Drivers championship heatmap (default)
pitlane analyze season-summary \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024

# Constructors championship heatmap
pitlane analyze season-summary \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --type constructors
```

**Parameters:**
- `--workspace-id`: Workspace ID (required)
- `--year`: Championship year (required)
- `--type`: Summary type — `drivers` or `constructors` (default: `drivers`)

**Returns:**
- `chart_path`: Path to interactive HTML heatmap
- `workspace`: Workspace directory
- `year`: Championship year
- `summary_type`: `"drivers"` or `"constructors"`
- `analysis_round`: Last completed race round
- `total_races`: Total races scheduled in the season
- `season_complete`: Boolean — whether all races have been run
- `leader`: `{name, points, team, position}`
- `statistics`:
  - `total_competitors`: Number of drivers/constructors in standings
  - `competitors`: Per-competitor breakdown with:
    - `name`, `championship_position`, `points`, `team`

**Visualization:**
- Left panel (85%): Per-round points heatmap — each cell shows points scored at that race; hover shows finishing position (drivers mode)
- Right panel (15%): Total season points per competitor
- Championship leader sits at the top of the heatmap (sorted ascending by total)
- Sprint points are added to the same round as the race weekend
- Saved as an interactive HTML file (hover tooltips preserved)

**Example Questions:**
- "Summarize the 2024 season"
- "Show me the championship standings heatmap"
- "Show me season statistics for all drivers"
- "Give me a constructors' season overview"
- "Season overview for 2023"
- "How many points did each driver score at each race?"

**Example Analysis Response:**
"Here's the 2024 drivers' championship heatmap after round [analysis_round]. [Leader] leads with [points] points. The heatmap shows points scored at each round — hover over any cell to see the finishing position. [Driver 2] has been consistent with points at almost every round, while [Driver N] had a strong mid-season run."

**Interpretation:**
- Darker cells = more points scored at that round
- Sprint points are included in the same round column as the race
- For partial seasons, the title shows "After Round X"; for complete seasons it shows "Final — N Races"
- `season_complete: false` means the season is still in progress

**Note:** Loads results data only (no telemetry), so this command is fast. Results are saved as an HTML file to `charts/season_summary_<year>_<type>.html` in the workspace.

---

### 3. Season Race Excitement Ranking (Fetch)

Rank all races in a season by a composite "wildness" score derived from overtakes, position volatility, safety cars, and red flags. Also provides season-wide per-lap averages.

**Command:**
```bash
pitlane fetch season-summary \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024
```

**Parameters:**
- `--workspace-id`: Workspace ID (required)
- `--year`: Championship year (required)

**Returns:**
- `data_file`: Path to JSON file saved in workspace (`data/season_summary_<year>.json`)
- `year`: Championship year
- `total_races`: Number of races loaded

The saved JSON contains:
- `races`: List sorted by `wildness_score` descending, each entry with:
  - `round`, `event_name`, `country`, `date`, `session_type` (`"R"` or `"S"`)
  - `circuit_length_km`, `race_distance_km`
  - `podium`: List of top 3 finishers — each is `{driver, team}` (driver abbreviation + team name)
  - `race_summary`: `{total_overtakes, total_position_changes, average_volatility, mean_pit_stops, total_laps}`
  - `num_safety_cars`, `num_virtual_safety_cars`, `num_red_flags`
  - `wildness_score`: 0–1 composite score (40% overtake density, 30% volatility, 20% safety cars, 10% red flags)
- `season_averages`: Per-lap normalized averages — `overtakes_per_lap`, `position_changes_per_lap`, `average_volatility`, `mean_pit_stops`

After running, read the JSON from the workspace to interpret results:
```bash
# The CLI prints data_file path; read it with the Read tool
```

**Example Questions:**
- "Which was the craziest race of 2024?"
- "Rank the 2024 races by how wild they were"
- "Which race had the most overtakes this year?"
- "What were the average pit stops per race in 2023?"
- "Which sprint race was the most exciting?"

**Note:** This command loads every race session in the season (including sprints), which can be slow on first run. Subsequent calls benefit from FastF1's cache. Sprint weekends produce two entries — one for the Sprint (`S`) and one for the Race (`R`).

---

## When to Use Fetch vs Analyze for Season Summary

| Question type | Command |
|---|---|
| "Summarize the season" / "Show championship standings" | `pitlane analyze season-summary` |
| "Which race was craziest?" / "Rank races by excitement/wildness" | `pitlane fetch season-summary` |
| "Who scored the most points?" / "Show points per race" | `pitlane analyze season-summary` |
| "Which race had the most overtakes/safety cars?" | `pitlane fetch season-summary` |
| Comprehensive season overview (championship + excitement) | Run both — they complement each other |

The two commands are independent: `analyze` focuses on **who scored points when** (championship context), while `fetch` focuses on **how exciting each race was** (action metrics). For a full season debrief, run both.

---

## Planned Analysis Types

### 4. Driver Standings Heatmap (Not Yet Implemented)
**What it would do:**
- Visualize driver standings evolution throughout the season
- Show position changes race-by-race in a heatmap format
- Highlight performance trends across the calendar

**Example Questions:**
- "Show me how the championship battle has evolved this season"
- "Visualize the top 10 standings progression"
- "How has McLaren's position changed throughout the year?"
