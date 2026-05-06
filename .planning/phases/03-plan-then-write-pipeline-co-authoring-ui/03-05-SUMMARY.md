---
plan: 03-05
phase: 03-plan-then-write-pipeline-co-authoring-ui
status: complete
completed_at: 2026-05-05
---

# 03-05 Summary — SvelteKit Stage 1 + Stage 2 UI

## What was built

**Task 1: store.ts and api.ts**
- `packages/pitlane-studio/frontend/src/lib/store.ts` — Svelte writable stores for `stage`, `selectedYear`, `selectedRound`, `articleId`, `angles`, `selectedAngleId`, `anglesLoading`, `anglesError`, `outlineBeats`, `outlineGenerating`, `approvalPending`, `beatProseStates`, `actSidebarData`. TypeScript interfaces: `AngleCandidate`, `OutlineBeat`, `BeatProseState`, `ActData`.
- `packages/pitlane-studio/frontend/src/lib/api.ts` — Typed fetch wrappers: `getYears()`, `getRounds()`, `createArticle()`, `getAngles()`, `generateOutline()`, `patchOutline()`, `approveOutline()`, `getActs()`, `openBeatStream()` (EventSource).

**Task 2: Components + App Shell**
- `packages/pitlane-studio/frontend/src/lib/components/RaceSelector.svelte` — Year + Round `<select>` dropdowns, `onMount` for year fetch, async round loading with loading/error states.
- `packages/pitlane-studio/frontend/src/lib/components/AngleCard.svelte` — Signal type chip, angle name (20px/600), confidence badge (HIGH/MED/LOW with exact UI-SPEC colors), 3-line clamped data rationale, selected state with `#e10600` border + box-shadow.
- `packages/pitlane-studio/frontend/src/lib/components/OutlinePanel.svelte` — Beat rows with title input + data anchors textarea, up/down reorder arrows, inline delete confirmation ("Remove this beat? [Remove Beat] [Keep It]"), Add Beat (disabled at 8), gate warning, "Approve Outline and Generate Prose" button (48px height, full-width, `#e10600`).
- `packages/pitlane-studio/frontend/src/routes/+page.svelte` — Three-column app shell: 48px header (wordmark + RaceSelector + Copy Markdown button), 280px left panel (hidden Stage 1, outline nav Stage 2+), fluid main content (Stage 1 angle grid / Stage 2 OutlinePanel / Stage 3 placeholder), 260px right sidebar (Five Acts stub).

## Key decisions / deviations
- Right sidebar in 03-05 is an inline stub ("Five Acts" with ACT_LABELS and actSidebarData from store); full `FiveActSidebar.svelte` component deferred to 03-06.
- Stage 3 renders a placeholder div "Beat editor loading..." — wired in 03-06.
- Copy Markdown button in header wired to inline `copyMarkdown()` using `get(outlineBeats)` for Stage 2 markdown; upgraded to TipTap JSON traversal in 03-06.

## Artifacts delivered
- `packages/pitlane-studio/frontend/src/lib/store.ts`
- `packages/pitlane-studio/frontend/src/lib/api.ts`
- `packages/pitlane-studio/frontend/src/lib/components/RaceSelector.svelte`
- `packages/pitlane-studio/frontend/src/lib/components/AngleCard.svelte`
- `packages/pitlane-studio/frontend/src/lib/components/OutlinePanel.svelte`
- `packages/pitlane-studio/frontend/src/routes/+page.svelte`
- Static build output in `packages/pitlane-studio/src/pitlane_studio/static/` (200.html + index.html + _app/)

## Issues encountered
- `"type": "module"` missing in package.json caused Vite 8 ESM error — added.
- `prerender: { handleHttpError: 'ignore' }` added to suppress favicon 404 during SvelteKit prerender.
- `frontend/.gitignore` created to prevent `node_modules/` and `.svelte-kit/` from being committed.
- Root `.gitignore` `lib/` pattern (unanchored) was blocking `frontend/src/lib/` — fixed to `/lib/` (anchored to repo root).
- CWD drift after `cd frontend && npm` calls caused git commands to fail — fixed with absolute path prefix on all git commands.
- Invalid Svelte prop syntax `{articleId: $articleId ?? ''}` — corrected to `articleId={$articleId ?? ''}`.

## Test status
59 tests passed, 2 expected skips (live-data integration tests). No regressions.
