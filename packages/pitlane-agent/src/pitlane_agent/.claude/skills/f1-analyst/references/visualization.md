# Circuit Visualization

Visualize circuit layouts with numbered corner labels to understand track geography.

## Available Analysis Types

### 1. Track Map with Numbered Corners

Display a circuit layout with labeled corner positions, showing the track outline and corner numbering used by FIA.

**Command:**
```bash
pitlane analyze track-map \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session Q
```

**What it does:**
- Loads position data from the fastest lap to draw the track outline
- Retrieves circuit info with corner positions, numbers, and angles
- Rotates the track for standard TV-style orientation
- Draws numbered corner markers with connecting lines to the track
- Returns JSON with chart path, corner count, and corner details
- Chart is saved to workspace charts directory

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R=Race, Q=Qualifying, FP1, FP2, FP3, S=Sprint, SQ)

**Example Questions:**
- "Show me the Monaco circuit layout"
- "What corners does Silverstone have?"
- "Draw me a map of the Spa-Francorchamps track"
- "How many corners are there at Monza?"
- "Show me the circuit for the Azerbaijan Grand Prix"

**Limitations:**
- Requires position data to be available (typically 2018 onwards)
- Track outline comes from the fastest lap, so slight variations possible
- Some circuits may have corners with letter suffixes (e.g., 9a, 9b) for tight sequences

## Analysis Workflow

### Step 1: Identify Session
Extract from user's question:
- Year and Grand Prix
- Session type (any session works; qualifying often has clean laps)

### Step 2: Generate Track Map
Run `pitlane analyze track-map` with appropriate parameters.

### Step 3: Analyze Results
The command returns JSON with:
- Chart file path
- Circuit name and event metadata
- Number of corners
- Corner details (number and optional letter for each corner)

### Step 4: Format Response

#### Summary
1-2 sentences describing the circuit layout — number of corners, notable features.

Example: "The Monaco street circuit features 19 corners across its 3.337 km layout, including the famous hairpin at Turn 6 (Fairmont) and the tight chicane at Turn 10-11 (Nouvelle Chicane)."

#### Key Insights
- Total number of corners and circuit character (high-speed, technical, street circuit)
- Notable corner sequences or complexes
- Relevance to race strategy (overtaking opportunities, DRS zones near corners)

#### Visualization
**YOU MUST include the chart using markdown image syntax:**

```markdown
![Track Map - Monaco 2024](/Users/user/.pitlane/workspaces/{workspace_id}/charts/track_map_2024_monaco_Q.png)
```

Use the full workspace path returned by the command. The web app will automatically rewrite this to a web-relative URL.

**Chart interpretation guide:**
- White line shows the track outline from the fastest lap
- Grey circles with numbers indicate corner positions
- Corner numbers follow FIA numbering (shown on TV graphics)
- Letters after numbers (e.g., 9a, 9b) indicate sub-sections of the same corner complex
- Track is rotated for standard viewing orientation

## Example Analysis

**User:** "Show me the Monaco circuit layout"

**Response:**

### Summary
The Monaco street circuit features 19 corners across its iconic 3.337 km layout. The tight, twisting nature of the track makes it one of the most demanding circuits on the calendar, with very limited overtaking opportunities outside of the first chicane.

### Key Insights
- **19 corners** packed into one of the shortest tracks on the calendar
- **Turn 6 (Fairmont Hairpin)**: The slowest corner in F1, taken at ~60 km/h
- **Turns 10-11 (Nouvelle Chicane)**: Primary overtaking opportunity with DRS on the preceding straight
- **Turn 1 (Sainte Devote)**: Key first-lap corner, often sees contact
- **Swimming Pool section (Turns 13-16)**: High-speed sequence requiring precision

### Circuit Map
![Track Map - Monaco 2024](/Users/user/.pitlane/workspaces/abc123/charts/track_map_2024_monaco_Q.png)

*The track map shows the full circuit layout with numbered corner positions following FIA convention. Corner markers are placed outside the track with connecting lines indicating their location.*
