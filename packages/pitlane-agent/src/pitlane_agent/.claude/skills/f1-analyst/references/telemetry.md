# Telemetry Analysis

Analyze detailed car telemetry data including speed traces, gear shifts, throttle/brake application, and lap comparisons.

## Available Analysis Types

### 1. Speed Trace Overlay

Compare speed profiles between drivers across track distance to identify performance differences.

**Command:**
```bash
pitlane analyze speed-trace \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp "Spanish Grand Prix" \
  --session Q \
  --drivers VER --drivers HAM --drivers LEC
```

**What it does:**
- Loads telemetry data for specified drivers' fastest laps
- Creates overlaid speed vs. distance plot showing where drivers gain/lose speed
- Returns JSON with chart path, speed statistics, and delta analysis
- Chart is saved to workspace charts directory

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Spanish Grand Prix", "Monaco")
- `--session`: Session type (R=Race, Q=Qualifying, FP1, FP2, FP3, S=Sprint, SQ)
- `--drivers`: 2-5 driver abbreviations to compare (specify multiple times: --drivers VER --drivers HAM)
- `--annotate-corners`: (optional flag) Add vertical corner markers and labels to the chart for easy track reference

**Example Questions:**
- "Compare Verstappen and Hamilton's speed traces at Silverstone qualifying"
- "Where did Leclerc lose time to Sainz in Q3?"
- "Show me the speed difference between the top 3 qualifiers"
- "Which driver carries more speed through the corners at Monaco?"
- "Show speed trace with corner labels at Spa"
- "Annotate corners on the speed comparison for Monaco qualifying"

**Limitations:**
- Requires telemetry data to be available (typically 2018 onwards, varies by session)
- Compares fastest laps only (not arbitrary lap selection)
- Minimum 2 drivers, maximum 5 drivers for chart readability
- Some historic sessions may have incomplete telemetry data

### 2. Gear Shifts on Track Map

Visualize gear usage overlaid on the circuit layout, showing which gear a driver uses through each section of the track with numbered corner labels.

**Command:**
```bash
pitlane analyze gear-shifts-map \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session Q \
  --drivers VER
```

**What it does:**
- Loads fastest lap telemetry including position data (X, Y) and car data (nGear)
- Merges position and gear telemetry on time-based index
- Creates color-coded track map showing gear selection (1-8)
- Adds numbered corner markers with connecting lines for reference
- Displays vertical colorbar on the right showing gear range
- Returns JSON with chart path, gear statistics, and lap details

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R=Race, Q=Qualifying, FP1, FP2, FP3, S=Sprint, SQ)
- `--drivers`: Single driver abbreviation (only 1 driver supported)

**Example Questions:**
- "Show me Verstappen's gear usage on track at Monaco qualifying"
- "What gear does Hamilton use through Maggots-Becketts?"
- "Create a gear shift map for Norris at Spa"
- "Which gear is used most at Monza?"
- "Visualize Leclerc's gearing strategy around Silverstone"

**Returned Statistics:**
- `gear_distribution`: Count and percentage for each gear used
- `most_used_gear`: The gear used most frequently on the lap
- `highest_gear`: Maximum gear reached (typically on straights)
- `total_gear_changes`: Number of gear shifts during the lap
- `lap_number`: Which lap was analyzed (fastest lap)
- `lap_time`: Lap time in format MM:SS.mmm

**Chart Interpretation:**
- Track outline colored by gear selection (1-8)
- Colors from the "Paired" colormap distinguish between gears
- Grey circles with white numbers show corner positions
- Vertical colorbar on right shows gear number mapping (1-8)
- Title includes driver name, lap number, and lap time
- Track rotated for standard TV-style viewing orientation

**Limitations:**
- Only supports 1 driver at a time for clarity
- Requires both position and gear telemetry (2018+ seasons)
- Uses fastest lap only (not arbitrary lap selection)
- Some circuits may have limited corner data
- Gear data may be unavailable for some older sessions

### 3. Multi-Channel Telemetry Comparison

Compare all five telemetry channels (Speed, RPM, Gear, Throttle, Brake) between drivers in a single interactive chart with synchronized subplots.

