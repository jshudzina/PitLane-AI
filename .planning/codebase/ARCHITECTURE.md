<!-- refreshed: 2026-05-02 -->
# Architecture

**Analysis Date:** 2026-05-02

A three-package monorepo delivering F1 data analysis through both a CLI and a web UI, with an AI agent layer powered by the Claude Agent SDK backed by ELO rating models and FastF1 telemetry data.

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interfaces                              │
├─────────────────────────────┬───────────────────────────────────────┤
│  CLI  `pitlane`             │  Web UI  `pitlane-web`                │
│  `pitlane_agent/cli.py`     │  `pitlane_web/app.py`                 │
└──────────┬──────────────────┴────────────┬────────────────────────┘
           │                               │
           ▼                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     pitlane-agent (core package)                      │
│  F1Agent  `agent.py`   Claude Agent SDK  `claude_agent_sdk`          │
│  Tool Permissions  `tool_permissions.py`  Tracing  `tracing.py`       │
├─────────────────────────────────────────────────────────────────────┤
│  Commands (pure functions, no SDK dependency)                        │
│   fetch/        analyze/         workspace/      temporal/           │
│  `commands/fetch`  `commands/analyze`  `commands/workspace`          │
├─────────────────────────────────────────────────────────────────────┤
│  Utilities                                                           │
│   FastF1 helpers  ELO DB  Stats DB  Plotting  Race stats            │
│   `utils/`                                                           │
└──────────┬───────────────────────────────────────────────────────────┘
           │ depends on
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       pitlane-elo                                     │
│  ratings/  endure_elo  speed_elo  constructor_elo  (RatingModel ABC) │
│  snapshots.py   stories/signals.py   separation/   prediction/       │
│  data.py  (DuckDB-backed Parquet store)                              │
└──────────────────────────────────────────────────────────────────────┘
           │ data stored in
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│              ~/.pitlane/  (user home data store)                      │
│   workspaces/<uuid>/   cache/fastf1/   cache/temporal/               │
│   (+ bundled Parquet at pitlane_agent/data/)                         │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Key File |
|-----------|---------------|----------|
| `F1Agent` | Claude Agent SDK wrapper; session, sandbox, tool permission wiring | `packages/pitlane-agent/src/pitlane_agent/agent.py` |
| CLI (`pitlane`) | Click command tree; thin dispatch layer over commands | `packages/pitlane-agent/src/pitlane_agent/cli.py` |
| `fetch` commands | Pull F1 data (session info, standings, schedule) via FastF1/Ergast | `packages/pitlane-agent/src/pitlane_agent/commands/fetch/` |
| `analyze` commands | Generate Matplotlib/Plotly charts (lap times, telemetry, strategy) | `packages/pitlane-agent/src/pitlane_agent/commands/analyze/` |
| `workspace` commands | Manage `~/.pitlane/workspaces/<uuid>` directories and conversation state | `packages/pitlane-agent/src/pitlane_agent/commands/workspace/operations.py` |
| `temporal` module | Determine current F1 season phase, active weekend, TTL-cached | `packages/pitlane-agent/src/pitlane_agent/temporal/` |
| `tool_permissions` | `can_use_tool` and `PreToolUse` hooks; sandbox + domain allowlists | `packages/pitlane-agent/src/pitlane_agent/tool_permissions.py` |
| `tracing` | OpenTelemetry PostToolUse hook; console ANSI trace output | `packages/pitlane-agent/src/pitlane_agent/tracing.py` |
| `pitlane-web` | FastAPI app with SSE streaming; LRU `AgentCache` | `packages/pitlane-web/src/pitlane_web/app.py` |
| `AgentCache` | OrderedDict-backed LRU pool of `F1Agent` instances (one per web session) | `packages/pitlane-web/src/pitlane_web/agent_manager.py` |
| `RatingModel` ABC | Interface for all ELO variants (`process_race`, `predict_win_probabilities`) | `packages/pitlane-elo/src/pitlane_elo/ratings/base.py` |
| `EndureElo` | Powell sequential knock-out model; Numba JIT `_inclusion_exclusion` | `packages/pitlane-elo/src/pitlane_elo/ratings/endure_elo.py` |
| `SpeedElo` | Simple pairwise speed-based ELO | `packages/pitlane-elo/src/pitlane_elo/ratings/speed_elo.py` |
| `RatingsStore` | DuckDB-backed Parquet persistence for ELO snapshots and model state | `packages/pitlane-elo/src/pitlane_elo/ratings_store.py` |
| `stories/signals` | Translates ELO trajectories into narrative signals (hot streaks, teammate shifts) | `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` |
| `separation/` | Driver vs constructor rating decomposition (van Kesteren model) | `packages/pitlane-elo/src/pitlane_elo/separation/` |

## Pattern Overview

