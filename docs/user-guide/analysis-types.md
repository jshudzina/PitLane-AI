# Analysis Types

PitLane-AI provides several types of F1 data analysis through specialized skills. Each analysis type uses FastF1 for data access and matplotlib for visualizations.

## Lap Time Analysis

Compare driver lap times with statistical visualizations.

### What It Provides

- Lap time distributions (violin plots, box plots)
- Statistical summaries (mean, median, std dev)
- Pace comparison across drivers
- Qualifying vs. race pace analysis

### Use Cases

- "Compare Verstappen and Hamilton lap times in Monaco 2024"
- "Who was fastest in Q3?"
- "Show me lap time consistency for the top 5 drivers"
- "Analyze pace during the race"

### CLI Command

```bash
pitlane analyze lap-times \
  --session-id abc123 \
  --year 2024 \
  --gp Monaco \
  --session Q \
  --drivers VER --drivers HAM
```

### Output

**Chart:** `workspace/charts/lap_times.png`
- Violin plot showing lap time distribution
- Box plots for outlier detection
- Statistical annotations

**Data:** `workspace/data/lap_times.json`
- Per-driver statistics
- Raw lap times
- Session metadata

### Example Query

```
User: Compare Verstappen and Norris lap times in Silverstone 2024 qualifying

Agent: I'll fetch the lap times for VER and NOR from Silverstone Q...
       [Generates lap_times.png]
       Here's the comparison: Verstappen was 0.234s faster on average.
```

## Tyre Strategy Analysis

Visualize pit stop strategy and compound usage throughout a race.

### What It Provides

- Stint timeline visualization
- Compound usage (Soft, Medium, Hard)
- Pit stop timing and frequency
- Strategy comparison across drivers

### Use Cases

- "Show me Ferrari's tyre strategy in Monaco"
- "What compounds did the top 10 use?"
- "Compare one-stop vs. two-stop strategies"
- "When did drivers pit?"

### CLI Command

```bash
pitlane analyze tyre-strategy \
  --session-id abc123 \
  --year 2024 \
  --gp Monaco \
  --session R
```

### Output

**Chart:** `workspace/charts/strategy.png`
- Horizontal timeline showing stint durations
- Color-coded compounds
- Pit stop markers

**Data:** `workspace/data/strategy.json`
- Per-driver stint information
- Compound choices
- Lap numbers for pit stops

## Driver Information

Query driver details, codes, and career information.

### What It Provides

- Driver names and codes
- Team affiliations by season
- Nationality and date of birth
- Wikipedia links for details

### Use Cases

- "Who drove for Ferrari in 2019?"
- "What's Leclerc's driver code?"
- "List all drivers in the 2024 season"
- "Show me Alpine's driver lineup"

### CLI Command

```bash
pitlane fetch drivers \
  --session-id abc123 \
  --year 2024 \
  --team Ferrari  # optional
```

### Output

**Data:** `workspace/data/drivers.json`
```json
{
  "season": 2024,
  "team": "Ferrari",
  "drivers": [
    {
      "code": "LEC",
      "givenName": "Charles",
      "familyName": "Leclerc",
      "nationality": "Monegasque",
      "url": "https://en.wikipedia.org/wiki/Charles_Leclerc"
    }
  ]
}
```

## Event Schedule

Query race calendar, dates, and session timings.

### What It Provides

- Season calendar with race dates
- Location and round numbers
- Session schedules (FP1, FP2, FP3, Q, R)
- Sprint weekend identification

### Use Cases

- "When is the next race?"
- "Show me the 2024 calendar"
- "What time is qualifying in Monaco?"
- "List all sprint weekends"

### CLI Command

```bash
pitlane fetch schedule \
  --session-id abc123 \
  --year 2024
```

### Output

**Data:** `workspace/data/schedule.json`
```json
{
  "season": 2024,
  "events": [
    {
      "round": 8,
      "raceName": "Monaco Grand Prix",
      "date": "2024-05-26",
      "time": "13:00:00",
      "location": "Monaco",
      "country": "Monaco"
    }
  ]
}
```

## Telemetry Analysis

Compare detailed car telemetry between laps (speed, throttle, brake, gear).

### What It Provides

- Speed traces across lap distance
- Throttle and brake application
- Gear shifts visualization
- Corner-by-corner comparison

### Use Cases

- "Compare speed traces for Verstappen and Hamilton"
- "Show me braking points in Monaco Turn 1"
- "Where do drivers go flat out?"
- "Analyze gear shifts around the lap"

### CLI Command

```bash
pitlane analyze telemetry \
  --session-id abc123 \
  --year 2024 \
  --gp Monaco \
  --session Q \
  --drivers VER --drivers HAM \
  --lap-number 10  # specific lap
```

### Output

**Chart:** `workspace/charts/telemetry.png`
- Multi-panel plot (speed, throttle, brake, gear)
- Lap distance on X-axis
- Driver comparison overlay

**Data:** `workspace/data/telemetry.json`
- Per-driver telemetry data
- Distance, speed, throttle, brake, gear
- Lap metadata

## Analysis Workflow

Typical analysis flow:

1. **Create Workspace**
   ```bash
   SESSION_ID=$(pitlane workspace create | jq -r '.session_id')
   ```

2. **Fetch Session Info**
   ```bash
   pitlane fetch session-info --session-id $SESSION_ID --year 2024 --gp Monaco --session Q
   ```

3. **Run Analysis**
   ```bash
   pitlane analyze lap-times --session-id $SESSION_ID --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
   ```

4. **View Results**
   ```bash
   # Charts saved to workspace
   open ~/.pitlane/workspaces/$SESSION_ID/charts/lap_times.png

   # Data saved to workspace
   cat ~/.pitlane/workspaces/$SESSION_ID/data/lap_times.json | jq
   ```

## Agent Mode

In agent mode (CLI or web), simply ask natural language questions:

**Chat Interface:**
```
User: Compare Verstappen and Hamilton qualifying pace in Monaco 2024

Agent: I'll analyze the qualifying lap times for VER and HAM...

      [Invokes f1-analyst skill]
      [Fetches session data via pitlane CLI]
      [Generates lap time visualization]

      Here's the analysis:

      Verstappen:
      - Mean: 1:12.345 (+/- 0.234s)
      - Best: 1:12.123

      Hamilton:
      - Mean: 1:12.567 (+/- 0.321s)
      - Best: 1:12.234

      [lap_times.png displayed]

      Verstappen was consistently faster by ~0.2s on average.
```

The agent automatically:
- Determines the relevant skill (f1-analyst)
- Extracts parameters (year, GP, session, drivers)
- Executes CLI commands via Bash tool
- Generates and references visualizations
- Provides natural language summary

## Data Sources

| Analysis Type | Data Source |
|---------------|-------------|
| Lap Times | FastF1 API |
| Tyre Strategy | FastF1 API |
| Telemetry | FastF1 API |
| Driver Info | Ergast API |
| Schedule | FastF1 Schedule |

## Limitations

- **Historical Data**: FastF1 data available from 2018 onwards (incomplete before)
- **Live Timing**: Not real-time (data available ~1 hour after session)
- **Telemetry**: Limited to GPS-based data (no internal car sensors)
- **Sprint Weekends**: Different session structure (SQ instead of Q)

## Related Documentation

- [CLI Reference](cli-reference.md) - Detailed CLI command syntax
- [Skills Usage](skills-usage.md) - How agent skills work
- [Architecture: Skills](../architecture/skills.md) - Skill system internals
