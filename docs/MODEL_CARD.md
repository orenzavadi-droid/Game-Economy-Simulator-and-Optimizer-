# Model card — Assumption-driven soft-currency economy

**Purpose:** A publicly reproducible practice simulator for an entry-level Game Economist portfolio. It is intentionally generalized across progression-based F2P games; it is **not** a trained model of any published game.

## A. Population and time

- A single original cohort of 5,000 synthetic installs, observed for 30 simulated post-install days.
- Three latent personas assigned at Day 0: Casual 50%, Regular 35%, Engaged 15%.
- Independent random draws for daily play, second quest, upgrade interest, cosmetic interest and churn, with fixed seed per run.
- A churned account stops playing. Its wallet balance stays on the ledger; virtual coins are not destroyed automatically by inactivity.
- A 30-day D7 return is an activity event on the exact seventh day divided by **all original installs**, not just surviving players.

## B. Economy loop and assumed choice rules

1. If the player is alive, a persona-dependent random draw decides whether they are active that day.
2. Active players receive a login bonus and complete 1 or 2 quests. The quest bonus is scaled by the reward lever.
3. The cost of the next progression upgrade grows geometrically with already purchased upgrades. Eligible active players buy with a persona-dependent probability.
4. After reaching level 2, active players may buy optional cosmetics if they can afford them. Optional purchase propensity can be scaled without assuming those cosmetics unlock progression.
5. A player can become inactive permanently after daily activity based on a persona-dependent base hazard and small, assumed hazard adjustments for prolonged stalled progression or surplus wallets.
6. Per-player wallets are reconciled to event logs: `initial_wallet + sum(coin_delta) = ending_wallet`. Negative wallets are forbidden.

### Assumptions (not estimates)

| Setting | Casual | Regular | Engaged |
|---|---:|---:|---:|
| Day-level play probability conditional on alive | .45 | .60 | .75 |
| Daily churn hazard (baseline) | .15 | .10 | .075 |
| Upgrade probability, conditional on eligibility | .54 | .72 | .85 |
| Cosmetic purchase probability, conditional on eligibility | .12 | .20 | .27 |
| Second quest probability, conditional on activity | .26 | .50 | .72 |

Baseline coins: 100 initial, 12 login bonus, 26 per quest, 68 first upgrade (each successive ×1.34), and 42 optional cosmetic. Game-wide nominal rewards and costs can be changed in code.

### Policy levers

- `reward_multiplier`: quest reward amount, not login bonus.
- `upgrade_price_multiplier`: every progression upgrade cost.
- `cosmetic_offer_multiplier`: **probability** of a cosmetic offer purchase conditional on eligibility, not price or cash conversion.
- `activity_multiplier`, `churn_multiplier`: modeling stress-test levers, not measured interventions.

## C. Metrics and denominators

| Metric | Definition | Caveat |
|---|---|---|
| Exact-day D1 / D7 / D30 | active players on Day N / original installs | Based on synthetic retention process |
| Affordability gap | active play-days where balance after daily income is below the next upgrade cost, before purchase decision / all active play-days | Does not imply the player wanted an upgrade |
| Upgrades / install | total purchases of progression upgrades / all original installs | Performance depends on fixed behavior propensities |
| Surplus active play-days | active play-days ending with wallet ≥ 3 × next upgrade price / all active play-days | Proxy for over-accumulation, arbitrary threshold |
| Source/sink ratio | total soft currency minted / total coins spent | A flow ratio, **not** a direct inflation measure |
| Sink utilization | total spending / total minted currency | Does not mean gameplay is better when higher |
| Survivor median wallet | median end wallet among players not churned by final day | Survivorship selection affects the value |
| Net issuance | minted soft coins less spent soft coins | Original endowment excluded |
| Upgrade by Day 7 | installs with first upgrade on or before Day 7 / all installs | Not a time-to-event causal analysis |

## D. Optimization and holdout discipline

The 27 candidates are a fixed Cartesian grid (3 quest reward levels × 3 upgrade pricing levels × 3 optional sink propensities). Four training seeds are shared across candidates and a baseline; four disjoint holdout seeds are reserved for evaluation of the selected candidate and baseline only.

**Training guardrails:** the candidate's mean affordability gap must not exceed baseline; average upgrades must be ≥98% baseline; median survivor wallet ≤115% baseline; source-to-sink ratio ≤110% baseline; Casual persona affordability gap ≤ baseline +1 percentage point. These design limits are chosen for illustration and **are not industry standards**.

**Training decision score** = `3 × affordability-gap improvement (pp) + 0.9 × upgrade throughput improvement (%) + 0.6 × surplus reduction (pp) − 0.6 × positive wallet inflation (%)`.

The search filters candidates by the guardrails and picks the highest training score. The separate holdout is evaluated exactly once for reporting, not for selection. Per-seed minimum and maximum paired deltas show seed sensitivity, **not confidence intervals from real player observations**. A simple three-objective Pareto flag highlights nondominated feasible candidates (minimize affordability gap, maximize throughput, minimize survivor median wallet).

**What this does not establish:** The rule set is not calibrated; a holdout seed only validates robustness to pseudorandom sampling of this model. It cannot establish external generalizability or a causal effect on real human players. The score does not factor genuine monetization, fairness, or consent data.

## E. Data, ethics and limitations

No proprietary or personally identifying player data. Every event is generated locally. All behavioral parameters are assumed. The project does not measure revenue, ARPU, ARPDAU, LTV, ad engagement, player lifetime, actual retention uplift, real-money pricing, or actual player welfare. A decision-maker would need calibrated data and real experimentation before deploying a policy. An optional sink should not be used to engineer harmful spending pressure.

## F. Further validation needed for a live title

Reconstruct event instrumentation from live logs; monitor sources and sinks segmented by level, tenure and behavior; calibrate the daily play and purchase choice rules; simulate more complex scarcity dynamics; define product-specific progression and player experience guardrails; use responsible A/B testing to evaluate true effects.
