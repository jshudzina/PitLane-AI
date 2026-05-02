# Feature Landscape

**Domain:** F1 sports co-authoring / structured narrative journalism tool
**Researched:** 2026-05-02
**Note on sources:** External research tools (WebSearch, WebFetch) were unavailable during this session. Analysis draws on training knowledge through August 2025 of comparable tools (Wordsmith/Automated Insights, Statsperform Opta Stories, Lex, Jasper, Notion, Craft, Coda) plus deep reading of the project's own design documents (PROJECT.md, F1_ELO_Story_Detection_System_Design.md). Confidence levels are noted per section.

---

## Table Stakes

Features the writer expects to just work. Missing any of these makes the tool feel unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Story angle surface on race load** | The whole value prop is "not a blank page" — if angle cards don't appear immediately after selecting a race, the tool feels broken | Medium | Requires story detection pipeline already in place (it is) |
| **Named narrative frames, not raw stats** | Wölker & Powell (2018): readers and journalists respond to labeled archetypes, not ELO numbers. Comparable tools (Wordsmith) surface "narrative templates," not data dumps | Low (framing) / Medium (detection) | e.g. "Strategic Gamble That Backfired," not "Lap delta = +0.4s" |
| **Outline approval gate before prose** | Wang et al. (2025): plan-then-write consistently outperforms streaming full text. Writers who've used any AI writing tool have been burned by receiving 1500 words of prose in the wrong direction | Low (UI gate) / Medium (pipeline) | Must be a hard gate — prose generation blocked until outline is confirmed |
| **Beat-by-beat prose editor** | If the writer approved an outline with 8 beats, they expect to see 8 prose segments, not one wall of text. Notion/Craft-style block editing is the expectation set by comparable tools | Medium | Block-per-beat model; each beat independently revisable |
| **Placeholder hooks for human-only content** | Wölker & Powell: credibility comes from context, causality, quotes — things the journalist provides. Without explicit "INSERT QUOTE HERE" placeholders, prose reads as complete but hollow | Low | Structured, visually distinct slots; not optional hints |
| **Substack export** | Publishing destination is Substack; copy-pasting unstructured markdown into Substack is the current workflow and it is painful | Medium (unofficial API) / Low (markdown fallback) | Unofficial API first; markdown fallback required per PROJECT.md |
| **Race selector / session picker** | Writer needs to choose which race to write about; this is the entry point | Low | Already have FastF1 session data; dropdown or card grid |
| **Persistent draft state** | Workspace must survive a browser refresh; writers lose trust fast if work disappears | Low | Workspace management already exists at `~/.pitlane/workspaces/<uuid>/` |
| **Copy to clipboard at any stage** | Minimum viable escape hatch at outline stage, beat stage, or full article stage | Very Low | Every text surface needs a copy button |
| **Five-act timeline visibility** | Writer needs to see which phase of the race each beat maps to (qualifying, lap-1, pit window, final stint, implications). Comparable structured editors (Coda, Craft) show document structure at all times | Low (UI) | Sidebar or header showing current act context |

---

## Differentiators