**Overall:** Layered command architecture with an AI agent facade

**Key Characteristics:**
- Commands are pure Python functions (no SDK dependency) callable from both CLI and Claude agent tools
- The Claude Agent SDK is the "brain" — the agent calls `pitlane` CLI sub-commands via `Bash` tool, with `PreToolUse` and `can_use_tool` hooks enforcing sandbox rules
- Workspaces are filesystem directories (`~/.pitlane/workspaces/<uuid>/`) used as the shared state boundary between CLI, agent, and web layers
- Data is separated: FastF1 telemetry is fetched on demand and cached; ELO state is pre-computed and stored as Parquet; session stats are bundled into the package as Parquet artifacts

## Layers

**CLI Layer:**
- Purpose: User-facing command dispatch
- Location: `packages/pitlane-agent/src/pitlane_agent/cli.py`, `cli_fetch.py`, `cli_analyze.py`, `cli_stories.py`
- Contains: Click group/command definitions
- Depends on: commands layer, temporal module
- Used by: end users, Claude agent (via Bash tool)

**Agent Layer:**
- Purpose: Claude Agent SDK integration; wraps LLM interaction, tool permissions, tracing
- Location: `packages/pitlane-agent/src/pitlane_agent/agent.py`
- Contains: `F1Agent` class; `_build_system_prompt`, `chat`, `chat_full`
- Depends on: workspace commands, temporal module, tool_permissions, tracing
- Used by: `pitlane-web` AgentCache; direct SDK consumers

**Commands Layer:**
- Purpose: Business logic for F1 data fetching, chart generation, workspace management
- Location: `packages/pitlane-agent/src/pitlane_agent/commands/`
- Contains: `fetch/`, `analyze/`, `workspace/` subpackages
- Depends on: utils layer, pitlane-elo
- Used by: CLI layer, agent layer (indirectly via CLI), web app

**Utils Layer:**
- Purpose: Shared helpers (FastF1 loading, DuckDB queries, plotting, constants)
- Location: `packages/pitlane-agent/src/pitlane_agent/utils/`
- Contains: `fastf1_helpers.py`, `elo_db.py`, `stats_db.py`, `plotting.py`, `race_stats.py`, `constants.py`, `circuits.py`
- Depends on: FastF1, DuckDB, Matplotlib, pitlane-elo (for data types)
- Used by: commands layer

**ELO / Analytics Layer:**
- Purpose: Rating model computation, story detection, driver/car separation
- Location: `packages/pitlane-elo/src/pitlane_elo/`
- Contains: `ratings/`, `stories/`, `separation/`, `prediction/`, `snapshots.py`, `data.py`
- Depends on: DuckDB, Numba, NumPy, SciPy
- Used by: pitlane-agent (data queries), pitlane-elo CLI (`pitlane-elo`)

## Data Flow

### Agent Chat Request (Web UI Path)

1. Browser POST → FastAPI `app.py` route (`packages/pitlane-web/src/pitlane_web/app.py`)
2. `AgentCache.get_or_create(workspace_id)` → returns or instantiates `F1Agent` (`packages/pitlane-web/src/pitlane_web/agent_manager.py`)
3. `F1Agent.chat(message)` builds system prompt with `temporal_context`, configures SDK options (`packages/pitlane-agent/src/pitlane_agent/agent.py`)
4. `ClaudeSDKClient` sends to Anthropic API; Claude executes tools (Bash, Read, Write, WebFetch, WebSearch, Skill)
5. `PreToolUse` hook validates each tool call against sandbox rules (`packages/pitlane-agent/src/pitlane_agent/tool_permissions.py`)
6. Bash tool executes `pitlane fetch ...` or `pitlane analyze ...` sub-commands, writing output to `~/.pitlane/workspaces/<uuid>/`
7. Assistant text blocks yield through `chat()` async iterator → SSE stream to browser

### CLI Analysis Path

1. User runs `pitlane fetch session-info --workspace-id X --year Y --gp Z --session R`
2. `cli_fetch.py` validates workspace, resolves path, calls `get_session_info(year, gp, session)` in `commands/fetch/session_info.py`
3. FastF1 loads session (with `~/.pitlane/cache/fastf1/` cache)
4. Result JSON written to `~/.pitlane/workspaces/<uuid>/data/`
5. User runs `pitlane analyze lap-times --workspace-id X ...`
6. `cli_analyze.py` calls `generate_lap_times_chart(...)` in `commands/analyze/lap_times.py`
7. Matplotlib chart PNG written to `~/.pitlane/workspaces/<uuid>/charts/`

### ELO Snapshot Build Path

