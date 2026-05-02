# Technology Stack — PitLane Studio

**Project:** pitlane-studio (co-authoring interface, new package in existing uv monorepo)
**Researched:** 2026-05-02
**Overall confidence:** MEDIUM
**Note on tooling:** External search tools (WebSearch, WebFetch, Bash/Context7 CLI) were denied in this research session. Substack API findings are LOW confidence from training data (cutoff August 2025); all other recommendations are MEDIUM–HIGH, grounded in the verified codebase files read at session start.

---

## Context: What the Existing Stack Constrains

From `.planning/codebase/STACK.md` and `.planning/codebase/ARCHITECTURE.md`:

- Python 3.12–3.14, uv monorepo, hatchling build backend — new package must follow this exactly
- FastAPI + uvicorn + Jinja2 is the established web pattern (pitlane-web)
- No Node.js build pipeline exists anywhere in the repo
- SSE streaming is already in use; async FastAPI is idiomatic here
- No auth; single-user personal tool
- DuckDB + Parquet for data; workspace filesystem (`~/.pitlane/workspaces/<uuid>/`) for session state
- ruff for linting; conventional commits enforced by pre-commit hook

---

## Recommended Stack

### Backend (Python / FastAPI)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `fastapi` | >=0.128.0 | HTTP API for studio routes | Already in monorepo; proven pattern from pitlane-web; async-native |
| `uvicorn[standard]` | >=0.40.0 | ASGI server | Already in monorepo |
| `jinja2` | >=3.1 | SSR shell page only (not editor UI) | Already in monorepo; delivers the HTML document that boots the SPA |
| `httpx` | >=0.27 | Substack API calls (async HTTP client) | FastAPI ecosystem standard; async-native; already a transitive dep in many fastapi installs |
| `python-multipart` | >=0.0.9 | Form body parsing | Already in monorepo |
| `pydantic` | >=2.0 | Request/response models for studio API | FastAPI 0.115+ requires Pydantic v2; already present as FastAPI dep |

Do NOT add: `requests` (sync, incompatible with async FastAPI routes without `run_in_executor`), `aiohttp` (redundant with `httpx`).

### Frontend — Recommendation: SvelteKit (SPA mode, static output) served by FastAPI

**Decision:** Use a lightweight SPA (Svelte 5 + SvelteKit in SPA/static mode), NOT Jinja2 + HTMX.

**Rationale:**

The structured editor requirement is the deciding factor. The UI needs:
1. Story angle cards with selection state that persists across view changes
2. A beat-by-beat prose editor with inline placeholder blocks (non-textarea content regions)
3. A five-act timeline with drag-to-reorder beats
4. Bidirectional state: approving an outline triggers AI prose generation per beat; each beat has an accept/edit/regenerate cycle

HTMX handles server-driven partial HTML swaps well — it's excellent for forms, tables, chat streams. It is structurally wrong for a document editor with:
- Client-side drag-and-drop ordering
- Inline block placeholder components with local editing state
- Per-beat regeneration that must not disturb adjacent beats' state