Features that make PitLane Studio distinctly useful vs. a generic AI writer. Not baseline expectations — these are reasons to use this tool instead of ChatGPT.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **ELO-grounded angle cards** | Every story angle is anchored to a specific quantified signal (SurpriseScore, ΔR̂, Teammate ΔR̂ crossing). A generic AI writer makes up "Verstappen dominated" — this tool shows the ELO trajectory proving it | High (already built in signals.py) | The endure-Elo SurpriseScore, streak detection, car/driver decoupling are all implemented; surfacing them in angle cards is the UI work |
| **Contextual explainability filter on angles** | Pasz (2025): outliers explained by Safety Car timing or tyre compound mismatch are not stories. Surface only angles that survived the situational filter; tell the writer *why* each angle passed | Medium | Cross-checks against race condition flags before surfacing; differentiates from tools that surface any statistical anomaly |
| **Angle confidence signal** | Show the writer which angles are high-confidence (k-factor low, SurpriseScore unambiguous) vs. speculative (early season, high uncertainty) — Statsperform Opta Stories does not do this; it surfaces angles with false confidence | Low (UI) / Medium (signal extraction) | Use k-factor width as uncertainty proxy; display visually on each angle card |
| **Five-act timeline spine linked to pitlane data sources** | Each beat in the outline maps to a specific CLI data source (qualifying lap data, lap-1 sector times, pit window gap data, final-stint tyre wear, championship standings). Writer sees "this beat can be backed by lap telemetry" not "AI will make up prose" | High | Requires mapping from Bouzarth dramatic acts to FastF1 data access points |
| **Teammate battle tracking as first-class angle type** | Within-team ΔR̂ crossing zero is a structurally important F1 narrative. No generic AI writer knows about teammate pairings. Opta Stories focuses on match-level events, not season-arc signals | Medium (signal exists) / Low (UI card type) | Already tracked in signals.py; needs dedicated angle card template |
| **Structured placeholder hooks that enforce journalist voice** | Wölker & Powell: algorithmic text is credible; journalist's differentiated value is causal reasoning and quotes. Placeholder hooks are not suggestions — they are enforced gaps that the tool refuses to fill with AI prose, preserving the journalist's voice contract | Low (implementation) / High (design discipline) | Distinct visual treatment (e.g., highlighted block, different background); AI prose stops at the boundary |
| **Angle selection as editorial decision record** | When writer selects an angle card, that selection is logged. Post-race, they can see "I chose 'Strategic Gamble' over 'Dominant Tyre Management' — here's why the other angles existed." Builds a personal editorial record across the season | Low | Useful for a solo writer tracking their own editorial instincts over a season |
| **Car vs. driver decoupling angle** | Rc (qualifying) diverging from constructor race ELO is a rich angle type no generic tool can detect. Specific to this data stack | Medium (signal exists) / Low (card) | "Ferrari was fastest in qualifying but seventh in race pace — this is a strategy and reliability story" |
| **Live update mode (v1.5 candidate)** | Round-by-round ELO updating during a race creates in-race story signals. Surfacing "this is becoming a comeback story" in real time while the race runs is a meaningful differentiator from post-race-only tools | High | Out of scope for v1; flag for v1.5. Requires live FastF1 stream connection |

---

## Anti-Features

Things to deliberately NOT build. These are traps that look like features.

### Anti-Feature 1: One-shot full-article generation

**What looks like a feature:** "Generate the full article from race data in one click."

**Why it's a trap:** Wang et al. (2025) is unambiguous — LLMs degrade after the first 40-60% of long output. A 1200-word race report generated in one pass will have a strong lede and a weak closing; the plan-then-write pipeline is not a UX nicety, it is a quality guarantee. More importantly: one-shot generation removes the journalist from the editorial decision loop entirely. The tool becomes a ghostwriter, not a co-author. The writer loses their editorial fingerprint and the tool loses its differentiation from ChatGPT.

**What to do instead:** Hard gate at outline approval. Every prose segment is beat-scoped. The writer can always regenerate a single beat; they cannot bypass the outline gate.

---

### Anti-Feature 2: Chat box / free-text prompting as the primary interface

**What looks like a feature:** "Ask the AI anything about this race" as the main interaction model.

**Why it's a trap:** Sánchez-López et al. (2025) specifically identifies this failure mode — effective tools encode journalist intent through structured choices, not open-ended prompting. A chat interface degrades into a general-purpose research tool (the journalist types "tell me about Verstappen's pace") and the tool's structural knowledge of ELO signals, act structure, and angle taxonomy goes unused. Chat also produces inconsistent output length, tone, and structure across sessions.

**What to do instead:** Angle card selection + outline approval is the primary interface. A "dig deeper" affordance on each data signal (showing the underlying ELO chart or lap delta) is acceptable as a secondary surface, but it should surface data, not generate more prose.

---

### Anti-Feature 3: Audience framing controls in v1

**What looks like a feature:** "Write this for casual fans / hardcore analysts / Substack subscribers."

**Why it's a trap:** Audience controls require the tool to maintain and test multiple voice profiles — medium complexity, high validation cost. More critically, they invite the journalist to offload voice decisions to the tool, which erodes the journalist's own voice over time. The Wölker & Powell finding applies here: the journalist's value is precisely their contextual framing, not the AI's ability to simulate it in multiple registers.

