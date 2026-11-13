"""Generate an evidence-qualified economic design decision memo."""
from pathlib import Path
import pandas as pd
import json
ROOT=Path(__file__).resolve().parents[1]
r=ROOT/'reports'; d=ROOT/'data'
v=pd.read_csv(d/'optimizer_validation_summary.csv').set_index('metric')
s=json.loads((r/'optimization_selection.json').read_text())


def rate(metric, suffix='%', scale=100):
    row=v.loc[metric]
    return f"{row.baseline_mean*scale:.2f}{suffix} → {row.recommended_mean*scale:.2f}{suffix} (paired change: {row.paired_delta_mean*scale:+.2f}{suffix})"


content=f'''# Economy balancing — decision memo (synthetic portfolio model)

**Decision question:** In a 30-day single-currency F2P model, can we reduce days when an active player cannot afford a progression upgrade, while protecting progression throughput and monitoring currency accumulation?

## Recommendation from the training search

Selected **candidate {s['selected_candidate']}** after evaluating 27 preregistered-on-code combinations using four training seeds. Its configuration relative to the baseline is:

- Quest rewards **×{s['reward_multiplier']:.2f}**; upgrade prices **×{s['upgrade_price_multiplier']:.2f}**; optional cosmetic purchase propensity **×{s['cosmetic_offer_multiplier']:.2f}**.
- This is the highest objective score among candidates meeting the defined training guardrails, **not a production recommendation**.
- Scoring and guardrails were defined before the four separate holdout seeds were evaluated; see `docs/MODEL_CARD.md`.

## Holdout model results

| Metric | Baseline → candidate (4 paired holdout seeds) |
|---|---|
| Upgrade affordability gap | {rate('affordability_gap_active_pct')} |
| Progression upgrades per original install | {rate('avg_upgrades_per_install','',1)} |
| Median soft-coin balance among survivors | {rate('median_wallet_survivors_day_end',' coins',1)} |
| Soft currency sources / sinks | {rate('source_to_sink_ratio','',1)} |
| Share of active play-days with surplus wallets | {rate('surplus_active_pct')} |
| Exact-day D7 return rate | {rate('d7_retention')} |

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
'''
(r/'decision_memo.md').write_text(content,encoding='utf8')
print('Wrote decision_memo.md')
