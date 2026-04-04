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

---

### Paper 4 — Pasz (2025): *Determinants of Lap Times in F1, 2019–2025*
**Not an ELO paper, but provides critical context for what drives lap-time variance.** Using Fixed Effects and GAMM on lap-level data:

- Time-varying, race-specific factors (tyre compound, stint length, pit stops, track/weather conditions) explain *more* variance than static team/driver identity
- Non-linear tyre degradation effects discovered via GAMM smooth terms
- Safety Car and VSC periods create lagged performance effects on subsequent laps

**Implication for story detection:** A large deviation in an ELO-based expected finish may simply reflect known situational factors (e.g., a well-timed pit on a Safety Car). A robust story detector should try to flag whether an outlier is "explainable" vs. "genuinely surprising." Pasz's variable taxonomy is the right checklist for the explainable side.

---

## 2. System Architecture

The system has two parallel tracks that feed a shared story detection layer. The **Bayesian track** (van Kesteren & Bergkamp) is the primary rating engine, running after each race weekend. The **endure-Elo track** (Powell) is the real-time supplement, running round-by-round during a race for live story signals. Both feed into prediction assessment and story detection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RAW DATA INPUTS                                  │
│       Race results · Qualifying times · Weather · Track type · DNFs         │
└──────────────────────┬──────────────────────────┬──────────────────────────┘
                       │                          │
         ┌─────────────▼──────────┐   ┌───────────▼────────────┐
         │  PRIMARY: BAYESIAN     │   │  REAL-TIME: ENDURE-ELO │
         │  van Kesteren & Bergk. │   │  Powell (2023)         │
         │  Fit in PyMC after     │   │  Updates round-by-     │
         │  each race weekend     │   │  round during race     │
         │  ─────────────────     │   │  ──────────────────    │
         │  θ_d  long-term driver │   │  R̂ᵢ  driver rating    │
         │  θ_ds seasonal form    │   │  AR(1) + OU spacing    │
         │  θ_t  constructor      │   │  Robust DNF handling   │
         │  θ_ts seasonal car     │   │  Qualifying Rc         │
         │  Credible intervals    │   │                        │
         └─────────────┬──────────┘   └───────────┬────────────┘
                       │                          │
                       └────────────┬─────────────┘
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
where α is a learned weighting (roughly α ≈ 0.88 / 0.12 ≈ 7.3 in log-odds terms, but should be estimated empirically via cross-validation).

Alternatively, borrow the van Kesteren parameterisation:
```
ϑ_competitor = θ_driver + θ_constructor
```
and estimate both via a joint maximisation — the endure-Elo algorithm can be extended to do this simultaneously.

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

Practically, set a floor `k_min` (e.g. 0.05) so established ratings still respond to real form changes, and a ceiling `k_max` (e.g. 0.5) for new entrants.

### 5.2 Between-race time discounting (AR(1) / Ornstein-Uhlenbeck)

Between rounds separated by h time steps, apply Powell's discounting:
```
R̂ᵢ,t ← φʰ · R̂ᵢ,t₋ₕ
kᵢ,t ← kᵢ,t₋ₕ + (1 − φ²ʰ)(k∞ − kᵢ,t₋ₕ)
```
The parameter φ encodes how quickly ability is assumed to decay. A suggested value for F1 is φ ≈ 0.99 per race (abilities are fairly stable race-to-race within a season), dropping to φ ≈ 0.95 between seasons to allow for car development gains/losses.

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
| **van Kesteren (PyMC)** | **Primary engine** | After each race weekend | Best calibrated ratings; proper uncertainty; native driver/car split |
| Endure-Elo (variable k, robust) | Real-time supplement | Round-by-round during race | Best live signal; handles DNFs well; fast |
| Endure-Elo (fixed k) | Sanity check baseline | After each race | Simple benchmark; should be outperformed by both above |
| Speed-Elo (round-robin) | Lower bound benchmark | After each race | Weakest; included to quantify the endure vs speed gap |
| Xun qualifying Rc | Car-pace standalone | After each qualifying | Independent of race outcomes; divergence from θ_t is a story signal |

The primary diagnostic is: **does van Kesteren's θ_d posterior mean for driver i correlate with endure-Elo's R̂ᵢ after the same race?** Strong agreement validates both; systematic divergence reveals where the models differ in their treatment of information (uncertainty quantification, DNF handling, car/driver attribution).

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
If a driver's seasonal form parameter (equivalent to θ_ds in van Kesteren) is significantly positive relative to their long-term ability (θ_d), they are "overachieving" — a story. Conversely, underachieving relative to long-term form level is also a story (pressure, car issues, personal factors).

### 7.2 Outlier detection

**Per-race expected position:**
Given ratings before each race, compute the expected finishing position for each competitor (and a confidence interval). Define the **surprise score**:
```
SurpriseScore = (actual_position − expected_position) / σ_position
```
Any |SurpriseScore| > 2.0 is a story candidate. The sign tells you direction: negative = better than expected, positive = worse.