**Command:**
```bash
pitlane analyze telemetry \
  --workspace-id $PITLANE_WORKSPACE_ID \
  --year 2024 \
  --gp Monaco \
  --session Q \
  --drivers VER --drivers HAM \
  --annotate-corners
```

**What it does:**
- Loads telemetry data for specified drivers' fastest laps
- Creates 5 synchronized subplots: Speed (km/h), RPM, Gear, Throttle (%), Brake
- Interactive Plotly HTML chart with hover tooltips showing per-driver deltas
- Teammate differentiation: solid vs dashed lines for drivers on the same team
- Returns JSON with chart path, per-driver statistics, and delta analysis
- Chart is saved as HTML to workspace charts directory

**Parameters:**
- `--year`: Season year (e.g., 2024)
- `--gp`: Grand Prix name (e.g., "Monaco", "Silverstone")
- `--session`: Session type (R=Race, Q=Qualifying, FP1, FP2, FP3, S=Sprint, SQ)
- `--drivers`: 2-5 driver abbreviations to compare (specify multiple times)
- `--annotate-corners`: (optional flag) Add vertical corner markers to all subplots
- `--test N --day N`: For pre-season testing sessions (mutually exclusive with --gp/--session)

**Example Questions:**
- "Show me a full telemetry comparison between Verstappen and Hamilton at Monaco"
- "Compare all telemetry channels for the top 3 qualifiers at Silverstone"
- "Where is Norris losing time to Verstappen in braking and throttle application?"
- "Show me the complete telemetry overlay including RPM and gear shifts"
- "Full telemetry comparison with corner annotations at Spa"
- "Compare telemetry for the Red Bull drivers in pre-season testing day 2"

**Returned Statistics (per driver):**
- `max_speed`: Maximum speed reached (km/h)
- `avg_speed`: Average speed across the lap (km/h)
- `max_rpm`: Maximum RPM reached
- `fastest_lap_time`: Lap time in HH:MM:SS format
- `fastest_lap_number`: Which lap number was analyzed

**Chart Interpretation:**
- 5 vertically stacked subplots sharing the same X-axis (distance in meters)
- Hover over any subplot to see all drivers' values and deltas at that distance
- Each driver colored by team color; teammates distinguished by solid vs dashed lines
- Zooming/panning one subplot synchronizes all subplots
- Corner annotations (when enabled) appear as vertical dashed lines across all subplots

**Limitations:**
- Requires telemetry data to be available (typically 2018 onwards)
- Compares fastest laps only (not arbitrary lap selection)
- Minimum 2 drivers, maximum 5 drivers for chart readability
- Brake data is boolean (on/off), not brake pressure

## Analysis Workflow

### Step 1: Identify Session and Drivers
Extract from user's question:
- Year and Grand Prix
- Session type (qualifying usually best for pure speed comparison)
- Specific drivers or comparison request (e.g., "top 3", "pole vs P2")

### Step 2: Generate Visualization
Choose the appropriate command:
- `pitlane analyze speed-trace` for speed-only comparison (PNG)
- `pitlane analyze gear-shifts-map` for gear usage on track map (PNG)
- `pitlane analyze telemetry` for full multi-channel comparison (interactive HTML)

### Step 3: Analyze Results
The command returns JSON with:
- Chart file path
- Speed statistics per driver (max speed, average speed, fastest lap time)
- Speed delta analysis (where maximum difference occurs on track)

### Step 4: Format Response

#### Summary
2-3 sentences directly answering the question with key findings. Focus on:
- Maximum speed differences and where they occur
- Braking point differences (sharp speed drops)
- Corner speed comparison (minimum speeds in turns)
- Acceleration differences (rate of speed increase)

Example: "Verstappen's fastest lap showed superior straight-line speed of 312 km/h compared to Hamilton's 308 km/h, with the maximum difference of 4.2 km/h occurring 2,847 meters from the start. Hamilton carried more speed through Turn 9 (187 km/h vs 183 km/h), suggesting different setup philosophies."

#### Key Insights
Identify where drivers gain/lose time based on speed traces:
- **Braking points**: Sharp speed drops indicate braking zones - earlier/later braking affects corner entry
- **Cornering speeds**: Minimum speed in corners shows mechanical grip and setup
- **Acceleration zones**: Slope of speed increase shows traction and power delivery
- **Straight-line speed**: Maximum speeds indicate drag levels and engine power
- **Speed delta location**: Where maximum difference occurs (straight, corner, exit)

