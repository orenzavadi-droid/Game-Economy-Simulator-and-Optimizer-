import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.economy import EconomyConfig, PERSONAS, simulate_full
from src.optimize import TRAIN_SEEDS, HOLDOUT_SEEDS, optimize_economy, evaluate_candidate


def test_event_ledger_reconciles_individual_wallets():
    r=simulate_full(EconomyConfig(n_players=300,n_days=12),collect_events=True)
    ledger=r.events.groupby('player_id').coin_delta.sum()
    expected=r.players.set_index('player_id').initial_wallet.add(ledger,fill_value=0)
    actual=r.players.set_index('player_id').ending_wallet
    assert np.allclose(expected.sort_index(),actual.sort_index())


def test_events_source_and_sinks_sum_to_summary():
    r=simulate_full(EconomyConfig(n_players=350,n_days=30),collect_events=True)
    events=r.events
    assert abs(events[events.coin_delta>0].coin_delta.sum()-r.summary.earned_coins.iloc[0]) < 1e-6
    assert abs(-events[events.coin_delta<0].coin_delta.sum()-r.summary.spent_coins.iloc[0]) < 1e-6


def test_session_events_equal_daily_activity():
    r=simulate_full(EconomyConfig(n_players=350,n_days=30),collect_events=True)
    count=r.events[r.events.event_type=='session_start'].groupby('day').size()
    assert count.to_dict()==dict(zip(r.daily.day,r.daily.active_players))


def test_event_ids_and_player_keys_unique():
    r=simulate_full(EconomyConfig(n_players=350,n_days=30),collect_events=True)
    assert r.events.event_id.is_unique
    assert r.players.player_id.is_unique
    assert r.events.player_id.isin(r.players.player_id).all()


def test_purchase_event_deltas_negative():
    r=simulate_full(EconomyConfig(n_players=350,n_days=30),collect_events=True)
    purchases=r.events[r.events.event_type.isin(['upgrade_purchase','cosmetic_purchase'])]
    assert (purchases.coin_delta<0).all()
    assert (r.players.ending_wallet>=0).all()


def test_retention_uses_all_installs_on_exact_day():
    r=simulate_full(EconomyConfig(n_players=350,n_days=30),collect_events=True)
    day7=r.events[(r.events.day==7)&(r.events.event_type=='session_start')]
    assert r.summary.d7_retention.iloc[0]==len(day7)/350
    assert (r.daily.cohort_size==350).all()


def test_persona_affordability_in_valid_bounds():
    r=simulate_full(EconomyConfig(n_players=350,n_days=30))
    assert set(r.personas.persona.unique())==set(PERSONAS)
    assert r.personas.affordability_gap_active_pct.between(0,1).all()


def test_invalid_new_parameters_rejected():
    for key,val in [('activity_multiplier',0),('churn_multiplier',-1),('surplus_balance_ratio',0),('stalled_progression_days',0)]:
        with pytest.raises(ValueError):simulate_full(replace(EconomyConfig(n_players=300),**{key:val}))


def test_matching_seed_yields_same_player_archetypes_across_policies():
    a=simulate_full(EconomyConfig(n_players=300,n_days=10))
    b=simulate_full(EconomyConfig(n_players=300,n_days=10,reward_multiplier=1.2))
    assert a.players[['player_id','persona']].equals(b.players[['player_id','persona']])


def test_optimizer_seed_sets_do_not_overlap():
    assert not set(TRAIN_SEEDS).intersection(HOLDOUT_SEEDS)


def test_candidate_grid_and_selected_candidate():
    # Use precomputed build artifacts to avoid rerunning 108 training simulations.
    root=Path(__file__).resolve().parents[1]
    path=root/'data/optimizer_candidates.csv'
    if not path.exists():pytest.skip('Run analysis to create optimization results')
    c=pd.read_csv(path)
    s=json.loads((root/'reports/optimization_selection.json').read_text())
    assert len(c)==27
    selected=c[c.candidate==s['selected_candidate']].iloc[0]
    assert bool(selected.feasible)
    assert abs(selected.objective_score-c[c.feasible].objective_score.max())<1e-9
    assert c.pareto_efficient.sum()>=1


def test_holdout_results_cover_each_metric_and_pair():
    root=Path(__file__).resolve().parents[1]
    path=root/'data/optimizer_holdout_by_seed.csv'
    if not path.exists():pytest.skip('Run analysis first')
    h=pd.read_csv(path)
    assert set(h.seed)==set(HOLDOUT_SEEDS)
    assert (h.groupby('seed').scenario.nunique()==2).all()


def test_sql_currency_audit_all_accounts():
    root=Path(__file__).resolve().parents[1]
    path=root/'reports/sql_outputs/04_wallet_reconciliation.csv'
    if not path.exists():pytest.skip('Run analysis first')
    audit=pd.read_csv(path)
    assert len(audit)==20000
    assert (audit.wallet_difference.abs()<1e-7).all()


def test_sql_daily_vs_simulation_sources_and_sinks():
    root=Path(__file__).resolve().parents[1]
    data=root/'data'
    if not (data/'daily_metrics.csv').exists():pytest.skip('Run analysis first')
    sql=pd.read_csv(root/'reports/sql_outputs/01_daily_currency_flows.csv')
    daily=pd.read_csv(data/'daily_metrics.csv')
    merged=sql.merge(daily,on=['scenario','day'],validate='one_to_one')
    assert len(merged)==120
    assert np.allclose(merged.currency_sources,merged.earned_coins)
    assert np.allclose(merged.currency_sinks,merged.spent_coins)


def test_artifact_html_uses_cdn_and_has_four_tabs():
    root=Path(__file__).resolve().parents[1]
    htmlfile=root/'reports/interactive_dashboard.html'
    if not htmlfile.exists():pytest.skip('Build dashboard first')
    html=htmlfile.read_text(encoding='utf-8')
    assert 'src="https://cdn.plot.ly' in html  # Interactive plots load Plotly on demand
    assert all(f'id="{tab}"' in html for tab in ('economy','optimization','personas','robustness'))
    assert len(html)>50_000
