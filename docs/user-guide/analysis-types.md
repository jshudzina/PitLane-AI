# Analysis Types

PitLane-AI provides several types of F1 data analysis through the web interface. Simply ask questions in natural language, and the AI agent will automatically fetch data, generate visualizations, and provide insights. Each analysis type uses FastF1 for data access and matplotlib for visualizations.

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

### Example Interaction

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

### What You'll Get

The agent will generate a horizontal timeline visualization showing:
- Stint durations for each driver
- Color-coded tyre compounds (Soft, Medium, Hard)
- Pit stop timing markers
- Strategy comparison across the field

## Qualifying Results

View the final qualifying classification and each driver's gap to pole, colored by qualifying phase.

### What It Provides

- Horizontal bar chart: bar length = gap to pole position in seconds
- Q3 finishers shown in team color; Q2 eliminees in dimmed team color; Q1 eliminees in gray
- Dashed section dividers separating Q3, Q2, and Q1 phases
- Automatic support for 20-car (≤2025) and 22-car (2026+) qualifying formats

### Use Cases

- "Who took pole at Monaco 2024?"
- "Which drivers made it to Q3?"
- "Show me the qualifying gap between Verstappen and Hamilton"
- "Who was knocked out in Q1?"
- "Show me the sprint shootout results from China"

### What You'll Get

The agent generates a horizontal bar chart showing:
- Each driver's gap to pole (P1 at top, last qualifier at bottom)
- Color coding by phase: full team color for Q3 finishers, dimmed for Q2 eliminees, gray for Q1 eliminees
- Dashed dividers marking the Q3/Q2 and Q2/Q1 cutoffs
- Pole sitter name and lap time in the response

Works for standard qualifying (`Q`), sprint qualifying (`SQ`), and sprint shootout (`SS`) sessions.

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

### What You'll Get

The agent will provide driver information including:
- Driver names and three-letter codes (e.g., LEC for Leclerc)
- Team affiliations for the requested season
- Nationality and biographical details
- Links to Wikipedia for more information

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

### What You'll Get

The agent will provide schedule information including:
- Race dates and locations for the season
- Session timings (Practice, Qualifying, Race)
- Sprint weekend identification
- Round numbers and Grand Prix names

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

### What You'll Get

The agent will generate a multi-panel telemetry plot showing:
- Speed traces across lap distance
- Throttle and brake application patterns
- Gear shift visualization
- Corner-by-corner driver comparison overlay

## How to Use

Using PitLane-AI is simple:

1. **Open the Web Interface**
   - Start the web app (see [Web Interface](web-interface.md))
   - Navigate to [http://localhost:8000](http://localhost:8000)

2. **Ask Your Question**
   - Type your question in natural language
   - Be specific about the race, session, and drivers you're interested in
   - Example: "Compare Verstappen and Hamilton qualifying pace in Monaco 2024"

3. **Review the Results**
   - The agent will stream its analysis in real-time
   - Visualizations (charts, plots) are generated automatically
   - Interactive charts are displayed directly in the chat

### Example Interaction

```
User: Compare Verstappen and Hamilton qualifying pace in Monaco 2024

Agent: I'll analyze the qualifying lap times for VER and HAM in Monaco 2024...

      [Fetches session data]
      [Generates lap time visualization]

      Here's the analysis:

      Verstappen:
      - Mean: 1:12.345 (+/- 0.234s)
      - Best: 1:12.123

      Hamilton:
      - Mean: 1:12.567 (+/- 0.321s)
      - Best: 1:12.234

      [lap_times.png displayed in chat]

      Verstappen was consistently faster by ~0.2s on average.
```

The agent automatically:
- Determines what analysis to perform
- Extracts parameters (year, GP, session, drivers)
- Fetches and processes F1 data
- Generates visualizations
- Provides natural language insights

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

- [Web Interface](web-interface.md) - Getting started with the web app
- [Architecture: Skills](../architecture/skills.md) - How the agent system works
- [Agent CLI](../agent-cli/cli-reference.md) - CLI reference (for agents/developers)
