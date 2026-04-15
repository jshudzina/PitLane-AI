# F1 ELO Story Detection System — Design Document

---

## 1. Research Foundation: What the Papers Tell Us

Before designing the system, it's worth distilling what each paper contributes and where they agree, disagree, or complement each other.

### Paper 1 — Powell (2023): *Generalizing the Elo Rating System — Why Endurance is Better than Speed*
**The most theoretically rigorous ELO paper for F1 specifically.** Powell argues that F1 is fundamentally an *endurance* competition, not a *speed* competition: competitors race until they fail, and the last one standing wins. This leads to his **endure-Elo** system, grounded in the Plackett-Luce model with exponential failure times.

Key mechanics:
- Each race is decomposed into *m−1* sequential knock-out rounds, where the worst competitor is eliminated each round
- Each competitor i gets a "strength" parameter R̂ᵢ; the elimination probability in each round is `e^(−R̂ᵢ) / Σ e^(−R̂ⱼ)`
- After each round, ratings update by `R̂ᵢ ← R̂ᵢ + k[𝟙(i survives) − P(i survives)]`
- Competitor-specific k-factors decay as data accumulates; time-discounting via an AR(1) process (`φ` parameter) handles form changes between races

**Key result:** Across 52 F1 seasons (873 races), the endure-Elo user beats the speed-Elo user 76.3% of the time. The endure-Elo system is substantially better at predicting race winners because it treats poor results by strong competitors as relatively uninformative (failures can be unlucky), while being very sensitive to strong performances (enduring to the end is not luck).

**Practical implication for story detection:** Endure-Elo is *forgiving of crashes/DNFs* and *excited by unexpected victories*, making it ideal for detecting when a driver or constructor is genuinely outperforming expectations vs. just avoiding bad luck.

---

### Paper 2 — Xun: *From Pole to Podium: Adjusting Elo to Separate Car and Driver*
**The most direct practical ELO implementation for F1.** Xun proposes two parallel tracks:

**Car Rating (Rc):**
```
Rcᵢ = (T_driver − T_fastest) / T_fastest
```
Where T_driver is the team's average fastest qualifying lap and T_fastest is the fastest lap across all drivers that session. Lower Rc = faster car. This is computed *per Grand Prix*, not annually, capturing the fact that car performance varies by track.

**Driver ELO:** Standard round-robin tournament ELO, initialised at 2000. Each race is treated as n(n−1)/2 pairwise comparisons.

**Key problems Xun identifies and partially solves:**
- DNFs unfairly tank driver ratings → exclude races where drivers didn't finish
- Recency bias at season end → use average Elo across the season, not final value
- The two ratings are then combined via linear regression to predict finishing position

**Limitation:** Xun uses speed-Elo (round-robin pairwise), not endure-Elo, so Powell's critique applies. The car rating (Rc) from qualifying is, however, a valuable standalone signal.

---

### Paper 3 — van Kesteren & Bergkamp (2023): *Bayesian Analysis of F1 Race Results*
**The gold standard for disentangling driver skill and constructor advantage.** Using a Bayesian multilevel rank-ordered logit model across 2014–2021:

- **~88% of variance in race results is explained by the constructor**, ~12% by driver skill
- The model includes long-term driver skill (θ_d), seasonal driver form (θ_ds), long-term constructor advantage (θ_t), and seasonal constructor form (θ_ts)
- Credible intervals are given for all parameters, allowing principled uncertainty quantification
- Wet races and street circuits are modelled as separate contexts because they change the car/driver contribution balance

**Key insight for story detection:** The separation of *long-term* and *seasonal* parameters is exactly what you need to distinguish "this driver has always been elite" from "this driver is hot right now."

**Empirical evaluation result:** When the van Kesteren Bayesian model was evaluated head-to-head against endure-Elo using log-likelihood across calibration (1980–2013), validation (2014–2021), and holdout (2022–2025) windows, **endure-Elo outperformed it on every window**. The theoretical advantages of the Bayesian approach (explicit uncertainty quantification, native driver/constructor decomposition) did not translate into prediction accuracy. The paper's structural insight — that wet races and street circuits are distinct contexts — is retained as a covariate design recommendation. Note also that empirical OLS estimation (`pitlane-elo estimate-alpha`) yields an alpha of ~0.77 for 2014–2024, somewhat lower than the ~88% variance ratio reported here, reflecting a different estimand (linear ELO weighting vs. variance decomposition).

