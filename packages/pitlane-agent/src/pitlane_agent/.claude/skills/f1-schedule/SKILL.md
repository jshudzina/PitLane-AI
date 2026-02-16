---
name: f1-schedule
description: Answer questions about the F1 event schedule for a given year. The schedule includes dates, location (city and country), round number, and session information.
allowed-tools: Bash(pitlane *), Read, Write
---

# F1 Schedule Information

You have access to F1 event schedule data via the workspace-based PitLane CLI. Answer questions about race calendars, event dates, locations, and session schedules with accurate historical and current data.

## When to Use This Skill

Use this skill when users ask about:
- **Race calendars**: "What races are in the 2024 season?"
- **Event dates**: "When is the Monaco Grand Prix?"
- **Locations**: "Where is the Canadian GP held?"
- **Session schedules**: "What time is qualifying at Silverstone?"
- **Event formats**: "Which races have sprint weekends?"

**Complementary with f1-analyst**: This skill provides "when and where" information. Use the f1-analyst skill for race results, lap times, and performance analysis.

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

## Step 2: Identify the Query Parameters

Extract from the user's question:
- **Year**: e.g., 2024, 2023 (required)
- **Round Number**: e.g., 1, 6, 15 (optional filter)
- **Country**: e.g., "Monaco", "Italy", "United Kingdom" (optional filter)
- **Include Testing**: Whether to include pre-season testing (default: yes)

If the user doesn't specify a year, default to the most recent completed or current season.

## Step 3: Get Schedule Using PitLane CLI

Use the PitLane CLI to fetch schedule data. All commands require a `--workspace-id` parameter which is provided by the F1Agent managing your workspace.

### Get Full Season Calendar
```bash
pitlane fetch event-schedule --workspace-id $PITLANE_WORKSPACE_ID --year 2024
```
Returns JSON with all events for the season and saves to workspace.

### Get Specific Round
```bash
pitlane fetch event-schedule --workspace-id $PITLANE_WORKSPACE_ID --year 2024 --round 6
```
Returns data for only round 6.

### Filter by Country
```bash
pitlane fetch event-schedule --workspace-id $PITLANE_WORKSPACE_ID --year 2024 --country Italy
```
Returns all Italian races (e.g., Imola, Monza if both are scheduled).

### Exclude Testing Sessions
```bash
pitlane fetch event-schedule --workspace-id $PITLANE_WORKSPACE_ID --year 2024 --no-testing
```
Returns only championship rounds without pre-season testing.

After fetching, data is saved to the workspace at `{workspace}/data/schedule.json` which you can read using the Read tool.

## Step 4: Format Your Response

Structure your response based on the question:

### For Full Calendar Queries
Present a clean table or list format:

```markdown
## 2024 F1 Calendar

| Round | Date | Grand Prix | Location |
|-------|------|------------|----------|
| 1 | Mar 2 | Bahrain | Sakhir, Bahrain |
| 2 | Mar 9 | Saudi Arabia | Jeddah, Saudi Arabia |
...
```

### For Specific Event Queries
Provide detailed session information:

```markdown
## Monaco Grand Prix 2024

**Location**: Monte Carlo, Monaco
**Event Date**: May 26, 2024
**Format**: Conventional

**Sessions:**
- Practice 1: Friday, May 24 at 13:30 local (11:30 UTC)
- Practice 2: Friday, May 24 at 17:00 local (15:00 UTC)
- Practice 3: Saturday, May 25 at 12:30 local (10:30 UTC)
- Qualifying: Saturday, May 25 at 16:00 local (14:00 UTC)
- Race: Sunday, May 26 at 15:00 local (13:00 UTC)
```

### For Sprint Weekend Queries
Highlight the sprint format:

```markdown
The 2024 season includes **6 sprint weekends**:
- Round 4: China (Shanghai)
- Round 6: Miami (Miami)
- Round 11: Austria (Spielberg)
...

Sprint weekends feature a modified schedule with Sprint Qualifying on Friday and the Sprint Race on Saturday.
```

## Data Field Reference

The script returns events with these fields:
- **round**: Championship round number (0 for testing)
- **country**: Host country name
- **location**: City or region
- **official_name**: Full sponsor-inclusive name
- **event_name**: Short name used for API access
- **event_date**: Reference date (typically final session)
- **event_format**: "conventional", "sprint", "sprint_shootout", or "testing"
- **f1_api_support**: Whether F1 timing data is available
- **sessions**: Array of session objects with:
  - **name**: e.g., "Practice 1", "Qualifying", "Race", "Sprint"
  - **date_local**: Local timezone timestamp
  - **date_utc**: UTC timestamp

## Example Questions and Approaches

**"What's the 2024 F1 calendar?"**
1. Run event_schedule for 2024 without filters
2. Present a complete table of all rounds with dates and locations
3. Note the total number of races

**"When is the Monaco Grand Prix in 2024?"**
1. Run event_schedule for 2024 filtering by country "Monaco"
2. Extract the event date and session times
3. Present the full weekend schedule with local times

**"Which races are in Italy this year?"**
1. Run event_schedule for current year filtering by country "Italy"
2. List all Italian rounds (might be multiple: Imola, Monza)
3. Include dates and any format differences

**"What time is qualifying at Silverstone?"**
1. Determine the year (default to current)
2. Run event_schedule filtering by country "United Kingdom"
3. Extract qualifying session times in both local and UTC
4. Present clearly formatted times

**"How many sprint races are there in 2024?"**
1. Run event_schedule for 2024
2. Filter results to events where event_format contains "sprint"
3. Count and list all sprint weekends with locations

## Notes

- **Historical Data**: Schedule data is available from 1950 onwards via Ergast backend for older seasons
- **Time Accuracy**: Exact session times are only available from 2018 onwards
- **Time Zones**: Always provide both local and UTC times when available
- **Event Names**: Use official event names when referencing specific races
- **Testing Sessions**: Pre-season testing has RoundNumber of 0 and EventFormat of "testing". To access testing session data (lap times, telemetry), use `--test` and `--day` options in fetch/analyze commands instead of `--gp` and `--session`. Do NOT pass "Pre-Season Testing" as a GP name — FastF1 will match it to the wrong event.
