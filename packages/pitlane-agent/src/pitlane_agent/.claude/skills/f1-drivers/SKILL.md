---
name: f1-drivers
description: Get information about F1 drivers including driver codes, names, nationalities, and Wikipedia links. Use when user asks about driver details, driver codes, or who drove in a specific season.
allowed-tools: Bash(pitlane *), Read
---

# F1 Driver Information

You have access to F1 driver information via the workspace-based PitLane CLI which uses FastF1's Ergast API. Answer questions about F1 drivers past and present with accurate reference data.

## When to Use This Skill

Use this skill when users ask about:
- **Driver codes**: "What's Verstappen's driver code?" or "What is VER's full name?"
- **Driver details**: "Tell me about Lewis Hamilton" or "When was Max Verstappen born?"
- **Season rosters**: "Who drove in 2024?" or "List all drivers from the 2023 season"
- **Driver search**: "Find Dutch drivers" or "Show me all drivers"
- **Wikipedia links**: "Show me Max Verstappen's Wikipedia page"

**Complementary with f1-analyst**: This skill provides driver reference data. Use f1-analyst for performance analysis (lap times, race results).

## Step 1: Create or Get Workspace Workspace ID

**IMPORTANT**: Before running any fetch commands, you need a workspace ID.

### If this is a new conversation:
Create a new workspace and capture the workspace ID from the output:

```bash
pitlane workspace create
```

This returns JSON like:
```json
{
  "workspace_id": "abc-123-def",
  "workspace_path": "/Users/user/.pitlane/workspaces/abc-123-def",
  "created_at": "2024-01-27T10:30:00Z"
}
```

**Extract the `workspace_id` from this output - you'll use it in all subsequent commands.**

### If continuing an existing conversation:
Use the same workspace ID you created earlier in this conversation.

## Step 2: Identify Query Parameters

Extract from the user's question:
- **Driver Code**: 3-letter abbreviation (e.g., "VER", "HAM", "LEC")
- **Season**: Year (e.g., 2024, 2023) to get all drivers from that season
- **Limit**: Number of results (default: 100)
- **Offset**: Pagination offset (default: 0)

## Step 3: Get Driver Data Using PitLane CLI

All commands require a `--workspace-id` parameter which is provided by the F1Agent managing your workspace.

### Search by Driver Code
```bash
pitlane fetch driver-info --workspace-id $PITLANE_WORKSPACE_ID --driver-code VER
```
Returns information for Max Verstappen and saves to workspace.

### Get All Drivers from a Season
```bash
pitlane fetch driver-info --workspace-id $PITLANE_WORKSPACE_ID --season 2024
```
Returns all drivers who participated in the 2024 season (~20 drivers).

### Get All F1 Drivers in History
```bash
pitlane fetch driver-info --workspace-id $PITLANE_WORKSPACE_ID --limit 50
```
Returns up to 50 drivers from F1 history (1950-present).

### Pagination for Large Results
```bash
pitlane fetch driver-info --workspace-id $PITLANE_WORKSPACE_ID --limit 100 --offset 100
```
Gets drivers 101-200 from the complete dataset.

After fetching, data is saved to the workspace at `{workspace}/data/drivers.json` which you can read using the Read tool.

## Step 4: Format Your Response

### For Single Driver Queries
```markdown
## Max Verstappen (VER)

**Full Name**: Max Verstappen
**Nationality**: Dutch
**Born**: September 30, 1997
**Driver Number**: 1
**Driver Code**: VER

[Wikipedia Page](https://en.wikipedia.org/wiki/Max_Verstappen)
```

### For Season Roster Queries
Present as a table:
```markdown
## 2024 F1 Drivers

| Code | Name | Number | Nationality |
|------|------|--------|-------------|
| VER | Max Verstappen | 1 | Dutch |
| HAM | Lewis Hamilton | 44 | British |
| LEC | Charles Leclerc | 16 | Monegasque |
...
```

### For Driver Code Lookups
When users ask "what's the driver code for X?":
- Provide the 3-letter code prominently (e.g., "VER")
- Clarify it's used in f1-analyst commands
- Show example: `pitlane lap-times --drivers VER`

## Data Field Reference

The script returns drivers with these fields:
- **driver_id**: Unique identifier (e.g., "verstappen")
- **driver_code**: 3-letter code (e.g., "VER") - used by f1-analyst
- **driver_number**: Car number (e.g., 1) - may be null for historical drivers
- **given_name**: First name
- **family_name**: Last name
- **full_name**: Combined full name
- **date_of_birth**: Birth date (YYYY-MM-DD format)
- **nationality**: Driver nationality
- **url**: Wikipedia page URL

## Example Questions and Approaches

**"What's Verstappen's driver code?"**
1. Run: `driver_info --driver-code VER`
2. Return "VER" prominently
3. Note this code is used in f1-analyst commands

**"Who drove in 2024?"**
1. Run: `driver_info --season 2024`
2. Present as a table with codes, names, numbers, nationalities
3. Include total count

**"Tell me about Lewis Hamilton"**
1. Run: `driver_info --driver-code HAM`
2. Present full details with Wikipedia link
3. Include biographical information

**"List all Dutch drivers"**
1. Run: `driver_info --limit 1000` (get all drivers)
2. Filter results by nationality = "Dutch"
3. Present as list or table

## Notes

- Driver codes are 3-letter abbreviations used by f1-analyst
- Data sourced from Ergast API via FastF1
- Historical data available back to 1950
- Not all historical drivers have driver numbers
- Wikipedia links are official URLs from Ergast database