---

### Paper 4 — Pasz (2025): *Determinants of Lap Times in F1, 2019–2025*
**Not an ELO paper, but provides critical context for what drives lap-time variance.** Using Fixed Effects and GAMM on lap-level data:

- Time-varying, race-specific factors (tyre compound, stint length, pit stops, track/weather conditions) explain *more* variance than static team/driver identity
- Non-linear tyre degradation effects discovered via GAMM smooth terms
- Safety Car and VSC periods create lagged performance effects on subsequent laps

**Implication for story detection:** A large deviation in an ELO-based expected finish may simply reflect known situational factors (e.g., a well-timed pit on a Safety Car). A robust story detector should try to flag whether an outlier is "explainable" vs. "genuinely surprising." Pasz's variable taxonomy is the right checklist for the explainable side.

---

## 2. System Architecture

The system uses endure-Elo (Powell 2023) as the single primary rating engine, updating after each race. Xun's qualifying-based Car Rating (Rc) runs in parallel as an independent car-pace signal — it is not a rating model but a per-race measurement. Both feed into prediction assessment and story detection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RAW DATA INPUTS                                  │
│       Race results · Qualifying times · Weather · Track type · DNFs         │
└──────────────────────┬──────────────────────────┬──────────────────────────┘
                       │                          │
         ┌─────────────▼──────────────────┐   ┌───▼─────────────────────────┐
         │  PRIMARY: ENDURE-ELO           │   │  CAR PACE: Xun Rc           │
         │  Powell (2023)                 │   │  Per-race qualifying signal  │
         │  Updates after each race       │   │  ─────────────────────────  │
         │  Round-by-round during race    │   │  Rcᵢ = (T_team − T_fastest) │
         │  ─────────────────────────     │   │        / T_fastest           │
         │  R̂ᵢ  driver rating            │   │  Independent of race outcome │
         │  k-factor (Glicko precision)  │   │  Updates after qualifying    │
         │  AR(1) + OU spacing            │   │                             │
         │  Robust DNF handling           │   │                             │
         │  Calibrated: k_max=0.8665,     │   │                             │
         │  φ_race=0.999, φ_season=0.947  │   │                             │
         └─────────────┬──────────────────┘   └───────────┬─────────────────┘
                       │                                  │
                       └──────────────┬───────────────────┘
                                      │
                           ┌──────────▼──────────┐
                           │  LAYER 4: PREDICTION│
                           │  Log-likelihood     │
                           │  Brier score        │
                           │  RMSE · Calibration │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │  LAYER 5: STORIES   │
                           │  Trend signals      │
                           │  Outlier signals    │
                           │  Narrative triggers │
                           └─────────────────────┘
