"""Transparent, assumption-based, training/holdout economy grid search.

The score and constraints are portfolio-design choices, NOT learned weights or
production economy goals. The holdout is unexamined during selection.
"""
from __future__ import annotations
from dataclasses import replace
from itertools import product
import numpy as np
import pandas as pd
from src.economy import EconomyConfig, simulate_full

TRAIN_SEEDS = (41001, 41002, 41003, 41004)
HOLDOUT_SEEDS = (51001, 51002, 51003, 51004)
REWARD_GRID = (0.90, 1.00, 1.10)
UPGRADE_GRID = (0.85, 1.00, 1.15)
SINK_GRID = (1.00, 1.30, 1.60)
METRICS = ("affordability_gap_active_pct", "avg_upgrades_per_install",
           "median_wallet_survivors_day_end", "source_to_sink_ratio",
           "sink_utilization", "surplus_active_pct", "d7_retention")


def evaluate_candidate(config: EconomyConfig, seeds: tuple[int, ...], n_players: int = 2000) -> dict:
    metrics = []
    for seed in seeds:
        res = simulate_full(replace(config, seed=seed, n_players=n_players))
        row = res.summary.iloc[0][list(METRICS)].to_dict()
        casual = res.personas[res.personas.persona == "Casual"]
        row["casual_gap"] = float(np.average(casual.affordability_gap_active_pct,
                                             weights=casual.active_players)) if casual.active_players.sum() else 0
        metrics.append(row)
    return pd.DataFrame(metrics).mean().to_dict()


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 1.0


