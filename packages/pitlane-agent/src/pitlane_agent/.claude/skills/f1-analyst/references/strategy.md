# Strategy and Results Analysis

Analyze race strategy, tyre choices, pit stops, and results to understand team decisions and race outcomes.

## Available Analysis Types

### 1. Tyre Strategy Visualization

Visualize pit stop timing and tyre compound usage across all drivers in a race.

**Command:**
```bash
pitlane analyze tyre-strategy \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session R
```

**What it does:**
- Creates a visualization showing when each driver pitted and what compounds they used
- Displays stint lengths and tyre degradation patterns
- Returns JSON with chart path and strategy summary
- Chart is saved to workspace charts directory

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Typically R (Race), but can analyze sprint sessions (S)

**Example Questions:**
- "Show me Ferrari's tyre strategy at Monaco"
- "What compounds did the front runners use at Silverstone?"
- "Compare Red Bull and Mercedes pit strategies"
- "Who did a one-stop strategy vs two-stop?"

## Analysis Workflow

### Step 1: Identify Session Parameters
Extract from the user's question:
- Year (default to most recent completed season if not specified)
- Grand Prix name (use official names)
- Session type (usually Race)
- Specific teams or drivers of interest (optional)

### Step 2: Generate Visualization
Run the `pitlane analyze tyre-strategy` command with appropriate parameters.

### Step 3: Analyze Results
The command returns JSON with:
- Chart file path
- Strategy summary for each driver (compounds used, stint lengths, pit lap numbers)
- Total pit stops per driver

Read the workspace data files if you need additional details:
- Session data: `{workspace}/data/session_info.json`
- Driver data: `{workspace}/data/drivers.json`

### Step 4: Format Response

Structure your response as:

#### Summary
2-3 sentences directly answering the question. Lead with the key finding (e.g., "Ferrari used a two-stop strategy with Medium-Hard-Medium compounds, while the race winner executed a one-stop strategy").

#### Key Insights
- Identify strategy patterns (one-stop vs two-stop vs three-stop)
- Note compound choices and their effectiveness
- Highlight pit timing differences between teams/drivers
- Explain how strategy affected race outcome
- Compare strategies across teams or within a team

#### Visualization
**YOU MUST include the chart using markdown image syntax:**

```markdown
![Tyre Strategy at Monaco 2024 Race](/Users/user/.pitlane/workspaces/{workspace_id}/charts/tyre_strategy.png)
```

Use the full workspace path returned by the command. The web app will automatically rewrite this to a web-relative URL.

## Example Analysis

**User:** "Show me Ferrari's tyre strategy at Monaco"

**Response:**

### Summary
Ferrari employed different strategies for their two drivers at Monaco 2024. Leclerc ran a one-stop strategy (Soft-Hard), while Sainz attempted a two-stop approach (Soft-Medium-Hard). Leclerc's strategy proved more effective, finishing P3 compared to Sainz's P5.

### Key Insights
- Leclerc's single pit stop on lap 18 minimized time loss in Monaco's difficult-to-overtake layout
- Sainz's two-stop strategy aimed for tire advantage in final stint but lost positions during second stop
- Both drivers started on softs to maximize qualifying track position
- Red Bull's Verstappen (race winner) also ran one-stop, validating Ferrari's approach for Leclerc
- The hard compound showed strong longevity, enabling 45+ lap stints

### Visualization
![Tyre Strategy at Monaco 2024 Race](/Users/user/.pitlane/workspaces/abc123/charts/tyre_strategy.png)

*The visualization shows pit stop timing and compound usage for all drivers throughout the race.*

### 2. Position Changes Visualization

Track how driver positions evolve throughout a race, showing overtakes and pit stop impacts.

**Command:**
```bash
pitlane analyze position-changes \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session R
```

**What it does:**
- Creates line plot showing each driver's position lap-by-lap
- Marks pit stops with visual indicators (▼)
- Calculates overtake statistics and position volatility
- Returns JSON with chart path and detailed statistics

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R = Race, S = Sprint, SQ = Sprint Qualifying)
- `--drivers`: (Optional) Specific drivers (e.g., `--drivers VER --drivers HAM`)
- `--top-n`: (Optional) Show only top N finishers (e.g., `--top-n 10`)

**Note:** Cannot specify both `--drivers` and `--top-n` simultaneously.

**Example Questions:**
- "Show me position changes during the Monaco race"
- "How many overtakes did the top 5 make?"
- "Track Verstappen and Hamilton's battle"
- "Who gained the most positions at Monza?"

**Statistics Returned:**
- **Per driver:** start/finish position, net change, overtakes, times overtaken, biggest gain/loss, volatility, total laps, pit stops
- **Aggregate:** total overtakes, total position changes, average volatility

## Position Changes Analysis Workflow

### Step 1: Identify Parameters
- Year and Grand Prix
- Session type (typically Race, but can be Sprint)
- Optional: Specific drivers or top N finishers

### Step 2: Generate Visualization
Run the `pitlane analyze position-changes` command with appropriate filters.