**What to do instead:** Single voice, defined once during tool setup (or left at a sensible default). Voice personalization is explicitly marked as v2 in PROJECT.md.

---

### Anti-Feature 4: Multimodal chart generation / automatic chart insertion

**What looks like a feature:** "Automatically pair each beat with a chart of the supporting data."

**Why it's a trap:** Chart generation requires significant additional infrastructure (rendering engine, chart type selection logic, Substack image upload flow) and the v1 data signals are already being used to generate prose, not visualizations. More importantly, chart selection is a high-judgment editorial call — the wrong chart next to a prose claim actively undermines credibility. Manual chart insertion (paste from pitlane CLI output) is sufficient for v1.

**What to do instead:** Include a data citation block alongside each beat that shows the underlying signal value (e.g., "SurpriseScore: -3.1 | Based on last 6-race ELO trajectory"). The journalist decides whether to surface this as a chart or prose. Chart pairing is explicitly v2 in PROJECT.md.

---

### Anti-Feature 5: Automated publication / "publish to Substack" button that bypasses review

**What looks like a feature:** "When you're done, publish directly to Substack."

**Why it's a trap:** A single-click publish removes the final editorial check. Substack posts with AI errors (wrong driver name, incorrect lap count, misattributed quote placeholder) damage a writer's credibility permanently. The informal Substack API integration is also unreliable — if it silently fails mid-publish, the writer may not notice.

**What to do instead:** Export creates a Substack draft, never a published post. The writer reviews in Substack's native editor before publishing. "Export to draft" not "Publish."

---

### Anti-Feature 6: Template library / angle library that grows unbounded

**What looks like a feature:** "Choose from 50 pre-built story angle templates."

**Why it's a trap:** A large library shifts the cognitive load from "the tool surfaces what's relevant" to "the writer must browse and choose." This recreates the blank page problem in a different form. The value of 4-6 data-grounded angle cards is precisely their specificity to this race — not their membership in a general taxonomy. A template library also encourages generic angles ("strong qualifying performance") that don't require the ELO infrastructure at all.

**What to do instead:** The angle detection pipeline generates only the angles the race data supports. No template browsing. The taxonomy of angle types (hot streak, giant-killing, strategic gamble, etc.) is fixed in the detection layer, not user-browsable.

---

## Feature Dependencies

```
Race selection
  → Story signal computation (ELO + Rc + SurpriseScore)
    → Contextual explainability filter (race condition flags)
      → Angle card generation (4-6 named narrative frames)
        → Angle card selection (writer chooses one)
          → Five-act timeline scaffold (acts populated from angle + data sources)
            → Beat-by-beat outline generation
              → Outline approval gate (hard gate — writer confirms)
                → Beat-by-beat prose generation (with placeholder hooks)
                  → Prose editor (individual beat revision)
                    → Full article assembly
                      → Substack export (draft, not publish)
```

Secondary flows (no hard dependency on primary chain):
```
Any beat → Data citation block (ELO signal value underlying that beat)
Any beat → Placeholder hook insertion (writer-only content)
Angle selection → Angle decision log (editorial record)
```

---

## MVP Recommendation

**Prioritize (v1):**

1. Story angle surface — 4-6 ELO-grounded angle cards per race. This is the core differentiator and the value the writer cannot get from any other tool.
2. Five-act timeline spine — outline scaffold that maps each beat to a FastF1 data source. Provides structure without requiring prose generation.
3. Outline approval gate + beat-by-beat prose — the plan-then-write pipeline. Generate prose only after writer approves structure.
4. Placeholder hooks — enforced human-only content slots in every prose segment.
5. Substack export to draft — the publishing destination; markdown fallback ensures it always works.
6. Persistent draft state — the workspace already exists; wire it to the UI so nothing is lost.

**Defer (v2 or later):**

- Live in-race update mode — high complexity, requires live FastF1 stream; v1.5 at earliest
- Audience framing controls — explicitly v2 per PROJECT.md
- Multimodal chart generation / chart pairing — explicitly v2 per PROJECT.md
- Character arc detection — explicitly v2 per PROJECT.md
- Angle decision log / editorial history — low complexity but not core; add after v1 validated

