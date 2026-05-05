# Phase 3: Discussion Log

**Date:** 2026-05-05
**Areas discussed:** SSE Streaming & Approval Gate API, Frontend Serving & Dev Workflow

---

## Area 1: SSE Streaming & Approval Gate API

### Q: One SSE connection for all 5 beats vs. 5 separate SSE requests?
**User:** Neither fixed — wants flexibility beyond 5 acts. Journalist should be able to define custom beat structure, with 5 acts as the default starting point.
**Resolution:** One SSE request per beat (N requests for N approved beats), made sequentially by the frontend. Variable beat count supported.

### Q: Auto-advance through all beats, or manual trigger per beat?
**User:** Auto-advance (recommended).
**Resolution:** Frontend auto-advances through all beats after outline approval. No per-beat manual trigger.

### Q: Backend enforcement of approval gate?
**User:** Backend enforces via ArticleStore state (recommended).
**Resolution:** `/stream` endpoints return HTTP 409 if `article.status != "outline_approved"`. Existing state machine transition is the mechanism.

### Q: Where does beat prose persist?
**User:** Persist to SQLite as each beat completes (recommended).
**Resolution:** New `beats` table in `articles.db`. Written on `beat_done` SSE event. New `outline_beats` table for the outline itself.

---

## Area 2: Frontend Serving & Dev Workflow

### Q: SvelteKit static build served by FastAPI vs. separate dev server?
**User:** Static build served by FastAPI (recommended).
**Resolution:** `packages/pitlane-studio/frontend/` → build → `packages/pitlane-studio/src/pitlane_studio/static/`. FastAPI mounts StaticFiles at `/`. Port 8001, single process.

### Q: How to handle TipTap + Svelte 5 MEDIUM confidence risk?
**User:** Research first — spike plan before full implementation (recommended).
**Resolution:** Wave 0 of Phase 3 includes a TipTap + Svelte 5 spike (onMount pattern, getJSON(), custom node) before the full editor wave.

### Q: Where does the SvelteKit app live?
**User:** `packages/pitlane-studio/frontend/` (recommended).
**Resolution:** Co-located with the Python package. Build output to `../src/pitlane_studio/static/`.

---

## Claude's Discretion (not discussed by user)

- Placeholder hook representation in TipTap — Claude picks approach
- Race selector UX details — Claude picks simple functional approach
- SSE event payload schema — Claude specifies
- FastAPI router organization — Claude follows existing `app.py` pattern

---

## Deferred Ideas

- Substack API export (XPRT-02, XPRT-03) — v2
- Draggable beat reordering (CM-02) — v2
- Draft list / resume (CM-01) — v2
- Audience framing (WE-01), character arcs (WE-02), chart pairing (WE-03) — v2
