# Testing Session Analysis

Analyze data from F1 pre-season and in-season testing. Testing data requires different interpretation than race weekend data.

## How Testing Differs from Race Weekends

- **One car per team** — drivers share the car, alternating runs. Teams typically split by half-days or full days, swapping at the lunch break.
- **No competitive context** — lap times are misleading. Teams run different fuel loads (~0.3s/lap per 10kg of fuel), engine modes, tyre compounds, and programmes. Do NOT rank teams by testing lap times.
- **Varied programmes** — teams cycle through different run types throughout the day, not chasing outright pace.
- **Interruptions are normal** — stints may be cut short for setup changes, sensor checks, or mechanical issues. Low lap counts early in testing don't necessarily indicate problems.

## Common Run Programmes

| Programme | Description | What to look for |
|-----------|-------------|------------------|
| **Reliability checks** | Systems validation — gearbox, fuel system, power unit, active aero modes | High lap count, consistent running, few red flags |
| **Qualifying simulation** | Short stints on low fuel with fresh tyres, pushing for peak lap time | Isolated fast laps, often on softs, preceded by an out-lap |
| **Race simulation** | High-fuel long stints (15-30+ laps) measuring degradation | Consistent stint pace, gradual lap time increase, pit stop practice |
| **Aero correlation** | Runs with aero rakes and flow-vis paint to validate CFD/wind tunnel models | Slower laps with visible sensor equipment, not representative of pace |
| **Setup evaluation** | Varying mechanical/aero configurations across fuel loads and compounds | Back-to-back runs with similar lap counts but different pace profiles |
| **Practice starts** | Repeated start procedure practice from the grid | Very short runs, often just a few hundred metres |

## Interpreting Testing Data

**Meaningful comparisons:**
- Teammate pace on the same programme (same fuel, same tyres, same part of the day)
- Long-run degradation trends — how much lap time drops off over a stint
- Stint consistency — tight lap time clusters suggest the car/driver found a rhythm
- Lap count — high counts with consistent times suggest reliability; low counts may indicate issues

**Misleading comparisons:**
- Cross-team lap time rankings (different programmes, fuel loads, engine modes)
- Single fastest laps without programme context
- Day-to-day comparisons (track evolution, weather, different programmes)

## Available Commands

All analysis commands work with `--test N --day N` instead of `--gp` and `--session`:

```bash
# Session overview
pitlane fetch session-info --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 1 --day 2

# Lap time scatter plot
pitlane analyze lap-times --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 1 --day 1 --drivers VER --drivers HAM

# Lap time distributions
pitlane analyze lap-times-distribution --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 1 --day 2

# Speed trace comparison
pitlane analyze speed-trace --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 2 --day 3 --drivers VER --drivers LEC

# Gear shifts on track
pitlane analyze gear-shifts-map --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 1 --day 1 --drivers VER

# Track map
pitlane analyze track-map --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 1 --day 1

# Race control messages (flags, stoppages)
pitlane fetch race-control --workspace-id $PITLANE_WORKSPACE_ID --year 2026 --test 1 --day 2
```

**Important:** Do NOT pass "Pre-Season Testing" as `--gp` — it will match the wrong event. Always use `--test`/`--day`.

**Not available for testing:** qualifying results, race results, championship standings, tyre strategy charts (these are race-weekend-specific).

## Response Formatting

When analyzing testing data, always:

1. **Caveat competitiveness** — remind that testing times don't reflect true performance order
2. **Identify the programme** — note whether laps look like qualifying sims, race sims, or aero runs
3. **Focus on trends** — emphasise consistency, degradation, and reliability over absolute pace
4. **Note the driver** — mention which driver was in the car if relevant (teams share one car)

### Example Response Structure

> ### Summary
> Verstappen completed 68 laps on Day 2 of the first test, splitting time between a morning race simulation on mediums and an afternoon qualifying simulation on softs. His long-run pace showed consistent 1:33.x times with moderate degradation of ~0.15s/lap over a 25-lap stint.
>
> ### Key Observations
> - **Race sim (AM):** 25-lap stint on mediums, 1:33.2-1:33.8 range, ~0.15s/lap degradation
> - **Qualifying sim (PM):** Best lap 1:31.456 on fresh softs — note: fuel load and engine mode unknown, so not directly comparable to other teams
> - **Reliability:** Clean running with no mechanical stoppages
>
> ### Visualization
> ![Lap Times — Verstappen, Test 1 Day 2](/path/to/chart.png)
