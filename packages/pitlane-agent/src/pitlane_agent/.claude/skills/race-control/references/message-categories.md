# Race Control Message Field Reference

This document provides detailed field descriptions for race control messages returned by the `pitlane fetch race-control` command.

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

**Field notes**:
- `flag` field populated with specific flag type
- `scope` typically "Track" or "Sector"
- `sector` populated for sector-specific flags

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

**Field notes**:
- `flag` is `null`
- Contains important incident and penalty information
- Includes track limits violations and steward decisions

### Drs
DRS (Drag Reduction System) status changes.

**Messages**:
- `"DRS ENABLED"` - DRS available for overtaking
- `"DRS DISABLED"` - DRS not available (weather, incidents, etc.)

**Field notes**:
- `flag` is `null`
- Usually only 2-3 messages per race (enable at race start, disable if needed)
- Affects overtaking capability

### SafetyCar
Safety car deployment and status.

**Common messages**:
- `"SAFETY CAR DEPLOYED"` - SC entering track
- `"SAFETY CAR IN THIS LAP"` - SC will withdraw at end of lap
- `"VIRTUAL SAFETY CAR"` - VSC deployed
- `"VIRTUAL SAFETY CAR ENDING"` - VSC will end

**Field notes**:
- `flag` is `null`
- Critical for understanding race strategy and position changes
- Often preceded by incident messages in "Other" category

## Flag Types

Detailed descriptions of each flag type when `category` is "Flag".

### RED
- **Meaning**: Session stopped immediately
- **Impact**: All cars must return to pit lane or grid
- **Strategy**: Teams can change tires during red flag (free stop)
- **Follow-up**: Look for "TRACK CLEAR" then "GREEN LIGHT - PIT EXIT OPEN"

### YELLOW
- **Meaning**: Incident in area, single waved flag
- **Impact**: Drivers must slow down, no overtaking in affected area
- **Severity**: Less severe than DOUBLE YELLOW
- **Common**: Typically sector-specific

### DOUBLE YELLOW
- **Meaning**: Serious incident in area
- **Impact**: Drivers must slow significantly, be prepared to stop, no overtaking
- **Severity**: More severe than single YELLOW
- **Common**: Major incidents, track blockages

### GREEN
- **Meaning**: Normal racing conditions or pit exit open
- **Context**: Often "GREEN LIGHT - PIT EXIT OPEN" before session start
- **Impact**: Signals safe conditions or session (re)start

### BLUE
- **Meaning**: Lapped car warning
- **Impact**: Shown to slower cars being lapped by leaders
- **Frequency**: Very common (60+ per race at some circuits)
- **Filter note**: Filtered in high/medium detail levels (low information value)

### CLEAR
- **Meaning**: Previous flag condition resolved
- **Impact**: Normal racing resumed in that area
- **Context**: Usually follows YELLOW or DOUBLE YELLOW
- **Filter note**: Filtered in high/medium detail levels (just clearing state)

### CHEQUERED
- **Meaning**: Session finished
- **Impact**: Racing has ended, cars complete cool-down lap
- **Occurrence**: One per session at the end

## Example Messages by Category

### Flag Category Examples

```json
{
  "lap": 1,
  "time": "2024-05-26T13:03:11",
  "category": "Flag",
  "message": "RED FLAG",
  "flag": "RED",
  "scope": "Track",
  "sector": null,
  "racing_number": null
}
```

```json
{
  "lap": 5,
  "time": "2024-05-26T13:10:23",
  "category": "Flag",
  "message": "DOUBLE YELLOW IN TRACK SECTOR 7",
  "flag": "DOUBLE YELLOW",
  "scope": "Sector",
  "sector": 7,
  "racing_number": null
}
```

```json
{
  "lap": 39,
  "time": "2024-09-22T13:07:07",
  "category": "Flag",
  "message": "WAVED BLUE FLAG FOR CAR 18 (STR) TIMED AT 21:07:06",
  "flag": "BLUE",
  "scope": "Driver",
  "sector": null,
  "racing_number": "18"
}
```

### Other Category Examples

```json
{
  "lap": 1,
  "time": "2024-12-01T15:25:34",
  "category": "Other",
  "message": "PIT ENTRY INCIDENT INVOLVING CAR 11 (PER) NOTED - DRIVING ERRATICALLY",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

```json
{
  "lap": 8,
  "time": "2024-05-26T13:15:42",
  "category": "Other",
  "message": "FIA STEWARDS: 10 SECOND TIME PENALTY FOR CAR 31 (OCO) - CAUSING A COLLISION",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

```json
{
  "lap": 5,
  "time": "2024-09-22T12:11:55",
  "category": "Other",
  "message": "CAR 55 (SAI) LAP DELETED - TRACK LIMITS AT TURN 7 LAP 1 20:04:38",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

### DRS Category Examples

```json
{
  "lap": 2,
  "time": "2024-09-22T12:05:39",
  "category": "Drs",
  "message": "DRS ENABLED",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

```json
{
  "lap": 1,
  "time": "2024-05-26T12:57:06",
  "category": "Drs",
  "message": "DRS DISABLED",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

### SafetyCar Category Examples

```json
{
  "lap": 1,
  "time": "2024-12-01T16:04:33",
  "category": "SafetyCar",
  "message": "SAFETY CAR DEPLOYED",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

```json
{
  "lap": 4,
  "time": "2024-12-01T16:10:56",
  "category": "SafetyCar",
  "message": "SAFETY CAR IN THIS LAP",
  "flag": null,
  "scope": null,
  "sector": null,
  "racing_number": null
}
```

## Common Driver Racing Numbers (2024)

For reference when filtering by driver:

| Number | Driver | Team |
|--------|--------|------|
| 1 | Max Verstappen | Red Bull Racing |
| 4 | Lando Norris | McLaren |
| 11 | Sergio Perez | Red Bull Racing |
| 14 | Fernando Alonso | Aston Martin |
| 16 | Charles Leclerc | Ferrari |
| 18 | Lance Stroll | Aston Martin |
| 22 | Yuki Tsunoda | RB |
| 23 | Alex Albon | Williams |
| 24 | Zhou Guanyu | Kick Sauber |
| 27 | Nico Hulkenberg | Haas |
| 31 | Esteban Ocon | Alpine |
| 43 | Franco Colapinto | Williams |
| 44 | Lewis Hamilton | Mercedes |
| 55 | Carlos Sainz | Ferrari |
| 63 | George Russell | Mercedes |
| 77 | Valtteri Bottas | Kick Sauber |
| 81 | Oscar Piastri | McLaren |

## Data Availability Notes

- **Older races**: May have limited or no race control messages (data availability varies by year/series)
- **Practice sessions**: Typically fewer messages than qualifying or race
- **Sprint events**: Sprint qualifying and sprint race have separate message sets
- **Pre-race messages**: Include pit exit status, weather forecasts (lap is `null`)
- **Message timing**: Messages may appear several laps after the actual event due to steward review time
