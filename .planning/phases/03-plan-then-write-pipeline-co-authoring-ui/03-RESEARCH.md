# Phase 3: Plan-Then-Write Pipeline + Co-Authoring UI — Research

**Researched:** 2026-05-05
**Domain:** FastAPI SSE streaming, Anthropic async streaming, SvelteKit 5 static build, TipTap 2.x custom nodes, SQLAlchemy Core tables
**Confidence:** HIGH (core stack), MEDIUM (TipTap + Svelte 5 integration spike required)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Beats are variable in count — journalist can add, remove, or reorder beats before approval. Five-act framework is the default starting structure. Pipeline generates one streaming LLM call per approved beat.
- **D-02:** The full approved outline (all beat titles and data anchors) is injected into every individual beat's generation prompt.
- **D-03:** One SSE request per beat, made sequentially by the frontend. Endpoint: `GET /articles/{id}/beats/{beat_number}/stream`. After outline approval, the frontend auto-advances through all approved beats. Endpoint: `GET /articles/{id}/beats/{beat_number}/stream`.
- **D-04:** SSE events per beat stream: `beat_start`, `token`, `beat_done` (full prose + placeholder markers), `error`.
- **D-05:** Backend enforces the hard approval gate via ArticleStore state. The `/stream` endpoints return HTTP 409 if `article.status != "outline_approved"`. No bypass path.
- **D-06:** Beat prose persisted to SQLite on `beat_done`. New `beats` table: `(article_id, beat_number, beat_title, prose, placeholder_markers_json, created_at, updated_at)`.
- **D-07:** Outline persisted to SQLite when first generated and when edited. New `outline_beats` table: `(article_id, beat_number, beat_title, data_anchors, act_number, position)`. Approval updates ArticleStore status to `outline_approved`.
- **D-08:** SvelteKit static build served by FastAPI at `/`. Build output: `packages/pitlane-studio/src/pitlane_studio/static/`. FastAPI mounts this as StaticFiles. Single process, single port (8001). No CORS config needed.
- **D-09:** SvelteKit app lives at `packages/pitlane-studio/frontend/`. Build command: `npm run build` from `frontend/`, output to `../src/pitlane_studio/static/`. Frontend has own `package.json`, `vite.config.ts`, `svelte.config.js`.
- **D-10:** TipTap + Svelte 5 integration is flagged MEDIUM confidence. Wave 0 of Phase 3 planning includes a TipTap + Svelte 5 spike: validate `onMount` instantiation, `editor.getJSON()` round-trip, and custom node extension. Spike must pass before full editor implementation wave.

### Claude's Discretion

- Placeholder hook representation in TipTap — custom inline node extension (decided in UI-SPEC: `inline: true`, `atom: true`, custom node type per hook type).
- Race selector UX — two chained `<select>` dropdowns: Year then Round (decided in UI-SPEC).
- Exact SSE event schema beyond the four named events — decided in UI-SPEC (see SSE Event Schema section).
- FastAPI route organization — follow existing `app.py` pattern; use APIRouter groupings.

### Deferred Ideas (OUT OF SCOPE)

- Substack unofficial API draft export (XPRT-02, XPRT-03)
- Draggable beat reordering in timeline view (CM-02)
- Article draft list / resume saved drafts (CM-01)
- Audience framing controls (WE-01)
- Character arc detection (WE-02)
- Multimodal chart pairing (WE-03)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ACT-03 | Always-visible five-act sidebar showing act labels, data sources, and key data points | FiveActMapper.fetch_act_data() already built; FastAPI GET /acts/{year}/{round} route feeds sidebar data; Svelte component reads on race load |
| PTW-01 | Generate structured article outline (5 beat dicts) via single non-streaming LLM call after angle selection | Anthropic SDK sync messages.create(); outline as structured JSON; validated with Pydantic; persisted to outline_beats table |
| PTW-02 | Explicit approval gate — no prose generated until outline approved; hard backend 409 enforcement | ArticleStore state machine (outline_generated → outline_approved transition); FastAPI returns 409 if wrong status; UI hides button |
| PTW-03 | After approval, generate prose for each beat via separate streaming LLM calls; full outline in every prompt | AsyncAnthropic.messages.stream() + text_stream iteration; FastAPI StreamingResponse generator; SSE format per D-04 |
| PTW-04 | Each beat contains enforced placeholder hooks (quote, context, causal); tool never fills them | Placeholder markers injected into prompt instructions; detected in prose via regex; serialized as placeholder_markers_json in beats table |
| UI-01 | Race selector + 4–6 angle cards (name, signal type, confidence, data rationale) | GET /races/years, GET /races/{year}/rounds routes; GET /articles/{id}/angles calls AngleService; Svelte angle card components |
| UI-02 | TipTap block editor per beat; placeholder hooks as visually distinct non-editable blocks | TipTap 2.27.2 custom inline node extensions (atom: true); onMount instantiation; getJSON round-trip |
| UI-03 | Five-beat outline panel; editable beat titles/data anchors; approve before prose generation | Outline Panel component; PATCH /articles/{id}/outline to persist edits; POST /articles/{id}/approve endpoint |
| XPRT-01 | Copy clean markdown with [JOURNALIST: type] markers at any time | Client-side export: editor.getJSON() → traverse nodes → serialize custom nodes as [JOURNALIST: type] markers; navigator.clipboard.writeText() |
</phase_requirements>

---

## Summary

Phase 3 builds the full journalist-facing writing workflow: PipelineOrchestrator (Python backend) + FastAPI routes + SvelteKit 5 frontend. The backend is a natural extension of the existing patterns — new SQLAlchemy Core tables following `article_store.py`, new service classes imported at module top following `angles.py`, new FastAPI router files extending `app.py`. The main technical unknowns are concentrated in the TipTap + Svelte 5 integration (D-10 spike), FastAPI SSE streaming (well-understood but version-gated), and the Anthropic async streaming wire-up inside a FastAPI generator.

