# Temporal Context System

## Overview

The temporal context system provides the F1 agent with real-time awareness of the F1 calendar at multiple granularities: season, race weekend, and session levels. This ensures the agent always knows the current date context and can accurately respond to queries like "latest race results" or "next race."

## Problem Solved

**Before:** When users asked for "latest race results," the agent would return 2024 data instead of 2026 data because:
- No system prompt provided current date context
- No default year logic in CLI commands
- Agent relied on hardcoded examples in documentation

**After:** The agent now automatically:
- Knows the current season and phase (pre/in/post/off-season)
- Identifies current/next/last race weekends
- Detects live or recent sessions
- Uses appropriate default years for queries

## Architecture

```
temporal/
├── __init__.py          # Public API exports
├── context.py           # Data structures and TemporalContextManager
├── analyzer.py          # Season/race/session detection logic
├── cache.py             # Intelligent caching with TTL
└── formatter.py         # System prompt formatting
```

## Features

### 1. Multi-Granularity Awareness

**Season Level**
- Current year (2026)
- Phase: Pre-season, In-season, Post-season, Off-season
- Races completed/remaining

**Race Weekend Level**
- Current/next/last race events
- Location, round number, event format
- Sprint vs conventional weekend detection

**Session Level**
- Live/recent/upcoming sessions
- Time until/since sessions
- Session types (FP1, FP2, FP3, Q, S, SQ, R)

### 2. Intelligent Caching

Cache TTL adapts to temporal state:
- **Off-season**: 7 days (rare queries, stable data)
- **Pre-season**: 3 days (testing schedule updates)
- **Between weekends**: 12 hours (stable schedule)
- **Race weekend**: 15 min - 1 hour (sessions approaching)
- **Live session**: 5 minutes (real-time data)

### 3. System Prompt Injection

The agent receives context like this:

```markdown
## F1 Temporal Context

**Current Season:** 2026
**Phase:** Pre Season

**Next Race:** Australian Grand Prix
- Round 1 in Melbourne, Australia
- Race Weekend: March 08, 2026
- 32 days until race weekend
- Format: Conventional weekend
```

During a live race weekend:

```markdown
## F1 Temporal Context

**ACTIVE RACE WEEKEND: Monaco Grand Prix**
- Round 5 in Monte Carlo, Monaco

**Current Session:** Qualifying ⚡ LIVE
- Started 45 minutes ago

**Next Session:** Race
- Sunday 15:00 local (13:00 UTC)
- 22 hours until start
```

### 4. Environment Variables

The system also sets environment variables for quick access:
- `PITLANE_CURRENT_SEASON` - Current F1 season year
- `PITLANE_SEASON_PHASE` - pre_season/in_season/post_season/off_season
- `PITLANE_CURRENT_RACE` - Current race event name (if any)
- `PITLANE_CURRENT_ROUND` - Current round number (if any)

## Usage

### Agent Integration (Automatic)

The agent automatically injects temporal context by default:

```python
from pitlane_agent.agent import F1Agent

# Temporal context enabled by default
agent = F1Agent()

# Disable if needed
agent = F1Agent(inject_temporal_context=False)
```

### CLI Inspection

Check current temporal context:

```bash
# Human-readable text
pitlane temporal-context

# System prompt format
pitlane temporal-context --format prompt

# JSON format
pitlane temporal-context --format json

# Force refresh from FastF1
pitlane temporal-context --refresh

# Detailed verbosity
pitlane temporal-context --format prompt --verbosity detailed
```

### Programmatic Access

```python
from pitlane_agent.temporal import get_temporal_context

# Get current context
context = get_temporal_context()

print(f"Season: {context.current_season}")
print(f"Phase: {context.season_phase.value}")

if context.current_weekend:
    print(f"Race: {context.current_weekend.event_name}")

if context.next_race:
    print(f"Next race: {context.next_race.event_name}")
    print(f"Days until: {context.days_until_next_race}")
```

## Examples

### Pre-Season (Current)

```
Season: 2026
Phase: Pre Season
Next Race: Australian Grand Prix (Round 1) - March 8, 2026
Days Until: 32
Cache TTL: 3 days
```

### During In-Season (Between Races)

```
Season: 2026
Phase: In Season (Round 5 of 24 completed)
Last Race: Spanish Grand Prix - Completed May 10, 2026 (2 weeks ago)
Next Race: Monaco Grand Prix (Round 6) - May 24, 2026 (7 days)
Cache TTL: 12 hours
```

### During Live Session

```
Season: 2026
Phase: In Season (Round 6 of 24)
ACTIVE RACE WEEKEND: Monaco Grand Prix
Current Session: Qualifying ⚡ LIVE (started 45 minutes ago)
Next Session: Race - Tomorrow 15:00 local (22 hours)
Cache TTL: 5 minutes
```

## Data Source

- **Primary**: FastF1 (`fastf1.get_event_schedule()`)
- **Cache**: `~/.pitlane/cache/temporal/context_cache.json`
- **No external dependencies**: Uses existing FastF1 integration

## Testing

Run the test suite:

```bash
cd packages/pitlane-agent
PYTHONPATH=src pytest tests/temporal/ -v
```

All 16 tests validate:
- Data structure serialization
- Cache TTL and expiration
- Formatting for different verbosity levels
- Live session detection

## Benefits

✅ **Automatic date awareness** - Agent knows it's 2026, not 2024
✅ **Context-aware responses** - "Latest race" uses correct year/race
✅ **Live session detection** - Knows when races are happening now
✅ **Intelligent caching** - Fast responses, fresh data when needed
✅ **No breaking changes** - Backward compatible, opt-in via flag
✅ **No new dependencies** - Uses existing FastF1 library

## Future Enhancements

Potential additions (out of scope for initial implementation):
- Weather context for upcoming sessions
- Championship standings context
- Track-specific information (circuit characteristics)
- Historical context (last year's winner)
- Multi-series support (F2, F3, F1 Academy)
- WebSocket updates for live session notifications
