# SQL data analysis guide

The packaged `data/game_economy.sqlite` SQLite database contains three tables:

- **`players`**: one row per scenario × original synthetic install, including initial/final wallets and total upgrades.
- **`events`**: event-level log with `scenario`, `day`, `player_id`, `persona`, `event_type`, `units`, `coin_delta`, and `level_after`. Event types: `session_start`, `login_reward`, `quest_reward`, `upgrade_purchase`, `cosmetic_purchase`, and `churn`. A purchase has a **negative** `coin_delta`.
- **`daily_metrics`**: simulation aggregates for model-vs-SQL cross-checks.

All tables are synthetic. Primary conceptual join key: **(`scenario`, `player_id`)**. `event_id` increments separately for each scenario, so it is not a global player identifier.

## Queries

1. `01_daily_currency_flows.sql`: model-level daily minted and spent currency.
2. `02_cohort_retention_by_persona.sql`: exact-day D1/D7/D30 returns using original-install denominators.
3. `03_progression_by_segment.sql`: upgrades, cosmetics, play-days and end balances per persona.
4. `04_wallet_reconciliation.sql`: per-player conservation audit; **all** wallet differences must be zero.
5. `05_source_sink_by_persona.sql`: how sources and sinks differ by modeled player segment.
6. `06_time_to_first_upgrade.sql`: conditional time to first upgrade and Day-7 cumulative upgrade incidence.

To inspect with a command-line SQLite client:

```bash
sqlite3 -header -csv data/game_economy.sqlite < sql/05_source_sink_by_persona.sql
```

Or use any SQLite GUI. The six query output CSV files in `reports/sql_outputs/` are precomputed, including a full 20,000-player reconciliation audit.

## Data integrity

The application asserts that sum of event credits less debits equals final wallets minus initial endowments. The SQL audit reconstructs the same conservation identity player-by-player from an independently queried database. **Do not treat exact ledger reconciliation as proof of calibrated human behavior.**
