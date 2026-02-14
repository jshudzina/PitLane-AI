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
  - `eliminated`: Count who are eliminated
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

## Planned Analysis Types

The following standings analysis types are planned for future implementation:

### 2. Driver Standings Heatmap (Not Yet Implemented)
**What it would do:**
- Visualize driver standings evolution throughout the season
- Show position changes race-by-race in a heatmap format
- Highlight performance trends across the calendar

**Example Questions:**
- "Show me how the championship battle has evolved this season"
- "Visualize the top 10 standings progression"
- "How has McLaren's position changed throughout the year?"

### 3. Season Summary

Rank all races in a season by a composite "wildness" score derived from overtakes, position volatility, safety cars, and red flags. Also provides season-wide averages.

**Command:**
```bash
pitlane fetch season-summary --workspace-id $PITLANE_WORKSPACE_ID --year 2024
```

**Parameters:**
- `--workspace-id`: Workspace ID (required)
- `--year`: Championship year (required)

**Returns:**
- `year`: Championship year
- `total_races`: Number of races loaded
- `races`: List sorted by `wildness_score` (descending), each containing:
  - `round`, `event_name`, `country`, `date`
  - `race_summary`: `total_overtakes`, `total_position_changes`, `average_volatility`, `mean_pit_stops`
  - `num_safety_cars`, `num_virtual_safety_cars`, `num_red_flags`
  - `wildness_score`: 0–1 composite score
- `season_averages`: Average `total_overtakes`, `total_position_changes`, `average_volatility`, `mean_pit_stops` across all races

**Example Questions:**
- "Which was the craziest race of 2024?"
- "Rank the 2024 races by how wild they were"
- "Give me a season summary for 2024"
- "Which race had the most overtakes this year?"
- "What were the average pit stops per race in 2023?"

**Note:** This command loads every race in the season, which can be slow on first run. Subsequent calls benefit from FastF1's cache.

### 4. Season Summary Heatmap (Not Yet Implemented)
**What it would do:**
- Visualize points scored by each driver at each race in a heatmap
- Show at a glance which drivers scored big at which rounds
- Complement the season summary data with a visual breakdown

**Example Questions:**
- "Show me a heatmap of points scored across the season"
- "Visualize each driver's points at every race in 2024"