**Key finding:** FastAPI 0.128.0 (installed) does NOT include native `fastapi.sse` — that was introduced in 0.135.0. The correct SSE approach for this project is `StreamingResponse` with an async generator that yields SSE-formatted strings. This is the established pattern that works with 0.128.x and requires no additional packages. The `sse-starlette` library is an option but adds a dependency for functionality achievable with stdlib.

**Key finding:** TipTap 3.x (latest: 3.22.5) is now the default on npm. The project specifies TipTap 2.x. The correct install is `@tiptap/core@2` which pins to 2.27.2 (the latest 2.x stable). The v2-latest tag confirms 2.27.2. No Svelte-specific TipTap package exists for v2 — TipTap is headless, so Svelte 5 integrates it the same way as vanilla JS, via `onMount`.

**Primary recommendation:** Implement SSE using FastAPI's built-in `StreamingResponse` with async generator. Install TipTap 2.27.2 (pinned to `^2.0.0` or `2.27.2` exactly). Instantiate TipTap in Svelte 5 `onMount`. Run the Wave 0 spike before any other TipTap work.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Outline generation (PTW-01) | API / Backend | — | Non-streaming LLM call; result must be persisted to SQLite before returning to frontend |
| Approval gate enforcement (PTW-02) | API / Backend | Browser / Client | Backend is authoritative (HTTP 409); client UI hides button as UX assist only |
| Beat prose SSE streaming (PTW-03) | API / Backend | Browser / Client | Backend streams tokens; client consumes EventSource; both must be implemented |
| Placeholder hook insertion (PTW-04) | API / Backend | Browser / Client | Backend detects placeholder positions in prose; frontend renders them as custom nodes |
| Markdown export (XPRT-01) | Browser / Client | — | Client-side only: getJSON() traversal + clipboard write; no server round-trip needed |
| Five-act sidebar data (ACT-03) | API / Backend | Browser / Client | FiveActMapper.fetch_act_data() is Python; FastAPI route serves data; frontend renders |
| Angle cards (UI-01) | API / Backend | Browser / Client | AngleService runs server-side; frontend displays results |
| Outline editing / persistence (UI-03) | Browser / Client | API / Backend | Editor state in Svelte; PATCH to backend persists on save; approval via POST |
| TipTap editor state (UI-02) | Browser / Client | — | All editor state (prose, placeholder nodes, cursor) lives in client TipTap instance |
| SQLite persistence (D-06, D-07) | Database / Storage | — | beats + outline_beats tables; follows ArticleStore SQLAlchemy Core pattern |

---

## Standard Stack

### Core — Backend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.128.0 (installed) | API routes, StreamingResponse SSE | Already in project; upgrade to ≥0.135.0 deferred — StreamingResponse SSE works at 0.128.0 |
| SQLAlchemy (Core) | ≥2.0 (installed) | `beats` + `outline_beats` tables | Established pattern in `article_store.py`; no ORM |
| anthropic | 0.97.0 (installed) | AsyncAnthropic for beat prose streaming | Already used in angles.py for DNF check; async client for SSE integration |
| Pydantic | ≥2.0 (installed) | Request/response schemas for new routes | Established project pattern |

### Core — Frontend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte | 5.55.5 | UI component framework | Project decision; Svelte 5 is latest stable |
| @sveltejs/kit | 2.59.1 | SvelteKit framework for routing + build | Project decision; adapter-static for final build |
| @sveltejs/adapter-static | 3.0.10 | SPA static output for FastAPI serving | Required by D-08/D-09; outputs to FastAPI static directory |
| @sveltejs/vite-plugin-svelte | 7.1.0 | Svelte Vite integration | Required by SvelteKit |
| vite | 8.0.10 | Build tool + dev server | SvelteKit built on Vite; dev proxy to FastAPI |
| @tiptap/core | 2.27.2 (2.x latest) | ProseMirror-based rich text editor | Project decision; headless, no Svelte wrapper needed |
| @tiptap/pm | 2.27.2 | ProseMirror core modules required by TipTap | Required peer dependency for TipTap 2.x |
| @tiptap/starter-kit | 2.27.2 | Bold, italic, paragraph, history extensions | Provides base formatting; project requires only bold + italic |
| @tiptap/extension-placeholder | 2.27.2 | Editor-level placeholder text (empty state hint) | Optional but clean; UI-SPEC implies empty state hint |
| lucide-svelte | 1.0.1 | Icon library (quote, info-circle, git-merge per UI-SPEC) | Specified in UI-SPEC and 03-UI-SPEC.md; MIT, tree-shakeable |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| StreamingResponse (FastAPI 0.128.0) | Upgrade to FastAPI ≥0.135.0 + native EventSourceResponse | Upgrade is straightforward (no breaking changes in 0.128→0.135 for this usage) but adds risk to a working install; StreamingResponse achieves identical result |
| StreamingResponse | sse-starlette 3.2.0 | Adds dependency; sse-starlette not currently installed; StreamingResponse is sufficient |
| @tiptap/core 2.x | @tiptap/core 3.x (latest) | TipTap 3.x is a major rewrite; CONTEXT.md specifies 2.x; 2.27.2 is latest stable v2 |
| Custom Node (TipTap inline atom) | Mark extension | Marks survive only if text is selected; atom nodes survive getJSON round-trips as discrete objects; UI-SPEC and CONTEXT.md decided: custom inline node |

**Installation — Frontend:**
```bash
cd packages/pitlane-studio/frontend
npm install @tiptap/core@^2.27.2 @tiptap/pm@^2.27.2 @tiptap/starter-kit@^2.27.2 @tiptap/extension-placeholder@^2.27.2 lucide-svelte
```

