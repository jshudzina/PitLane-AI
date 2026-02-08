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

#### Quick Reference: Critical Events

| Event | Impact | Detail Level |
|-------|--------|--------------|
| **RED flag** | Race stopped, large lap time gaps, free tire changes | High |
| **SAFETY CAR / VSC** | Field bunched, common pit stop trigger | High |
| **DOUBLE YELLOW** | Serious incident, significant slowdown required, explains lap time spikes | Medium |
| **YELLOW** | Incident in area, moderate slowdown, no overtaking | Medium |
| **DRS DISABLED** | No overtaking assistance, harder to pass | Medium |
| **Collisions** | Check for penalties, retirements, position changes | High |
| **BLUE flags** | Lapped car warnings (common, low analytical value) | Full |
| **Track limits** | Lap time deletions, warnings, penalties | Full |

#### Reference Documentation

Based on the detail level you fetched, consult the appropriate reference:

- **[fields.md](references/fields.md)** - Message structure, field descriptions, categories (read first for schema)
- **[high-detail-events.md](references/high-detail-events.md)** - RED flags, safety cars, major incidents
- **[medium-detail-events.md](references/medium-detail-events.md)** - YELLOW flags, DRS changes, penalties
- **[full-detail-events.md](references/full-detail-events.md)** - BLUE flags, track limits, administrative messages

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


## Notes

- Not all sessions have race control messages (older races may have limited data)
- Pre-race messages (pit exit status, rain risk) included in full detail level
- BLUE flags filtered in high/medium detail (very common, low information value - just lapping notifications)
- Track limits violations filtered in high/medium detail (administrative, frequent)
- "NO FURTHER INVESTIGATION" messages filtered in high/medium (incidents that didn't warrant penalties)
- Detail levels are recommendations - use full detail if uncertain about what you're looking for