def optimize_economy(base: EconomyConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    base = base or EconomyConfig()
    base = replace(base, scenario="Baseline")
    baseline = evaluate_candidate(base, TRAIN_SEEDS)
    rows = []
    for i, (reward, price, sink) in enumerate(product(REWARD_GRID, UPGRADE_GRID, SINK_GRID), start=1):
        conf = replace(base, scenario=f"C{i:02d}", reward_multiplier=reward,
                       upgrade_price_multiplier=price, cosmetic_offer_multiplier=sink)
        agg = evaluate_candidate(conf, TRAIN_SEEDS)
        # Predeclared guardrails relative to the train-seed baseline, not optimized on holdout.
        checks = {
            "gap_not_worse": agg["affordability_gap_active_pct"] <= baseline["affordability_gap_active_pct"] + 1e-9,
            "upgrade_floor": agg["avg_upgrades_per_install"] >= 0.98 * baseline["avg_upgrades_per_install"],
            "wallet_cap": agg["median_wallet_survivors_day_end"] <= 1.15 * baseline["median_wallet_survivors_day_end"],
            "source_sink_cap": agg["source_to_sink_ratio"] <= 1.10 * baseline["source_to_sink_ratio"],
            "casual_gap_guardrail": agg["casual_gap"] <= baseline["casual_gap"] + 0.01,
        }
        friction_gain_pp = 100 * (baseline["affordability_gap_active_pct"] - agg["affordability_gap_active_pct"])
        upgrades_gain_pct = 100 * (_safe_ratio(agg["avg_upgrades_per_install"], baseline["avg_upgrades_per_install"]) - 1)
        surplus_gain_pp = 100 * (baseline["surplus_active_pct"] - agg["surplus_active_pct"])
        wallet_excess_pct = 100 * max(0, _safe_ratio(agg["median_wallet_survivors_day_end"], baseline["median_wallet_survivors_day_end"]) - 1)
        score = 3 * friction_gain_pp + 0.9 * upgrades_gain_pct + 0.6 * surplus_gain_pp - 0.6 * wallet_excess_pct
        rows.append({"candidate": conf.scenario, "reward_multiplier": reward,
                     "upgrade_price_multiplier": price, "cosmetic_offer_multiplier": sink,
                     **agg, "feasible": all(checks.values()), "objective_score": score,
                     "failed_guardrails": ", ".join(k for k, ok in checks.items() if not ok) or "None",
                     "gap_improvement_pp": friction_gain_pp,
                     "upgrades_improvement_pct": upgrades_gain_pct,
                     "wallet_increase_pct": 100 * (_safe_ratio(agg["median_wallet_survivors_day_end"], baseline["median_wallet_survivors_day_end"]) - 1)})
    candidates = pd.DataFrame(rows)
    # Simple 3-objective, non-dominated set among feasible points.
    candidates["pareto_efficient"] = False
    feasible_ids = candidates.index[candidates.feasible].tolist()
    for idx in feasible_ids:
        target = candidates.loc[idx]
        dominated = False
        for other_idx in feasible_ids:
            if other_idx == idx:
                continue
            other = candidates.loc[other_idx]
            not_worse = (other.affordability_gap_active_pct <= target.affordability_gap_active_pct and
                         other.avg_upgrades_per_install >= target.avg_upgrades_per_install and
                         other.median_wallet_survivors_day_end <= target.median_wallet_survivors_day_end)
            strictly_better = (other.affordability_gap_active_pct < target.affordability_gap_active_pct or
                               other.avg_upgrades_per_install > target.avg_upgrades_per_install or
                               other.median_wallet_survivors_day_end < target.median_wallet_survivors_day_end)
            if not_worse and strictly_better:
                dominated = True
                break
        candidates.loc[idx, "pareto_efficient"] = not dominated
    feasible = candidates[candidates.feasible].sort_values(["objective_score", "candidate"], ascending=[False, True])
    if feasible.empty:
        raise RuntimeError("No feasible grid candidates; guardrails require reconsideration")
    chosen = feasible.iloc[0]
    best_config = replace(base, scenario="Recommended", reward_multiplier=float(chosen.reward_multiplier),
                          upgrade_price_multiplier=float(chosen.upgrade_price_multiplier),
                          cosmetic_offer_multiplier=float(chosen.cosmetic_offer_multiplier))
    holdout_rows = []
    for seed in HOLDOUT_SEEDS:
        for label, conf in (("Baseline", base), ("Recommended", best_config)):
            res = simulate_full(replace(conf, seed=seed, n_players=2500))
            holdout_rows.append({"seed": seed, "scenario": label, **res.summary.iloc[0][list(METRICS)].to_dict()})
    holdout = pd.DataFrame(holdout_rows)
    comparisons = []
    for metric in METRICS:
        pivot = holdout.pivot(index="seed", columns="scenario", values=metric)
        delta = pivot["Recommended"] - pivot["Baseline"]
        comparisons.append({"metric": metric, "baseline_mean": float(pivot["Baseline"].mean()),
                            "recommended_mean": float(pivot["Recommended"].mean()),
                            "paired_delta_mean": float(delta.mean()),
                            "delta_min": float(delta.min()), "delta_max": float(delta.max()),
                            "number_of_seed_pairs": len(delta)})
    validation = pd.DataFrame(comparisons)
    selection = {"selected_candidate": chosen.candidate,
                 "reward_multiplier": float(chosen.reward_multiplier),
                 "upgrade_price_multiplier": float(chosen.upgrade_price_multiplier),
                 "cosmetic_offer_multiplier": float(chosen.cosmetic_offer_multiplier),
                 "objective_score_training": float(chosen.objective_score),
                 "training_seeds": list(TRAIN_SEEDS), "holdout_seeds": list(HOLDOUT_SEEDS),
                 "train_players_per_seed": 2000, "holdout_players_per_seed": 2500,
                 "guardrails": {"max_affordability_gap": "<= baseline train mean",
                                "min_upgrades": ">= 98% of baseline train mean",
                                "max_median_wallet": "<= 115% of baseline train mean",
                                "max_source_sink_ratio": "<= 110% of baseline train mean",
                                "casual_gap": "<= baseline train mean + 1 percentage point"}}
    return candidates, holdout, validation, selection
