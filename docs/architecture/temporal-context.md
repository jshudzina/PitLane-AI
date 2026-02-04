# Temporal Context

The temporal context system provides real-time awareness of the F1 calendar, enabling the agent to understand "where we are" in the racing season at multiple granularities.

## Overview

When analyzing F1 data, context matters. A question about "the last race" means different things in March (pre-season) vs. July (mid-season) vs. December (off-season). The temporal context system makes the agent **season-aware**, automatically injecting relevant calendar information into the system prompt.

## Architecture

```
┌─────────────────────────────────────────┐
│   TemporalContextManager                │
├─────────────────────────────────────────┤
│  - Intelligent Caching (TTL-based)      │
│  - FastF1 Schedule Integration          │
│  - Session-Level Granularity            │
└────────────┬────────────────────────────┘
             │
             ├──> TemporalCache
             │    (Disk-based, adaptive TTL)
             │
             ├──> TemporalAnalyzer
             │    (Calendar analysis logic)
             │
             └──> TemporalFormatter
                  (System prompt formatting)
```

## Context Levels

The system provides temporal awareness at three levels:

### 1. Season Level

Tracks the overall championship phase:

- **Pre-Season** (Jan-Feb): Before first race
- **In-Season** (Mar-Nov): During championship
- **Post-Season** (Nov-Dec): After final race
- **Off-Season** (Dec-Feb): Winter break

### 2. Race Weekend Level

Tracks the current, last, and next race weekends:

- **Current Weekend**: Active race weekend (if within event window)
- **Last Completed**: Most recently finished race
- **Next Race**: Upcoming race with countdown

### 3. Session Level

Tracks individual sessions with real-time status:

- **Live Sessions**: Currently happening (with live indicator)
- **Recent Sessions**: Completed within last 24 hours
- **Upcoming Sessions**: Future sessions with countdown

## Data Structures

### TemporalContext

The root context object:

```python
@dataclass
class TemporalContext:
    current_time_utc: datetime
    current_season: int
    season_phase: F1Season  # pre_season, in_season, post_season, off_season

    # Race weekend context
    current_weekend: RaceWeekendContext | None
    last_completed_race: RaceWeekendContext | None
    next_race: RaceWeekendContext | None

    # Quick stats
    races_completed: int
    races_remaining: int
    days_until_next_race: int | None

    # Cache metadata
    cache_timestamp: datetime
    ttl_seconds: int
```

### RaceWeekendContext

Details about a specific race weekend:

```python
@dataclass
class RaceWeekendContext:
    round_number: int
    event_name: str           # "Monaco Grand Prix"
    country: str
    location: str
    event_date: datetime
    phase: RaceWeekendPhase   # practice, qualifying, race, etc.

    # Session tracking
    current_session: SessionContext | None
    next_session: SessionContext | None
    all_sessions: list[SessionContext]
    is_sprint_weekend: bool
```

### SessionContext

Details about an individual session:

```python
@dataclass
class SessionContext:
    name: str                 # "Race", "Qualifying", "FP1"
    session_type: str         # "R", "Q", "FP1", etc.
    date_utc: datetime
    date_local: datetime

    # Real-time status
    is_live: bool             # Currently happening
    is_recent: bool           # Within last 24h
    minutes_until: int | None # Countdown to start (None if past)
    minutes_since: int | None # Time since end (None if future)
```

## Caching Strategy

The temporal context uses **intelligent adaptive caching** to minimize API calls while maintaining accuracy:

### Cache TTL (Time-To-Live)

The cache TTL adapts based on how far we are from the next event:

| Time Until Next Session | TTL |
|-------------------------|-----|
| < 1 hour | 5 minutes |
| < 24 hours | 30 minutes |
| < 7 days | 6 hours |
| ≥ 7 days | 24 hours |

**Rationale**: During race weekends, context changes rapidly (sessions start/end). During off-weeks, context is stable.

### Cache Location

Context is cached at:

```
~/.pitlane/cache/temporal/
└── temporal_context.json
```

Cache includes:
- Full temporal context JSON
- Cache timestamp
- TTL seconds (for validation)

## System Prompt Injection

The temporal context is formatted and injected into the agent's system prompt:

```python
temporal_ctx = get_temporal_context()
temporal_prompt = format_for_system_prompt(temporal_ctx, verbosity="normal")

system_prompt = {
    "type": "preset",
    "preset": "claude_code",
    "append": temporal_prompt,
}
```

### Verbosity Levels

The formatter supports three verbosity levels:

| Level | Description | Use Case |
|-------|-------------|----------|
| `minimal` | Season phase and next race only | Token-constrained environments |
| `normal` | Full context with current/last/next races | Standard agent usage (default) |
| `detailed` | Includes all session details | Debugging and development |

### Example Formatted Prompt

```markdown
# F1 Temporal Context (2024-05-23 14:30 UTC)

**Season Status**: 2024 Season - In Progress
- Races completed: 7/24
- Races remaining: 17

**Current Race Weekend**: Monaco Grand Prix (Round 8)
- Location: Monaco, Monaco
- Event Date: 2024-05-26
- Phase: Practice
- Current Session: FP1 (Live - Started 15 minutes ago)
- Next Session: FP2 (in 2 hours 15 minutes)

**Last Completed Race**: Emilia Romagna Grand Prix (Round 7)
- Location: Imola, Italy
- Completed: 3 days ago

**Next Race**: Monaco Grand Prix (in 3 days)
```

This context enables the agent to:
- Understand temporal references ("last race", "this weekend")
- Provide relevant suggestions ("FP1 just started - want to analyze lap times?")
- Avoid confusion about historical vs. current data

## Usage

### Get Current Context

```python
from pitlane_agent.temporal import get_temporal_context

context = get_temporal_context()

print(f"Season: {context.current_season}")
print(f"Phase: {context.season_phase}")
print(f"Next race: {context.next_race.event_name}")
```

### Force Cache Refresh

```python
from pitlane_agent.temporal import TemporalContextManager

manager = TemporalContextManager()
context = manager.get_context(force_refresh=True)
```

### Format for Prompt

```python
from pitlane_agent.temporal import format_for_system_prompt

# Normal verbosity (default)
prompt = format_for_system_prompt(context)

# Minimal (token-efficient)
prompt = format_for_system_prompt(context, verbosity="minimal")

# Detailed (debugging)
prompt = format_for_system_prompt(context, verbosity="detailed")
```

## Benefits

### 1. Contextual Understanding

The agent knows temporal references without asking:

- "Analyze the last race" → Automatically knows which race
- "What's happening this weekend?" → Knows current event and sessions
- "When's the next race?" → Instant countdown

### 2. Reduced Token Usage

Without temporal context, the agent would need to:
1. Fetch the schedule
2. Determine current race
3. Parse session times
4. Calculate countdowns

With temporal context, all this is pre-computed and cached.

### 3. Real-Time Awareness

During race weekends, the agent knows:
- If qualifying is live right now
- When the next session starts
- How long ago a session ended

This enables intelligent suggestions and relevant analysis prompts.

## Related Documentation

- [Agent System](agent-system.md) - How temporal context integrates with F1Agent
- [API Reference: Temporal](../api-reference/pitlane-agent/temporal.md) - Full API documentation