```

---

## 3. Layer 1: Rating Computation

### 3.1 Driver endure-Elo

Implement Powell's endure-Elo. For a race with m finishers ranked by finishing position:

1. **Decompose** the race into m−1 sequential knock-out rounds. Round 1 eliminates the last-place finisher, round 2 eliminates the second-to-last, etc.

2. **Elimination probability** at each round for competitor i, given the surviving set Q:
   ```
   P(i eliminated in round) = e^(−R̂ᵢ) / Σⱼ∈Q e^(−R̂ⱼ)
   P(i survives round) = 1 − P(i eliminated in round)
   ```

3. **Update rule** after each round:
   ```
   R̂ᵢ ← R̂ᵢ + kᵢ · [𝟙(i survives round) − P(i survives round)]
   ```

4. **DNF handling:** The ideal treatment distinguishes crash retirements (informative — the driver participated to their limit) from mechanical failures (uninformative — the car ended the race, not the driver). However, this distinction is **not cheaply available in post-2023 data** from standard sources (FastF1, Ergast). The practical approach by data era:

   - **Pre-2024 data:** Use the `statusId` field in the Ergast historical database, which carries sufficient granularity to separate crash, collision, and mechanical codes. Apply the Xun treatment: include crashes in ELO (ranked at elimination position), exclude mechanical DNFs.
   - **2024–present:** Treat all DNFs uniformly using endure-Elo's inherent robustness. Because endure-Elo is forgiving of elimination early in a race (the failure-rate model treats early exits as relatively uninformative about true ability), the distortion from not separating crash vs. mechanical is substantially smaller than it would be under speed-Elo. As a practical safeguard, cap the downward ELO adjustment for any DNF at `0.5 × k_min` to prevent a single uninformative retirement from collapsing a well-established rating.
   - **Regardless of era:** Record all DNF events as a *separate* signal for story detection. DNF clustering for a constructor (≥3 in a 5-race window) triggers the reliability story flag independently of the ELO computation.

5. **Initialisation:** Start each driver at R̂ = 0 on their first race. Season-to-season carryover handled in Layer 3.

### 3.2 Constructor endure-Elo

Run a *parallel* endure-Elo track treating each constructor as a single entity. Each race, the constructor's "performance" is the average of its two drivers' finishing positions (adjusted for driver skill — see Layer 2). This produces a constructor R̂ series that evolves independently of driver ratings.

Separately, compute Xun's qualifying-based **Car Rating (Rc)** per Grand Prix:
```
Rcᵢ = (T_team_avg_qual − T_fastest_qual) / T_fastest_qual
```
This is a fast-updating, track-specific signal of raw car pace that doesn't depend on race outcomes.

### 3.3 Wet/street circuit contexts

Following van Kesteren & Bergkamp, maintain *context-specific* rating tracks:
- **Dry race, permanent circuit** (baseline)
- **Wet race** (separate driver rating — some drivers are much stronger in the wet)
- **Street circuit** (separate constructor rating — some cars suit tight circuits better, e.g. Red Bull at Monaco)

Each context-specific rating updates only when that context occurs. This avoids contaminating the dry-track constructor rating with Monaco wet-race noise.

---

## 4. Layer 2: Driver/Constructor Separation

The ~88/12 split found by van Kesteren & Bergkamp means that raw driver ELO contains a large constructor signal. To isolate driver skill:

### 4.1 Teammate normalisation

For any race where both teammates finish, compute the **within-team delta**:
```
ΔR̂ᵢ = R̂ᵢ(driver) − R̂ⱼ(teammate)
```
This delta is a purer measure of driver skill because both drivers are in the same car. Track this series per driver across their career.

### 4.2 Car-adjusted driver score

After each race, compute an adjusted score that removes estimated constructor contribution:
```
DriverSkill_adjusted = R̂ᵢ(driver) − α · R̂ᵢ(constructor)
```
where α is a learned weighting estimated empirically via OLS (`pitlane-elo estimate-alpha`). **Calibrated value: `alpha = 0.7747`** over 2014–2024. Note this is a different quantity from van Kesteren's ~88% variance ratio — it is the linear coefficient relating constructor ELO to raw driver ELO, not a variance decomposition.

The endure-Elo algorithm can be extended to do this simultaneously by decomposing updates into shared (constructor) and individual (driver) components — see Section 5.4B for the update-level formulation.

### 4.3 Driver transfer signals

When a driver changes team, the separation becomes directly observable. The Räikkönen example from van Kesteren is instructive: Räikkönen moved from Ferrari to Alfa Romeo in 2019 and immediately performed like a midfield driver, not a top-3 one. This gives a strong identification event for both car quality and driver skill. Flag every team change as a **separation calibration opportunity** in the system.

---

## 5. Layer 3: Temporal Modelling

This is where the system tracks form rather than just ability.

### 5.1 Competitor-specific k-factors (Glicko-style)

Following Powell's extended endure-Elo, each competitor has their own uncertainty parameter. The k-factor update after each round:
```
kᵢ⁻¹ ← kᵢ⁻¹ + P(i survives round) · (1 − P(i survives round))
kᵢ,t = kᵢ,t + k adjustment (from eq. 5 in Powell)
```
Early in a driver's career or after a long absence, kᵢ is high (ratings move fast). After many races, kᵢ stabilises and ratings only shift meaningfully when results are genuinely surprising.

Practically, set a floor `k_min` (e.g. 0.05) so established ratings still respond to real form changes, and a ceiling `k_max` for new entrants. **Calibrated value: `k_max = 0.8665`** (random search + Nelder-Mead over 1980–2013; validated 2014–2021; holdout 2022–2025 — see Section 10).

### 5.2 Between-race time discounting (AR(1) / Ornstein-Uhlenbeck)

Between rounds separated by h time steps, apply Powell's discounting:
```
R̂ᵢ,t ← φʰ · R̂ᵢ,t₋ₕ
kᵢ,t ← kᵢ,t₋ₕ + (1 − φ²ʰ)(k∞ − kᵢ,t₋ₕ)
```
The parameter φ encodes how quickly ability is assumed to decay. **Calibrated values: `phi_race = 0.9990` per race, `phi_season = 0.9472` between seasons.** Within-season decay is nearly flat — calibration found that abilities are very stable race-to-race and that most meaningful forgetting happens at the season boundary. The between-season value (0.9472) is meaningfully lower than a naïve 0.95 starting point, reflecting genuine off-season uncertainty from car development and team changes.

**k∞** (the asymptotic variance) should reflect the realistic spread of driver and constructor ability. A reasonable starting estimate from Powell's guidance: `k∞^(1/2) ≈ 0.75 × log(q/(1−q))` where q is the probability the stronger competitor beats the weaker one in a given matchup — try q = 0.7 as a prior for F1.

**Irregular race spacing — practical fix:** Powell's h-step formula above is already a discrete approximation to the continuous-time Ornstein-Uhlenbeck (OU) process, which handles variable gaps correctly. The underlying relationship is φ = e^{−θ·Δt}, where θ is the mean-reversion rate and Δt is the actual elapsed time in days. Rather than counting races (h = 1 per race), express h as calendar days and fit θ accordingly. This matters most for the summer break (~8 weeks) and for sprint weekends where two ELO-relevant events occur within 3 days. Concretely:

```
# Convert calendar gap to OU-equivalent h
θ = −log(φ_per_race) / 14    # per-day rate, assuming ~14 days average between races
h_days = actual_calendar_days_since_last_race
φ_effective = exp(−θ · h_days)

