# Race Control Message Field Reference

Reference for message structure, fields, and data schema returned by `pitlane fetch race-control`.

## Contents
- [Message Structure](#message-structure)
- [Field Descriptions](#field-descriptions)
- [Category Values](#category-values)
- [Flag Types](#flag-types)
- [Driver Racing Numbers](#driver-racing-numbers)
- [Data Availability](#data-availability)

## Message Structure

Each race control message has the following JSON structure:

```json
{
  "lap": 1,
  "time": "2024-05-26T13:03:11",
  "category": "Flag",
  "message": "GREEN LIGHT - PIT EXIT OPEN",
  "flag": "GREEN",
  "scope": "Track",
  "sector": 7,
  "racing_number": "1"
}
```

## Field Descriptions

### lap
- **Type**: Integer or `null`
- **Description**: Lap number when the message occurred (1-based)
- **Can be null**: Yes (for pre-race messages like pit exit status, rain risk)
- **Example**: `1`, `15`, `null`

### time
- **Type**: String (ISO 8601 timestamp)
- **Description**: Timestamp when the message was issued
- **Format**: `YYYY-MM-DDTHH:MM:SS`
- **Example**: `"2024-05-26T13:03:11"`

### category
- **Type**: String
- **Description**: Category of the race control message
- **Possible values**: `"Flag"`, `"Other"`, `"Drs"`, `"SafetyCar"`
- **See**: Category Values section below

### message
- **Type**: String
- **Description**: The actual message text from race control
- **Format**: Uppercase text, may contain car numbers and driver codes
- **Example**: `"RED FLAG"`, `"TURN 8 INCIDENT INVOLVING CARS 10 (GAS) AND 31 (OCO) NOTED - CAUSING A COLLISION"`

### flag
- **Type**: String or `null`
- **Description**: Type of flag if category is "Flag"
- **Can be null**: Yes (for non-flag messages)
- **Possible values**: `"RED"`, `"YELLOW"`, `"DOUBLE YELLOW"`, `"GREEN"`, `"BLUE"`, `"CLEAR"`, `"CHEQUERED"`
- **See**: Flag Types section below

### scope
- **Type**: String or `null`
- **Description**: Scope of the message
- **Possible values**: `"Track"`, `"Sector"`, `"Driver"`, or `null`
- **Track**: Message applies to entire track
- **Sector**: Message applies to specific sector (see sector field)
- **Driver**: Message applies to specific driver (see racing_number field)

### sector
- **Type**: Integer or `null`
- **Description**: Track sector number if scope is "Sector"
- **Can be null**: Yes (when not sector-specific)
- **Numbering**: Track-specific, typically 1-20 depending on circuit
- **Example**: `3`, `7`, `12`

### racing_number
- **Type**: String or `null`
- **Description**: Driver's racing number if message is driver-specific
- **Can be null**: Yes (when not driver-specific)
- **Format**: String representation of number
- **Example**: `"1"` (Verstappen), `"44"` (Hamilton), `"16"` (Leclerc)

## Category Values

### Flag
Messages related to flag conditions on track.

**Common messages**:
- `"RED FLAG"` - Session stopped
- `"YELLOW IN TRACK SECTOR X"` - Single yellow flag
- `"DOUBLE YELLOW IN TRACK SECTOR X"` - Double yellow flag
- `"GREEN LIGHT - PIT EXIT OPEN"` - Pit exit open (often race start)
- `"BLUE FLAG FOR CAR X"` - Lapped car warning
- `"CLEAR IN TRACK SECTOR X"` - Flag condition cleared
- `"CHEQUERED FLAG"` - Session end

### Other
General race control messages not fitting other categories.

**Common messages**:
- `"TURN X INCIDENT INVOLVING CAR(S) Y NOTED - CAUSING A COLLISION"`
- `"FIA STEWARDS: X SECOND TIME PENALTY FOR CAR Y"`
- `"CAR X (ABC) TIME ... DELETED - TRACK LIMITS AT TURN Y"`
- `"PIT EXIT CLOSED"` / `"PIT EXIT OPEN"`
- `"RISK OF RAIN FOR F1 RACE IS X%"`
- `"FIA STEWARDS: ... UNDER INVESTIGATION"`
- `"FIA STEWARDS: ... REVIEWED NO FURTHER INVESTIGATION"`

### Drs
DRS (Drag Reduction System) status changes.

**Messages**:
- `"DRS ENABLED"` - DRS available for overtaking
- `"DRS DISABLED"` - DRS not available (weather, incidents, etc.)

### SafetyCar
Safety car deployment and status.

**Common messages**:
- `"SAFETY CAR DEPLOYED"` - SC entering track
- `"SAFETY CAR IN THIS LAP"` - SC will withdraw at end of lap
- `"VIRTUAL SAFETY CAR"` - VSC deployed
- `"VIRTUAL SAFETY CAR ENDING"` - VSC will end

## Flag Types

Quick reference for flag values when `category` is "Flag":

| Flag Type | Meaning | Detail Level |
|-----------|---------|--------------|
| **RED** | Session stopped immediately | High |
| **YELLOW** | Incident in area, single waved | Medium |
| **DOUBLE YELLOW** | Serious incident, be prepared to stop | Medium |
| **GREEN** | Normal racing conditions / pit exit open | High |
| **BLUE** | Lapped car warning | Full |
| **CLEAR** | Flag condition resolved | Full |
| **CHEQUERED** | Session finished | High |

See detail-level reference files for interpretation guidance and strategy impacts.

## Driver Racing Numbers

Driver racing numbers for a session are included in the `session-info` data:

```bash
pitlane fetch session-info --session-id $PITLANE_SESSION_ID --year YEAR --gp "Grand Prix Name" --session SESSION_TYPE
```

The session info includes a `drivers` array with each driver's `number` field containing their racing number for that session.

**Note**: Racing numbers change between seasons (e.g., previous year's champion gets #1). The session-info data reflects the numbers used in that specific session.

## Data Availability

- **Older races**: May have limited or no race control messages (data availability varies by year/series)
- **Practice sessions**: Typically fewer messages than qualifying or race
- **Sprint events**: Sprint qualifying and sprint race have separate message sets
- **Pre-race messages**: Include pit exit status, weather forecasts (lap is `null`)
- **Message timing**: Messages may appear several laps after the actual event due to steward review time
