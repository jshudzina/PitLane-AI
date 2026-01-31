# Lap Time Analysis

Analyze driver lap times to understand performance, consistency, and pace across sessions.

## Available Analysis Types

### 1. Driver Lap Times Scatterplot

Compare lap times across drivers to identify pace differences and consistency patterns.

**Command:**
```bash
pitlane analyze lap-times \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session Q \
  --drivers VER --drivers HAM --drivers LEC
```

**What it does:**
- Creates a scatter plot showing each lap time for selected drivers
- Returns JSON with chart path and statistics (fastest lap, average lap time, lap count)
- Chart is saved to workspace charts directory

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R=Race, Q=Qualifying, FP1, FP2, FP3, S=Sprint, SQ=Sprint Qualifying)
- `--drivers`: Driver abbreviations (can specify multiple, see SKILL.md for reference)

**Example Questions:**
- "Compare Verstappen and Norris lap times at Silverstone qualifying"
- "Show me lap time consistency for the top 3 drivers in Monaco"
- "Who was faster in FP2 - Hamilton or Russell?"

### 2. Driver Lap Times Distribution Plot

Analyze lap time distributions to understand statistical spread, consistency, and tire compound effects across drivers.

**Command:**
```bash
# Default to top 10 finishers
pitlane analyze lap-times-distribution \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session R

# With specific drivers
pitlane analyze lap-times-distribution \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session R \
  --drivers VER --drivers HAM --drivers LEC
```

**What it does:**
- Creates a violin plot showing lap time distributions for each driver
- Overlays individual laps as points, colored by tire compound (SOFT=red, MEDIUM=yellow, HARD=white)
- Returns JSON with chart path and statistics (best, median, lap count, compounds used)
- Chart is saved to workspace charts directory
- Defaults to top 10 finishers if no drivers specified

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R=Race, Q=Qualifying, FP1, FP2, FP3, S=Sprint, SQ=Sprint Qualifying)
- `--drivers` (optional): Driver abbreviations (specify multiple times or omit for top 10)

**Example Questions:**
- "Show me lap time consistency for top finishers at Silverstone race"
- "Compare pace distribution between Verstappen and Norris in qualifying"
- "Which drivers had the widest lap time spread in the Monaco race?"
- "How did tire compounds affect lap time distributions at Monza?"

**Interpretation Guide:**
- **Violin width**: Shows density of laps at that time range
  - Wider = more laps clustered at that time
  - Narrow = fewer laps at that time
- **Individual points (swarm)**: Each lap colored by compound
  - Point spread = consistency variation
  - Tight clustering = driver found optimal pace
  - Vertical spread = inconsistency or degradation

## Analysis Workflow

### Step 1: Choose Analysis Type
- Use **Scatterplot** (`lap-times`) to see lap-by-lap progression through the session
- Use **Distribution** (`lap-times-distribution`) to compare statistical spread and tire compound effects

### Step 2: Identify Session Parameters
Extract from the user's question:
- Year (default to most recent completed season if not specified)
- Grand Prix name (use official names)
- Session type
- Drivers to compare (if specific drivers mentioned)

### Step 3: Generate Visualization
Run the appropriate command (`pitlane analyze lap-times` or `pitlane analyze lap-times-distribution`) with appropriate parameters.

### Step 4: Analyze Results
The command returns JSON with:
- Chart file path
- Statistics for each driver (fastest lap, average, consistency)
- Lap count

### Step 5: Format Response

Structure your response as:

#### Summary
2-3 sentences directly answering the question. Lead with the key finding (e.g., "Verstappen was 0.3s faster than Norris with a best lap of 1:12.345").

#### Key Insights
- Highlight pace differences with specific times
- Note consistency patterns (e.g., "Hamilton's lap times varied by only 0.2s")
- Compare to session context (qualifying vs race pace)
- Identify any anomalies or interesting patterns

#### Visualization
**YOU MUST include the chart using markdown image syntax:**

```markdown
![Verstappen vs Hamilton Lap Times at Monaco 2024 Qualifying](/Users/user/.pitlane/workspaces/{session_id}/charts/lap_times.png)
```

Use the full workspace path returned by the command. The web app will automatically rewrite this to a web-relative URL.

## Example Analysis

**User:** "Compare Verstappen and Norris lap times at Silverstone qualifying"

**Response:**

### Summary
Verstappen outpaced Norris in Silverstone qualifying with a fastest lap of 1:27.097 compared to Norris's 1:27.420, a gap of 0.323 seconds. Both drivers showed strong consistency across their qualifying runs.

### Key Insights
- Verstappen's fastest lap came in Q3, lap 2
- Norris was more consistent with only 0.4s spread across his laps
- Both drivers improved progressively through Q1, Q2, and Q3
- The gap narrowed in Q3 compared to earlier sessions

### Visualization
![Verstappen vs Norris Lap Times at Silverstone 2024 Qualifying](/Users/user/.pitlane/workspaces/abc123/charts/lap_times.png)

*The scatter plot shows lap time distribution across all three qualifying sessions.*