### Step 3: Interpret Results
The command returns JSON with:
- Chart file path
- Per-driver statistics (overtakes, net change, volatility)
- Aggregate race statistics
- Excluded drivers (DNS/DNF with no position data)

### Step 4: Format Response

#### Summary
2-3 sentences answering the question with key findings (e.g., "Verstappen gained 5 positions from P6 to P1, making 7 overtakes. Hamilton lost 3 positions after a late pit stop").

#### Key Insights
- Identify biggest movers (most positions gained/lost)
- Note overtaking patterns and wheel-to-wheel battles
- Explain how pit stops affected positions
- Highlight position volatility (chaotic vs stable races)
- Compare strategies' effects on track position

#### Visualization
**YOU MUST include the chart using markdown image syntax:**

```markdown
![Position Changes at Monaco 2024 Race](/Users/user/.pitlane/workspaces/{workspace_id}/charts/position_changes.png)
```

## Example Position Changes Analysis

**User:** "Show me position changes for the top 5 at Monaco"

**Response:**

### Summary
The Monaco 2024 race saw relatively stable positions among the top 5 finishers. Verstappen maintained P1 throughout after starting on pole, while Leclerc executed a strong recovery from P4 to P2 with strategic overtakes on laps 18 and 32.

### Key Insights
- Verstappen (P1 start → P1 finish): 0 net change, but defended against 3 overtake attempts
- Leclerc (P4 → P2): +2 positions, 4 successful overtakes, benefited from early pit stop
- Norris (P2 → P3): -1 position, lost out to Leclerc after late pit stop on lap 45
- Piastri (P3 → P4): -1 position, stable race with minimal position changes (volatility: 0.5)
- Sainz (P5 → P5): 0 net change, but showed high volatility (2.1) with multiple position swaps

Total overtakes in top 5: 12 position changes across 78 laps

### Visualization
![Position Changes at Monaco 2024 Race](/Users/user/.pitlane/workspaces/abc123/charts/position_changes_top5.png)

*The visualization shows position evolution with pit stops marked by downward triangles. Notice Leclerc's aggressive climb and the stability of Verstappen's lead.*

### 3. Team Pace Comparison

Compare lap time distributions between teams to identify pace hierarchy and consistency.

**Command:**
```bash
pitlane analyze team-pace \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session R
```

**With team filter:**
```bash
pitlane analyze team-pace \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session R \
  --teams Ferrari \
  --teams Mercedes
```

**What it does:**
- Creates a box plot showing lap time distribution for each team
- Teams sorted left-to-right from fastest median to slowest
- Uses quick laps only (excludes pit in/out, safety car, formation laps)
- Returns JSON with chart path and per-team statistics

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R, Q, FP1, FP2, FP3, S, SQ; defaults to R when only `--gp` is provided)
- `--teams`: (Optional) Specific teams to compare, specify multiple times

**Statistics Returned (per team, sorted fastest first):**
- `team`: Team name
- `median_s`: Median lap time in seconds
- `mean_s`: Mean lap time in seconds
- `std_dev_s`: Standard deviation — lower means more consistent
- `pace_delta_s`: Seconds behind the fastest team's median (0.0 for fastest team)
- `lap_count`: Number of quick laps analyzed

**Example Questions:**
- "Compare team pace at Monaco"
- "Which team was most consistent in the race?"
- "How far behind Ferrari was McLaren at Silverstone?"
- "Show me the pace gap between Red Bull and Mercedes in qualifying"

## Team Pace Analysis Workflow

### Step 1: Identify Parameters
- Year and Grand Prix
- Session type (R for race pace, Q for one-lap pace, FP sessions for long-run comparisons)
- Optional: Specific teams to highlight

### Step 2: Generate Visualization
Run `pitlane analyze team-pace` with appropriate parameters.

### Step 3: Interpret Results
The command returns JSON with:
- `chart_path`: Path to the saved PNG
- `teams_plotted`: List of teams sorted fastest to slowest by median
- `statistics`: Per-team data (median, mean, std_dev, pace_delta, lap_count)

### Step 4: Format Response

#### Summary
2-3 sentences directly answering the question. Lead with the pace hierarchy
(e.g., "Red Bull led the race pace at Monaco with a median of 85.2s, 0.8s ahead
of Ferrari. McLaren showed the strongest consistency with a std_dev of 0.31s").

#### Key Insights
- Identify the fastest team by median pace and their `pace_delta_s` advantage
- Highlight consistency differences (`std_dev_s` — lower is better)
- Note teams with low `lap_count` (possible DNF, DNS, or few representative laps)
- Compare gaps between teams fighting for the same championship positions

#### Visualization
**YOU MUST include the chart using markdown image syntax:**

```markdown
![Team Pace at Monaco 2024 Race](/path/to/workspace/charts/team_pace_2024_monaco_R.png)
```

Use the full `chart_path` value returned by the command.

## Future Analysis Types

The following strategy analysis types are planned for future implementation:

- **Qualifying Results Overview**: Summarize qualifying session results