#### Visualization
**YOU MUST include the chart in the response.** Use the full workspace path returned by the command. The web app will automatically rewrite workspace paths to web-relative URLs.

**For PNG charts (speed-trace, gear-shifts-map):** Use markdown image syntax:

```markdown
![Speed Trace Comparison at Spanish GP 2024](/Users/user/.pitlane/workspaces/{workspace_id}/charts/speed_trace_2024_spanish_grand_prix_Q_HAM_LEC_VER.png)
```

**For HTML charts (telemetry):** Also use markdown image syntax — the web app automatically converts `.html` references to interactive iframes:

```markdown
![Telemetry Comparison at Monaco 2024](/Users/user/.pitlane/workspaces/{workspace_id}/charts/telemetry_2024_monaco_Q_HAM_VER.html)
```

**Chart interpretation guide:**
- X-axis shows distance from start line in meters
- Y-axis shows speed in km/h
- Each driver's trace is a continuous line in their team color
- Sharp drops = braking zones
- Local minimums = corner apex speeds
- Rising slopes = acceleration zones
- Horizontal sections = flat-out / DRS zones
- Vertical dashed lines = corner positions (when `--annotate-corners` is used)
- Labels above the chart = corner numbers (e.g., "1", "2", "9a")

## Example Analysis

**User:** "Compare Verstappen and Hamilton's speed traces at Spanish GP qualifying"

**Response:**

### Summary
Verstappen's pole lap at Spanish GP 2024 qualifying showed superior straight-line speed reaching 312 km/h compared to Hamilton's 308 km/h. The maximum speed difference of 4.2 km/h occurred 2,847 meters from the start (main straight). However, Hamilton carried 4 km/h more speed through Turn 9 (187 km/h vs 183 km/h), suggesting different downforce levels.

### Key Insights
- **Maximum speed difference**: 4.2 km/h at 2,847m from start (main straight before Turn 1)
- **Braking zones**: Verstappen braked later into Turn 1, carrying 2 km/h more entry speed
- **Turn 4 traction**: Hamilton showed slightly better traction out of Turn 4 (acceleration slope 5% steeper)
- **High-speed corners**: Turn 9 speed difference (4 km/h advantage to Hamilton) suggests higher downforce setup
- **Final sector**: Both drivers identical approach to final chicane, indicating setup convergence
- **Lap time correlation**: Turn 9 speed advantage translated to 0.15s gain for Hamilton in that sector, but Verstappen's straight-line speed more than compensated

### Speed Trace Analysis
![Speed Trace Comparison at Spanish GP 2024](/Users/user/.pitlane/workspaces/abc123/charts/speed_trace_2024_spanish_grand_prix_Q_HAM_VER.png)

*The speed traces show distance on the x-axis (meters from start) and speed on the y-axis (km/h). Overlaid traces allow identification of braking points (sharp drops), acceleration zones (rising slopes), and cornering speeds (local minimums). Verstappen's trace (Red Bull blue) consistently runs above Hamilton's (Mercedes silver) on straights, while Hamilton's trace shows advantage through high-speed Turn 9.*

### Race Strategy Implications
- Verstappen's low-drag setup favors overtaking but may increase tire degradation in high-speed corners
- Hamilton's higher downforce provides tire preservation and wet weather advantage
- DRS effectiveness will be crucial for Verstappen to maintain/extend lead

## Telemetry Data Available in FastF1

FastF1 provides access to:
- Speed (km/h)
- RPM
- Gear selection (1-8)
- Throttle position (0-100%)
- Brake application (boolean)
- DRS status
- Position data (X, Y coordinates)

## Technical Notes

**Telemetry Availability:**
- Typically available from 2018 season onwards
- Some sessions may have partial or missing telemetry
- Archive data may be incomplete for older seasons

**Data Frequency:**
- FastF1 provides telemetry at ~250Hz (4ms intervals)
- Distance calculation interpolates GPS position data
- Lap distance is normalized to track length

**Comparison Method:**
- Speed traces compare fastest laps of each driver
- Distance-based alignment (not time-based) for spatial comparison
- Enables identification of where on track differences occur