Implementing any of that in HTMX requires either Alpine.js bolted on for state (at which point you've built a worse React) or a tangle of `hx-swap-oob` + `_hyperscript` that becomes unmaintainable. The pitlane-web SSE chat interface works perfectly with HTMX *because* it's a linear append — studio is fundamentally different.

**Why Svelte over React or Vue:**

| Criterion | Svelte 5 | React 19 | Vue 3 |
|-----------|----------|----------|-------|
| Bundle size (no vdom runtime) | Smallest | Largest | Medium |
| No Node.js server needed | Yes (static build) | Yes | Yes |
| Integration with FastAPI | Static files served by FastAPI | Same | Same |
| Drag-and-drop ecosystem | `svelte-dnd-action` | `dnd-kit` | `vue-draggable` |
| Prose editor integration | TipTap works | TipTap works | TipTap works |
| Complexity for single-user tool | Low — no framework overhead | Medium | Medium |
| Learning curve relative to codebase | No existing JS — start fresh either way | Heavier | Medium |

Svelte 5 produces the smallest runtime (critical for a personal tool with no CDN optimization), has the simplest state model (runes vs. hooks/ref), and SvelteKit's static adapter outputs plain HTML/JS/CSS that FastAPI serves as `StaticFiles`. There is no Node.js server in production.

**Integration with FastAPI:** Build the Svelte app to `packages/pitlane-studio/src/pitlane_studio/static/` and mount with `app.mount("/studio", StaticFiles(directory="static", html=True))`. The FastAPI backend is the only server process. This keeps the monorepo pattern: one `uvicorn` process, all routes under one server.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Svelte | 5.x | Reactive UI framework | Smallest bundle; simplest state model; no vdom |
| SvelteKit | 2.x | App structure + static adapter | Static build output; no separate Node server |
| `@sveltejs/adapter-static` | latest | Produce static HTML/JS/CSS | FastAPI serves the output directly |
| Vite | 6.x | Build tool (bundled with SvelteKit) | Fast dev server; tree-shaking; no Webpack |
| TipTap | 2.x | Structured prose editor | ProseMirror-based; has placeholder extension; block-based; actively maintained; works in Svelte |
| `svelte-dnd-action` | latest | Drag-and-drop timeline beats | Purpose-built for Svelte; accessibility-aware |

**TipTap vs. alternatives for the structured editor:**

TipTap (built on ProseMirror) is the correct choice because:
- It has a first-party `Placeholder` extension that renders placeholder text in empty nodes
- Its `Node` extension model lets you define custom beat block types (e.g. `BeatBlock`, `QuoteHook`, `ContextHook`) with schema-enforced structure
- The `@tiptap/extension-placeholder` extension handles inline placeholder text without custom DOM manipulation
- It works in any framework via its headless core — Svelte integration is straightforward (mount via `onMount` / `useEffect` equivalent)
- Editor.js and Quill are alternatives but have weaker schema enforcement and smaller extension ecosystems

**Do NOT use:** BlockNote (opinionated UI; hard to customize schema), Lexical (Facebook; React-first; Svelte integration is experimental), Slate.js (unmaintained periods; complex state model for this use case).

**Build toolchain note:** Adding Svelte requires a `package.json` at the monorepo root or inside `packages/pitlane-studio/`. This is a Node.js dev-only dependency — it does NOT conflict with uv. The Python package is `pitlane-studio`; the frontend build is a dev step that outputs static files committed to (or built into) the package. Precedent: many Python monorepos have a `frontend/` or per-package `ui/` directory with its own `package.json`. The static output is what gets served; Node is never in the production path.

---

### Substack Unofficial API

**Confidence: LOW** — verified against training data only; no live endpoint verification possible in this session. Treat as hypothesis requiring validation before Phase implementation.

**What exists:**

Substack does not publish an official API (as of August 2025). The "unofficial API" is the same HTTP API the Substack web app uses, reverse-engineered from browser network traffic. It is cookie-authenticated (session cookies from a logged-in browser session) and undocumented.

**Known working endpoints (training data, LOW confidence):**

| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `https://<publication>.substack.com/api/v1/drafts` | POST | Create a new draft | Body: `{"draft_title": "...", "draft_subtitle": "...", "draft_body": "<tiptap-json>"}` |
| `https://<publication>.substack.com/api/v1/drafts/<id>` | PUT | Update existing draft | Same body shape |
| `https://<publication>.substack.com/api/v1/posts` | GET | List published posts | Pagination via `offset` param |
| `https://<publication>.substack.com/api/v1/drafts` | GET | List drafts | |

**Authentication mechanism:**

Substack uses cookie-based auth. The relevant cookies are `substack.sid` and `substack.sid.sig` (set after login). There is no API key system. To authenticate programmatically: log in via browser, export the session cookies, pass them as a `Cookie` header on all API requests. This is fragile — cookies expire and require re-login.

**Python options:**

No well-maintained, widely-adopted Python Substack API client library exists as of August 2025. The options are:

1. **Roll your own with `httpx`** (RECOMMENDED): 30–50 lines of Python using `httpx.AsyncClient` with a cookie jar loaded from a file. This is what most open-source Substack scrapers do. Full control, no external dependency, no maintenance risk from a third-party wrapper going stale.

2. **`substack-api` (PyPI, various authors)**: Multiple packages with this name exist on PyPI with low download counts, inconsistent maintenance, and varying quality. None are authoritative. Do not depend on one without validating it's alive.

3. **Playwright/Selenium browser automation**: Reliable (the real browser auth flow), but heavy (headless Chromium is a 150MB+ install) and slow. Not appropriate for an export action in a writing tool.

**Body format — critical detail:**

Substack stores post body content as its own variant of ProseMirror JSON (the same format TipTap uses internally). If the frontend uses TipTap, the editor's `getJSON()` output can be sent to the Substack draft API with minimal transformation. This is the strongest technical reason to choose TipTap as the editor: it produces the same document format Substack ingests.

**Known fragility:**

- Cookie expiry requires periodic re-authentication; no refresh token flow
- Endpoint paths and request body schema can change without notice (Substack has done this)
- Rate limits are unadvertised; aggressive use risks temporary IP blocks
- The `draft_body` schema has undocumented required fields (e.g., node type names) that can silently break formatting

**Markdown fallback (required per PROJECT.md):**

When the API is unavailable or cookies have expired, the tool must fall back to producing a markdown file the journalist can paste into the Substack editor manually. Substack's editor accepts pasted markdown with reasonable fidelity. Use Python's `markdown` library (already in monorepo as `markdown >=3.5`) to render, or a TipTap-to-markdown serializer on the frontend side (TipTap has `@tiptap/extension-markdown` for this).

**Implementation recommendation:**

Build a `SubstackExporter` class in `packages/pitlane-studio/src/pitlane_studio/export/substack.py`:
- Constructor accepts `publication_slug` and a path to a cookie file (JSON, exported from browser)
- `async def create_draft(title, tiptap_json) -> str` — returns draft URL
- `async def update_draft(draft_id, tiptap_json) -> None`
- Falls back to writing a `.md` file to workspace if `SubstackAuthError` is raised
- Cookie file path configurable via `PITLANE_SUBSTACK_COOKIE_FILE` env var

---

### Supporting Libraries (Python, new for pitlane-studio)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `httpx` | >=0.27 | Async HTTP for Substack API calls | Transitive dep of many packages; likely already present; add explicitly |
| `python-slugify` | >=8.0 | Generate workspace filenames from article titles | Small, zero-dep utility |

No new database dependencies. pitlane-studio uses the same DuckDB + Parquet pattern as other packages, accessed by importing `pitlane-elo` and `pitlane-agent` directly.

---

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| HTMX | Correct for chat/forms; wrong for document editor with drag-and-drop, per-block state, and inline placeholder components |
| Alpine.js | Would be needed to paper over HTMX gaps; adds complexity without solving the core editor problem |
| Next.js / Nuxt | React/Vue full-stack frameworks require their own server; conflicts with FastAPI-as-sole-server pattern |
| React | Heavier bundle than Svelte; React 19 server components pattern doesn't fit FastAPI backend; no existing JS ecosystem in repo to leverage |
| Editor.js | Block-based but weaker schema enforcement; smaller extension ecosystem than TipTap |
| Quill | Effectively unmaintained (last major release 2019-era); Delta format doesn't match Substack's ProseMirror JSON |
| BlockNote | Opinionated UI shell; hard to match F1 journalism design; wraps TipTap anyway |
| Celery / Redis | No background job queue needed; story generation is request-response via SSE, same pattern as pitlane-web |
| SQLite (new) | DuckDB already serves structured data; don't introduce a second embedded DB |
| `requests` | Sync; blocks the FastAPI event loop; use `httpx` instead |

---

## Package Structure

Following the pitlane-web pattern exactly:

```
packages/pitlane-studio/
  pyproject.toml                  # hatchling backend, requires pitlane-agent, pitlane-elo
  src/
    pitlane_studio/
      __init__.py
      app.py                      # FastAPI app, mounts static/, registers routers
      cli.py                      # click entry point: pitlane-studio serve
      config.py                   # env var constants (PITLANE_STUDIO_*)
      routers/
        angles.py                 # /api/studio/angles — story angle detection
        timeline.py               # /api/studio/timeline — five-act beat CRUD
        drafts.py                 # /api/studio/drafts — prose generation per beat
        export.py                 # /api/studio/export — Substack + markdown
      export/
        substack.py               # SubstackExporter class
        markdown.py               # TipTap JSON → markdown serializer
      static/                     # built Svelte app output (gitignored or committed)
      templates/
        studio.html               # shell Jinja2 page that boots the SPA
  ui/                             # Svelte source (dev-only, Node toolchain)
    package.json
    vite.config.js
    src/
      app/
        components/
          AngleCard.svelte
          BeatEditor.svelte        # TipTap instance per beat
          Timeline.svelte          # svelte-dnd-action list
          ExportPanel.svelte
```

Entry point registered in `pyproject.toml`:
```
[project.scripts]
pitlane-studio = "pitlane_studio.cli:main"
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Frontend framework | Svelte 5 + SvelteKit | React 19 | Heavier runtime; no existing React in repo; no benefit for single-user tool |
| Frontend framework | Svelte 5 + SvelteKit | HTMX + Alpine | Wrong interaction model for document editor; drag-and-drop requires client-side state |
| Prose editor | TipTap 2.x | Editor.js | Weaker schema; ProseMirror JSON alignment with Substack is TipTap's unique advantage |
| Prose editor | TipTap 2.x | Lexical | React-first; Svelte integration is experimental |
| Substack client | Custom `httpx` | PyPI `substack-api` | No authoritative Python Substack library; rolling own is 50 lines and has no maintenance risk |
| HTTP client | `httpx` | `aiohttp` | `httpx` is the FastAPI ecosystem standard; cleaner API; both are fine but don't need two |

---

## Installation

Python side (added to `packages/pitlane-studio/pyproject.toml`):
```toml
[project]
name = "pitlane-studio"
requires-python = ">=3.12,<3.15"
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.40.0",
    "jinja2>=3.1",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
    "python-slugify>=8.0",
    "pitlane-agent",
    "pitlane-elo",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Node.js side (packages/pitlane-studio/ui/package.json — dev only):
```json
{
  "devDependencies": {
    "@sveltejs/kit": "^2.0.0",
    "@sveltejs/adapter-static": "^3.0.0",
    "svelte": "^5.0.0",
    "vite": "^6.0.0"
  },
  "dependencies": {
    "@tiptap/core": "^2.0.0",
    "@tiptap/starter-kit": "^2.0.0",
    "@tiptap/extension-placeholder": "^2.0.0",
    "svelte-dnd-action": "^0.9.0"
  }
}
```

---

## Substack Unofficial API — Validation Required

Before building the export feature, validate these endpoints against a live Substack publication:

1. POST `https://<pub>.substack.com/api/v1/drafts` with exported session cookies
2. Confirm `draft_body` field accepts TipTap JSON directly or requires transformation
3. Confirm whether `Content-Type: application/json` with Bearer token in Authorization header works vs. cookie-only auth
4. Test draft creation → check Substack editor renders the content correctly
5. Document which cookie names are required (`substack.sid`, `substack.sid.sig`, potentially `__cf_bm`)

This validation should happen in Phase 1 of studio development, before any UI work, to establish whether the API path is viable or the markdown fallback becomes primary.

---

## Configuration (new env vars for pitlane-studio)

| Variable | Default | Purpose |
|----------|---------|---------|
| `PITLANE_STUDIO_HOST` | `127.0.0.1` | Bind address for studio server |
| `PITLANE_STUDIO_PORT` | `8001` | Port (avoids collision with pitlane-web on 8000) |
| `PITLANE_SUBSTACK_COOKIE_FILE` | `~/.pitlane/substack_cookies.json` | Path to exported Substack session cookies |
| `PITLANE_SUBSTACK_PUBLICATION` | required for export | Substack publication slug (e.g. `mypub`) |

---

## Sources

- Codebase context: `.planning/codebase/STACK.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/INTEGRATIONS.md` (HIGH confidence — verified from source files)
- PROJECT.md requirements: `.planning/PROJECT.md` (HIGH confidence — verified from source file)
- TipTap documentation: training knowledge of TipTap 2.x ProseMirror JSON format and extension model (MEDIUM confidence — last verified August 2025; check tiptap.dev for current extension names)
- Substack unofficial API: training knowledge from reverse-engineering reports and community blog posts (LOW confidence — requires live validation; endpoint paths and body schema change without notice)
- SvelteKit static adapter: training knowledge (MEDIUM confidence — stable feature since SvelteKit 1.x)
- `svelte-dnd-action`: training knowledge (MEDIUM confidence — actively maintained as of August 2025)

---

*Stack research: 2026-05-02*
