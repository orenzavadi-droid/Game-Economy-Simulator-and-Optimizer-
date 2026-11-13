import numpy as np
import pandas as pd
import pytest
from src.economy import EconomyConfig, default_scenarios, simulate


def test_reproducible():
    config = EconomyConfig(n_players=300, n_days=10)
    first = simulate(config)
    second = simulate(config)
    for a, b in zip(first, second):
        pd.testing.assert_frame_equal(a, b)


def test_conservation_and_nonnegative_spend():
    daily, summary, _ = simulate(EconomyConfig(n_players=600, n_days=30))
    assert np.allclose(daily.earned_coins, daily.login_source + daily.quest_source)
    assert np.allclose(daily.spent_coins, daily.upgrade_sink + daily.cosmetic_sink)
    assert (daily.spent_coins >= 0).all()
    assert (daily.median_wallet_survivors >= 0).all()
    assert abs(summary.earned_coins.iloc[0] - daily.earned_coins.sum()) < 1e-6
    assert abs(summary.spent_coins.iloc[0] - daily.spent_coins.sum()) < 1e-6


def test_retention_denominator_fixed_and_in_bounds():
    daily, _, _ = simulate(EconomyConfig(n_players=600, n_days=30))
    assert (daily.cohort_size == 600).all()
    assert ((daily.retention >= 0) & (daily.retention <= 1)).all()
    assert np.allclose(daily.retention, daily.active_players / 600)


def test_monotonic_known_scenario_parameters():
    variants = default_scenarios(n_players=250, n_days=30)
    assert variants[1].reward_multiplier > variants[0].reward_multiplier
    assert variants[2].upgrade_price_multiplier > variants[0].upgrade_price_multiplier
    assert variants[3].cosmetic_offer_multiplier > variants[0].cosmetic_offer_multiplier


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        simulate(EconomyConfig(n_players=30))