**Probability uplift:**
```
UpliftScore = log(P_endureElo(winner) / P_speedElo(winner))
```
When a driver with a history of "bouncing back" wins, endure-Elo had them higher than speed-Elo — the uplift score flags this systematically.

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
- Driver ratings cross-validated against van Kesteren & Bergkamp θ_d posteriors
- Target correlation >0.7 with van Kesteren achieved

### Phase 3: van Kesteren (PyMC) primary engine + Story detection

**3a — Implement van Kesteren & Bergkamp in PyMC** (this replaces the heuristic α estimation from Phase 2 and validates the Phase 2 teammate normalisation):

*Step 1 — Minimal viable model (single season, no seasonal form):*
```python
import pymc as pm, pytensor.tensor as pt, numpy as np, arviz as az

# Inputs:
# race_orders: list of n_races arrays, each giving driver indices in finishing order
# driver_team: array of shape (n_drivers,) mapping driver → team index
# dnf_mask: bool array, True = DNF (excluded from that race's likelihood)

with pm.Model() as f1_base:
    σ_d = pm.HalfNormal("σ_d", sigma=1.0)
    σ_t = pm.HalfNormal("σ_t", sigma=1.0)

    θ_d = pm.Normal("θ_d", mu=0, sigma=σ_d, shape=n_drivers)
    θ_t = pm.Normal("θ_t", mu=0, sigma=σ_t, shape=n_teams)

    η = θ_d + θ_t[driver_team]   # latent strength, shape (n_drivers,)

    # Plackett-Luce log-likelihood via pm.Potential.
    # For a race with finishing order [d_0, ..., d_{m-1}]:
    #   log p(order) = sum_k [ η[d_k] − logsumexp(η[d_k:]) ]
    # Using pm.Potential avoids creating observed RVs over a mutable Python list,
    # which would produce incorrect symbolic graph construction in PyTensor.
    for r, order in enumerate(race_orders):
        η_r = η[order]   # strengths in finishing order, shape (m,)
        lse = pt.stack([pt.logsumexp(η_r[k:], axis=0) for k in range(len(order) - 1)])
        pm.Potential(f"race_{r}", pt.sum(η_r[:-1] - lse))

    trace_base = pm.sample(1000, tune=1000, target_accept=0.9, return_inferencedata=True)
```

Validate: θ_d posterior means should reproduce the known 2019 hierarchy (Hamilton >> Verstappen >> Leclerc/Bottas tier >> midfield). If they do, the model is correctly specified before adding complexity.

*Step 2 — Add seasonal form deviations:*
```python
    θ_ds = pm.Normal("θ_ds", mu=0, sigma=pm.HalfNormal("σ_ds", 0.5), shape=n_drivers)
    θ_ts = pm.Normal("θ_ts", mu=0, sigma=pm.HalfNormal("σ_ts", 0.5), shape=n_teams)
    η = θ_d + θ_t[driver_team] + θ_ds + θ_ts[driver_team]
```

The seasonal form parameters (θ_ds, θ_ts) are the key addition for story detection — they encode "is this driver/team performing above or below their long-run ability right now?"

*Step 3 — Cross-season carry-forward priors:*

After fitting season *s*, extract posterior means and standard deviations for each driver's θ_d. Use these as the prior for season *s+1*:

```python
# After fitting season s:
θ_d_mean_s  = trace_s.posterior["θ_d"].mean(("chain", "draw")).values
θ_d_std_s   = trace_s.posterior["θ_d"].std(("chain", "draw")).values

# Season s+1 prior — shrink std slightly to reflect one more year of uncertainty:
with pm.Model() as f1_season_next:
    θ_d = pm.Normal("θ_d", mu=θ_d_mean_s, sigma=θ_d_std_s * 1.2, shape=n_drivers)
    # ... rest of model
```

The 1.2× inflation on σ represents the additional uncertainty from off-season change (car development, team switches, fitness). Tune this multiplier empirically.

*Step 4 — Context covariates (wet / street):*

Add a binary covariate for wet races and street circuits. Rather than separate rating tracks (which fragment an already-small sample), encode context as a fixed effect on the latent strength:

```python
    β_wet    = pm.Normal("β_wet",    mu=0, sigma=0.5, shape=n_drivers)  # driver-level: wet skill is individual
    β_street = pm.Normal("β_street", mu=0, sigma=0.5, shape=n_teams)    # team-level: street performance is car-driven (low-speed aero, cooling)
    η = θ_d + θ_t[driver_team] + θ_ds + θ_ts[driver_team] \
        + is_wet[r] * β_wet + is_street[r] * β_street[driver_team]
```

*Validation target for Phase 3a:* θ_d posterior means should correlate >0.75 with van Kesteren & Bergkamp's published posteriors for the 2014–2021 period. The credible intervals on θ_t should reproduce their ~88% constructor / ~12% driver decomposition (i.e., σ_t >> σ_d in the posterior).

