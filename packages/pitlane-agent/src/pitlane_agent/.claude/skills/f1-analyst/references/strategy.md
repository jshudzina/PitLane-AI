# Strategy and Results Analysis

Analyze race strategy, tyre choices, pit stops, and results to understand team decisions and race outcomes.

## Available Analysis Types

### 1. Tyre Strategy Visualization

Visualize pit stop timing and tyre compound usage across all drivers in a race.

**Command:**
```bash
pitlane analyze tyre-strategy \
  --session-id $PITLANE_SESSION_ID \
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
![Tyre Strategy at Monaco 2024 Race](/Users/user/.pitlane/workspaces/{session_id}/charts/tyre_strategy.png)
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

## Future Analysis Types

The following strategy analysis types are planned for future implementation:

- **Position Changes**: Track driver positions throughout the race
- **Team Pace Comparison**: Compare average pace between teams
- **Qualifying Results Overview**: Summarize qualifying session results
