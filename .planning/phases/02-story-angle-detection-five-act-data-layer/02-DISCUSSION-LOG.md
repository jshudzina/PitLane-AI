# Phase 2: Story Angle Detection + Five-Act Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 2-Story Angle Detection + Five-Act Data Layer
**Areas discussed:** DNF web search mechanism, AngleCandidate schema, Addition of non-ELO signals

---

## DNF Web Search Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Claude API + web search tool | Targeted API call with web_search tool, returns structured JSON {dnf, reason}. Uses SDK already pinned. | ✓ |
| Brave Search API direct HTTP | Direct aiohttp call to Brave Search API, parse keywords. Requires new API key env var. | |
| Race control messages from pitlane-agent | Parse FastF1 race control for retirements — but explicitly excluded by ANGL-03. | |

**User's choice:** Claude API + web search tool

### DNF Response Interpretation
| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON response | Prompt Claude to return `{"dnf": true/false, "reason": "..."}`. Deterministic and testable. | ✓ |
| Free-text keyword scan | Parse response for 'DNF'/'retired'. Simpler but fragile. | |

**User's choice:** Structured JSON response

### DNF Result Caching
| Option | Description | Selected |
|--------|-------------|----------|
| In-memory cache per AngleService instance | Dict keyed by (year, round, driver_id). Lost on restart — acceptable. | ✓ |
| Persisted in SQLite | Store DNF verdicts in articles.db. Durable across sessions. | |

**User's choice:** In-memory cache

### Signal Types That Trigger DNF Check
| Option | Description | Selected |
|--------|-------------|----------|
| slump | ΔR̂ < -0.5 over 3 races — classic crisis angle | ✓ |
| surprise_under | Driver underperformed expectations; DNF could explain it | ✓ |
| teammate_shift | Structural multi-race pattern — DNF less relevant | |
| surprise_over | Positive signal — no DNF concern | |

**User's choice:** slump + surprise_under only

---

## AngleCandidate Schema

| Option | Description | Selected |
|--------|-------------|----------|
| New AngleCandidate dataclass | Pydantic BaseModel with angle_id, name, signal_type, confidence, data_rationale, dnf_suppressed | ✓ |
| Annotated StorySignal | Add confidence/dnf_checked fields to StorySignal — mixes ELO and UI concerns | |
| Plain dict | list[dict] — no type safety | |

**User's choice:** New AngleCandidate dataclass

### Confidence Field
| Option | Description | Selected |
|--------|-------------|----------|
| Normalized signal value 0–1 | ELO: min(value/threshold, 1.0); wildness: direct; standings/chaos: normalized | ✓ |
| Bucketed: low/medium/high | Ratio bucketed into 3 tiers — more readable | |
| You decide | Leave to Claude's discretion | |

**User's choice:** Normalized signal value 0–1
**Notes:** User initially questioned whether "confidence" was meaningful ("sounds like bullshit"). Resolved by using actual normalized signal magnitude rather than a fabricated score — and making it concrete per signal type.

### Data Rationale Field
| Option | Description | Selected |
|--------|-------------|----------|
| StorySignal.narrative as-is | Already human-readable from detect_stories() | ✓ |
| Abbreviated signal stats | Raw numbers — jargon-heavy for journalists | |
| You decide | Claude builds from available fields | |

**User's choice:** StorySignal.narrative as-is

---

## Addition of Non-ELO Signals

**Context:** User requested adding signals beyond ELO (championship standings, wildness score, other pitlane-agent analysis) before finalizing the AngleCandidate schema. ANGL-01 currently says "ELO signals only" — user agreed to update REQUIREMENTS.md.

| Signal | Description | Selected |
|--------|-------------|----------|
| Wildness score | Race wildness_score from season_summary.py (0–1 composite of overtakes, volatility, SC, red flags) | ✓ |
| Championship standings shift | Leader change or significant points delta between rounds. Calls get_driver_standings(). | ✓ |
| Lap 1 chaos | Position changes in lap 1 vs. normal. Calls position_changes command. | ✓ |

**User's choice:** All three non-ELO signals included

### Signal Pool Organization
| Option | Description | Selected |
|--------|-------------|----------|
| All signals compete together, top 6 by magnitude | ELO + non-ELO in single pool, sorted by confidence, top 6 taken | ✓ |
| Reserve slots: ELO first, non-ELO fills gaps | ELO always gets priority slots | |

**User's choice:** All signals compete together

### Requirements Update
| Option | Description | Selected |
|--------|-------------|----------|
| Update ANGL-01 in REQUIREMENTS.md | Reflects expanded signal set accurately | ✓ |
| Keep ANGL-01 as-is (implementation detail) | Requirements stay ELO-focused | |

**User's choice:** Update ANGL-01

---

## Claude's Discretion

- Exact function call signatures for non-ELO commands (position_changes, race_control)
- Narrative string templates for non-ELO `AngleCandidate.data_rationale`
- Model choice for DNF check API call (Haiku recommended — binary classification task)

## Deferred Ideas

- Five-act SQLite persistence — user chose in-memory cache; revisit in v2 if restart latency is an issue
- Additional non-ELO signals (fastest lap, constructor battle) — not discussed; possible future iteration
- Novelty filter tracking via served-angles history vs. raw signal recomputation — user accepted raw recomputation
