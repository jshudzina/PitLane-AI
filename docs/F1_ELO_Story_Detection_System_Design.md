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

The system has five layers: **Rating Computation**, **Separation** (driver vs. constructor), **Temporal Modelling**, **Prediction Assessment**, and **Story Detection**.

```
┌─────────────────────────────────────────────────────────────────┐
│                   RAW DATA INPUTS                               │
│  Race results · Qualifying times · Weather · Track type · DNFs  │
└────────────────────────┬────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   LAYER 1: RATINGS  │
              │  Driver endure-Elo  │
              │  Constructor Elo    │
              │  Qualifying Rc      │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  LAYER 2: SEPARATION│
              │  Teammate normaliz. │
              │  Driver ÷ Car split │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  LAYER 3: TEMPORAL  │
              │  k-factor decay     │
              │  AR(1) discounting  │
              │  Seasonal resets    │
              └──────────┬──────────┘
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

4. **DNF handling:** Treat mechanical DNFs and crash retirements differently:
   - For a driver who *crashed out* (driver fault more likely): include in ELO, ranked at their elimination position
   - For a driver with a *mechanical failure*: exclude from that race's ELO computation entirely (following Xun's finding that excluding DNFs improves RMSE from 0.46 → 0.44)
   - Record DNF frequency as a *separate* signal for story detection (high DNF rate = reliability story)

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

### 5.2 Between-race time discounting (AR(1))

Between rounds separated by h time steps, apply Powell's discounting:
```
R̂ᵢ,t ← φʰ · R̂ᵢ,t₋ₕ
kᵢ,t ← kᵢ,t₋ₕ + (1 − φ²ʰ)(k∞ − kᵢ,t₋ₕ)
```
The parameter φ encodes how quickly ability is assumed to decay. A suggested value for F1 is φ ≈ 0.99 per race (abilities are fairly stable race-to-race within a season), dropping to φ ≈ 0.95 between seasons to allow for car development gains/losses.

**k∞** (the asymptotic variance) should reflect the realistic spread of driver and constructor ability. A reasonable starting estimate from Powell's guidance: `k∞^(1/2) ≈ 0.75 × log(q/(1−q))` where q is the probability the stronger competitor beats the weaker one in a given matchup — try q = 0.7 as a prior for F1.

### 5.3 Seasonal resets

At the start of each new season:
- Apply an additional φ_season discount to all R̂ values (e.g. φ_season = 0.90), pulling ratings toward 0
- Reset k-factors toward k∞ (increased uncertainty reflects new regulations, new car, etc.)
- This prevents ratings carrying too much historical inertia into a totally new technical era (e.g. the 2022 regulation change)

**Regulation change flag:** For major regulation changes (2014 hybrid era, 2022 ground-effect era), apply a larger reset (φ_reg = 0.70 or even full reset) and set k to k∞ for all competitors.

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

| Model | Description | Expected Strength |
|---|---|---|
| Endure-Elo (fixed k) | Powell base version | Best single baseline |
| Endure-Elo (variable k) | Powell extended | Best for long-horizon tracking |
| Speed-Elo (round-robin) | Xun / standard approach | Weaker, good benchmark |
| Car + Driver combined | Xun qualifying Rc + driver ELO | Strong for qualifying-heavy tracks |
| Bayesian ROL | van Kesteren approach | Gold standard but slower to update |

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

### Phase 1: Historical baseline (recommended)
- Implement endure-Elo on Ergast API data (1970–present; https://ergast.com/mrd)
- Compute qualifying-based Rc for all GPs since 2006 (when qualifying data is reliable)
- Calibrate k, k∞, φ, φ_season on pre-2015 data; validate on 2015–2021; hold out 2022–present
- Measure log-likelihood, Brier score, RMSE against speed-Elo baseline
- Expected: replicate Powell's finding that endure-Elo wins ~76% of race-level comparisons

### Phase 2: Driver/constructor separation
- Implement teammate normalisation
- Estimate α (constructor weight in raw driver ELO) empirically
- Compare against van Kesteren & Bergkamp posterior estimates as ground truth
- Target: driver ratings that correlate strongly (>0.7) with van Kesteren's θ_d posteriors

### Phase 3: Story detection engine
- Build trend and outlier computation pipeline (rolling windows, surprise scores)
- Implement contextual filter using race condition flags (wet, SC deployed, etc.)
- Tune narrative thresholds against historical "known stories" (e.g. Leclerc's 2019 breakthrough, Hamilton's 2021 form dip mid-season, Ferrari's 2022 reliability crisis)

### Phase 4: Live updating
- Connect to live results feed (FastF1 Python library is the standard tool)
- Update endure-Elo round by round during a race for in-race story detection
- Surface stories immediately after each race result is confirmed

---

## 9. Key Design Decisions and Trade-offs

**Why endure-Elo over speed-Elo?**
Powell demonstrates this conclusively: speed-Elo severely over-penalises Vettel, Bottas, Verstappen, and Leclerc when crashes or mechanical failures send them to the back. Endure-Elo treats those results as relatively uninformative (consistent with a low failure-rate driver just being unlucky). Story detection built on speed-Elo would generate excessive false-positive "crisis" stories after every DNF.

**Why not just use the van Kesteren Bayesian model?**
The Bayesian ROL is the most rigorous approach but it's a batch model — it requires re-fitting MCMC chains to include new data. Endure-Elo is an online algorithm that updates after each race with negligible computation. For a story detection system that needs to produce output minutes after a race ends, the endure-Elo is the practical choice. The van Kesteren model's findings (especially the 88/12 split and driver trajectory plots) serve as the *calibration target* rather than the live engine.

**Why keep Xun's qualifying Rc?**
It updates every qualifying session, giving you a pure car-pace signal that's independent of race outcomes. When a car qualifies fast but race results disappoint (or vice versa), that divergence is itself a story. The Rc also adjusts naturally for track-type variation (e.g. a high-downforce car may have a very different Rc at Monaco vs. Monza).

**Wet races and street circuits:**
Van Kesteren & Bergkamp show these are genuinely distinct contexts. Mixing them into a single rating creates noise. Maintain separate context ratings but weight them lightly (fewer events per season), and explicitly flag context-switching as a story opportunity — *"Which driver genuinely elevates in the wet?"*

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