**3b — Story detection engine** (build on van Kesteren posteriors):
- Replace raw R̂ᵢ signals with posterior means and credible intervals from θ_d + θ_ds
- Trend signals: is θ_ds for driver i trending significantly positive/negative across the last 3–5 races?
- Outlier signals: did this race result fall outside the 95% predictive interval?
- Implement contextual explainability filter using race condition flags (wet, SC, VSC, sprint format)
- Tune narrative thresholds against known historical stories:
  - Leclerc 2019 breakthrough (Bahrain, Italy): θ_ds spike above θ_d baseline
  - Hamilton 2021 mid-season form dip: θ_ds temporarily negative relative to θ_d
  - Ferrari 2022 reliability crisis: θ_ts diverges sharply negative from θ_t trend
  - McLaren 2023 late-season surge: θ_ts positive step mid-season
- **2026 live mode:** With 3 races of data, posteriors on θ_d are wide — this is correct and should be communicated. Story engine runs in high-uncertainty mode; only surface signals with posterior probability > 0.90. Ratings stabilise meaningfully after races 6–8.

### Phase 4: Live updating
- Connect to live results feed (FastF1 Python library is the standard tool)
- Apply OU-based time discounting using race weekend start timestamps, not race number
- Update endure-Elo round by round during a race for in-race story detection
- Surface stories immediately after each race result is confirmed; re-evaluate after post-race steward decisions that change finishing order

---

## 9. Key Design Decisions and Trade-offs

**Why van Kesteren & Bergkamp as the primary engine?**
The main historical argument for using endure-Elo as the live engine was that MCMC is too slow for real-time updates. This doesn't hold: there is at least a week between every F1 race, and a single season of ~20 drivers × ~23 races fits in Stan or PyMC in seconds to a few minutes. Van Kesteren gives proper posterior uncertainty (credible intervals on θ_d and θ_t), handles the driver/constructor decomposition natively, and eliminates the need to estimate α manually as done in Phase 2. The cost of the heuristic approach (teammate normalisation + empirical α) is that it approximates what the Bayesian model does exactly.

**What role does endure-Elo now play?**
It is the **real-time supplement during a race weekend**. Van Kesteren is a batch model and cannot update mid-race as retirements happen. Endure-Elo fills this gap: it updates round-by-round as the race unfolds, producing live story signals (sudden championship shift, underdog breakthrough, reliability crisis forming). After the race weekend, the van Kesteren model re-fits with the new results and becomes the authoritative rating again. Endure-Elo also retains value as a fast sanity check — if it diverges strongly from van Kesteren posteriors after a race, that is itself worth investigating.

**Why endure-Elo rather than speed-Elo for the real-time role?**
Powell demonstrates this conclusively: speed-Elo severely over-penalises Vettel, Bottas, Verstappen, and Leclerc when crashes or mechanical failures send them to the back. Endure-Elo treats those results as relatively uninformative (consistent with a low failure-rate driver just being unlucky). Story detection built on speed-Elo would generate excessive false-positive "crisis" stories after every DNF — particularly problematic post-2023 where crashes and mechanicals cannot be cheaply separated.

**Why season-by-season fitting rather than a joint multi-decade model?**
A joint model spanning 1970–present would in principle allow cross-era comparisons (Hamilton vs. Senna) but requires specifying how driver skill and constructor advantage evolve across major technical eras — a non-trivial modelling choice with significant identifiability risks. Season-by-season fitting with **informative carry-forward priors** is the pragmatic alternative: the posterior means for θ_d from season *s* become the prior means for season *s+1*, providing soft continuity without the complexity. Cross-era comparison is noted as a future extension but is not blocking.

**Why keep Xun's qualifying Rc?**
The van Kesteren model uses race finishing positions only. Qualifying times give a pure car-pace signal that is independent of race-day strategy, tyre management, and luck. When Rc (qualifying) diverges from θ_t (race constructor rating), that divergence is a story in its own right: the car is fast but something is being lost on race day, or vice versa. Rc also updates *before* the race, giving a pre-race prior on car performance that the race-outcome model cannot provide.

**Wet races and street circuits:**
Van Kesteren & Bergkamp show these are genuinely distinct contexts. The PyMC implementation should include context indicators as covariates or maintain separate seasonal form parameters for wet/street events, weighted lightly given the small sample size per season. Flag context-switching explicitly as a story opportunity — *"Which driver genuinely elevates in the wet?"*

---

## 10. Prediction Accuracy Benchmark Summary

Based on the papers, here are the expected performance levels:

| Metric | Baseline (uniform) | Speed-Elo | Endure-Elo | van Kesteren Bayes |
|---|---|---|---|---|
| Win LL/race | ~−3.0 | ~−2.8 | ~−2.4 | ~−2.3 (estimated) |
| Brier score | 0.095 | ~0.085 | ~0.075 | ~0.070 (estimated) |
| Winner prob (median) | 5.0% | ~9.1% | ~15.5% | ~18% (estimated) |
| RMSE (position) | ~5.8 | ~0.46* | ~0.42* | ~0.40* (estimated) |

*Xun's RMSE figures; direct comparisons require identical test sets

The endure-Elo system represents the best practical trade-off: near-Bayesian accuracy with real-time updateability. Any residual gap vs. the Bayesian benchmark represents the information value of explicit uncertainty quantification, which can be partially recovered through Glicko-style variable k-factors.
