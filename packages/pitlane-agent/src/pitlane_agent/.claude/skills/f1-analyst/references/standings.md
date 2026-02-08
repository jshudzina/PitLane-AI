# Standings Analysis

Analyze championship standings, driver/constructor performance across the season, and title fight scenarios.

## Available Analysis Types

### 1. Championship Possibilities

Calculate which drivers or constructors can still mathematically win their respective championship based on current standings and remaining races.

**Command:**
```bash
pitlane analyze championship-possibilities \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --championship drivers
```

**Parameters:**
- `--session-id`: Workspace session ID (required)
- `--year`: Championship year (required)
- `--championship`: Type - "drivers" or "constructors" (default: drivers)

**Returns:**
- `chart_path`: Path to visualization
- `workspace`: Workspace directory
- `year`: Championship year
- `championship_type`: "drivers" or "constructors"
- `current_round`: Current round number in the season
- `remaining_races`: Number of races remaining
- `remaining_sprints`: Number of sprint races remaining
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

**Example Analysis Response:**
"Based on the current standings with [X] races remaining, [Y] drivers can still mathematically win the championship. [Leader name] leads with [Z] points. [Driver 2] needs to outscore [Leader] by at least [points_behind + 1] points across the remaining races to take the title. [Driver 3] is mathematically eliminated as their maximum possible points ([max]) is less than the leader's current total."

**Interpretation:**
- Filled bars show current championship points
- Extended hatched bars show maximum possible points
- Green bars indicate the driver/constructor can still mathematically win
- Gray bars indicate mathematical elimination
- The visualization accounts for both standard race points and sprint race points

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

### 3. Season Summary Visualization (Not Yet Implemented)
**What it would do:**
- Provide comprehensive overview of the entire season
- Aggregate performance metrics for drivers and teams
- Visualize points distribution and race wins

**Example Questions:**
- "Give me a season summary for 2024"
- "Show me overall performance statistics for this year"
- "Compare drivers' full season results"
