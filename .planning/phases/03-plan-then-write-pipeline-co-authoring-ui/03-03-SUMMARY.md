---
plan: 03-03
phase: 03-plan-then-write-pipeline-co-authoring-ui
status: checkpoint
completed: 2026-05-05
---

# 03-03: TipTap 2.x SvelteKit Spike — Summary

## What Was Built

- `packages/pitlane-studio/frontend/` — full SvelteKit static-output scaffold
- `package.json` — TipTap 2.27.2 (`@tiptap/core: "^2.0.0"`, `@tiptap/starter-kit`, `@tiptap/pm`, `@tiptap/extension-placeholder`), Svelte 5.55.5, SvelteKit 2.59.1, Vite 8.0.10, lucide-svelte
- `svelte.config.js` — adapter-static outputting to `../src/pitlane_studio/static/` with `200.html` SPA fallback; `handleHttpError: 'ignore'`
- `vite.config.ts` — dev proxy to FastAPI on port 8001 for `/articles`, `/acts`, `/races`
- `src/routes/+layout.ts` — `prerender = true`, `ssr = false`
- `src/lib/extensions/placeholder-nodes.ts` — `PlaceholderQuote`, `PlaceholderContext`, `PlaceholderCausal` — all `atom: true`, `inline: true`, styled inline-block chips
- `src/lib/components/BeatEditorSpike.svelte` — `onMount` TipTap instantiation; getJSON round-trip validation for all three node types; displays SPIKE PASS/FAIL result
- `src/routes/+page.svelte` — spike entry point
- Build output: `packages/pitlane-studio/src/pitlane_studio/static/` — `200.html`, `index.html`, `_app/`

## Self-Check

- [x] TipTap 2.27.2 installed (confirmed: `node -e "..."` → `2.27.2`)
- [x] `PlaceholderQuote`, `PlaceholderContext`, `PlaceholderCausal` defined with `atom: true`, `inline: true`
- [x] `BeatEditorSpike.svelte` uses `onMount` (not `$effect`) for editor init
- [x] `npm run build` exits 0 — output at `static/200.html`, `static/index.html`
- [x] `"type": "module"` in package.json (required for ESM-only SvelteKit/Vite)
- [x] `.gitignore` added — `node_modules/` and `.svelte-kit/` excluded from tracking
- [x] Python test suite: 50 passed, 2 skipped, 10 xfailed — no regressions

## Deviations

- Added `"type": "module"` to `package.json` — required by SvelteKit/Vite 8 (ESM-only); not in original plan spec but mandatory for the build to succeed
- Added `prerender.handleHttpError: 'ignore'` to `svelte.config.js` — prerender crawler hit `/favicon.png` 404; this is a cosmetic asset, not a functional route; ignoring is correct for a personal dev tool
- Added `frontend/static/favicon.png` placeholder — SvelteKit adapter-static requires it for the prerender step

## Checkpoint Status

**Awaiting human browser verification.** Run the dev server to test:

```bash
cd packages/pitlane-studio/frontend && npm run dev
```

Then open: http://localhost:5173/

Verify:
1. "Spike Result" box shows green "SPIKE PASS: All three placeholder node types round-trip through getJSON()"
2. TipTap editor shows three inline placeholder chips (green quote, blue context, yellow causal)
3. JSON output shows `"type": "placeholderQuote"`, `"type": "placeholderContext"`, `"type": "placeholderCausal"`
4. Browser console shows no errors
5. Clicking inside placeholder nodes does NOT allow typing (atom node behavior)

Type "spike passed" to confirm and advance to Wave 1.

## key-files

created:
  - packages/pitlane-studio/frontend/package.json
  - packages/pitlane-studio/frontend/svelte.config.js
  - packages/pitlane-studio/frontend/vite.config.ts
  - packages/pitlane-studio/frontend/src/app.html
  - packages/pitlane-studio/frontend/src/routes/+layout.ts
  - packages/pitlane-studio/frontend/src/routes/+page.svelte
  - packages/pitlane-studio/frontend/src/lib/extensions/placeholder-nodes.ts
  - packages/pitlane-studio/frontend/src/lib/components/BeatEditorSpike.svelte
  - packages/pitlane-studio/frontend/static/favicon.png
  - packages/pitlane-studio/src/pitlane_studio/static/200.html
  - packages/pitlane-studio/src/pitlane_studio/static/index.html