---

## Observations from Comparable Tools

**Wordsmith / Automated Insights** (MEDIUM confidence — training data, not verified with live docs):
- Core feature: template-based NLG where editors define "narratives" (conditional prose blocks) and the engine selects and fills them based on data thresholds
- What it gets right: named narrative templates, data-conditional selection, structured output
- What it gets wrong: the journalist designs templates once; the tool executes them mechanically. There is no angle *discovery* — the journalist must already know what stories exist. PitLane Studio's differentiator is that angle detection is data-driven, not pre-authored.
- Missing: no plan-then-write pipeline; no beat-level revision; no placeholder hooks for journalist voice

**Statsperform Opta Stories** (MEDIUM confidence — training data):
- Core feature: automated post-match summaries for team sports, distributed to news outlets at scale
- What it gets right: fast, reliable structured sports prose; well-defined narrative taxonomy
- What it gets wrong: optimized for volume and speed, not journalist control. Output is complete prose — no outline gate, no human-in-the-loop, no voice preservation. Designed for replacement journalism, not co-authoring.
- Missing: everything in the "differentiators" column above — no ELO signal, no confidence display, no placeholder hooks

**Lex** (MEDIUM confidence — training data):
- Core feature: AI writing assistant embedded in a document editor; the writer types, Lex suggests continuations
- What it gets right: low friction, natural writing flow, good at unblocking mid-draft
- What it gets wrong: blank page problem still exists — Lex waits for the writer to start. No structural scaffolding, no data grounding, no outline enforcement.
- Lesson for PitLane Studio: Lex's inline suggestion model is frustrating when the writer doesn't know *what* to write, only *how* to write. Angle cards solve the "what" problem before the writer reaches for "how."

**Jasper (sports vertical)** (LOW confidence — less direct knowledge of sports-specific features):
- Core feature: template-based content generation with brand voice training
- What it gets wrong for this use case: generic templates, no sports-domain data integration, voice consistency requires extensive training data from the writer
- Lesson: Brand voice training is a maintenance burden for a solo writer. The placeholder hook model (AI handles data prose, journalist provides voice content) is a more sustainable division than trying to train the AI to mimic the journalist's voice globally.

**Notion / Craft / Coda** (HIGH confidence — well-documented structured editors):
- What structured editors do well: block-based editing makes every paragraph independently revisable; document structure (headers, outline view) is always visible; database-linked content (Notion's relational blocks) shows structured data inline with prose
- What frustrates writers in structured editors: block editors add friction when you just want to type; outline views become stale when sections reorder; database-linked blocks break export to other tools
- Lesson for PitLane Studio: beats should be blocks (independently revisable), the five-act spine should be always-visible in a sidebar (not buried in an outline panel), and export should flatten the structure into clean prose for Substack without leaking block metadata

---

## Sources

- PROJECT.md — project requirements, design decisions, out-of-scope list (HIGH confidence)
- F1_ELO_Story_Detection_System_Design.md — story detection layer design, signal taxonomy, narrative trigger thresholds (HIGH confidence)
- Wölker & Powell (2018) — algorithmic journalism credibility; journalist differentiated value (HIGH confidence, cited in project docs)
- Bouzarth et al. (2021) — five-act dramatic structure for sports analytics (HIGH confidence, cited in project docs)
- Sánchez-López et al. (2025) — structured choices vs. free-text prompting for journalist intent (HIGH confidence, cited in project docs)
- Wang et al. (2025) — plan-then-write pipeline quality advantage (HIGH confidence, cited in project docs)
- Wordsmith/Automated Insights feature set — training knowledge through August 2025 (MEDIUM confidence)
- Statsperform Opta Stories feature set — training knowledge through August 2025 (MEDIUM confidence)
- Lex AI writing assistant — training knowledge through August 2025 (MEDIUM confidence)
- Jasper sports vertical — training knowledge through August 2025 (LOW confidence)
- Notion/Craft/Coda structured editors — training knowledge through August 2025 (HIGH confidence)
