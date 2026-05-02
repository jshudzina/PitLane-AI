# Architecture Patterns

**Domain:** F1 co-authoring interface integrated into existing Python monorepo
**Researched:** 2026-05-02
**Confidence:** HIGH — based on direct code inspection of all relevant packages

---

## Recommended Architecture

pitlane-studio is a fourth uv workspace package (`packages/pitlane-studio/`) that imports pitlane-agent and pitlane-elo as library dependencies. It owns a FastAPI web server (mirroring pitlane-web's pattern), a SQLite-backed article store, and an orchestrated plan-then-write pipeline. It does not spawn subprocesses; it calls Python functions directly.

```text
Browser
  │  HTTP (HTMX fragments + SSE for prose streaming)
  ▼
┌──────────────────────────────────────────────────────────────────┐
│  pitlane-studio  (new package)                                   │
│                                                                  │
│  FastAPI app  (studio_app.py)                                    │
│    /race/{year}/{round}/angles     → AngleService                │
│    /article/{id}/outline           → PipelineOrchestrator        │
│    /article/{id}/beat/{n}/prose    → PipelineOrchestrator (SSE)  │
│    /article/{id}/export            → SubstackExporter            │
│                                                                  │
│  AngleService          (angle_service.py)                        │
│    calls detect_stories() + fetch commands → story angle cards   │
│                                                                  │
│  FiveActMapper         (five_act_mapper.py)                      │
│    static config: act → pitlane commands → fetch functions       │
│                                                                  │
│  PipelineOrchestrator  (pipeline.py)                             │
│    Step 1: generate_outline()  → claude API (non-streaming)      │
│    Step 2: approve_outline()   → stores approved outline         │
│    Step 3: generate_beat(n)    → claude API (streaming, per-beat)│
│                                                                  │
│  ArticleStore          (article_store.py)                        │
│    SQLite at ~/.pitlane/studio/articles.db                       │
│    Tables: articles, beats, angles                               │
│                                                                  │
│  SubstackExporter      (substack_export.py)                      │
│    unofficial API + markdown fallback                            │
└──────┬─────────────────────┬────────────────────────────────────┘
       │ import               │ import
       ▼                      ▼
┌─────────────────┐  ┌──────────────────────────────────────────┐
│  pitlane-elo    │  │  pitlane-agent                           │
│                 │  │                                          │
│  detect_stories │  │  commands/fetch/*   (pure functions)     │
│  StorySignal    │  │  commands/analyze/* (pure functions)     │
│  get_race_      │  │  commands/workspace/operations.py        │
│  snapshot       │  │  temporal/context.py                     │
└─────────────────┘  └──────────────────────────────────────────┘
       │                      │
       └──────────────────────┘
                 │ data from
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  ~/.pitlane/  (shared user home)                                 │
│    cache/fastf1/          (FastF1 telemetry cache)               │
│    cache/temporal/        (temporal context cache)               │
│    data/elo_snapshots/    (bundled Parquet, read by pitlane-elo) │
│    studio/articles.db     (new — owned by pitlane-studio)        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Package | Responsibility | What It Does Not Own |
|-----------|---------|---------------|----------------------|
| `AngleService` | pitlane-studio | Combine ELO signals + telemetry into 4-6 named story angle cards per race | ELO computation, telemetry fetching |
| `FiveActMapper` | pitlane-studio | Static mapping from five dramatic acts to specific fetch/analyze functions | Data fetching itself |
| `PipelineOrchestrator` | pitlane-studio | Two-phase plan-then-write: outline generation → per-beat prose | LLM client selection, storage |
| `ArticleStore` | pitlane-studio | SQLite persistence: articles, beats, outline state, approval status | Workspace system (not using it) |
| `SubstackExporter` | pitlane-studio | Unofficial Substack API + markdown fallback | Publishing policy |
| `detect_stories()` | pitlane-elo | All story signal detection from ELO snapshots | Anything narrative-frame-level |
| `commands/fetch/*` | pitlane-agent | Pure Python data fetching functions (no Click dependency) | Prose generation |
| `commands/analyze/*` | pitlane-agent | Pure chart generation functions | Pipeline orchestration |

---

## Integration Pattern: pitlane-studio → pitlane-agent

**Decision: Direct Python import. No subprocess.**

Rationale: The existing architecture already separates business logic into `commands/` as pure Python functions with no Click dependency. `commands/fetch/session_info.py` exports `get_session_info(year, gp, session)` directly. `commands/analyze/lap_times.py` exports `generate_lap_times_chart(...)` directly. pitlane-studio imports these functions the same way the CLI layer does — with no Click, no subprocess, no IPC. The Claude agent's Bash-tool approach (calling the `pitlane` CLI binary) exists specifically because Claude cannot import Python modules; pitlane-studio is Python code and has no such constraint.

```python
# In pitlane-studio's AngleService — direct imports
from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_agent.commands.fetch.race_control import get_race_control
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.temporal import get_temporal_context
```

The `commands/__init__.py` already re-exports all public command functions — pitlane-studio can import from there.

**What pitlane-studio does NOT use from pitlane-agent:**
- `F1Agent` — studio has its own pipeline orchestrator; it does not need the full agent loop
- `tool_permissions.py` — no sandboxed Claude session; direct Anthropic API calls
- `AgentCache` — no web session pooling needed; studio articles are stateful by design

---

## Integration Pattern: pitlane-studio → pitlane-elo

**Decision: Direct Python import of `detect_stories()` and supporting types.**

```python
from pitlane_elo.stories.signals import detect_stories, StorySignal
from pitlane_elo.snapshots import get_race_snapshot
```

`detect_stories(year, round_num)` returns `list[StorySignal]`. Each `StorySignal` carries a `narrative` string already formatted for prompt injection, plus typed fields (`signal_type`, `driver_id`, `value`). The `AngleService` maps these into named story-angle cards by grouping and ranking signals, then enriches each with telemetry context fetched via pitlane-agent commands.

The existing anti-pattern in `cli_stories.py` (importing pitlane-elo directly at call time without going through a `commands/` wrapper) is documented in ARCHITECTURE.md. pitlane-studio should not replicate this — direct imports from pitlane-elo at module top level are correct because pitlane-studio is a peer package with an explicit dependency, not a CLI command handler that should go through the commands abstraction.

---

## Article State Persistence

**Decision: Separate SQLite database at `~/.pitlane/studio/articles.db`. Not an extension of the workspace system.**

Rationale: The workspace system (`~/.pitlane/workspaces/<uuid>/`) is designed for ephemeral analysis sessions — each workspace is a scratch directory for one conversation, with no cross-workspace relationships and no structured schema. Article drafts have fundamentally different state requirements: they are named, versioned, race-scoped, persist across sessions, and have a multi-step status machine (signals_fetched → outline_generated → outline_approved → beats_in_progress → complete → exported). SQLite is the correct fit: it gives structured queries for "all articles for year X", atomic beat appends, status transitions, and foreign-key relationships between articles and their beats.

The workspace system is still used for telemetry data cached by pitlane-agent commands (FastF1 cache at `~/.pitlane/cache/fastf1/`). pitlane-studio does not create workspaces — it calls the command functions directly and receives data as Python return values, writing nothing to the workspace filesystem.

### Schema

```sql
CREATE TABLE articles (
    id          TEXT PRIMARY KEY,   -- uuid
    year        INTEGER NOT NULL,
    round       INTEGER NOT NULL,
    gp_name     TEXT NOT NULL,
    angle_key   TEXT NOT NULL,      -- e.g. "hot_streak:VER" — selected story angle
    angle_label TEXT NOT NULL,      -- e.g. "Verstappen's Resurgence"
    status      TEXT NOT NULL,      -- signals_fetched | outline_generated | outline_approved
                                    -- | beats_in_progress | complete | exported
    outline     TEXT,               -- JSON: list of beat dicts with act, title, data_hook
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE beats (
    id          TEXT PRIMARY KEY,
    article_id  TEXT NOT NULL REFERENCES articles(id),
    beat_index  INTEGER NOT NULL,
    act         INTEGER NOT NULL,   -- 1-5 (Bouzarth five-act)
    title       TEXT NOT NULL,
    prose       TEXT,               -- null until generated
    placeholder_hooks TEXT,         -- JSON: list of strings (quote slots, context slots)
    status      TEXT NOT NULL,      -- pending | generating | complete | edited
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE angles (
    id          TEXT PRIMARY KEY,
    article_id  TEXT NOT NULL REFERENCES articles(id),
    signal_type TEXT NOT NULL,
    driver_id   TEXT NOT NULL,
    value       REAL NOT NULL,
    narrative   TEXT NOT NULL,
    selected    INTEGER NOT NULL DEFAULT 0
);
```

---

## Plan-Then-Write Pipeline

**Decision: Two-phase orchestration with a hard approval gate. Outline phase is a single non-streaming Anthropic API call. Beat prose is one streaming call per beat.**

This directly implements the Wang et al. (2025) finding that plan-then-write consistently outperforms streaming full-text, and Sánchez-López et al. (2025) that structured choices outperform free-text prompting.

### Data Flow

```
Phase 1: Angle Selection (AngleService)
  1. detect_stories(year, round) → list[StorySignal]          [pitlane-elo import]
  2. get_session_info(...), get_race_control(...)               [pitlane-agent imports]
  3. AngleService.build_angle_cards(signals, session_info)
     → list[AngleCard]  (4-6 named narrative frames)
  4. UI: journalist selects one angle card
  5. ArticleStore.create_article(year, round, angle)

Phase 2: Outline Generation (PipelineOrchestrator)
  1. FiveActMapper.resolve_data(year, round, angle)
     → dict: act_number → fetched data (from pitlane-agent commands)
  2. Anthropic API call (non-streaming, ~500 token output):
     prompt: angle narrative + five-act data summaries
     → JSON: list of 5-8 beat dicts {act, title, data_hook, placeholder_hooks}
  3. ArticleStore.save_outline(article_id, outline_json)
  4. Article status: outline_generated
  5. UI: journalist reviews beats, reorders, deletes, approves
  6. ArticleStore.approve_outline(article_id)
  7. Article status: outline_approved

Phase 3: Beat Prose Generation (PipelineOrchestrator)
  For each approved beat (journalist triggers one at a time, or all sequentially):
  1. Build prompt: beat title + act context + data_hook data + placeholder hook instructions
  2. Anthropic API streaming call (200-400 tokens per beat)
     → prose chunk stream → SSE to browser
  3. ArticleStore.save_beat_prose(article_id, beat_index, prose)
  4. Beat status: complete
  5. UI: journalist edits prose, fills placeholder hooks manually

Phase 4: Export (SubstackExporter)
  1. ArticleStore.load_article_full(article_id) → article + all beats
  2. Render beats as ordered markdown
  3. Attempt unofficial Substack API post
  4. On failure: return markdown string for manual copy
```

### Prompt Construction

Each beat prompt includes:
- The approved outline (all beats listed, current beat highlighted)
- The data hook for this beat (specific telemetry or ELO values)
- Explicit instructions to leave placeholder brackets `[JOURNALIST: add quote from X]` for human-only content
- Word count target (150-250 words per beat)
- The selected story angle's `narrative` string from `StorySignal`

The outline is always included in full at beat-generation time so the LLM has structural context without needing session continuity.

---

## Five-Act Mapping

**Decision: Static configuration dict mapping act numbers to specific pitlane-agent command functions and result keys.**

The FiveActMapper is not dynamic or AI-driven. It is a Python dict that says "Act 1 (inciting incident) = qualifying results + grid penalties; Act 2 (complications) = lap 1 incidents from race control; Act 3 (crisis) = tyre strategy + pit window; Act 4 (climax) = lap times final stint + position changes; Act 5 (resolution) = driver standings delta + championship implications." Each act entry maps to specific functions from `pitlane_agent.commands` and specific keys to extract from their return values.

```python
# five_act_mapper.py — illustrative structure
from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_agent.commands.fetch.race_control import get_race_control
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.analyze.tyre_strategy import generate_tyre_strategy_chart

ACT_MAP = {
    1: {  # Inciting incident: qualifying / grid
        "label": "Qualifying & Grid",
        "fetchers": [
            {"fn": get_session_info, "session": "Q", "key": "qualifying_results"},
        ],
    },
    2: {  # Complications: lap 1
        "label": "Lap 1 Chaos",
        "fetchers": [
            {"fn": get_race_control, "session": "R", "filter": "lap<=3", "key": "early_incidents"},
        ],
    },
    3: {  # Crisis: pit window
        "label": "Pit Window",
        "fetchers": [
            {"fn": get_session_info, "session": "R", "key": "pit_stops"},
        ],
    },
    4: {  # Climax: final stint
        "label": "Final Stint",
        "fetchers": [
            {"fn": get_session_info, "session": "R", "key": "race_results"},
        ],
    },
    5: {  # Resolution: championship
        "label": "Championship Implications",
        "fetchers": [
            {"fn": get_driver_standings, "key": "standings_delta"},
        ],
    },
}
```

All fetch functions return Python dicts/lists directly (they are the `commands/` layer functions, not CLI wrappers). The mapper calls them, collects results, and passes structured summaries to the outline prompt.

---

## Patterns to Follow

### Pattern 1: FastAPI app mirrors pitlane-web

pitlane-studio's FastAPI app follows the same structure as `pitlane_web/app.py`:
- Entry point registered in `pyproject.toml` as `pitlane-studio = "pitlane_studio.cli:main"`
- `studio_app.py` contains all routes
- `config.py` holds all constants
- `security.py` for any input sanitization (article IDs, filenames)
- SSE streaming for beat prose generation (same pattern as the chat SSE in pitlane-web)

### Pattern 2: All imports at module top level

Per project feedback (`feedback_imports_at_top.md`): all imports from pitlane-agent and pitlane-elo go at the top of each studio module. No lazy imports inside functions.

### Pattern 3: SQLite via stdlib sqlite3, not DuckDB

DuckDB is the right tool for pitlane-elo's analytical Parquet queries. For article state (small, relational, transactional, low read volume), stdlib `sqlite3` with WAL mode is sufficient and adds no new dependency. Use context managers for connections; one connection per request lifecycle.

### Pattern 4: Direct Anthropic SDK, not F1Agent

pitlane-studio's pipeline uses `anthropic.Anthropic()` directly for outline and beat generation. It does not use `F1Agent` because:
- No Bash tool needed (data is fetched by Python function calls, not CLI subprocesses)
- No skill loading needed (studio has its own prompt construction)
- No workspace sandbox needed (studio owns its own state)
- Streaming can be done with `client.messages.stream()` for beat prose

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Calling the `pitlane` CLI binary via subprocess

**What happens:** `subprocess.run(["pitlane", "fetch", "session-info", ...])` to get data.
**Why bad:** Forces parsing of CLI output (JSON written to workspace files), adds process overhead, requires a workspace directory per call, and makes the integration fragile to CLI flag changes. The commands layer is pure Python functions specifically to avoid this.
**Instead:** Import `get_session_info(year, gp, session)` directly from `pitlane_agent.commands.fetch.session_info`.

### Anti-Pattern 2: Extending the workspace system for article state

**What happens:** Writing article JSON into `~/.pitlane/workspaces/<uuid>/data/articles/`.
**Why bad:** Workspaces are ephemeral and UUID-keyed — there is no stable cross-session way to find "all articles for 2026 Bahrain GP." The workspace system has no query capability. The workspace clean-up logic would delete article drafts. Article state is fundamentally relational (article → beats, article → angles), not a bag of files.
**Instead:** SQLite at `~/.pitlane/studio/articles.db`.

### Anti-Pattern 3: One streaming LLM call for the full article

**What happens:** Single `client.messages.stream()` call with all five acts in the prompt, generating 1500-2500 words of prose.
**Why bad:** Wang et al. (2025) quantifies prose quality degradation after the first 40-60% of long output. The journalist also has no approval point before prose generation begins. A 2000-word generation that misses the selected angle cannot be corrected mid-stream.
**Instead:** Outline in Phase 2 (non-streaming, ~500 tokens, journalist approves), then per-beat streaming calls (150-250 tokens each) in Phase 3.

### Anti-Pattern 4: Generating placeholder hooks via AI

**What happens:** Asking the LLM to decide where journalist quotes and context should go.
**Why bad:** The outline approval step is where the journalist reviews beat structure and hook placement. AI-generated hook placement removes journalist agency and produces formulaic output. Wölker & Powell (2018) establish that journalist value is context, causality, and interviews — the tool should preserve space for these, not decide where they go via AI.
**Instead:** Beat prompts explicitly instruct the LLM to insert `[JOURNALIST: ...]` brackets at locations where human-only content belongs. The `placeholder_hooks` column in the `beats` table stores these as structured strings visible in the UI.

---

## Build Order

Dependencies must exist before dependents. The correct implementation order:

```
1. pitlane-studio package scaffold
   └── pyproject.toml with pitlane-agent + pitlane-elo as workspace dependencies
   └── packages/pitlane-studio/src/pitlane_studio/__init__.py

2. ArticleStore (article_store.py)
   └── SQLite schema, CRUD operations, status transitions
   └── No external dependencies beyond stdlib sqlite3
   └── Testable in isolation with in-memory SQLite

3. AngleService (angle_service.py)
   └── Imports detect_stories from pitlane-elo [pitlane-elo must exist — it does]
   └── Imports session fetch commands from pitlane-agent [exists]
   └── Produces AngleCard objects (new dataclass, owned by pitlane-studio)
   └── Requires: ArticleStore (for create_article)

4. FiveActMapper (five_act_mapper.py)
   └── Static config dict + data resolution logic
   └── Imports pitlane-agent command functions [exist]
   └── No dependency on AngleService or ArticleStore

5. PipelineOrchestrator (pipeline.py)
   └── Imports FiveActMapper, ArticleStore
   └── Imports anthropic SDK (new dependency on pitlane-studio only)
   └── Owns prompt construction for outline and beat phases
   └── Requires: FiveActMapper + ArticleStore both complete

6. FastAPI app + routes (studio_app.py)
   └── Wires AngleService, PipelineOrchestrator, ArticleStore, SubstackExporter
   └── SSE streaming endpoint for beat prose
   └── HTMX-compatible fragment endpoints for angle cards, outline editor
   └── Requires: all services complete

7. SubstackExporter (substack_export.py)
   └── Unofficial API attempt + markdown fallback
   └── Only dependency: ArticleStore (to load full article)
   └── Can be built in parallel with steps 5-6

8. Frontend templates (Jinja2 + HTMX)
   └── Angle card selection view
   └── Outline approval editor (reorder/delete beats before approval)
   └── Beat-by-beat prose editor with placeholder hook highlighting
   └── Requires: FastAPI app routes finalized
```

---

## Scalability Considerations

This is a personal productivity tool (single user, no SLA). Scalability is not a concern. The architecture is sized appropriately:

| Concern | Approach |
|---------|----------|
| Article storage | SQLite, WAL mode — sufficient for thousands of articles |
| FastF1 telemetry | Cached at `~/.pitlane/cache/fastf1/`; no per-request fetching after first load |
| LLM calls | Direct Anthropic API; no rate limit concern for single-user tool |
| Concurrent requests | Single-user: no concurrency needed; FastAPI async is still correct for SSE |

---

## Sources

All findings are based on direct code inspection. No external sources required.

- `packages/pitlane-agent/src/pitlane_agent/agent.py` — F1Agent, SDK integration pattern
- `packages/pitlane-agent/src/pitlane_agent/commands/workspace/operations.py` — workspace system design and limitations
- `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` — StorySignal, detect_stories API
- `.planning/codebase/ARCHITECTURE.md` — existing system architecture, anti-patterns
- `.planning/codebase/STRUCTURE.md` — package layout, naming conventions, where to add new code
- `.planning/PROJECT.md` — requirements, constraints, key decisions, research grounding

*Architecture analysis: 2026-05-02*
