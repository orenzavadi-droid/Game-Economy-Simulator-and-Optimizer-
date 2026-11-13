# Economy balancing — decision memo (synthetic portfolio model)

**Decision question:** In a 30-day single-currency F2P model, can we reduce days when an active player cannot afford a progression upgrade, while protecting progression throughput and monitoring currency accumulation?

## Recommendation from the training search

Selected **candidate C20** after evaluating 27 preregistered-on-code combinations using four training seeds. Its configuration relative to the baseline is:

- Quest rewards **×1.10**; upgrade prices **×0.85**; optional cosmetic purchase propensity **×1.30**.
- This is the highest objective score among candidates meeting the defined training guardrails, **not a production recommendation**.
- Scoring and guardrails were defined before the four separate holdout seeds were evaluated; see `docs/MODEL_CARD.md`.

## Holdout model results

| Metric | Baseline → candidate (4 paired holdout seeds) |
|---|---|
| Upgrade affordability gap | 37.31% → 31.44% (paired change: -5.87 percentage points) |
| Progression upgrades per original install | 2.02 → 2.21 (paired change: +0.20) |
| Median soft-coin balance among survivors | 160.00 coins → 144.40 coins (paired change: -15.60 coins) |
| Soft currency sources / sinks | 1.04 → 1.08 (paired change: +0.03) |
| Share of active play-days with surplus wallets | 1.39% → 4.10% (paired change: +2.71 percentage points) |
| Exact-day D7 return rate | 25.87% → 25.86% (paired change: -0.01 percentage points) |

**Interpretation:** This candidate makes upgrades easier to afford and raises modeled progression volume. The median survivor wallet declines under the assumed decision rules.

**Tradeoff:** The sources/sinks ratio **rises**, sink utilization declines, and the percentage of active play-days in the defined surplus-wallet state **increases**. This is **not unambiguously better**. It illustrates why reducing progression friction can conflict with controlling currency surplus. An economy designer would need to refine the objective, evaluate segmentation and likely test alternatives before taking action.

The tiny difference in D7 return cannot be interpreted as proof of no retention effect. Retention's modeled response to friction is small **by assumption**. There is no empirical price elasticity or revenue estimate here.

## Implementation guardrails and open questions

1. Validate with product-specific event data and genre context before setting price/reward policy.
2. Measure progression at each tier, with special attention to Casual players and players approaching content walls.
3. Inspect **the fraction of play-days with unaffordable upgrades** alongside the **frequency of over-accumulated wallets** rather than optimizing one statistic in isolation.
4. Investigate optional sinks carefully, making sure they remain optional and do not manipulate spending choices.
5. If real data are available, calibrate the rules and follow with an appropriately designed randomized experiment; do not claim causal uplift from this simulation.

## Reproduction and verification

- Run `python -m src.run_analysis` from the repository root; the deterministic training/holdout search, event log, SQLite DB, and data outputs are regenerated.
- Run `python -m pytest -q` to check identity, reproducibility, and cohort logic.
- Review `sql/04_wallet_reconciliation.sql` and its output to verify that every simulated wallet is conserved.
- Open `reports/interactive_dashboard.html` locally to explore the scenario tradeoffs and stress tests.

**Scope:** A hypothetical soft-currency model, not a product release, live customer study, or real-money economy.
