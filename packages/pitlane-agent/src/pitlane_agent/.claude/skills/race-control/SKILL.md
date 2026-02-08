---
name: race-control
description: Contextualizes race control messages to explain F1 session events. Use when user asks about race incidents, safety cars, flags, penalties, why drivers pitted unexpectedly, what caused anomalies in lap times or positions, or wants timeline of race interruptions.
---

# Race Control Message Contextualization

Interpret race control messages to explain what happened during an F1 session and provide context for data anomalies.

## Workflow

### 1. Determine Scope

Based on the user's question, identify the appropriate scope and filters:

- **Specific event investigation**: "Why did Hamilton pit early on lap 3?"
  → Fetch laps 1-5, medium detail to see incidents/flags that might have triggered it

- **Event type focus**: "What flags were shown in sector 2?"
  → Fetch --sector 2 --category Flag

- **Full race timeline**: "What major events happened in the race?"
  → Fetch high detail (only major events like red flags, safety cars, race start/finish)

- **Driver-specific inquiry**: "What happened to Verstappen?"
  → Fetch --driver 1 (Verstappen's racing number)

- **Complete incident analysis**: "Give me everything that happened in lap 15"
  → Fetch --lap-start 15 --lap-end 15 --detail full

### 2. Fetch Messages

Use `pitlane fetch race-control` with appropriate filters. The session ID is available in `$PITLANE_SESSION_ID`.

#### Basic Examples

```bash
# Major events only (default - recommended starting point)
pitlane fetch race-control \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session R

# Investigate specific lap range
pitlane fetch race-control \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session R \
  --lap-start 10 \
  --lap-end 15 \
  --detail medium

# Safety car periods only
pitlane fetch race-control \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session R \
  --category SafetyCar

# Driver-specific events
pitlane fetch race-control \
  --session-id $PITLANE_SESSION_ID \
  --year 2024 \
  --gp Monaco \
  --session R \
  --driver 1
```

#### Filter Reference

**Detail Levels** (progressive disclosure):
- `--detail high` (default): RED flags, safety cars, race start/finish, major collisions (~10-20 messages)
- `--detail medium`: + YELLOW flags (single/double), DRS changes, significant penalties (~30-50 messages)
- `--detail full`: All messages including BLUE flags, CLEAR, track limits violations (~100+ messages)

**Category Filters**:
- `--category Flag`: Flag-related messages (RED, YELLOW, BLUE, GREEN, CHEQUERED, CLEAR)
- `--category Other`: General messages (incidents, penalties, track limits)
- `--category Drs`: DRS enabled/disabled status
- `--category SafetyCar`: Safety car deployment and withdrawal

**Other Filters**:
- `--flag-type RED`: Specific flag type (RED, YELLOW, DOUBLE YELLOW, GREEN, BLUE, CLEAR, CHEQUERED)
- `--driver N`: Racing number (e.g., 1 for Verstappen, 44 for Hamilton, 16 for Leclerc)
- `--lap-start N --lap-end M`: Lap range (inclusive)
- `--sector N`: Track sector number (track-specific)

**Filter Combination**:
Filters are applied in sequence. For example, `--category Flag --detail high` shows only high-impact flag messages.

### 3. Interpret and Contextualize

Read the saved file at `data/race_control.json` and analyze the messages chronologically.

#### Identify Critical Events

**RED flag** → Race stopped immediately
- Explains large gaps in lap times
- Drivers may pit during red flag (free tire change)
- Session resumes when "TRACK CLEAR" + "GREEN LIGHT - PIT EXIT OPEN" appear

**SAFETY CAR / VSC** → Race neutralized
- Explains bunched field in positions
- Common strategy trigger (cheap pit stop under SC)
- VSC (Virtual Safety Car) less restrictive than full SC

**DOUBLE YELLOW** → Serious incident in sector
- Drivers must slow significantly and be prepared to stop
- No overtaking allowed
- Explains slow sector times or lap time spikes

**YELLOW** → Incident in area
- Drivers must slow and no overtaking
- Single waved flag vs double (severity indicator)

**DRS DISABLED** → No DRS overtaking assistance
- Explains why overtaking became difficult
- Often disabled due to weather or incidents

**Collisions/Incidents** → Race-changing events
- Check for penalties issued (time penalties, DSQ)
- Explains position changes or retirements
- May trigger subsequent safety measures

#### Connect to Other Data

When contextualizing, connect race control events to other F1 data:

- **Early pit stop + RED flag nearby** → Team anticipated red flag or pitted under red flag conditions
- **Position change + YELLOW/DOUBLE YELLOW** → Driver may have had incident or went off track
- **Lap time spike + sector-specific flag** → Driver slowed for flags in that sector
- **Bunched field + SAFETY CAR** → SC compressed the field, reset race strategy
- **DRS disabled + overtaking difficulty** → DRS unavailability explains lack of overtakes

#### Provide Timeline

Present events chronologically with lap numbers and impact assessment:

**Example**:
- **Lap 1**: Race start (GREEN LIGHT - PIT EXIT OPEN)
- **Lap 1**: RED FLAG - Major collision Turn 8 involving cars 10 and 31
- **Lap 1-5**: Race suspended (track cleanup)
- **Lap 6**: Race restart
- **Lap 8**: 10-second time penalty issued to car 31 for causing collision

## Example Scenarios

### "Why did the race restart on lap 5?"
**Approach**: Fetch high detail, look for RED flag deployment and clearance sequence
```bash
pitlane fetch race-control --session-id $PITLANE_SESSION_ID --year 2024 --gp Monaco --session R --detail high
```
**Analysis**: Find RED flag message, then "TRACK CLEAR", then "GREEN LIGHT - PIT EXIT OPEN"

### "What caused the safety car in Qatar?"
**Approach**: Fetch SafetyCar category to see deployment reason
```bash
pitlane fetch race-control --session-id $PITLANE_SESSION_ID --year 2024 --gp Qatar --session R --category SafetyCar
```
**Analysis**: Safety car messages often preceded by incident notes (COLLISION, etc.)

### "Were there yellow flags in sector 3 during qualifying?"
**Approach**: Filter by sector and flag category
```bash
pitlane fetch race-control --session-id $PITLANE_SESSION_ID --year 2024 --gp Monaco --session Q --sector 3 --category Flag
```
**Analysis**: Look for YELLOW or DOUBLE YELLOW flags in specified sector

### "Did Leclerc get penalized for anything?"
**Approach**: Filter by driver number (16 for Leclerc)
```bash
pitlane fetch race-control --session-id $PITLANE_SESSION_ID --year 2024 --gp Monaco --session R --driver 16 --detail full
```
**Analysis**: Check for PENALTY messages, time penalties, investigations

### "What happened in the first 5 laps?"
**Approach**: Use lap range with medium detail
```bash
pitlane fetch race-control --session-id $PITLANE_SESSION_ID --year 2024 --gp Monaco --session R --lap-start 1 --lap-end 5 --detail medium
```
**Analysis**: Chronologically list all significant events from race start

## Interpreting Common Patterns

### Safety Car Sequence
1. **"SAFETY CAR DEPLOYED"** → Incident occurred, SC entering track
2. **"SAFETY CAR IN THIS LAP"** → SC will return to pits at end of this lap
3. Next lap: Racing resumes with traditional restart

**Strategy Impact**: Teams often pit under SC (cheap stop, field bunched anyway)

### Red Flag Sequence
1. **"RED"** flag → Session stopped immediately, cars return to pit lane or grid
2. **"TRACK CLEAR"** → Incident resolved, debris removed
3. **"GREEN LIGHT - PIT EXIT OPEN"** → Session resumes, drivers can return to track

**Strategy Impact**: Free tire change during red flag, teams may adjust strategy

### Yellow Flag Progression
- **YELLOW** → Single waved, incident in area, slow down
- **DOUBLE YELLOW** → More serious, be prepared to stop, no overtaking
- **CLEAR** → Incident resolved, racing conditions restored

**Impact**: DOUBLE YELLOW in a sector explains significant lap time increases

### DRS Status
- **"DRS ENABLED"** → Overtaking assistance active on DRS zones
- **"DRS DISABLED"** → No DRS (weather, incidents, or track conditions)

**Impact**: DRS disabled explains why overtaking became difficult despite pace advantage

### Penalty Patterns
- **"INCIDENT ... NOTED"** → FIA aware, may investigate
- **"UNDER INVESTIGATION"** → Formal investigation opened
- **"REVIEWED NO FURTHER INVESTIGATION"** → No penalty
- **"X SECOND TIME PENALTY"** or **"DISQUALIFIED"** → Penalty issued

## Message Field Reference

For detailed field descriptions, message structure, and examples, see [references/message-categories.md](references/message-categories.md).

## Notes

- Not all sessions have race control messages (older races may have limited data)
- Pre-race messages (pit exit status, rain risk) included in full detail level
- BLUE flags filtered in high/medium detail (very common, low information value - just lapping notifications)
- Track limits violations filtered in high/medium detail (administrative, frequent)
- "NO FURTHER INVESTIGATION" messages filtered in high/medium (incidents that didn't warrant penalties)
- Detail levels are recommendations - use full detail if uncertain about what you're looking for