R̂ᵢ,t ← φ_effective · R̂ᵢ,t₋ₕ
```

This costs nothing extra at runtime and eliminates the distortion from treating a summer break the same as a back-to-back race weekend.

### 5.3 Seasonal resets

At the start of each new season:
- Apply an additional φ_season discount to all R̂ values (e.g. φ_season = 0.90), pulling ratings toward 0
- Reset k-factors toward k∞ (increased uncertainty reflects new regulations, new car, etc.)
- This prevents ratings carrying too much historical inertia into a totally new technical era (e.g. the 2022 regulation change)

**Regulation change flag:** For major regulation changes (2014 hybrid era, 2022 ground-effect era), apply a larger reset (φ_reg = 0.70 or even full reset) and set k to k∞ for all competitors.

### 5.4 AR(1) Robustness Improvements

The standard AR(1) with Gaussian, homoscedastic, independent innovations has four known failure modes in F1 that are worth addressing explicitly. Each has a targeted, low-cost fix that can be layered on without restructuring the core algorithm.

**A. Heavy-tailed innovations (crashes, mechanical failures)**

The Gaussian assumption treats a rare disaster race (crash, pit-lane fire, sudden power unit failure) as strong evidence of ability decline, because a Normal distribution puts negligible probability mass in the far tails. Post-2023, where crashes and mechanicals are not cheaply separable, this is a live problem.

Fix: Replace the implicit Normal innovation assumption with a **Student-t equivalent** by capping the magnitude of any single-race ELO update:

```
# After computing the raw update δᵢ = kᵢ · [𝟙(survives) − P(survives)]
# across all m−1 rounds:
δᵢ_total = Σ_rounds δᵢ_round
δᵢ_robust = sign(δᵢ_total) · min(|δᵢ_total|, 2.5 · k_min)
R̂ᵢ ← R̂ᵢ + δᵢ_robust
```

This is a soft-thresholding equivalent to using t-distributed innovations: large shocks are admitted but their leverage on the long-run ability estimate is bounded. The constant 2.5 × k_min is a tuning parameter; cross-validate against held-out seasons.

**B. Correlated innovations across teammates**

Teammates share a car. A power unit upgrade, floor revision, or strategic experiment affects both drivers simultaneously, creating a correlated shock that the single-driver AR(1) attributes (incorrectly) to individual ability change. The fix is to decompose the update into a shared team component and an individual component:

```
# After a race, compute each driver's raw update δᵢ
# For a two-driver team {i, j}:
δ_shared = (δᵢ + δⱼ) / 2      # goes to constructor ELO
δᵢ_driver = δᵢ − δ_shared      # goes to driver ELO
δⱼ_driver = δⱼ − δ_shared