1. `pitlane-elo snapshot --start-year 1970 --end-year 2026`
2. `snapshots.py:build_snapshots()` iterates races from `data.py` (DuckDB over Parquet race_entries)
3. `EndureElo.process_race()` updates ratings (Numba JIT compiled `_inclusion_exclusion`)
4. `RatingsStore` writes `elo_snapshots/<year>/<round>.parquet` and `elo_model_state.parquet`
5. `pitlane stories detect` reads snapshots via `stories/signals.py:detect_stories()`
6. Detected `StorySignal` objects written to `~/.pitlane/workspaces/<uuid>/data/stories_<year>_<round>.json`

### Temporal Context Path

1. `F1Agent._build_system_prompt()` calls `get_temporal_context()` (`packages/pitlane-agent/src/pitlane_agent/temporal/context.py`)
2. `TemporalContextManager.get_context()` checks `TemporalCache` (file-based JSON at `~/.pitlane/cache/temporal/`)
3. On cache miss: `TemporalAnalyzer.analyze()` calls `fastf1.get_event_schedule()`
4. Computed `TemporalContext` serialized to cache with TTL (shorter during live weekends)
5. `format_for_system_prompt()` renders human-readable context string appended to Claude's system prompt

**State Management:**
- Workspaces: filesystem at `~/.pitlane/workspaces/<uuid>/` (JSON metadata, JSON data files, PNG charts)
- FastF1 telemetry cache: `~/.pitlane/cache/fastf1/` (managed by FastF1 library)
- Temporal context cache: `~/.pitlane/cache/temporal/` (JSON, TTL-based)
- ELO model state: `packages/pitlane-agent/src/pitlane_agent/data/elo_model_state.parquet` (bundled; also written to package data dir by scripts)
- ELO snapshots: `packages/pitlane-agent/src/pitlane_agent/data/elo_snapshots/<year>/<round>.parquet`
- Session stats: `packages/pitlane-agent/src/pitlane_agent/data/session_stats.parquet` (bundled)

## Key Abstractions

**`RatingModel` ABC:**
- Purpose: Common interface enabling model-vs-model comparison in `prediction/forecast.py`
- Location: `packages/pitlane-elo/src/pitlane_elo/ratings/base.py`
- Pattern: Abstract base class; `process_race(entries)` and `predict_win_probabilities(driver_ids)` must be implemented
- Implementations: `EndureElo` (preferred), `SpeedElo`, `ConstructorElo`

**`TemporalContext` dataclass:**
- Purpose: Snapshot of current F1 season/weekend/session state injected into agent system prompt
- Location: `packages/pitlane-agent/src/pitlane_agent/temporal/context.py`
- Pattern: Immutable dataclass with `to_dict()` and a global `_manager` singleton (`get_temporal_context()`)

**`F1Agent`:**
- Purpose: Single entry point for all Claude-powered F1 analysis; handles workspace lifecycle, skill loading, sandbox, tracing
- Location: `packages/pitlane-agent/src/pitlane_agent/agent.py`
- Pattern: Stateful async class; `chat()` is an async generator yielding text chunks

**`AgentCache`:**
- Purpose: LRU pool mapping web session IDs to `F1Agent` instances, preventing one agent per request
- Location: `packages/pitlane-web/src/pitlane_web/agent_manager.py`
- Pattern: `OrderedDict` with `asyncio.Lock`; evicts oldest on capacity breach

**`StorySignal` dataclass:**
- Purpose: Detected narrative angle (hot streak, slump, surprise, teammate shift) with a human-readable `narrative` field for prompt injection
- Location: `packages/pitlane-elo/src/pitlane_elo/stories/signals.py`

**Workspace:**
- Purpose: Isolated filesystem sandbox per session/analysis; all CLI commands write inside it; agent reads/writes via tool permissions
- Location: `~/.pitlane/workspaces/<uuid>/` at runtime; operations in `packages/pitlane-agent/src/pitlane_agent/commands/workspace/operations.py`

## Entry Points

**`pitlane` CLI:**
- Location: `packages/pitlane-agent/src/pitlane_agent/cli.py`, registered as `pitlane = "pitlane_agent.cli:pitlane"` in `pyproject.toml`
- Triggers: `pitlane workspace ...`, `pitlane fetch ...`, `pitlane analyze ...`, `pitlane stories ...`, `pitlane temporal-context`
- Responsibilities: Click group assembly, library logging suppression

**`pitlane-elo` CLI:**
- Location: `packages/pitlane-elo/src/pitlane_elo/cli.py`, registered as `pitlane-elo = "pitlane_elo.cli:main"`
- Triggers: `pitlane-elo run`, `pitlane-elo snapshot`, `pitlane-elo calibrate`, `pitlane-elo stories`, `pitlane-elo compare`
- Responsibilities: ELO model training, evaluation, snapshot building, calibration