**Version verification:** [VERIFIED: npm registry — 2026-05-05]
- `@tiptap/core` latest 2.x: 2.27.2 (`v2-latest` tag confirmed)
- `@tiptap/starter-kit`, `@tiptap/pm`, `@tiptap/extension-placeholder`: all 2.27.2 (same release)
- `svelte`: 5.55.5, `@sveltejs/kit`: 2.59.1, `@sveltejs/adapter-static`: 3.0.10
- `vite`: 8.0.10, `@sveltejs/vite-plugin-svelte`: 7.1.0, `lucide-svelte`: 1.0.1

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (SvelteKit SPA at localhost:8001)
  │
  │  Initial load: GET /  → StaticFiles (FastAPI)
  │  API calls: GET/POST /articles/*, GET /acts/*, GET /races/*
  │  SSE: GET /articles/{id}/beats/{n}/stream  (EventSource)
  │
  ▼
FastAPI app (port 8001)
  ├── StaticFiles("/", directory="static")       ← SvelteKit build output
  ├── APIRouter: /articles                       ← PipelineOrchestrator, ArticleStore
  │     ├── POST /articles                       ← create article
  │     ├── GET  /articles/{id}/angles           ← AngleService
  │     ├── POST /articles/{id}/outline          ← PipelineOrchestrator.generate_outline()
  │     ├── PATCH /articles/{id}/outline         ← persist edits to outline_beats
  │     ├── POST /articles/{id}/approve          ← ArticleStore.transition_status("outline_approved")
  │     └── GET  /articles/{id}/beats/{n}/stream ← SSE → PipelineOrchestrator.stream_beat()
  ├── APIRouter: /acts                           ← FiveActMapper
  │     └── GET  /acts/{year}/{round}            ← FiveActMapper.fetch_act_data() all 5 acts
  └── APIRouter: /races                          ← pitlane-agent fetch commands
        ├── GET  /races/years                    ← available season years
        └── GET  /races/{year}/rounds            ← rounds for a year
          │
          ▼
  PipelineOrchestrator (service)
  ├── generate_outline(year, round, angle_id, article_id)
  │     → anthropic.Anthropic().messages.create() [non-streaming]
  │     → persist to outline_beats table
  │     → ArticleStore.transition_status("outline_generated")
  │
  └── stream_beat(article_id, beat_number)
        → ArticleStore.get() — check status == "outline_approved" (gate D-05)
        → AsyncAnthropic().messages.stream() [async, per-beat]
        → yield SSE events: beat_start → token × N → beat_done
        → on beat_done: persist to beats table
          │
          ▼
  SQLite (~/.pitlane/studio/articles.db)
  ├── articles          (existing — ArticleStore)
  ├── outline_beats     (new — D-07)
  └── beats             (new — D-06)
```

### Recommended Project Structure

```
packages/pitlane-studio/
├── src/pitlane_studio/
│   ├── app.py                    # extend: add routers + StaticFiles mount
│   ├── routers/                  # new
│   │   ├── __init__.py
│   │   ├── articles.py           # /articles/* routes
│   │   ├── acts.py               # /acts/* routes
│   │   └── races.py              # /races/* routes
│   ├── services/
│   │   ├── angles.py             # existing
│   │   ├── five_act.py           # existing
│   │   └── pipeline.py           # new: PipelineOrchestrator
│   ├── store/
│   │   ├── article_store.py      # existing
│   │   └── beat_store.py         # new: outline_beats + beats tables
│   └── static/                   # SvelteKit build output (gitignored)
│
└── frontend/                     # new SvelteKit app
    ├── package.json
    ├── vite.config.ts
    ├── svelte.config.js
    └── src/
        ├── lib/
        │   ├── components/
        │   │   ├── RaceSelector.svelte
        │   │   ├── AngleCard.svelte
        │   │   ├── OutlinePanel.svelte
        │   │   ├── BeatEditor.svelte       # TipTap instance
        │   │   ├── FiveActSidebar.svelte
        │   │   └── PlaceholderNode.svelte  # custom TipTap node renderer
        │   ├── extensions/
        │   │   └── placeholder-nodes.ts    # TipTap custom node extensions
        │   ├── api.ts                      # typed fetch wrappers
        │   └── store.ts                    # Svelte stores for app state
        └── routes/
            └── +page.svelte                # single-page app shell
```

---

## Pattern 1: FastAPI SSE StreamingResponse (Beat Streaming)

**What:** An async generator function yields SSE-formatted strings; FastAPI wraps it in `StreamingResponse` with `media_type="text/event-stream"`.

**When to use:** All `GET /articles/{id}/beats/{beat_number}/stream` endpoints.

**Critical format rule:** Each SSE message is `data: {json}\n\n` — the double newline terminates the message. Named events use `event: {name}\ndata: {json}\n\n`.

```python
# Source: VERIFIED via FastAPI 0.128.0 StreamingResponse (installed) + SSE spec
import asyncio
import json
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from anthropic import AsyncAnthropic

router = APIRouter()

async def _beat_sse_generator(article_id: str, beat_number: int):
    """Async generator yielding SSE-formatted strings for one beat."""
    # Gate check — 409 is raised BEFORE returning StreamingResponse
    # (must check before generator is consumed)
    store = ArticleStore()
    article = store.get(article_id)
    if article.status != "outline_approved":
        # Cannot raise HTTPException inside a generator after headers are sent.
        # Yield a structured error event and return.
        yield f"event: error\ndata: {json.dumps({'beat_number': beat_number, 'message': 'Outline not approved', 'retryable': False})}\n\n"
        return

    # beat_start event
    yield f"event: beat_start\ndata: {json.dumps({'beat_number': beat_number, 'beat_title': '...', 'total_beats': 5})}\n\n"

    client = AsyncAnthropic()
    full_prose = []

    async with client.messages.stream(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": beat_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            full_prose.append(text)
            yield f"event: token\ndata: {json.dumps({'beat_number': beat_number, 'token': text})}\n\n"

    prose = "".join(full_prose)
    placeholder_markers = _detect_placeholders(prose)

    # Persist beat prose
    beat_store.save_beat(article_id, beat_number, prose, placeholder_markers)

    yield f"event: beat_done\ndata: {json.dumps({'beat_number': beat_number, 'prose': prose, 'placeholder_markers': placeholder_markers})}\n\n"


@router.get("/articles/{article_id}/beats/{beat_number}/stream")
async def stream_beat(article_id: str, beat_number: int):
    # Gate check BEFORE creating StreamingResponse (allows HTTPException to work)
    store = ArticleStore()
    article = store.get(article_id)
    if article.status != "outline_approved":
        raise HTTPException(status_code=409, detail="Outline not approved")

    return StreamingResponse(
        _beat_sse_generator(article_id, beat_number),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",      # prevents Nginx buffering
            "Connection": "keep-alive",
        },
    )
```

**Key insight:** Raise `HTTPException` BEFORE returning `StreamingResponse`. Once the generator starts sending, HTTP status is already 200 and you cannot change it — the generator can only send an `error` SSE event at that point.

[VERIFIED: FastAPI 0.128.0 StreamingResponse API + SSE spec RFC 8895]

---

## Pattern 2: TipTap Custom Inline Atom Node (Svelte 5)

**What:** A TipTap Node extension with `inline: true`, `atom: true` creates a non-editable inline block that round-trips through `getJSON()` as a discrete node object with preserved attributes.

**When to use:** All three placeholder hook types: `placeholderQuote`, `placeholderContext`, `placeholderCausal`.

```typescript
// Source: VERIFIED via Context7 /ueberdosis/tiptap-docs + official docs
// packages/pitlane-studio/frontend/src/lib/extensions/placeholder-nodes.ts

import { Node, mergeAttributes } from '@tiptap/core'

export const PlaceholderQuote = Node.create({
  name: 'placeholderQuote',
  group: 'inline',
  inline: true,
  atom: true,         // non-editable, treated as single unit — survives getJSON()

  addAttributes() {
    return {
      type: { default: 'quote' },   // preserved in getJSON() output
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-placeholder-type="quote"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, {
      'data-placeholder-type': 'quote',
      class: 'placeholder-hook placeholder-hook--quote',
      contenteditable: 'false',
    }), 'JOURNALIST: Add quote']
  },
})

// PlaceholderContext and PlaceholderCausal follow the same pattern
// with name, data-placeholder-type, and label changed.
```

**getJSON() output for a placeholder node:**
```json
{
  "type": "placeholderQuote",
  "attrs": { "type": "quote" }
}
```

This is the node object the markdown exporter traverses to emit `[JOURNALIST: quote]`.

[VERIFIED: Context7 /ueberdosis/tiptap-docs — inline atom node pattern]

---

## Pattern 3: TipTap Instantiation in Svelte 5 onMount

**What:** TipTap Editor is a plain JS class; Svelte 5 `onMount` is the correct lifecycle hook for DOM-dependent setup (runs after component mounts, does not run during SSR). `$effect` is the Svelte 5 reactivity primitive but `onMount` remains the correct pattern for one-time DOM setup.

**Why not `$effect`:** `$effect` re-runs whenever its reactive dependencies change, making it unsuitable for one-time editor initialization. `onMount` runs exactly once after the first render.

```svelte
<!-- packages/pitlane-studio/frontend/src/lib/components/BeatEditor.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import { PlaceholderQuote, PlaceholderContext, PlaceholderCausal } from '../extensions/placeholder-nodes'

  let editorElement: HTMLElement
  let editor: Editor | null = null

  onMount(() => {
    editor = new Editor({
      element: editorElement,
      extensions: [
        StarterKit,
        PlaceholderQuote,
        PlaceholderContext,
        PlaceholderCausal,
      ],
      content: '',
    })

    // Cleanup returned from onMount — called on component destroy
    return () => {
      editor?.destroy()
      editor = null
    }
  })

  export function getContent() {
    return editor?.getJSON() ?? null
  }
</script>

<div bind:this={editorElement}></div>
```

[VERIFIED: Context7 /sveltejs/svelte — onMount lifecycle hook docs]
[ASSUMED: `$effect` vs `onMount` tradeoff for TipTap — spike required per D-10]

---

## Pattern 4: SvelteKit Static Build — svelte.config.js + vite.config.ts

**What:** `adapter-static` produces a self-contained `build/` folder (HTML, JS, CSS assets) that can be served from any static file host — or in this case, FastAPI's `StaticFiles`.

**Configuration (svelte.config.js):**
```javascript
// Source: VERIFIED Context7 /sveltejs/kit — adapter-static docs
// packages/pitlane-studio/frontend/svelte.config.js
import adapter from '@sveltejs/adapter-static'

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter({
      pages: '../src/pitlane_studio/static',    // D-09: output to FastAPI static dir
      assets: '../src/pitlane_studio/static',
      fallback: '200.html',    // SPA fallback for client-side routing
      precompress: false,
      strict: false,           // false because not all routes are prerenderable
    }),
  },
}

export default config
```

**Dev proxy (vite.config.ts) — forwards API calls to FastAPI during `npm run dev`:**
```typescript
// Source: VERIFIED Context7 /vitejs/vite — server.proxy docs
// packages/pitlane-studio/frontend/vite.config.ts
import { defineConfig } from 'vite'
import { sveltekit } from '@sveltejs/kit/vite'

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173,
    proxy: {
      '/articles': { target: 'http://localhost:8001', changeOrigin: false },
      '/acts':      { target: 'http://localhost:8001', changeOrigin: false },
      '/races':     { target: 'http://localhost:8001', changeOrigin: false },
    },
  },
})
```

**FastAPI StaticFiles mount (app.py extension):**
```python
# Source: VERIFIED Context7 /fastapi/fastapi — StaticFiles docs
# packages/pitlane-studio/src/pitlane_studio/app.py (additions)
from pathlib import Path
from fastapi.staticfiles import StaticFiles

_STATIC_DIR = Path(__file__).parent / "static"

# Mount AFTER all API routes — StaticFiles is a catch-all
# Must use html=True for SPA fallback support
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
```

[VERIFIED: Context7 /sveltejs/kit adapter-static + Context7 /vitejs/vite proxy + Context7 /fastapi/fastapi StaticFiles]

---

## Pattern 5: Anthropic Async Streaming Inside FastAPI Generator

**What:** `AsyncAnthropic` is the async client for use in `async def` contexts. Inside an `async def` FastAPI generator, use `async with client.messages.stream()` and iterate `stream.text_stream`.

```python
# Source: VERIFIED Context7 /anthropics/anthropic-sdk-python — async streaming
from anthropic import AsyncAnthropic

# AsyncAnthropic should be instantiated once (module-level singleton or per-request)
_client = AsyncAnthropic()

async def stream_beat_prose(beat_prompt: str):
    """Yield text tokens from Claude's streaming response."""
    async with _client.messages.stream(
        model="claude-sonnet-4-5-20250929",  # use latest claude model
        max_tokens=1024,
        messages=[{"role": "user", "content": beat_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
        # After loop, stream.get_final_message() available if needed for logging
```

[VERIFIED: Context7 /anthropics/anthropic-sdk-python]

---

## Pattern 6: SQLAlchemy Core — New Tables (beats + outline_beats)

Following the `article_store.py` pattern exactly — no ORM, `Table/Column/MetaData`, Python str for datetimes.

```python
# Source: VERIFIED from packages/pitlane-studio/src/pitlane_studio/store/article_store.py pattern
from sqlalchemy import Column, Integer, String, Table, MetaData, Text

metadata = MetaData()

outline_beats_table = Table(
    "outline_beats",
    metadata,
    Column("article_id", String, nullable=False),
    Column("beat_number", Integer, nullable=False),
    Column("beat_title", String, nullable=False),
    Column("data_anchors", Text, nullable=True),
    Column("act_number", Integer, nullable=True),
    Column("position", Integer, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

beats_table = Table(
    "beats",
    metadata,
    Column("article_id", String, nullable=False),
    Column("beat_number", Integer, nullable=False),
    Column("beat_title", String, nullable=False),
    Column("prose", Text, nullable=True),
    Column("placeholder_markers_json", Text, nullable=True),  # JSON list of {type, offset}
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)
```

[VERIFIED: from article_store.py codebase read]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE formatting | Custom SSE protocol parser | `f"event: {name}\ndata: {json}\n\n"` strings + StreamingResponse | SSE is a simple text protocol; stdlib string formatting is sufficient |
| Rich text editing | Custom contenteditable editor | TipTap 2.x | Custom editors miss ProseMirror schema validation, undo history, selection management, cursor edge cases |
| Custom node serialization | Custom JSON format for placeholder hooks | TipTap `atom: true` + `addAttributes()` | `getJSON()` automatically preserves all node attributes — no custom serializer needed |
| Background task for beat generation | asyncio.create_task() or Celery | SSE StreamingResponse generator | The generator IS the background task; client connection drives progress |
| Client-side markdown export | Server-side markdown rendering endpoint | `editor.getJSON()` traversal + `navigator.clipboard.writeText()` | Export is client-side; no server round-trip required; cleaner UX |
| Race/round data fetching | Scraping or external API | `pitlane_agent.commands.fetch.session_info.get_session_info()` + `get_season_summary()` | Already used in Phase 2; direct Python import |

**Key insight:** The entire export pipeline (XPRT-01) is client-side. The frontend traverses TipTap's JSON, serializes placeholder nodes as `[JOURNALIST: type]`, and writes to clipboard. No backend markdown endpoint is needed.

---

## SSE Event Schema (from UI-SPEC — Claude's Discretion)

Full payload spec for `GET /articles/{id}/beats/{beat_number}/stream`:

| Event | Payload | Frontend action |
|-------|---------|-----------------|
| `beat_start` | `{beat_number: int, beat_title: str, total_beats: int}` | Render beat block in streaming state; update left panel indicator |
| `token` | `{beat_number: int, token: str}` | Append token text to beat's TipTap editor content |
| `beat_done` | `{beat_number: int, prose: str, placeholder_markers: [{type: str, offset: int}]}` | Finalize beat; insert placeholder hook nodes at offsets; exit streaming state; trigger next beat SSE |
| `error` | `{beat_number: int, message: str, retryable: bool}` | Show error banner; show "Retry Beat" button if retryable |

Wire format example:
```
event: beat_start
data: {"beat_number": 1, "beat_title": "Grid and Qualifying", "total_beats": 5}

event: token
data: {"beat_number": 1, "token": "The grid "}

event: token
data: {"beat_number": 1, "token": "formed under "}

event: beat_done
data: {"beat_number": 1, "prose": "The grid formed under...", "placeholder_markers": [{"type": "quote", "offset": 45}]}

```

---

## Common Pitfalls

### Pitfall 1: HTTPException Raised Inside an Already-Started StreamingResponse
**What goes wrong:** If you check the approval gate inside the generator (after `StreamingResponse` is already being sent), HTTP status is already 200 — you cannot return a 409. The client sees a 200 with an `error` SSE event, not a proper HTTP error.
**Why it happens:** HTTP headers (including status) are sent when the first byte of the response body is written.
**How to avoid:** Perform ALL synchronous gate checks BEFORE creating the `StreamingResponse`. Raise `HTTPException` in the outer `async def` route handler, not inside the generator. Inside the generator, yield an `error` event only for errors that occur after streaming has started.
**Warning signs:** Client code that checks `response.status` for 409 will always see 200.

### Pitfall 2: TipTap Editor Instantiated Outside onMount (SSR or DOM-not-ready)
**What goes wrong:** TipTap's `Editor` class requires a real DOM element. If instantiated outside `onMount` (e.g., at module scope, in `$effect` before element is mounted, or during SvelteKit SSR), it throws `Cannot read properties of null (reading 'nodeType')` or similar.
**Why it happens:** SvelteKit with `adapter-static` still processes routes server-side during build. `onMount` is excluded from SSR execution.
**How to avoid:** Always create the TipTap `Editor` inside `onMount`. Bind the element with `bind:this={el}` and pass it to `element: el` in the Editor constructor.
**Warning signs:** `el` is `null` when TipTap constructor runs.

### Pitfall 3: SPA Fallback Missing — FastAPI Serves 404 for Deep Routes
**What goes wrong:** If the user navigates directly to `/` then to a Svelte state via `history.pushState`, a page refresh sends the path to FastAPI, which has no matching route and returns 404.
**Why it happens:** FastAPI `StaticFiles` looks for an exact file match. `/article/123` has no file.
**How to avoid:** Use `StaticFiles(html=True)` which serves `index.html` for unknown paths. Set `fallback: '200.html'` in `adapter-static` config.
**Warning signs:** Direct navigation to any URL besides `/` returns 404.

### Pitfall 4: TipTap `atom: true` Node With `contentDOM` — Contradictory Settings
**What goes wrong:** If you return both `atom: true` AND provide a `contentDOM` in `addNodeView`, TipTap ignores `contentDOM` — atom nodes have no editable content. Setting `contenteditable: false` on the DOM element is required for the cursor to skip over the node.
**Why it happens:** `atom: true` means "treat as single unit, no direct editing". Providing `contentDOM` contradicts this.
**How to avoid:** For placeholder hooks: `atom: true`, no `contentDOM`, `renderHTML` returns a fully-rendered span with hardcoded label text.
**Warning signs:** Cursor enters the placeholder node; user can type inside it.

### Pitfall 5: `@tiptap/core` 3.x Installed Instead of 2.x
**What goes wrong:** `npm install @tiptap/core` without a version specifier installs 3.22.5 (latest). TipTap 3.x is a major API rewrite — `Node.create()` API changed, extension registration changed.
**Why it happens:** npm default is `latest` tag, which now resolves to 3.x.
**How to avoid:** Always pin to `^2.0.0` or `@tiptap/core@2`. All four TipTap packages must be the same major version.
**Warning signs:** `import { Node } from '@tiptap/core'` shows unfamiliar API; `Node.create()` signature differs.

### Pitfall 6: `AsyncAnthropic` Used in Sync Context (or vice versa)
**What goes wrong:** Using `anthropic.Anthropic()` (sync) in an `async def` FastAPI generator blocks the event loop during LLM generation. Using `AsyncAnthropic()` outside `async` context causes `RuntimeError: no running event loop`.
**Why it happens:** FastAPI SSE generators are `async def`; sync blocking inside them defeats the purpose.
**How to avoid:** Use `AsyncAnthropic` exclusively inside `async def` generators. Module-level `_client = AsyncAnthropic()` is safe — instantiation is sync; only the API calls are async.
**Warning signs:** Event loop appears to hang during beat generation; other requests time out.

### Pitfall 7: outline_beats Table Has No Primary Key — Composite Key Required
**What goes wrong:** `(article_id, beat_number)` must be unique together. A single-column primary key on `id` requires an extra column. Without a PK or unique constraint, duplicate inserts cause silent data corruption.
**Why it happens:** D-06/D-07 tables use `(article_id, beat_number)` as a natural composite key — easy to forget to declare.
**How to avoid:** Declare `Column("article_id", String, primary_key=True)` and `Column("beat_number", Integer, primary_key=True)` for composite PK in SQLAlchemy Core. Use upsert (INSERT OR REPLACE) for idempotent persistence.
**Warning signs:** Two rows with same (article_id, beat_number) appear; last write wins non-deterministically.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sse-starlette for FastAPI SSE | FastAPI native `EventSourceResponse` (fastapi.sse) | FastAPI 0.135.0 (2026-03) | Installed version (0.128.0) predates this — use StreamingResponse |
| @tiptap/core 2.x as latest | @tiptap/core 3.x as latest | TipTap 3.0 release | Always install with `@tiptap/core@2` not `@tiptap/core` |
| Svelte 4 `onMount` | Svelte 5 `onMount` (unchanged) | Svelte 5 GA | `onMount` is still the DOM setup pattern; `$effect` is for reactive state, not one-time DOM init |
| SvelteKit pages adapter | `@sveltejs/adapter-static` for SPA | — | `fallback: '200.html'` required for FastAPI-served SPA |

**Deprecated/outdated:**
- `fastapi.sse.EventSourceResponse`: Available only in FastAPI ≥0.135.0; project has 0.128.0 — do not use.
- `sse-starlette`: Not installed; adds unnecessary dependency; `StreamingResponse` achieves the same result.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `onMount` is correct over `$effect` for TipTap Editor instantiation in Svelte 5 | Pattern 3 (TipTap instantiation) | Editor created multiple times or not at all; mitigated by Wave 0 spike (D-10) |
| A2 | `StaticFiles(html=True)` in FastAPI serves `200.html` as SPA fallback for unmatched paths | Pattern 4 (FastAPI StaticFiles) | Deep-link navigation returns 404; quick to verify in Wave 0 |
| A3 | `AsyncAnthropic` instance is safe to instantiate at module level (no event loop required at construction) | Pattern 5 (Anthropic async streaming) | Import-time error; mitigated by verifying in Wave 0 test |
| A4 | Mounting `StaticFiles` at `/` in FastAPI does not shadow API routes declared before the mount | Pattern 4 (FastAPI StaticFiles) | All API routes return 404 behind StaticFiles; must verify route declaration order |
| A5 | Vite dev server SSE proxy preserves `Transfer-Encoding: chunked` for EventSource connections | Pattern 4 (vite.config.ts proxy) | SSE tokens arrive all at once instead of streamed; Vite typically preserves streaming |

All A1-A5 are mitigated or fully resolved by the Wave 0 spike (D-10) and a Wave 0 smoke test of FastAPI StaticFiles + SSE routes.

---

## Open Questions

1. **SvelteKit `+layout.server.ts` vs fully client-side — prerendering with adapter-static**
   - What we know: `adapter-static` requires routes to be prerenderable (`export const prerender = true`) or have a fallback.
   - What's unclear: If Svelte routes fetch from FastAPI at runtime, they cannot prerender. The SPA fallback (`200.html`) handles this for navigation, but the build step may warn about dynamic routes.
   - Recommendation: Set `export const prerender = true` in root `+layout.ts` and add `export const ssr = false` to disable SSR globally; all data fetching is client-side at runtime.

2. **Token insertion into TipTap during SSE streaming — editor.commands.insertContent() vs direct transaction**
   - What we know: TipTap's `insertContent()` command inserts at cursor position; streaming tokens should append to the active beat's editor, not cursor.
   - What's unclear: Whether appending to a TipTap doc during an active SSE stream requires `editor.commands.insertContentAt({from: endPos, to: endPos}, token)` or a custom transaction.
   - Recommendation: Accumulate tokens in a Svelte store string, set editor content from full accumulated string on `beat_done`, rather than inserting per-token. This avoids ProseMirror transaction overhead per token and simplifies streaming state. Explore per-token insertion only if full-content-on-done is too jarring UX-wise.

3. **outline_beats composite PK upsert — INSERT OR REPLACE vs UPDATE**
   - What we know: SQLAlchemy Core does not have a built-in `UPSERT` for SQLite at the Core level without dialect-specific syntax.
   - What's unclear: Whether to use `INSERT OR REPLACE INTO` (SQLite-specific) or separate SELECT → INSERT/UPDATE logic.
   - Recommendation: Use SQLite-specific `INSERT OR REPLACE` via `text()` or SQLAlchemy's `insert().prefix_with("OR REPLACE")` — acceptable given SQLite is the only supported database.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend build | ✓ | v25.8.1 | — |
| npm | Frontend dependencies | ✓ | 11.11.0 | — |
| Python 3.14 | Backend runtime | ✓ | 3.14.3 | — |
| uv | Package management | ✓ | 0.10.9 | — |
| FastAPI (installed) | SSE StreamingResponse | ✓ | 0.128.0 | — |
| anthropic SDK (installed) | AsyncAnthropic streaming | ✓ | 0.97.0 | — |
| SQLAlchemy (installed) | beats/outline_beats tables | ✓ | ≥2.0 | — |
| @tiptap/core 2.x | Frontend editor | ✗ (not yet installed) | 2.27.2 available | — (must install) |
| @sveltejs/adapter-static | SvelteKit static build | ✗ (not yet installed) | 3.0.10 available | — (must install) |
| lucide-svelte | Frontend icons | ✗ (not yet installed) | 1.0.1 available | — (must install) |
| fastapi.sse.EventSourceResponse | Native FastAPI SSE | ✗ | Requires ≥0.135.0 | Use StreamingResponse (0.128.0) |
| sse-starlette | SSE helper | ✗ | Not installed | Use StreamingResponse |

**Missing dependencies with no fallback:**
- `@tiptap/core@^2.0.0`, `@tiptap/pm@^2.0.0`, `@tiptap/starter-kit@^2.0.0`, `@tiptap/extension-placeholder@^2.0.0`, `lucide-svelte`, `@sveltejs/adapter-static` — all installable via `npm install` in `frontend/`; frontend directory does not yet exist.

**Missing dependencies with fallback:**
- `fastapi.sse` — fallback is `StreamingResponse` (works at 0.128.0, no additional package needed).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `packages/pitlane-studio/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --directory packages/pitlane-studio pytest tests/test_beat_store.py tests/test_pipeline.py tests/test_routes.py -x` |
| Full suite command | `uv run --directory packages/pitlane-studio pytest` |
| Frontend testing | No framework specified — Wave 0 spike test is manual browser/console verification per D-10 |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACT-03 | GET /acts/{year}/{round} returns all 5 acts with labels + data | unit (mock FiveActMapper) | `pytest tests/test_routes.py::test_acts_route -x` | ❌ Wave 0 |
| PTW-01 | generate_outline() returns 5 beat dicts and persists to outline_beats | unit (mock anthropic) | `pytest tests/test_pipeline.py::test_generate_outline -x` | ❌ Wave 0 |
| PTW-02 | stream_beat returns HTTP 409 when article.status != "outline_approved" | unit (real SQLite) | `pytest tests/test_routes.py::test_stream_beat_gate_409 -x` | ❌ Wave 0 |
| PTW-02 | POST /articles/{id}/approve transitions status to outline_approved | unit (real SQLite) | `pytest tests/test_routes.py::test_approve_outline -x` | ❌ Wave 0 |
| PTW-03 | stream_beat generator yields beat_start, token×N, beat_done events | unit (mock AsyncAnthropic) | `pytest tests/test_pipeline.py::test_stream_beat_events -x` | ❌ Wave 0 |
| PTW-03 | SSE events are correctly formatted (data: {...}\n\n) | unit | `pytest tests/test_pipeline.py::test_sse_format -x` | ❌ Wave 0 |
| PTW-04 | Each generated beat prose contains placeholder markers for quote, context, causal | unit (mock LLM response) | `pytest tests/test_pipeline.py::test_placeholder_detection -x` | ❌ Wave 0 |
| PTW-04 | beat_done event includes placeholder_markers list | unit | `pytest tests/test_pipeline.py::test_beat_done_payload -x` | ❌ Wave 0 |
| UI-01 | GET /articles/{id}/angles returns 4–6 AngleCandidate dicts | integration (mock data gate) | `pytest tests/test_routes.py::test_angles_route -x` | ❌ Wave 0 |
| UI-03 | PATCH /articles/{id}/outline persists beat edits to outline_beats | unit (real SQLite) | `pytest tests/test_routes.py::test_patch_outline -x` | ❌ Wave 0 |
| XPRT-01 | Markdown export — placeholderQuote node serializes as [JOURNALIST: quote] | unit (JS/manual spike) | Manual: browser console — export function test | manual |
| D-06 | beat_store.save_beat() persists prose to beats table; upsert on re-run | unit (real SQLite) | `pytest tests/test_beat_store.py::test_save_beat -x` | ❌ Wave 0 |
| D-07 | beat_store.save_outline_beats() persists outline_beats; idempotent upsert | unit (real SQLite) | `pytest tests/test_beat_store.py::test_save_outline_beats -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run --directory packages/pitlane-studio pytest tests/test_beat_store.py tests/test_pipeline.py tests/test_routes.py -x`
- **Per wave merge:** `uv run --directory packages/pitlane-studio pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_beat_store.py` — covers D-06, D-07 (outline_beats + beats table CRUD + upsert)
- [ ] `tests/test_pipeline.py` — covers PTW-01, PTW-02, PTW-03, PTW-04 (PipelineOrchestrator with mocked anthropic)
- [ ] `tests/test_routes.py` — covers ACT-03, UI-01, UI-03, PTW-02 gate (FastAPI TestClient routes)
- [ ] `src/pitlane_studio/store/beat_store.py` — BeatStore class (outline_beats + beats tables)
- [ ] `src/pitlane_studio/services/pipeline.py` — PipelineOrchestrator skeleton
- [ ] `src/pitlane_studio/routers/` — router module directory
- [ ] `frontend/` — SvelteKit app directory + TipTap spike file per D-10

*(Frontend spike: manual browser verification. All Python tests: automated with pytest.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Personal tool; no auth |
| V3 Session Management | no | Personal tool; no sessions |
| V4 Access Control | no | Single user; no multi-tenancy |
| V5 Input Validation | yes | Pydantic BaseModel for all API request bodies; beat prompt content from LLM (trusted source) |
| V6 Cryptography | no | No secrets stored; SQLite has no encrypted content |
| V10 Malicious Code / Injection | yes | XSS: LLM-generated prose rendered in TipTap — TipTap sanitizes via ProseMirror schema by default; prose also sanitized through `safe_html` filter if ever rendered in Jinja2 templates |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection in beat prose rendered as HTML | Tampering | TipTap renders via ProseMirror schema (whitelist); custom nodes are atom (not raw HTML); `safe_html` filter on any Jinja2 `\| safe` path |
| SSE endpoint invoked before outline approval | Elevation of privilege | FastAPI route handler raises HTTP 409 before generator starts; ArticleStore status check in gate |
| SQLite injection via article_id | Tampering | SQLAlchemy Core parameterized queries (never string concatenation); `articles_table.select().where(table.c.id == article_id)` |
| Unbounded SSE stream (LLM never finishes) | DoS | `max_tokens=1024` cap on each beat generation call; FastAPI client disconnect closes generator |

---

## Project Constraints (from CLAUDE.md)

| Directive | Category | Impact on Phase 3 |
|-----------|----------|-------------------|
| `uv` only — never `pip` directly | Package manager | All Python deps added via `uv add --directory packages/pitlane-studio <dep>` |
| All imports at top of file — no lazy imports | Code style | PipelineOrchestrator, beat_store, routers: all imports at module top |
| SQLAlchemy Core only — no ORM/Session | Architecture | beats + outline_beats tables use Table/Column/MetaData exactly as article_store.py |
| Direct Python imports, never subprocess | Architecture | PipelineOrchestrator imports from `pitlane_agent.commands.*` and `pitlane_elo.studio_api` |
| `bleach.clean()` on any Jinja2 `\| safe` output | Security | Phase 3 primarily serves JSON via FastAPI — no Jinja2 templates for prose; apply if templates added |
| `claude-agent-sdk<0.2.0` pin | Dependency | Unchanged; Phase 3 uses `anthropic` SDK directly (consistent with Phase 2 angles.py) |
| Tests in `packages/pitlane-studio/tests/` | Testing | All new tests follow existing conftest.py + tmp_db_path pattern |
| Cross-package integration test must use real data | Testing | Existing; Phase 3 does not add new cross-package integration tests (pipeline uses mocks for unit tests) |
| Run tests: `uv run --directory packages/<name> pytest` | Testing | Phase 3 test command: `uv run --directory packages/pitlane-studio pytest` |
| `anthropic` SDK (not claude-agent-sdk) for LLM calls | Architecture | PipelineOrchestrator uses `AsyncAnthropic` from `anthropic` package — consistent with angles.py |

---

## Sources

### Primary (HIGH confidence)

- `/ueberdosis/tiptap-docs` (Context7) — custom inline atom node pattern, getJSON serialization, Node.create() API
- `/sveltejs/svelte` (Context7) — onMount lifecycle hook, Svelte 5 patterns
- `/sveltejs/kit` (Context7) — adapter-static configuration, svelte.config.js
- `/vitejs/vite` (Context7) — server.proxy configuration for dev
- `/fastapi/fastapi` (Context7) — StaticFiles mounting
- `/anthropics/anthropic-sdk-python` (Context7) — AsyncAnthropic streaming, text_stream iteration
- FastAPI 0.128.0 source — StreamingResponse + `media_type="text/event-stream"` (verified locally)
- Anthropic SDK 0.97.0 source — verified locally installed
- `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` — SQLAlchemy Core pattern to follow
- `packages/pitlane-studio/src/pitlane_studio/services/angles.py` — Anthropic SDK usage pattern
- npm registry (2026-05-05) — all package versions verified via `npm view <package> version`

### Secondary (MEDIUM confidence)

- FastAPI SSE tutorial page (fastapi.tiangolo.com) — StreamingResponse SSE format, cancellation notes
- TipTap official docs (tiptap.dev) — custom extensions overview, atom node behavior
- SvelteKit docs (svelte.dev) — vite proxy configuration FAQ

### Tertiary (LOW confidence)

- WebSearch: "FastAPI EventSourceResponse SSE version introduced" — confirmed fastapi.sse introduced in 0.135.0; project has 0.128.0

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via npm registry and local install
- Backend patterns (SSE, Anthropic streaming): HIGH — verified via Context7 docs + local package inspection
- SQLAlchemy Core tables: HIGH — pattern directly from existing article_store.py
- TipTap custom nodes: HIGH — verified via Context7 official TipTap docs
- Svelte 5 onMount: HIGH — verified via Context7 official Svelte docs
- TipTap + Svelte 5 integration (instantiation, getJSON, streaming token insertion): MEDIUM — spike required per D-10
- FastAPI StaticFiles SPA fallback behavior: MEDIUM — documented but not smoke-tested

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (stable ecosystem — TipTap 2.x, Svelte 5, FastAPI 0.128.0 are all stable releases)