# Update separately:
R̂ᵢ_driver ← R̂ᵢ_driver + kᵢ_driver · δᵢ_driver
R̂ᵢ_constructor ← R̂ᵢ_constructor + k_constructor · δ_shared
```

This is the online analogue of the driver + constructor decomposition already called for in Layer 2 (Section 4.2), but applied at the *update* level rather than just at the *scoring* level. It means driver ratings no longer jump in unison when the car gets a major upgrade.

**C. Competitor-specific decay rate φᵢ**

Using a single global φ forces every driver to have the same consistency profile. In practice, some drivers are structurally more volatile (rookies, drivers mid-career in new teams) and others highly stable. A pragmatic fix without full hierarchical estimation:

```
# Use the rolling variance of recent ELO updates as a consistency proxy
# For driver i over the last L races:
σ²ᵢ_recent = Var(δᵢ_race-1, ..., δᵢ_race-L)

# Adjust φᵢ toward the global φ weighted by evidence:
φᵢ = φ_global + β · (φᵢ_empirical − φ_global)

# where φᵢ_empirical is derived from the observed autocorrelation of δᵢ
# and β ∈ [0, 1] is a shrinkage weight (set β = races_i / (races_i + 10))
```

New drivers start at the global φ (no evidence for individual profile) and gradually acquire their own φᵢ as data accumulates. The shrinkage toward φ_global prevents overfitting on short samples.

**D. Structural breaks at regulation changes**

The AR(1) will smooth over regulation-era discontinuities, misattributing a step-change in constructor competitiveness to a slow trend. The seasonal reset in Section 5.3 partially addresses this, but known regulatory event dates should trigger an **explicit break**:

```
REGULATION_BREAK_YEARS = [2014, 2017, 2022]  # 2014/2022: powertrain + aero resets → φ_reg 0.60–0.70; 2017: aero-only, no PU change → use softer φ_reg ≈ 0.85
KNOWN_MIDSEASON_BREAKS = []  # e.g. specific rule clarifications that changed car behaviour

if race_year in REGULATION_BREAK_YEARS and race_number == 1:
    for all competitors:
        R̂ᵢ ← φ_reg · R̂ᵢ    # φ_reg = 0.60–0.75, calibrated per era
        kᵢ ← k∞              # full uncertainty reset
