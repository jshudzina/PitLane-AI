# High Detail Events Reference

Interpretation guide for **high detail** race control events (`--detail high` - default).

## What's Included

High detail shows only the most critical race-altering events:
- RED flags (session stopped)
- Safety car deployments (full SC and VSC)
- Race start/finish signals
- Major collisions and incidents

**Typical volume**: 10-20 messages per race

## Contents
- [RED Flag Events](#red-flag-events)
- [Safety Car Events](#safety-car-events)
- [Race Control Signals](#race-control-signals)
- [Major Incidents](#major-incidents)
- [Connecting to Data Anomalies](#connecting-to-data-anomalies)

## RED Flag Events

### What It Means
Session stopped immediately due to dangerous conditions. All cars must return to pit lane or grid.

### Message Pattern
1. **"RED FLAG"** → Session stopped
2. **"TRACK CLEAR"** → Incident resolved, debris removed
3. **"GREEN LIGHT - PIT EXIT OPEN"** → Session resumes

### Data Impacts

**Lap times**: Large gaps or missing laps between red flag deployment and restart
- If red flag at lap 3, may not see lap times until lap 8+

**Positions**: Can change significantly during red flag
- Drivers may retire during stoppage
- Grid order may reset depending on session type

**Pit stops**: Free tire change during red flag
- Teams may switch tire compounds without time penalty
- Explains unexpected tire strategy changes after restart

### Example Interpretation

**User asks**: "Why did Hamilton's lap times jump from 1:23 to no data for 5 laps?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --lap-start 1 --lap-end 10
```

If you see "RED FLAG" on lap 3 and "GREEN LIGHT" on lap 8:
- "There was a red flag on lap 3 that stopped the session. The race didn't resume until lap 8, which explains the missing lap time data during laps 3-7."

## Safety Car Events

### What It Means
Race neutralized to safely manage an incident. Field bunches together, no overtaking allowed.

### Message Patterns

**Full Safety Car**:
1. **"SAFETY CAR DEPLOYED"** → SC entering track
2. **"SAFETY CAR IN THIS LAP"** → SC returning to pits at end of lap
3. Next lap: Racing resumes

**Virtual Safety Car**:
1. **"VIRTUAL SAFETY CAR"** → VSC deployed (less restrictive than full SC)
2. **"VIRTUAL SAFETY CAR ENDING"** → VSC will end shortly

### Data Impacts

**Lap times**: All drivers have similar slow lap times during SC/VSC
- Full SC: All cars bunched, ~30-40s slower than racing pace
- VSC: Drivers maintain delta time, ~20-30% slower

**Positions**: Field compresses
- Gap from P1 to P10 may shrink from 30+ seconds to 1-2 seconds
- Previous race gaps are neutralized

**Pit stops**: Strategic opportunity
- Cheap pit stop (lose minimal positions since field is bunched)
- Common trigger for strategy changes
- Teams may "pit under safety car" to minimize time loss

### Example Interpretation

**User asks**: "Why did Verstappen pit on lap 15 when his tires seemed fine?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --lap-start 14 --lap-end 16 --category SafetyCar
```

If you see "SAFETY CAR DEPLOYED" on lap 15:
- "A safety car was deployed on lap 15. Teams often pit during safety car periods because it's a 'cheap' stop - the field is bunched anyway, so you lose minimal track position."

## Race Control Signals

### Session Start
**"GREEN LIGHT - PIT EXIT OPEN"**
- Pit lane opens, session begins
- Drivers can leave pit lane and start timed laps

### Session End
**"CHEQUERED FLAG"**
- Session completed
- Race winner determined, all drivers complete cool-down lap

### Data Impacts
- Lap 1 timing often includes formation lap and race start procedure
- Final lap may show slower times as drivers celebrate or cool down

## Major Incidents

### Collision Messages
**Format**: `"TURN X INCIDENT INVOLVING CAR(S) Y NOTED - CAUSING A COLLISION"`

### What to Look For
1. **Car numbers involved**: Which drivers were in the incident
2. **Location**: Track sector or corner where it occurred
3. **Severity**: Did it trigger a safety car or red flag?
4. **Follow-up**: Check for penalty messages or investigations

### Data Impacts

**Retirements**:
- Driver may not complete the race (DNF)
- Explains sudden disappearance from timing data

**Penalties**:
- Time penalties (5s, 10s) added post-race
- May change final race classification

**Strategy changes**:
- Incident may trigger safety measures (SC, red flag)
- Creates pit stop opportunities for uninvolved drivers

### Example Interpretation

**User asks**: "Why did Leclerc retire from the race?"

**Analysis**:
```bash
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --driver 16 --detail high
```

If you see collision message involving car 16:
- "Leclerc was involved in a collision at [location] on lap [X]. This appears to have caused damage that forced him to retire from the race."

## Connecting to Data Anomalies

### Early Pit Stop + RED Flag Nearby
**Pattern**: Driver pits unusually early, then red flag appears 1-2 laps later

**Interpretation**: Team may have anticipated red flag conditions (saw incident on TV/radio) or pitted during red flag period (free tire change)

### Position Changes + Safety Car
**Pattern**: Multiple position changes during safety car laps

**Interpretation**: Drivers pitted under safety car at different times. Those who pitted earlier lose fewer positions since field is bunched.

### Lap Time Spike + RED/SC Flag
**Pattern**: Driver's lap time suddenly 30+ seconds slower

**Interpretation**: Red flag or safety car deployment mid-lap, driver had to slow down significantly or return to pits.

### Bunched Field + Safety Car
**Pattern**: Race gaps compress from 30+ seconds to 1-2 seconds

**Interpretation**: Safety car neutralized the race. Previous race leader's advantage was eliminated, creating restart battle.

### Missing Laps + RED Flag
**Pattern**: No lap time data for driver across multiple laps

**Interpretation**: Session was red flagged. During red flag period, cars are in pits or on grid - no lap times are recorded.
