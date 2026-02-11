# Medium Detail Events Reference

Interpretation guide for **medium detail** race control events (`--detail medium`).

## What's Included

Medium detail includes all high detail events plus:
- YELLOW flags (single and double)
- DRS status changes
- Significant penalties and investigations

**Typical volume**: 30-50 messages per race

**Also see**: [high-detail-events.md](high-detail-events.md) for RED flags, safety cars, and major incidents

## Contents
- [Yellow Flag Events](#yellow-flag-events)
- [DRS Status Changes](#drs-status-changes)
- [Penalties and Investigations](#penalties-and-investigations)
- [Connecting to Data Anomalies](#connecting-to-data-anomalies)

## Yellow Flag Events

### Single YELLOW Flag

**What It Means**: Incident in specific area, drivers must slow down and be alert

**Message**: `"YELLOW IN TRACK SECTOR X"`

**Rules**:
- Drivers must slow down in affected sector
- No overtaking in yellow flag zone
- Less severe than double yellow

**Data Impacts**:
- **Sector times**: Slower sector times in affected sector (typically 0.5-2 seconds slower)
- **Lap times**: Overall lap time increase of 0.5-3 seconds depending on incident location
- **Qualifying**: Lap may be abandoned if yellow flag interrupts flying lap

### Double YELLOW Flag

**What It Means**: Serious incident in area, drivers must significantly reduce speed and be prepared to stop

**Message**: `"DOUBLE YELLOW IN TRACK SECTOR X"`

**Rules**:
- Drivers must slow significantly
- Must be prepared to stop or take evasive action
- Absolutely no overtaking
- More severe than single yellow - indicates danger

**Data Impacts**:
- **Sector times**: Significantly slower sector times (typically 2-5+ seconds slower)
- **Lap times**: Major lap time increase of 3-10+ seconds
- **Qualifying**: Lap effectively ruined - driver will likely abort and pit
- **Position changes**: Explains why driver lost time to competitors

### CLEAR Flag

**What It Means**: Yellow flag condition resolved, normal racing resumes

**Message**: `"CLEAR IN TRACK SECTOR X"`

**Impact**: Sector times return to normal pace on subsequent laps

**Note**: CLEAR messages are filtered in high detail mode (low information value - just state clearing).

### Example Interpretation

**User asks**: "Why was Sainz's lap 12 so slow in qualifying?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --lap-start 12 --lap-end 12 --detail medium --category Flag
```

If you see "DOUBLE YELLOW IN TRACK SECTOR 2" on lap 12:
- "There was a double yellow flag in sector 2 during lap 12, which required Sainz to significantly reduce speed. This explains his slow lap time and why he likely abandoned that lap attempt."

## DRS Status Changes

### What is DRS
DRS (Drag Reduction System) is an overtaking aid that reduces rear wing angle, allowing higher straight-line speed when within 1 second of car ahead.

### Message Patterns

**"DRS ENABLED"**
- DRS available for use in designated zones
- Typically enabled lap 2 or 3 of race
- Standard for most races

**"DRS DISABLED"**
- DRS not available (weather, track conditions, or incidents)
- Common in wet conditions or after major incidents
- Significantly affects overtaking difficulty

### Data Impacts

**Overtaking frequency**:
- DRS enabled: Higher overtaking rate, especially on long straights
- DRS disabled: Fewer overtakes, harder to pass despite pace advantage

**Lap times**:
- Minimal direct impact (DRS only available when close to another car)
- Cars in DRS range may be 0.2-0.4s faster per lap

**Race strategy**:
- DRS enabled: Following car has advantage, "DRS train" formations
- DRS disabled: Track position more valuable, fewer position changes

### Example Interpretation

**User asks**: "Why were there so few overtakes in this race despite close competition?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --category Drs
```

If you see "DRS DISABLED" at race start:
- "DRS was disabled for this race (likely due to weather conditions). Without DRS, overtaking is significantly harder even when a driver has a pace advantage, which explains the low number of position changes."

## Penalties and Investigations

### Investigation Messages

**"... NOTED"**
- FIA is aware of incident, may investigate
- No action taken yet
- Format: `"TURN X INCIDENT INVOLVING CAR Y NOTED - [REASON]"`

**"UNDER INVESTIGATION"**
- Formal investigation opened by stewards
- Penalty may be issued
- Format: `"[INCIDENT DESCRIPTION] UNDER INVESTIGATION"`

**"REVIEWED NO FURTHER INVESTIGATION"**
- Incident reviewed, no penalty
- Racing incident or no rule violation found

### Penalty Messages

**Time Penalties**:
- `"5 SECOND TIME PENALTY FOR CAR X"` - Added to final race time
- `"10 SECOND TIME PENALTY FOR CAR X"` - More severe offense
- Applied post-race or at next pit stop

**Other Penalties**:
- Drive-through penalty (must drive through pit lane at speed limit)
- Stop-go penalty (must stop in pit box for specified time)
- Grid penalty (for next race)
- Disqualification (DSQ)

### Common Penalty Reasons
- Causing a collision
- Forcing another driver off track
- Unsafe pit release
- Exceeding track limits (repeated violations)
- Ignoring flags (especially blue flags)

### Data Impacts

**Position changes**:
- Time penalties change final classification
- Driver may finish on track P3 but classified P5 after penalty

**Lap times**:
- Drive-through or stop-go penalties show as very slow lap time
- Driver effectively loses 20-30 seconds

**Strategy changes**:
- If penalty known during race, team may adjust strategy
- May affect when driver pits (can serve time penalty during pit stop)

### Example Interpretation

**User asks**: "Why did Perez finish P4 when he crossed the line in P3?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --driver 11 --detail medium
```

If you see "5 SECOND TIME PENALTY FOR CAR 11":
- "Perez received a 5-second time penalty during the race (for [reason]). This was added to his final race time, which dropped him from P3 on track to P4 in the final classification."

## Connecting to Data Anomalies

### Sector Time Spike + YELLOW Flag
**Pattern**: Driver's S2 time suddenly 2+ seconds slower

**Interpretation**: Yellow or double yellow flag in sector 2 required driver to slow down. This is expected behavior, not a performance issue.

### Multiple Slow Laps + Double YELLOW
**Pattern**: Several drivers all have slow lap times in same lap

**Interpretation**: Double yellow flag affected multiple drivers. Those on flying laps likely abandoned their attempts.

### Position Loss + Penalty
**Pattern**: Driver loses 1-2 positions after race ends

**Interpretation**: Time penalty was applied post-race. Check race control messages for penalty reason.

### DRS Disabled + Strategy Shift
**Pattern**: Teams stop pursuing overcut/undercut strategies, focus on track position

**Interpretation**: Without DRS, overtaking on track is much harder, so teams prioritize clean air and track position over tire strategy.

### Qualifying Lap Deleted + YELLOW Flag
**Pattern**: Driver's best lap time doesn't count toward grid position

**Interpretation**: Yellow flag was shown during that lap, invalidating the time due to failure to slow down sufficiently or complete the lap under yellow.
