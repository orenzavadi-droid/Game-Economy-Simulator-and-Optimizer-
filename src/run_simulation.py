"""CLI for generating the full project data and terminal summary."""
from __future__ import annotations
import argparse
import json
from dataclasses import replace
from pathlib import Path
import pandas as pd
from src.economy import EconomyConfig, simulate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible F2P economy simulation")
    parser.add_argument("--players", type=int, default=5000)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261112)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    daily_out, summaries, segment_out = [], [], []
    scenario_spec = json.loads((Path(__file__).resolve().parents[1] / "config" / "scenarios.json").read_text(encoding="utf-8"))
    for name, overrides in scenario_spec["scenarios"].items():
        config = replace(EconomyConfig(n_players=args.players, n_days=args.days, seed=args.seed), scenario=name, **overrides)
        daily, summary, segments = simulate(config)
        daily_out.append(daily)
        summaries.append(summary)
        segment_out.append(segments)
    args.output.mkdir(parents=True, exist_ok=True)
    pd.concat(daily_out, ignore_index=True).to_csv(args.output / "daily_metrics.csv", index=False)
    all_summary = pd.concat(summaries, ignore_index=True)
    all_summary.to_csv(args.output / "scenario_summary.csv", index=False)
    pd.concat(segment_out, ignore_index=True).to_csv(args.output / "persona_metrics.csv", index=False)
    pd.set_option("display.max_columns", 10)
    print(all_summary[["scenario", "d7_retention", "source_to_sink_ratio", "avg_upgrades_per_install", "affordability_gap_active_pct"]].to_string(index=False))
    print(f"\nData written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
