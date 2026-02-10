# Full Detail Events Reference

Interpretation guide for **full detail** race control events (`--detail full`).

## What's Included

Full detail includes all messages from high and medium detail, plus:
- BLUE flags (lapped car warnings)
- CLEAR flags (flag condition cleared)
- Track limits violations
- Administrative messages

**Typical volume**: 100+ messages per race

**Also see**:
- [high-detail-events.md](high-detail-events.md) - RED flags, safety cars, major incidents
- [medium-detail-events.md](medium-detail-events.md) - YELLOW flags, DRS, penalties

## Contents
- [Blue Flag Events](#blue-flag-events)
- [Clear Flag Events](#clear-flag-events)
- [Track Limits Violations](#track-limits-violations)
- [Administrative Messages](#administrative-messages)
- [When to Use Full Detail](#when-to-use-full-detail)

## Blue Flag Events

### What It Means
Warning shown to a slower car being lapped by faster cars. The lapped driver must allow the faster car(s) to pass safely.

### Message Pattern
**"WAVED BLUE FLAG FOR CAR X (ABC) TIMED AT HH:MM:SS"**

### Rules
- Shown to lapped cars (e.g., P15 being lapped by P1)
- Driver must allow faster car to pass within 3 blue flag signals
- Failure to comply: penalty (typically 5s time penalty or more)
- Multiple blue flags in sequence indicate urgency

### Frequency
**Very common**: 60-120+ blue flag messages per race at some circuits
- More flags at tracks with high speed differential
- More flags in races with large performance gaps between teams

### Data Impacts

**Minimal for analysis**:
- Blue flags don't directly affect lap times or strategy
- Lapped driver may lose 0.1-0.3s per lap allowing faster cars through
- Rarely explains significant anomalies

**When relevant**:
- If lapped driver doesn't yield: may receive penalty
- Can explain minor position swaps (letting leaders through)

### Why Filtered in High/Medium Detail
Blue flags provide little analytical value - they simply indicate normal lapping behavior. Including them creates noise without meaningful insight.

### Example Interpretation

**User asks**: "Why are there so many blue flag messages?"

**Analysis**: Blue flags are routine in F1 when leaders lap backmarkers. At circuits with large gaps between front and back of field, you'll see 60+ blue flags per race. This is normal racing behavior, not an anomaly.

## Clear Flag Events

### What It Means
Previous yellow flag condition has been resolved, normal racing resumes in that sector.

### Message Pattern
**"CLEAR IN TRACK SECTOR X"**

### Impact
- Drivers can resume normal racing speed in cleared sector
- No more slow-down or no-overtaking restrictions
- Sector times return to normal pace on next lap

### Frequency
**Moderate**: Every yellow flag eventually gets cleared (10-20 clear messages per race)

### Why Filtered in High/Medium Detail
CLEAR flags just indicate state transitions - the yellow flag ending. The yellow flag itself is the important event; the clearing is implied and adds little information.

### Example Interpretation

**User asks**: "When did sector 2 return to green flag conditions?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --sector 2 --detail full
```

Look for "CLEAR IN TRACK SECTOR 2" message - that's when normal racing resumed in sector 2.

## Track Limits Violations

### What It Means
Driver exceeded track limits (all four wheels beyond white line) and gained an advantage.

### Message Patterns

**Lap Time Deleted**:
`"CAR X (ABC) LAP DELETED - TRACK LIMITS AT TURN Y LAP Z HH:MM:SS"`
- Lap time invalidated
- Doesn't count for qualifying grid position or fastest lap

**Warning**:
`"CAR X (ABC) TRACK LIMITS AT TURN Y - WARNING"`
- First/second offense: warning only
- Repeated violations: may lead to penalty

**Penalty**:
`"5 SECOND TIME PENALTY FOR CAR X (ABC) - TRACK LIMITS"`
- Multiple violations (typically 3rd or 4th offense)
- Time added to race total

### Frequency
**Very common**: 20-50+ track limits messages per race/qualifying
- Varies by circuit (some tracks have more contentious corners)
- More common in wet conditions or when pushing hard

### Data Impacts

**Qualifying**:
- Deleted lap time doesn't count for grid position
- Driver may drop several positions if best lap deleted
- Explains unexpected low grid position

**Race**:
- Repeated violations lead to time penalty
- May explain post-race position change

### Why Filtered in High/Medium Detail
Track limits violations are administrative and very frequent. They rarely explain major race anomalies unless resulting in a significant penalty.

### Example Interpretation

**User asks**: "Why did Alonso start P8 when he was P4 in qualifying?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --driver 14 --detail full
```

If you see lap deleted message for Alonso's fastest lap:
- "Alonso's fastest qualifying lap was deleted for track limits at turn X. His next best lap was only good enough for P8 on the grid."

## Administrative Messages

### Pre-Race Information
- `"RISK OF RAIN FOR F1 RACE IS X%"` - Weather forecast
- `"PIT EXIT CLOSED"` / `"PIT EXIT OPEN"` - Pit lane status
- Various procedural notifications

### Steward Reviews
- `"... REVIEWED NO FURTHER INVESTIGATION"` - Incident reviewed, no action
- Investigation updates and administrative notes

### Frequency
**Variable**: 5-15 administrative messages per session

### Why Filtered in High/Medium Detail
These messages provide context but rarely explain data anomalies. They're useful for complete session understanding but not critical for most analyses.

## When to Use Full Detail

### Recommended Use Cases

**Complete incident investigation**:
When you need every piece of information about a specific lap or incident, use full detail to ensure nothing is missed.

```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --lap-start 15 --lap-end 15 --detail full
```

**Track limits analysis**:
Understanding qualifying grid position discrepancies or race penalties due to track limits.

```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --driver 14 --detail full
```

**Qualifying lap validation**:
Checking if lap times were deleted or if yellow flags affected qualifying runs.

```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --session Q --detail full
```

**Blue flag compliance**:
Investigating if a driver failed to yield to leaders (rare but can explain penalties).

```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --flag-type BLUE --detail full
```

### When NOT to Use Full Detail

**Initial exploration**: Start with high detail to get major events
**Race timeline**: Medium detail is usually sufficient for understanding race flow
**Strategy analysis**: High/medium detail captures pit stops triggers (SC, red flags)

### Best Practice
Start with high or medium detail. Only move to full detail if you need specific information about:
- Track limits violations
- Blue flag compliance issues
- Complete chronological event list
- Administrative or procedural details

## Message Volume Guidelines

| Detail Level | Typical Count | Best For |
|-------------|---------------|----------|
| **High** | 10-20 | Quick overview, major events |
| **Medium** | 30-50 | Most analyses, yellow flags, penalties |
| **Full** | 100-200+ | Complete investigation, track limits |

**Tip**: Use `--lap-start` and `--lap-end` filters with full detail to focus on specific laps, reducing message volume while maintaining completeness.
