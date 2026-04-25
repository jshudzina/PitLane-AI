---
name: story-lines
description: Detect ELO-based narrative story angles for F1 races and seasons. Use when the user asks about driver momentum, surprise performances, teammate battles, hot streaks, slumps, or wants story lines written to the workspace.
allowed-tools: Bash(pitlane *), Read, Write
---

# F1 Story Lines

You detect and synthesize ELO-based narrative story angles for F1 races. Story lines are grounded in the calibrated endure-ELO model and represent statistically significant deviations from expectation.

## Prerequisite: ELO Snapshots

Story detection requires pre-computed ELO snapshots. If you get an empty `signals` array, run a snapshot catchup first:

```bash
pitlane-elo snapshot-catchup
```

## Detecting Story Lines

### For a specific race

```bash
pitlane stories detect --year 2026 --round 3
```

Returns JSON saved to `{workspace}/data/stories_2026_3.json`.

**Options:**
- `--session-type R` (race, default) or `S` (sprint)
- `--trend-lookback 3` — how many prior races for momentum delta (default 3, use 6 for longer view)

### For a full season

```bash
pitlane stories season --year 2025
```

Returns JSON saved to `{workspace}/data/stories_2025_season.json`.

## Reading the Results

After running the command, read the output file:

```
Read {workspace}/data/stories_2026_3.json
```

## Signal Types

Each signal has a `signal_type`. Interpret them as follows:

### `hot_streak`
- **What it means:** A driver's ELO rating has risen significantly over the last N races (default: 3).
- **`value`:** ΔR̂ (positive). Higher = stronger momentum.
- **Threshold:** 0.5 ELO
- **Story angle:** Career breakthrough, form revival, new team adaptation succeeding, regulation beneficiary.
- **Example narrative:** "Norris is on the hottest streak in the field — +0.72 ELO over 3 races heading into Monaco."

### `slump`
- **What it means:** A driver's ELO has dropped significantly over recent races.
- **`value`:** ΔR̂ (negative). More negative = deeper slump.
- **Threshold:** −0.5 ELO
- **Story angle:** Car reliability crisis, driver under pressure, team strategy failures, form collapse.
- **Example narrative:** "Alonso has shed 0.61 ELO over 3 races — the deepest slump on the grid right now."

### `surprise_over`
- **What it means:** A driver finished far ahead of their predicted position (SurpriseScore < −2.0).
- **`value`:** SurpriseScore (negative = better than expected).
- **`context.expected_position`:** Model's predicted finish rank.
- **`context.actual_position`:** Where they actually finished.
- **Story angle:** Giant-killing, tactical brilliance, wet-weather specialist, Safety Car timing.
- **Note:** Cross-reference with race control data to check if a Safety Car or unexpected incident explains the result before calling it a genuine story.

### `surprise_under`
- **What it means:** A driver finished far behind their predicted position (SurpriseScore > 2.0).
- **Story angle:** Shock retirement, car failure after strong qualifying, strategic disaster.
- **Note:** Always check `dnf_category` in context — a mechanical DNF is less of a "story" than a crash or strategy error.

### `teammate_shift`
- **What it means:** Within-team ELO gap has been consistently one-sided (or just flipped).
- **`context.current_delta`:** Current gap (positive = driver_id leads teammate).
- **`context.historical_deltas`:** Gap over the last N races (newest first).
- **Story angle:** Intra-team power shift, new driver establishing hierarchy, team's primary driver under threat.
- **Flip signal:** When `historical_deltas` are all one sign but `current_delta` is the opposite, it's a power reversal story.

## Writing Story Lines to Workspace

Once you have the signals, synthesize them into narrative prose and write to the workspace:

```
Write {workspace}/data/story_lines_2026_3.md
```

**Good story line format:**

```markdown
# Story Lines: 2026 Round 3

## 1. [Driver] — Hot Streak (Hot_streak, ΔR̂ +0.72)
[2-3 sentences contextualizing the ELO trend with race results. What happened
over the 3 races? What does this mean for the next race? Is this a car story
or a driver story?]

## 2. [Driver] vs [Teammate] — Internal War Tipping Point (teammate_shift)
[Explain the gap direction and what it means for team dynamics.]
```

## Contextual Checks

Before finalizing a story line, consider:

1. **Is this race on a wet or street circuit?** Check `context` fields — wet races and street circuits can inflate/deflate performance deviations.
2. **Did a Safety Car or red flag affect the result?** Use the `race-control` skill to cross-check surprise signals against race incidents.
3. **Is the driver new or recently changing teams?** A high k-factor (uncertainty) means the surprise threshold is wider — check `pre_race_k` in context.
4. **DNF category:** For `surprise_under` signals, check if `dnf_category` is `mechanical` (less informative about driver ability) vs `crash` (more informative).

## Signal Priority

When writing story lines, prioritize signals in this order:
1. **`teammate_shift` with flipped gap** — rarest and most dramatic
2. **Strong `surprise_over`** (SurpriseScore < −3.0) — unexpected winner or giant-killing
3. **`hot_streak`** with ΔR̂ > 1.0 — multi-race dominance
4. **`surprise_under`** where DNF category is `none` (finished but badly underperformed)
5. **`slump`** with ΔR̂ < −1.0 — crisis narrative

## Notes

- Story signals are sorted by |value| descending in the JSON — the first signal is the strongest.
- The `narrative` field in each signal is a starting point, not a final story line. Enrich it with race results context.
- Signals reflect pre-race ELO (what the model expected going in), making them true out-of-sample assessments.
- The underlying model is calibrated endure-ELO (k_max=0.8665, φ_race=0.999) — see `docs/F1_ELO_Story_Detection_System_Design.md` for full methodology.