**`pitlane-web` server:**
- Location: `packages/pitlane-web/src/pitlane_web/cli.py`, registered as `pitlane-web = "pitlane_web.cli:main"`
- Triggers: uvicorn start with `app` from `pitlane_web.app`
- Responsibilities: HTTP API, session cookie management, rate limiting, SSE chat streaming

**`F1Agent` (SDK):**
- Location: `packages/pitlane-agent/src/pitlane_agent/agent.py` — `from pitlane_agent import F1Agent`
- Triggers: Programmatic async call to `agent.chat(message)` or `agent.chat_full(message)`

## Architectural Constraints

- **Async model:** `F1Agent.chat()` is an `AsyncIterator`; the web app uses FastAPI's async SSE; all `ClaudeSDKClient` calls are async. CLI commands are synchronous.
- **Sandbox boundary:** When `sandbox_enabled=True`, `ClaudeAgentOptions.sandbox=SandboxSettings(enabled=True)` enforces OS-level isolation. `tool_permissions.py` provides a software-layer complement (or sole enforcement when sandbox is off).
- **Allowed tools:** The SDK restricts Claude to `["Skill", "Bash", "Read", "Write", "WebFetch", "WebSearch"]`. Bash commands must be `pitlane` prefixed (when sandbox is off).
- **WebFetch domain allowlist:** Enforced in `tool_permissions.py:ALLOWED_WEBFETCH_DOMAINS` — wikipedia.org, ergast.com, formula1.com, fia.com.
- **Workspace isolation:** All file reads/writes by Claude are validated to be within `~/.pitlane/workspaces/<uuid>/` via `_is_within_workspace()`.
- **Numba JIT cache:** Numba redirects cache to `/tmp` (env var) to avoid path issues; `endure_elo.py` uses `@nb.njit(cache=True, parallel=True)`.
- **Global state:** `temporal/context.py` holds a module-level `_manager` singleton. `tool_permissions.py` uses module-level domain set constants.
- **Bundled data:** ELO snapshots, model state, and session stats Parquet files are committed to the repo under `packages/pitlane-agent/src/pitlane_agent/data/` and shipped in the wheel (hatchling `artifacts` config).

## Anti-Patterns

### Mixing CLI and SDK concerns in `cli_stories.py`

**What happens:** `cli_stories.py` (`packages/pitlane-agent/src/pitlane_agent/cli_stories.py`) imports from `pitlane_elo.stories.signals` directly at call time rather than through the `commands/` layer, bypassing the commands abstraction used by all other CLI modules.
**Why it's wrong:** Breaks the symmetry where `commands/` holds all pure logic callable from both CLI and the agent; makes this path untestable without the full ELO package.
**Do this instead:** Create `packages/pitlane-agent/src/pitlane_agent/commands/stories.py` with pure functions, and have `cli_stories.py` call those.

### `TemporalContextManager` lazy circular import

**What happens:** `TemporalContextManager.__init__` defers `from pitlane_agent.temporal.analyzer import TemporalAnalyzer` and `from pitlane_agent.temporal.cache import TemporalCache` to the method body instead of the module top.
**Why it's wrong:** Project feedback (`feedback_imports_at_top.md`) mandates imports at the top of files; lazy imports obscure dependencies and break static analysis.
**Do this instead:** Move both imports to the top of `packages/pitlane-agent/src/pitlane_agent/temporal/context.py`.

## Error Handling

**Strategy:** Exceptions propagate to the CLI layer where they are caught and serialized as `{"error": "..."}` JSON written to stderr; the process exits with code 1.

**Patterns:**
- All CLI command handlers wrap their core call in `try/except Exception as e` and output `json.dumps({"error": str(e)})` to stderr
- `F1Agent._build_system_prompt()` swallows exceptions silently (returns `None`) — temporal context failure is non-fatal
- `TemporalAnalyzer.analyze()` retries with `current_season - 1` if the current year's schedule isn't available
- FastF1 session loading failures propagate as exceptions to command handlers

## Cross-Cutting Concerns

**Logging:** Python standard `logging`; library loggers (`fastf1`, `pitlane_agent`, `pitlane_web`) set to WARNING/INFO via env `PITLANE_LOG_LEVEL`. Trace output uses a custom `_TraceFormatter` with ANSI colors written to stderr.
**Validation:** Input validation (year ranges, workspace existence, session type, file path safety) happens at the CLI layer before command dispatch. Web layer has `security.py` for filename and session ID validation.
**Authentication:** No user authentication. Rate limiting via `slowapi` on chat and chart endpoints in the web app. Tool-level permission enforcement via `tool_permissions.py`.
**Rate limiting:** `slowapi` in `pitlane_web/app.py`; in-memory storage; configurable via `RATE_LIMIT_CHAT`, `RATE_LIMIT_CHART`, `RATE_LIMIT_SESSION_CREATE` constants in `config.py`.

---

*Architecture analysis: 2026-05-02*
