"""One-command generation of version-2 datasets and SQLite query examples."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import pandas as pd
from src.economy import EconomyConfig, simulate_full
from src.optimize import optimize_economy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def main() -> None:
    DATA.mkdir(exist_ok=True)
    (REPORTS / "sql_outputs").mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / "config/scenarios.json").read_text())
    sim_params = spec["simulation"]
    defaults = EconomyConfig(n_players=sim_params["n_players"], n_days=sim_params["n_days"], seed=sim_params["seed"])
    days, summaries, personas, players, events = [], [], [], [], []
    for label, params in spec["scenarios"].items():
        r = simulate_full(replace(defaults, scenario=label, **params), collect_events=True)
        days.append(r.daily); summaries.append(r.summary); personas.append(r.personas)
        players.append(r.players); events.append(r.events)
    files = {"daily_metrics.csv": pd.concat(days, ignore_index=True),
             "scenario_summary.csv": pd.concat(summaries, ignore_index=True),
             "persona_metrics.csv": pd.concat(personas, ignore_index=True),
             "players.csv": pd.concat(players, ignore_index=True),
             "events.csv": pd.concat(events, ignore_index=True)}
    for fn, df in files.items():
        df.to_csv(DATA / fn, index=False)
    # SQLite source tables for SQL analytics with event-id composite key per scenario.
    db_path = DATA / "game_economy.sqlite"
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        files["events.csv"].to_sql("events", conn, if_exists="replace", index=False)
        files["players.csv"].to_sql("players", conn, if_exists="replace", index=False)
        files["daily_metrics.csv"].to_sql("daily_metrics", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX ix_event_scenario_day ON events(scenario,day)")
        conn.execute("CREATE INDEX ix_event_player ON events(scenario,player_id)")
        conn.execute("CREATE UNIQUE INDEX ix_player_id ON players(scenario,player_id)")
        for sql_path in sorted((ROOT / "sql").glob("[0-9]*.sql")):
            result = pd.read_sql_query(sql_path.read_text(encoding="utf8"), conn)
            result.to_csv(REPORTS / "sql_outputs" / (sql_path.stem + ".csv"), index=False)
    # Genuine programmatic reconciliation between ledger and aggregate simulation.
    with sqlite3.connect(db_path) as conn:
        audit = pd.read_sql_query((ROOT / "sql/04_wallet_reconciliation.sql").read_text(), conn)
    assert (audit.wallet_difference.abs() < 1e-7).all(), "Currency accounting failed SQL audit"
    assert len(audit) == 4 * defaults.n_players
    # Holdout never used for optimizer candidate selection.
    candidates, holdout, validation, selection = optimize_economy(defaults)
    for name, df in (("optimizer_candidates.csv", candidates),
                     ("optimizer_holdout_by_seed.csv", holdout),
                     ("optimizer_validation_summary.csv", validation)):
        df.to_csv(DATA / name, index=False)
    (REPORTS / "optimization_selection.json").write_text(json.dumps(selection, indent=2), encoding="utf8")
    # Illustrative archetypes, held outside the optimization set.
    profile_spec = json.loads((ROOT / "config/profiles.json").read_text())
    profiles = []
    for name, overrides in profile_spec["profiles"].items():
        profiles.append(simulate_full(replace(defaults, scenario=name, **overrides)).summary)
    pd.concat(profiles, ignore_index=True).to_csv(DATA / "profile_comparison.csv", index=False)
    # Out-of-model-assumption stresses, not empirical prediction intervals.
    stress_configs = {
        "Default assumptions": {}, "Activity -15%": {"activity_multiplier": 0.85},
        "Churn hazard +20%": {"churn_multiplier": 1.20},
        "Quest reward -15%": {"reward_multiplier": 0.85},
        "Upgrade prices +15%": {"upgrade_price_multiplier": 1.15},
    }
    stress_rows = []
    for label, kw in stress_configs.items():
        for seed in (61001, 61002, 61003, 61004):
            r = simulate_full(replace(defaults, seed=seed, n_players=2500, scenario=label, **kw))
            stress_rows.append({"stress": label, "seed": seed, **r.summary.iloc[0].to_dict()})
    pd.DataFrame(stress_rows).to_csv(DATA / "stress_sensitivity.csv", index=False)
    print(f"V2 generated: {len(files['events.csv']):,} event rows; {len(files['players.csv']):,} player rows; SQL ledger PASS")
    print(f"Best training candidate: {selection['selected_candidate']} ({selection['reward_multiplier']}, {selection['upgrade_price_multiplier']}, {selection['cosmetic_offer_multiplier']})")
    print(validation[['metric','baseline_mean','recommended_mean','paired_delta_mean']].to_string(index=False))


if __name__ == "__main__":
    main()