```

For 2026 specifically: the new power unit regulations (first race of the year is race 1 of the 2026 era) warrant a strong prior reset. With only 3 races of data at this writing, all ratings should carry high uncertainty regardless — the k∞ reset is self-enforcing here.

---

## 6. Layer 4: Prediction Assessment

This layer is how you evaluate which ELO variant is working best at any point in time.

### 6.1 Primary metric: Log-likelihood of race winner

For each race i, compute the probability that the actual winner j wins under the model:
```
P(j wins race i) = P(j survives all m−1 rounds) [endure-Elo]
```
The total log-likelihood over n races is:
```
LL = Σᵢ log P(actual winner i | model)
```
Higher LL = better model. This is how Powell benchmarks endure-Elo vs. speed-Elo (sum D(q,p) = 592 in favour of endure-Elo over 873 races).

### 6.2 Brier score (win probability calibration)

For each race, compute the Brier score for win prediction:
```
BS = (1/n) Σᵢ Σⱼ (P(j wins race i) − 𝟙(j won))²
```
Lower is better. Compare across: endure-Elo, speed-Elo, Xun's combined car+driver ELO, and a naive baseline (uniform 1/20 for each driver).

### 6.3 RMSE on finishing position

Following Xun, compute RMSE against actual finishing positions:
```
RMSE = √(1/n Σᵢ (predicted_position_i − actual_position_i)²)
```
For each driver per race, the model's expected finishing position is derived from the full probability distribution over rankings.

### 6.4 Calibration curve

Plot the model's predicted win probabilities against empirical win frequencies, binned by probability decile. A well-calibrated model should lie close to the diagonal. Poor calibration often reveals systematic bias (e.g., the model chronically underestimates high-probability favourites — a known issue with speed-Elo in F1 per Powell Figure 2).

### 6.5 Model comparison dashboard

Maintain a running comparison across the following model variants:

| Model | Role | Update cadence | Expected strength |
|---|---|---|---|
| **Endure-Elo (calibrated: k_max=0.8665, φ_race=0.999, φ_season=0.9472)** | **Primary engine** | After each race (round-by-round during race) | Best log-likelihood; robust DNF handling; fast |
| Endure-Elo (default params) | Regression baseline | After each race | Validates the calibration gain (+33.82 LL on holdout) |
| Speed-Elo (round-robin) | Lower bound benchmark | After each race | Weakest; quantifies the endure vs speed gap |
| Xun qualifying Rc | Car-pace standalone | After each qualifying | Independent of race outcomes; divergence from constructor ELO is a story signal |

The primary diagnostic is: **does the calibrated endure-Elo R̂ᵢ for driver i diverge significantly from the default-params endure-Elo after the same race?** Large divergences after unusual races (DNF clusters, regulation-era boundary races) reveal where parameter sensitivity matters most.

---

## 7. Layer 5: Story Angle Detection

This is the editorial layer — translating ELO signals into actionable narratives.

### 7.1 Trend detection

**Short-term momentum (within season):**
```
ΔR̂ᵢ_last_N = R̂ᵢ_current − R̂ᵢ_N_races_ago
```
Compute this for N = 3 and N = 6 races. A significant positive slope triggers:
- *"[Driver] is on the hottest streak in the field"*
- *"[Constructor] has made the biggest single-season gains"*

**Long-term trajectory (multi-season):**
Compare end-of-season R̂ values year-over-year. A driver showing consistent improvement signals a development story; a constructor rating falling despite driver transfers signals a car problem.

**Form vs. ability divergence:**
If a driver's trailing 6-race ΔR̂ is significantly above their career baseline R̂ (e.g. more than 1 standard deviation of the historical ΔR̂ distribution), they are "overachieving" relative to established ability — a story. The reverse (sustained drop below career baseline) signals a slump or car regression.

### 7.2 Outlier detection

**Per-race expected position:**
Given ratings before each race, compute the expected finishing position for each competitor using endure-Elo win probabilities. The uncertainty band around the expected position is derived from the driver's current k-factor: a high k-factor (new or recently volatile driver) means a wider band; a low k-factor (established rating) means a tighter one. Define the **surprise score**:
```
SurpriseScore = (actual_position − expected_position) / σ_position
```
Any |SurpriseScore| > 2.0 is a story candidate. The sign tells you direction: negative = better than expected, positive = worse.

**Calibrated vs. default uplift:**
```
UpliftScore = log(P_calibrated(winner) / P_default(winner))
```
When a driver with a history of "bouncing back" wins, the calibrated model (which has a higher k_max and therefore sharper rating spread) may assign them a meaningfully different probability than the default-params model — the uplift score flags races where the calibration makes the largest practical difference.

**Car/driver performance decoupling:**
Compare Xun's qualifying Rc (which updates after *each* qualifying session) against the race-outcome-based constructor endure-Elo. When they diverge significantly:
- High Rc (slow qualifying car) but high constructor race ELO → team is extracting value through race strategy, not raw pace. Story: *"[Team] is winning with strategy, not speed"*
- Low Rc (fast qualifying car) but falling constructor race ELO → car is quick but unreliable or badly managed in races. Story: *"[Team]'s pace isn't converting"*

**Teammate battles:**
Track the within-team ΔR̂ over the season. When the gap crosses a significance threshold:
- *"[Driver A] has statistically taken the upper hand over [Driver B] in their head-to-head"*
- Crossing zero (teammate catching up) is a story: *"[Driver B] is closing the internal war"*

### 7.3 Narrative trigger taxonomy

| Signal | Threshold | Story Angle |
|---|---|---|
| ΔR̂_3race > 0.5 | Top 3 in field for 3-race momentum | Hot streak / revival |
| ΔR̂_3race < −0.5 | Bottom 3 in field for 3-race momentum | Slump / crisis |
| SurpriseScore < −2.5 | Very surprising overperformance | Giant-killing / breakthrough |
| SurpriseScore > 2.5 | Very surprising underperformance | Shock result / car failure |
| Constructor ELO vs. Rc diverge > 1.5σ | Car/race gap | Strategy vs. pace narrative |
| Teammate ΔR̂ crosses zero (3+ races) | Intra-team shift | Internal war turning point |
| New driver's kᵢ drops below threshold | Established rating | "We now know who this driver is" |
| End-of-season R̂ vs. prior year > 0.8 | Multi-season growth | Best season of career / breakthrough year |
| Regulation-era comparison via φ-adjusted R̂ | Cross-era | All-time ranking / legacy narrative |

### 7.4 Contextual explainability filter

Before surfacing a story, cross-check with the Pasz (2025) variable list. An outlier is a *genuine* story if it cannot be explained by:
- Tyre compound selection mismatch
- Stint length (heavily worn tyres)
- Weather change (wet vs. dry)
- Safety Car timing

If the outlier coincides with a known situational factor, downgrade it. If it persists across multiple situational contexts, upgrade it.

---

## 8. Implementation Roadmap

### Phase 1: Historical baseline ✅ Complete
- Endure-Elo implemented on Ergast API data (1970–present)
- Qualifying-based Rc computed for all GPs since 2006
- k, k∞, φ, φ_season calibrated on pre-2015 data; validated on 2015–2021; holdout 2022–present
- Endure-Elo confirmed to outperform speed-Elo on log-likelihood, consistent with Powell's ~76% finding

### Phase 2: Driver/constructor separation ✅ Complete
- Teammate normalisation implemented
- α (constructor weight in raw driver ELO) estimated empirically
- α empirically estimated via OLS: `alpha = 0.7747` (2014–2024, `pitlane-elo estimate-alpha`)

### Phase 3: Hyperparameter calibration ✅ Complete

- `pitlane-elo calibrate` pipeline implemented (random search + Nelder-Mead local refinement)
- Temporal split anchored to regulation changes: warmup 1970–1979, calibration 1980–2013, validation 2014–2021, holdout 2022–2025
- Best config: `k_max = 0.8665`, `phi_race = 0.9990`, `phi_season = 0.9472`

| Window | Log-likelihood | Races |
|--------|---------------|-------|
| Calibration (1980–2013) | −1261.06 | 566 |
| Validation (2014–2021) | −252.35 | 160 |
| Holdout (2022–2025) | **−142.26** | 92 |
| Baseline (default params, holdout) | −176.08 | 92 |

Holdout improvement vs. baseline: **+33.82 log-likelihood**.

### Phase 4: Story detection engine

Build on calibrated endure-Elo R̂ᵢ signals and k-factor uncertainty:

- **Trend signals:** compute trailing 3-race and 6-race ΔR̂ per driver; flag top/bottom 3 in field
- **Outlier signals:** per-race SurpriseScore from expected vs. actual position; k-factor-based uncertainty band; flag |SurpriseScore| > 2.0
- **Car/driver decoupling:** compare Xun Rc (qualifying) against constructor endure-Elo; flag divergences > 1.5σ
- **Teammate delta:** track within-team ΔR̂; flag crossings and sustained gaps
- **Contextual explainability filter:** cross-check against race condition flags (wet, SC/VSC, sprint format, tyre compound) before surfacing a story
- **Tune thresholds against known historical stories:**
  - Leclerc 2019 breakthrough (Bahrain, Italy): R̂ spike and k-factor drop confirming new ability level
  - Hamilton 2021 mid-season form dip: trailing 6-race ΔR̂ turning negative
  - Ferrari 2022 reliability crisis: constructor ELO diverging negative from Rc
  - McLaren 2023 late-season surge: constructor ELO positive step mid-season
- **2026 live mode:** With 3 races of data, k-factors are still high — uncertainty bands are wide. Story engine runs in conservative mode; only surface signals where the SurpriseScore is unambiguous (> 2.5). Ratings stabilise meaningfully after races 6–8.

### Phase 5: Live updating
- Connect to live results feed (FastF1 Python library is the standard tool)
- Apply OU-based time discounting using race weekend start timestamps, not race number
- Update endure-Elo round by round during a race for in-race story detection
- Surface stories immediately after each race result is confirmed; re-evaluate after post-race steward decisions that change finishing order

---

## 9. Key Design Decisions and Trade-offs

**Why endure-Elo as the primary engine?**
Endure-Elo was empirically evaluated against the van Kesteren Bayesian model across calibration (1980–2013), validation (2014–2021), and holdout (2022–2025) windows. Endure-Elo outperformed the Bayesian model on log-likelihood in every window. The Bayesian model's theoretical advantages — explicit posterior uncertainty, native driver/constructor decomposition — did not translate to prediction accuracy. Endure-Elo also updates in real time (round-by-round during a race) and runs in milliseconds, which the MCMC-based Bayesian model cannot match. The Glicko-style variable k-factor provides a practical uncertainty proxy without requiring full posterior inference.

**Why these hyperparameters (k_max=0.8665, phi_race=0.999, phi_season=0.9472)?**
The `pitlane-elo calibrate` pipeline (PR #155) ran a random search over `(k_max, phi_race, phi_season)` followed by Nelder-Mead local refinement. The temporal split was anchored to regulation changes: warmup 1970–1979 (burn-in, unscored), calibration 1980–2013, validation 2014–2021 (2014 hybrid era generalization), holdout 2022–2025. The best config improved holdout log-likelihood by +33.82 vs. default parameters. Key findings: `phi_race ≈ 1.0` means within-season forgetting is negligible — driver ability is very stable race-to-race and only meaningful decay happens at the season boundary. `k_max = 0.8665` is substantially higher than the default 0.5, allowing new or resurgent drivers to establish ratings faster.

**Why endure-Elo rather than speed-Elo?**
Powell demonstrates this conclusively: speed-Elo severely over-penalises Vettel, Bottas, Verstappen, and Leclerc when crashes or mechanical failures send them to the back. Endure-Elo treats those results as relatively uninformative (consistent with a low failure-rate driver just being unlucky). Story detection built on speed-Elo would generate excessive false-positive "crisis" stories after every DNF — particularly problematic post-2023 where crashes and mechanicals cannot be cheaply separated.

**Why keep Xun's qualifying Rc?**
Endure-Elo uses race finishing positions only. Qualifying times give a pure car-pace signal that is independent of race-day strategy, tyre management, and luck. When Rc (qualifying) diverges from the constructor race ELO, that divergence is a story in its own right: the car is fast but something is being lost on race day, or vice versa. Rc also updates *before* the race, giving a pre-race prior on car performance that the race-outcome model cannot provide.

**Wet races and street circuits:**
Research (van Kesteren & Bergkamp; Pasz) shows these are genuinely distinct contexts. The endure-Elo implementation should maintain context-specific rating tracks for wet and street circuits (Section 3.3), or at minimum flag context-switching explicitly as a story opportunity — *"Which driver genuinely elevates in the wet?"*

---

## 10. Prediction Accuracy Benchmark Summary

Actual results from the calibration pipeline (PR #155). Baseline uses default params (`k_max=0.5`, `phi_race=0.99`, `phi_season=0.90`).

| Window | Races | Endure-Elo (default) LL/race | Endure-Elo (calibrated) LL/race |
|--------|-------|------------------------------|--------------------------------|
| Calibration 1980–2013 | 566 | — | **−2.228** (−1261.06 total) |
| Validation 2014–2021 | 160 | — | **−1.577** (−252.35 total) |
| Holdout 2022–2025 | 92 | −1.914 (−176.08 total) | **−1.546** (−142.26 total) |

**Holdout improvement: +33.82 log-likelihood (+19.1% reduction in loss vs. default params)**

For reference from Powell (2023) paper benchmarks on 873 races (1950–2022):

| Metric | Baseline (uniform) | Speed-Elo | Endure-Elo |
|---|---|---|---|
| Win LL/race | ~−3.0 | ~−2.8 | ~−2.4 |
| Brier score | 0.095 | ~0.085 | ~0.075 |
| Winner prob (median) | 5.0% | ~9.1% | ~15.5% |
| Race-level win rate vs speed-Elo | — | baseline | **76.3%** |

The calibrated endure-Elo (−1.546 LL/race on holdout) substantially improves on both Powell's −2.4 benchmark figure and the default-params result, reflecting both the calibrated hyperparameters and the higher overall quality of 2022–2025 F1 data.
