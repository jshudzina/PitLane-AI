# Domain Pitfalls

**Domain:** F1 co-authoring interface / sports journalism AI (PitLane Studio)
**Researched:** 2026-05-02
**Note on sources:** External tools (WebSearch, WebFetch, Bash/Context7 CLI) were denied in this research session. Findings draw from: the three project files read (`PROJECT.md`, `CONCERNS.md`, `docs/F1_ELO_Story_Detection_System_Design.md`), the four papers cited in those files (Wang et al. 2025, Wölker & Powell 2018, Bouzarth et al. 2021, Sánchez-López et al. 2025, Pasz 2025), and training knowledge about unofficial API patterns, LLM pipeline failure modes, and uv monorepo mechanics. Confidence levels reflect source quality.

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

---

### Pitfall 1: Substack Unofficial API Session Cookie Expiry Causes Silent Publish Failure

**What goes wrong:** The unofficial Substack API authenticates via session cookies scraped from a logged-in browser session (typically `substack.sid` or equivalent). These cookies expire on a rolling basis (typically 7–30 days depending on Substack's session policy, which is not documented). When the cookie expires, API calls that previously returned 200 begin returning 401 or redirecting to the login page with no structured error body — just HTML. A pipeline that doesn't explicitly check the response content type will silently "succeed" (no exception raised) but write nothing, or worse, log the HTML redirect as the published URL.

**Why it happens:** Browser-scraped sessions are not designed for programmatic use. Substack has no official API contract, so there is no token-refresh endpoint, no OAuth flow, and no documentation of session lifetime. The only reliable refresh mechanism is re-scraping credentials from an interactive browser session — which cannot be automated without a headless browser.

**Consequences:** A race recap written and "exported" on race day appears to succeed but is never published. The journalist discovers this only when checking Substack directly, by which time the race news cycle has passed.

**Prevention:**
1. After every API call, check `response.content_type == "application/json"` before treating it as success. Any HTML response means the session has expired.
2. Implement an explicit session health-check endpoint call (`GET /api/v1/user`) before every publish attempt, with a clear user-facing error message if it fails: "Substack session expired — refresh your credentials in settings."
3. Make the markdown copy/paste fallback a first-class UI affordance, not a buried fallback. Display it alongside the "Publish to Substack" button so it is always available without any auth dependency.
4. Never log the Substack session cookie to any file or console output — it is equivalent to a plaintext password.

**Detection (warning signs):**
- API response time drops to < 50ms (HTML redirect is served before the JSON API path is evaluated)
- `response.headers["Content-Type"]` contains `text/html`
- Response body contains `"login"` or `"sign_in"` strings
- The published post ID returned by the API is null or missing

**Phase to address:** Story export / Substack integration phase. Implement the health-check and fallback UI before wiring up any publish flow.

**Confidence:** MEDIUM — Substack's unofficial API behavior is consistent with patterns observed across other cookie-auth integrations. The specific session lifetime is not publicly documented.

---

### Pitfall 2: Substack Unofficial API Rate Limits and ToS Risk Are Unknowable

**What goes wrong:** Because Substack has no official developer program, there is no published rate limit, no per-IP quota, and no terms that explicitly address programmatic posting. Substack's ToS prohibits "automated access" in generic terms but has not (as of training knowledge cutoff) enforced against individual writers using personal-use automation. The risk is not immediate banning but account suspension without warning if Substack changes enforcement posture — which has happened to other platforms (Twitter/X, Reddit) with similar informal tolerance.

**Why it happens:** Platforms tolerate informal API use until they productize their own API and need to control the ecosystem. Substack has signalled intent to build a creator monetization ecosystem, which could trigger enforcement of automated-access terms.

**Consequences:** Loss of the Substack publishing integration mid-season, requiring migration of all articles to manual publishing.

**Prevention:**
1. Never build a feature that would break the journalist's workflow if Substack integration disappears overnight. The markdown fallback must be equivalent in all functional respects to the automated export.
2. Rate-limit your own calls: no more than one publish per hour, no scraping of other users' content.
3. Do not store or transmit other users' Substack session data — this is a personal tool for one account only.
4. Architecture review: design the export layer as a swappable adapter (Substack, Ghost, Markdown file, email) from the start. The interface should be `export(draft: Draft) -> ExportResult`, not `publish_to_substack(draft)` — so swapping the adapter requires no UI changes.

**Detection (warning signs):**
- Substack 429 responses (rate limiting, though this response code is not guaranteed for unofficial endpoints)
- Substack announcing a developer API program (signals they are about to lock down unofficial use)
- Error responses with `403 Forbidden` from Substack CDN rather than the application server

**Phase to address:** Architecture phase — design the adapter interface before writing any Substack-specific code.

**Confidence:** MEDIUM — ToS risk is real but enforcement history is absent; rate limit behavior inferred from general platform patterns.

---

### Pitfall 3: Plan-Then-Write Pipeline Collapses Into "Plan-Approve-Ignore" Pattern

**What goes wrong:** Wang et al. (2025) — cited explicitly in PROJECT.md — demonstrate that LLMs degrade after the first 40–60% of long output. The plan-then-write design addresses this by separating outline generation from prose generation. However, the most common failure mode in practice is not LLM degradation itself but **outline drift**: the LLM generates prose that does not follow the approved outline, effectively reverting to unconstrained generation despite the approval step. The journalist approves a five-act structure, then the AI generates prose that front-loads all detail in act 1, compresses acts 2–4 into a paragraph, and pads act 5 with generic observations. The structure disappears the moment prose generation begins.

**Why it happens:** LLMs do not have a persistent reference to the outline during generation unless it is explicitly re-injected at each beat. Without mechanical enforcement (generate beat 1, stop, generate beat 2, stop), the model treats the outline as a soft suggestion rather than a hard constraint.

**Consequences:** The journalist must re-edit prose to restore structure, negating the value of the approval step. After two or three experiences of this, the approval UI feels like theater and the tool feels untrustworthy.

**Prevention:**
1. Generate prose **one beat at a time**. Never send the full five-act outline plus "now write the full article." Send the outline plus "now write act 1 only: [beat text]" — complete — then "now write act 2 only: [beat text]" — and so on. Each beat is a separate API call with its own context window.
2. Inject the approved outline header into every beat's prompt: "You are writing beat 3 of 5. The full structure is: [outline]. Write only beat 3."
3. Enforce a **word count constraint** per beat (derived from total target length divided across beats). If beat output exceeds 150% of the target, flag it rather than silently accepting it.
4. The beat-by-beat generation model maps cleanly onto the five-act structure already defined (qualifying/lap-1/pit window/final stint/championship). Five API calls per article, not one.

**Detection (warning signs):**
- Beat 1 word count exceeds the total article target word count ÷ 2
- Acts 2–4 contain fewer than 2 unique data references (ELO stats, lap times, positions) while act 1 contains more than 5
- The phrase "in conclusion" or "to summarize" appears before the final act

**Phase to address:** Plan-then-write pipeline phase. Define the per-beat API call pattern before building the prose generation endpoint.

**Confidence:** HIGH — Wang et al. (2025) is cited in PROJECT.md as the direct design authority for plan-then-write. The beat-by-beat injection pattern is the standard mitigation for outline drift in structured generation pipelines.

---

### Pitfall 4: Story Angle Detection Surfaces Noise as Signal — The "Every Race is a Story" Problem

**What goes wrong:** The ELO signal detection system (`pitlane_elo/stories/signals.py`) uses threshold-based triggers (e.g., `ΔR̂_3race > 0.5`, `SurpriseScore > 2.5`) defined in the system design document. The story angle layer in PitLane Studio is supposed to map these signals to 4–6 named narrative frames per race. The critical failure mode is **threshold miscalibration**: in a typical 24-race season, multiple drivers will cross the `ΔR̂_3race > 0.5` threshold at any given point, producing 8–12 "hot streak" or "slump" signals simultaneously. The angle layer selects 4–6, but without ranking or editorial filtering, it presents all of them as equally newsworthy. The journalist sees six "story angles" for every race and quickly learns to ignore the card UI entirely.

**Why it happens:** The signal thresholds in the design document (`ΔR̂_3race > 0.5`, `SurpriseScore > 2.5`) were designed to flag *candidates*, not to rank editorial relevance. Translating signal candidates directly into story angle cards without a ranking or novelty filter produces false positives not because the signal is wrong, but because the signal is right about too many drivers simultaneously.

**Consequences:** Signal fatigue. The journalist stops trusting the angle cards and reverts to blank-page writing, eliminating the core value proposition.

**Prevention:**
1. Add a **novelty filter**: a signal is only surfaced as a story angle if it was not surfaced in the previous two races for the same driver/constructor. If Hamilton has been flagged as "hot streak" for three consecutive races, the angle for this race should be "Hamilton streak now at N races" (escalating the existing narrative), not a new card.
2. Add a **field-relative ranking**: only surface the top 2 signals per signal type (top 2 hot streaks, top 2 upsets, top 2 teammate battles). The design document's narrative trigger taxonomy (Section 7.3) already provides the thresholds; the ranking layer above them is what is missing.
3. Add a **Pasz contextual filter** before surfacing any angle: if the SurpriseScore outlier coincides with a Safety Car event, a known tyre compound mismatch, or a wet race, downgrade the signal one tier before presenting it as a story. The design document explicitly calls for this (Section 7.4) but the implementation path is not yet specified.
4. Bias toward recent form over short-window signals. Early-season races (races 1–7, before k-factors stabilize) should require a higher SurpriseScore threshold (> 3.0 rather than > 2.5) because k-factors are still high and uncertainty bands are wide. The design document notes this explicitly for 2026 data.

**Detection (warning signs):**
- Story angle card count exceeds 8 for a given race (means the filter is too permissive)
- The same driver appears on more than one angle card simultaneously (means signal types are not deduplicated by driver)
- Angle cards for the same narrative type (e.g., two separate "hot streak" cards) appear in a single race

**Phase to address:** Story angle detection phase. Implement ranking and novelty filter before building the card selection UI; otherwise the UI feedback loop will mask the problem.

**Confidence:** HIGH — The signal thresholds in the design document are explicitly framed as candidate triggers. The ranking/novelty gap is directly inferable from the system design. Confirmed by Sánchez-López et al. (2025) finding that structured choices (not raw signal lists) are what make journalist tools effective.

---

### Pitfall 5: Recent-Form Bias Produces False "Crisis" Signals From DNF Clusters

**What goes wrong:** The existing codebase has `exclude_mechanical_dnf=False` for all 2023+ data because post-2023 Ergast/Jolpica data classifies all DNFs as "retired" without distinguishing crash from mechanical failure (documented in `CONCERNS.md`, HIGH severity). EndureElo is forgiving of DNFs by design (low failure-rate drivers being unlucky), but the story detection layer uses raw trend signals — `ΔR̂_3race < −0.5` triggers a "slump/crisis" angle. A driver who retires from two consecutive races due to mechanical failures will show a negative 3-race ΔR̂ regardless of endure-Elo's built-in robustness, because the ΔR̂ is computed on the ELO snapshots *after* the capped-but-still-downward update. The story layer will surface "Driver X in crisis" when the actual story is "Team X has a reliability problem."

**Why it happens:** The ELO model and the story detection layer make independent decisions. EndureElo caps the DNF downward adjustment at `0.5 × k_min` (per the design document), which is correct for the rating. But the story detection layer sees the cumulative ΔR̂ over 3 races, which includes those capped-but-real downward adjustments. The two layers are not coordinated on DNF provenance.

**Consequences:** A "driver slump" story is surfaced when the correct story is "constructor reliability failure." The journalist publishes a narrative blaming the driver, which is both factually wrong and potentially damaging to their credibility.

**Prevention:**
1. Before surfacing any "slump" or "crisis" angle for a driver, cross-check the DNF record for that 3-race window. If ≥1 DNF is present in the window, the angle should be **demoted** or reframed: instead of "Driver X slump," present it as "Driver X: slump or bad luck? [N] DNFs in [N] races."
2. The design document already specifies a constructor DNF cluster signal (≥3 DNFs in a 5-race window → reliability story flag). Ensure this signal is evaluated *first* and, if triggered, suppresses or reframes any concurrent driver slump signal for those same drivers.
3. The `review_mechanical_dnfs.py` script exists to manually reclassify DNFs via LLM. Until DNF classification is automated and `exclude_mechanical_dnf=True` is re-enabled, the story layer must treat all DNFs as potentially mechanical.

**Detection (warning signs):**
- A driver "slump" angle surfaces in the same race as a constructor "reliability" angle for that driver's team
- The driver's teammate does not show a concurrent slump signal (asymmetric slumps with same-car context = more likely mechanical)
- The ΔR̂ drop coincides with known DNF events in the race data

**Phase to address:** Story angle detection phase, specifically the signal-to-angle mapping layer. Requires coordination with the existing tech debt around DNF classification.

**Confidence:** HIGH — Directly grounded in `CONCERNS.md` (HIGH severity item: DNF classification disabled for 2023+ data) and the system design document's explicit discussion of DNF treatment (Section 3.1, Section 9).

---

## Moderate Pitfalls

---

### Pitfall 6: Structured Beat Editor Becomes a Form Instead of a Canvas

**What goes wrong:** Sánchez-López et al. (2025) — cited in PROJECT.md — find that effective journalist tools encode intent through structured choices, not free-text prompting. The design correctly adopts story angle cards and an outline approval step. The failure mode is **over-structuring the prose editor**: if every beat has a mandatory field, a character limit indicator, a placeholder label, and inline suggestions, the journalist experiences the editor as a bureaucratic form rather than a writing surface. The tool that was supposed to accelerate writing instead makes every sentence feel like a compliance exercise.

**Why it happens:** Designers add structure incrementally in response to edge cases ("what if they don't know how long beat 2 should be?") until the editor has more scaffolding than content. Each individual constraint seems reasonable; the cumulative effect is oppressive.

**Prevention:**
1. The only mandatory structural element per beat is the **placeholder hook** — a clearly marked "[JOURNALIST: add quote/context/causal reasoning here]" block that the journalist can fill or delete. Everything else should be optional.
2. Word count indicators should be visible but not blocking. A soft warning ("Beat 2 is 40% longer than suggested") is acceptable; a hard character limit that prevents typing is not.
3. The outline approval step should show the structure, not the prose. Once prose begins, the outline is collapsed to a sidebar — visible but not competing with the writing surface.
4. Test the UX with a timer: if the journalist takes more than 90 seconds to figure out "where do I start writing" on the prose screen, there is too much scaffolding.

**Detection (warning signs):**
- User repeatedly deletes scaffold content before writing their own (scaffolding is friction, not help)
- Beat completion time is slower than equivalent blank-document writing
- User skips the approval step by clicking through it without reading (approval UI has lost its function)

**Phase to address:** Structured co-authoring UI phase. Keep the first prototype minimal and add structure only in response to observed writer friction, not in anticipation of it.

**Confidence:** HIGH — Directly grounded in Sánchez-López et al. (2025) finding on structured choices vs. free-text prompting, and in general UX research on progressive disclosure vs. up-front scaffolding.

---

### Pitfall 7: FastF1 Session Data Unavailability for Recent Races Breaks Story Detection Timing

**What goes wrong:** FastF1 fetches race data from the F1 live timing service and caches locally. For live and very recent races, full session data (including detailed lap times, tyre strategies, and telemetry) is not available immediately after the race — there is typically a 2–4 hour lag while the live timing service processes and publishes data, and in some cases data quality issues persist for 24+ hours. The story detection pipeline, if triggered immediately after race end, may operate on incomplete data: missing final lap times for DNS/DNF drivers, incomplete tyre strategy records, or missing race control messages.

**Why it happens:** The F1 live timing stream is optimized for real-time broadcast display, not for complete historical accuracy. FastF1 surfaces this data as-is without indicating completeness. Gaps in the data may silently produce incorrect outlier signals (a driver appearing to have a very fast final stint because their tire degradation data is missing).

**Consequences:** A story angle card surfaces a false "strategic masterstroke" signal that disappears when the journalist tries to verify it against the actual race replay. Trust in the signal layer erodes.

**Prevention:**
1. After every race, delay story detection by at least 4 hours. Do not trigger story angle generation until `session.load()` completes without warnings and the lap count for all classified finishers matches the official lap count.
2. Check `session.results` for completeness: if any classified finisher is missing a `FastestLapTime`, treat the session data as incomplete and defer.
3. Add a **data freshness indicator** to the story angle UI: "Angles based on data loaded [N hours] after race end. Verify lap time claims before publishing."
4. FastF1 already caches to disk at `~/.pitlane/cache/fastf1/`. Ensure the studio pipeline always loads from cache after an initial load, not on every request — the existing concern about per-request re-deserialization (`CONCERNS.md`, LOW severity) compounds this risk.

**Detection (warning signs):**
- `session.laps` count is less than `session.total_laps × number_of_classified_finishers`
- Any driver in `session.results` with `Status == "Classified"` has `NaN` for lap count fields
- FastF1 issues a `UserWarning: data may be incomplete` during session load

**Phase to address:** Story detection phase. Implement the data completeness check as a gate before the angle generation pipeline runs.

**Confidence:** MEDIUM — FastF1 data availability timing is a known community issue (referenced in FastF1 GitHub issues and documentation). The specific thresholds (4 hours, lap count check) are heuristic estimates from training knowledge and should be validated against actual race weekends.

---

### Pitfall 8: uv Monorepo Intra-Workspace Dependency Creates Silent Version Mismatches

**What goes wrong:** `pitlane-studio` will depend on `pitlane-agent` and `pitlane-elo` within the same uv workspace. uv resolves intra-workspace dependencies by path reference, not by version number — which means `pitlane-studio` always gets the current local version of its sibling packages. This is correct during development but creates a failure mode: if a breaking change is made to `pitlane-elo`'s public API (e.g., the signature of `detect_stories()` changes), `pitlane-studio` will silently begin calling the new signature incorrectly if there is no import-time type check or runtime validation. uv will not flag this because there is no version mismatch — both packages are at `0.1.0` locally.

**Why it happens:** Path-based resolution in workspaces bypasses semantic versioning. In a published-package workflow, a breaking change would require a major version bump and a corresponding range update in the dependent package's `pyproject.toml`. In a monorepo, that discipline requires explicit team convention rather than tooling enforcement.

**Consequences:** A refactor in `pitlane-elo` silently breaks `pitlane-studio` at runtime, discovered only when the studio server tries to call `detect_stories()` with old arguments and gets a TypeError at runtime.

**Prevention:**
1. Add type annotations to every public function boundary between packages that `pitlane-studio` will call. `mypy` or `pyright` run in the CI pipeline will catch signature mismatches before they reach runtime.
2. Define an explicit **internal interface module** in `pitlane-agent` and `pitlane-elo` (e.g., `pitlane_elo.studio_api`) that exports only the functions PitLane Studio is expected to call. Changes to internal functions don't break this surface; changes to the interface module are a deliberate decision.
3. Run `uv sync --all-packages` after any change to a dependency package and verify tests pass across all packages, not just the changed one.
4. Add an integration test in `pitlane-studio`'s test suite that calls the real `detect_stories()` function (not a mock) with known fixture data. This test fails immediately when a breaking change is made to the interface.

**Detection (warning signs):**
- A change to `pitlane-elo` is merged without running `pitlane-studio` tests (because no CI rule enforces cross-package test runs on dependency changes)
- `detect_stories()` return type changes from a list to a typed dataclass without a corresponding update in the caller

**Phase to address:** Package scaffolding phase for `pitlane-studio`. Define the internal interface module and cross-package integration test before writing any studio business logic.

**Confidence:** HIGH — uv workspace path-resolution behavior is documented in uv's official documentation. The failure mode is a standard monorepo pattern known from npm/cargo/uv workspaces. Confidence in the prevention strategy is HIGH.

---

### Pitfall 9: Claude Agent SDK Unpinned Pre-1.0 Dependency Breaks on Minor Upgrade

**What goes wrong:** `pitlane-agent` declares `claude-agent-sdk>=0.1.40` with no upper bound (`CONCERNS.md`, MEDIUM severity). PitLane Studio will add a second call site into the Claude Agent SDK (for plan-then-write beat generation). If the SDK releases a breaking change — even a minor one — between the version tested against and the next `uv sync`, both the existing chat interface and the new studio prose pipeline break simultaneously, in potentially different ways.

**Why it happens:** Pre-1.0 SDKs follow the convention that any minor version bump may contain breaking changes. The `>=0.1.40` pin provides no upper-bound protection. The project memory already flags this concern; adding a new SDK caller multiplies the blast radius.

**Prevention:**
1. Before starting the studio phase, pin the SDK: `claude-agent-sdk>=0.1.40,<0.2.0` in `pitlane-agent/pyproject.toml`. This is flagged in `CONCERNS.md` as the explicit fix.
2. After pinning, run the full test suite to confirm the pin is satisfied by the installed version.
3. Define a separate `pitlane-studio/pyproject.toml` dependency on the same pinned range, not a transitive dependency through `pitlane-agent`. This makes the studio's SDK dependency explicit and auditable.

**Detection (warning signs):**
- `uv sync` output shows the SDK version changing upward across a `.minor` boundary
- Any `ImportError` or `AttributeError` traceback that includes `claude_agent_sdk` in the frame

**Phase to address:** Package scaffolding phase. Fix the pin as a prerequisite before any studio code touches the SDK.

**Confidence:** HIGH — Directly from `CONCERNS.md` (explicitly documented concern). No external research needed.

---

## Minor Pitfalls

---

### Pitfall 10: ELO Delta Thresholds Are Tuned on Historical Data, Not 2026 Race Format

**What goes wrong:** The narrative trigger thresholds in the system design document (Section 7.3: `ΔR̂_3race > 0.5`, `SurpriseScore > 2.5`) were derived from calibration data spanning 1980–2025. The 2026 season introduces new power unit regulations (Section 5.4D notes this explicitly) that may compress or expand the typical ELO delta distribution for all drivers. If the 2026 field becomes more competitive (as new regulations historically tend to equalize performance before teams diverge), the `ΔR̂_3race > 0.5` threshold may be too high early in the season, producing zero story angles because no driver is differentiating enough — or too low after a dominant team emerges.

**Prevention:**
1. After 6 races of 2026 data, compute the empirical distribution of `ΔR̂_3race` across all drivers and verify the threshold falls within the top 20% of that distribution. Adjust if needed.
2. Display the current threshold and the field median ΔR̂ in a developer-visible debug panel. This makes miscalibration visible without requiring a code change.

**Phase to address:** Story detection phase, post-season-launch tuning iteration.

**Confidence:** MEDIUM — The calibration concern is explicitly noted in the design document. The magnitude of 2026 regulation impact is uncertain.

---

### Pitfall 11: Workspace Disk Accumulation Compounds With Studio Session Volume

**What goes wrong:** The existing `CONCERNS.md` (HIGH severity) documents that workspaces accumulate in `~/.pitlane/workspaces/` indefinitely. PitLane Studio adds a new session type — co-authoring drafts — which will likely produce larger workspace artifacts than the current chat sessions (full beat-by-beat prose, outline JSON, story angle selections). If the studio generates 10 articles per race weekend × 24 races, and each draft workspace is 50–200KB, disk accumulation accelerates by 120–480MB per season on top of existing chat workspace growth.

**Prevention:** Implement the workspace cleanup mechanism flagged in `CONCERNS.md` before shipping the studio. Add draft workspaces to the cleanup policy with a longer TTL (30 days vs. 7 days for chat sessions) since in-progress articles may span multiple sessions.

**Phase to address:** Infrastructure / pitlane-studio scaffolding phase. Prerequisite to production use.

**Confidence:** HIGH — Directly from `CONCERNS.md`.

---

### Pitfall 12: XSS Risk Carries Into Studio LLM-Generated Prose

**What goes wrong:** `CONCERNS.md` (MEDIUM severity) documents that `pitlane-web` renders LLM output via `| safe` in Jinja2 without sanitization. PitLane Studio's prose editor will render beat-by-beat LLM output in a browser UI. If the prose rendering path follows the same pattern as `pitlane-web`'s `message.html` template, any LLM output containing `<script>` or malformed HTML will be executed in the browser.

**Prevention:** The new studio frontend must sanitize LLM output before rendering. Do not inherit the `| safe` pattern from `pitlane-web`. Use `bleach.clean()` or equivalent on the server before injecting prose into the template. This is the fix already recommended in `CONCERNS.md` — implement it in the studio package from day one rather than carrying the debt forward.

**Phase to address:** Co-authoring UI phase. Establish the sanitization pattern at template creation, before any prose is rendered.

**Confidence:** HIGH — Directly from `CONCERNS.md`.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Package scaffolding | uv intra-workspace silent API drift (Pitfall 8) | Define interface module and cross-package integration test before business logic |
| Package scaffolding | Claude Agent SDK breaking on minor version bump (Pitfall 9) | Pin SDK to `<0.2.0` as prerequisite |
| Package scaffolding | Workspace disk accumulation accelerates with studio drafts (Pitfall 11) | Implement cleanup before first studio session |
| Story angle detection | Signal threshold miscalibration produces signal fatigue (Pitfall 4) | Add field-relative ranking and novelty filter to angle layer |
| Story angle detection | DNF-driven false "slump" angles (Pitfall 5) | Cross-check DNF record before surfacing any driver crisis angle |
| Story angle detection | ELO thresholds not yet validated for 2026 regulation era (Pitfall 10) | Recheck thresholds after 6 races of 2026 data |
| FastF1 data ingestion | Incomplete session data produces false outlier signals (Pitfall 7) | 4-hour delay gate + completeness check before angle generation |
| Plan-then-write pipeline | Outline drift — prose ignores the approved plan (Pitfall 3) | Per-beat API calls, not full-article generation |
| Co-authoring UI | Structured editor feels like a form (Pitfall 6) | Minimize mandatory scaffolding; only placeholder hooks are required |
| Co-authoring UI | XSS via LLM prose rendered with `| safe` (Pitfall 12) | Sanitize with `bleach.clean()` at template creation |
| Substack export | Session cookie expiry causes silent publish failure (Pitfall 1) | Health-check before publish + first-class markdown fallback |
| Substack export | ToS and rate limit risks are unknowable (Pitfall 2) | Adapter interface from day one; treat markdown fallback as primary path |

---

## Sources

- `PROJECT.md` — project requirements, design decisions, paper citations (HIGH confidence: primary source)
- `CONCERNS.md` — existing codebase audit (HIGH confidence: primary source)
- `docs/F1_ELO_Story_Detection_System_Design.md` — signal architecture, thresholds, DNF handling, calibration (HIGH confidence: primary source)
- Wang et al. (2025) — LLM long-form generation degradation; plan-then-write superiority (HIGH confidence: cited in PROJECT.md as design authority)
- Sánchez-López et al. (2025) — structured journalist tools; card-based choices over free-text prompting (HIGH confidence: cited in PROJECT.md)
- Wölker & Powell (2018) — journalist differentiated value; placeholder hooks (HIGH confidence: cited in PROJECT.md)
- Bouzarth et al. (2021) — five-act sports narrative structure (HIGH confidence: cited in PROJECT.md)
- Pasz (2025) — situational factors in lap-time variance; contextual explainability filter (HIGH confidence: cited in design document Section 7.4)
- Training knowledge: Substack unofficial API cookie-auth patterns, uv workspace dependency resolution, FastF1 data availability timing, LLM outline drift patterns (MEDIUM confidence: consistent with general platform patterns but not externally verified in this session)
