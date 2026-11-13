"""Synthetic free-to-play soft-currency economy simulator.

The model is a teaching/portfolio artifact, NOT fitted to real users. It does
not estimate true price elasticity, causal lift, willingness to pay, or revenue.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
import numpy as np
import pandas as pd

PERSONAS = ("Casual", "Regular", "Engaged")
PERSONA_WEIGHTS = np.array([0.50, 0.35, 0.15])
PERSONA_PLAY_PROB = np.array([0.45, 0.60, 0.75])
PERSONA_CHURN_HAZARD = np.array([0.15, 0.10, 0.075])
PERSONA_UPGRADE_PROPENSITY = np.array([0.54, 0.72, 0.85])
PERSONA_COSMETIC_PROPENSITY = np.array([0.12, 0.20, 0.27])
PERSONA_SECOND_QUEST_PROB = np.array([0.26, 0.50, 0.72])


@dataclass(frozen=True)
class EconomyConfig:
    scenario: str = "Baseline"
    n_players: int = 5000
    n_days: int = 30
    seed: int = 20261112
    initial_coins: int = 100
    login_reward: int = 12
    quest_reward: int = 26
    reward_multiplier: float = 1.0
    upgrade_base_cost: int = 68
    upgrade_price_multiplier: float = 1.0
    upgrade_cost_growth: float = 1.34
    cosmetic_cost: int = 42
    cosmetic_price_multiplier: float = 1.0
    cosmetic_offer_multiplier: float = 1.0
    activity_multiplier: float = 1.0
    churn_multiplier: float = 1.0
    stalled_progression_days: int = 6
    stalled_churn_increment: float = 0.008
    surplus_balance_ratio: float = 3.0
    surplus_churn_increment: float = 0.003

    def validate(self) -> None:
        if self.n_players < 100 or self.n_days < 7:
            raise ValueError("Requires >=100 players and >=7 days")
        if not isinstance(self.seed, int) or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be a 32-bit nonnegative integer")
        for field in ("initial_coins", "login_reward", "quest_reward", "upgrade_base_cost", "cosmetic_cost"):
            if getattr(self, field) < 0:
                raise ValueError(f"{field} must be nonnegative")
        for field in ("reward_multiplier", "upgrade_price_multiplier", "cosmetic_price_multiplier",
                      "cosmetic_offer_multiplier", "upgrade_cost_growth", "activity_multiplier", "churn_multiplier",
                      "surplus_balance_ratio"):
            if not np.isfinite(getattr(self, field)) or getattr(self, field) <= 0:
                raise ValueError(f"{field} must be positive and finite")
        if self.stalled_progression_days < 1:
            raise ValueError("stalled_progression_days must be at least 1")
        for field in ("stalled_churn_increment", "surplus_churn_increment"):
            if getattr(self, field) < 0:
                raise ValueError(f"{field} must be nonnegative")


def default_scenarios(n_players: int = 5000, n_days: int = 30, seed: int = 20261112) -> list[EconomyConfig]:
    base = EconomyConfig(n_players=n_players, n_days=n_days, seed=seed)
    return [base, replace(base, scenario="Reward +25%", reward_multiplier=1.25),
            replace(base, scenario="Upgrade Price +25%", upgrade_price_multiplier=1.25),
            replace(base, scenario="Targeted Sink +30%", cosmetic_offer_multiplier=1.30)]


@dataclass
class SimulationResult:
    daily: pd.DataFrame
    summary: pd.DataFrame
    personas: pd.DataFrame
    players: pd.DataFrame
    events: pd.DataFrame


def simulate_full(config: EconomyConfig, collect_events: bool = False) -> SimulationResult:
    """Simulate a fixed installed cohort from Day 1 to Day N.

    Matched pseudo-random streams are used across scenarios with equal seed and
    cohort size. Counterfactual comparisons are MODEL outcomes, not causal data.
    Events are generated only on request to make grid searches efficient.
    """
    config.validate()
    rng = np.random.default_rng(config.seed)
    p, d = config.n_players, config.n_days
    player_id = np.arange(1, p + 1, dtype=np.int32)
    persona_ix = rng.choice(len(PERSONAS), size=p, p=PERSONA_WEIGHTS)
    persona_names = np.asarray(PERSONAS, dtype=object)[persona_ix]

    draws_play = rng.random((d, p))
    draws_quest = rng.random((d, p))
    draws_upgrade = rng.random((d, p))
    draws_cosmetic = rng.random((d, p))
    draws_churn = rng.random((d, p))

    balance = np.full(p, config.initial_coins, dtype=np.float64)
    upgrades = np.zeros(p, dtype=np.int32)
    cosmetics = np.zeros(p, dtype=np.int32)
    alive = np.ones(p, dtype=bool)
    churn_day = np.zeros(p, dtype=np.int32)
    days_since_upgrade = np.zeros(p, dtype=np.int32)
    player_days_active = np.zeros(p, dtype=np.int32)
    total_earned = np.zeros(p, dtype=np.float64)
    total_spent = np.zeros(p, dtype=np.float64)
    daily_rows: list[dict[str, Any]] = []
    persona_rows: list[dict[str, Any]] = []
    event_frames: list[pd.DataFrame] = []

    def emit(mask: np.ndarray, day: int, event: str, coin_delta: np.ndarray | float = 0.0,
             units: np.ndarray | int = 1) -> None:
        if not collect_events or not mask.any():
            return
        idx = np.flatnonzero(mask)
        amount = np.broadcast_to(np.asarray(coin_delta), (p,))[idx] if np.ndim(coin_delta) else np.full(len(idx), float(coin_delta))
        unit_array = np.broadcast_to(np.asarray(units), (p,))[idx] if np.ndim(units) else np.full(len(idx), int(units))
        event_frames.append(pd.DataFrame({"scenario": config.scenario, "day": day,
                                          "player_id": player_id[idx], "persona": persona_names[idx],
                                          "event_type": event, "units": unit_array.astype(int),
                                          "coin_delta": amount.astype(float),
                                          "level_after": upgrades[idx].astype(int)}))

    for day in range(1, d + 1):
        preday_alive = alive.copy()
        active = preday_alive & (draws_play[day-1] < np.minimum(1.0, PERSONA_PLAY_PROB[persona_ix] * config.activity_multiplier))
        active_count = int(active.sum())
        player_days_active[active] += 1
        days_since_upgrade[active] += 1
        emit(active, day, "session_start")

        second_quest = draws_quest[day-1] < PERSONA_SECOND_QUEST_PROB[persona_ix]
        quests = np.where(active, 1 + second_quest.astype(np.int32), 0)
        login_income = active.astype(float) * config.login_reward
        quest_income = quests * config.quest_reward * config.reward_multiplier
        earned = login_income + quest_income
        balance += earned
        total_earned += earned
        emit(active, day, "login_reward", login_income)
        emit(active, day, "quest_reward", quest_income, quests)

        upgrade_price = np.ceil(config.upgrade_base_cost * config.upgrade_price_multiplier *
                                np.power(config.upgrade_cost_growth, np.minimum(upgrades, 30))).astype(float)
        upgrade_eligible = active & (balance >= upgrade_price)
        buy_upgrade = upgrade_eligible & (draws_upgrade[day-1] < PERSONA_UPGRADE_PROPENSITY[persona_ix])
        upgrade_spend = np.where(buy_upgrade, upgrade_price, 0.0)
        balance -= upgrade_spend
        upgrades[buy_upgrade] += 1
        days_since_upgrade[buy_upgrade] = 0
        emit(buy_upgrade, day, "upgrade_purchase", -upgrade_spend)

        cosmetic_price = float(np.ceil(config.cosmetic_cost * config.cosmetic_price_multiplier))
        chance = np.minimum(1.0, PERSONA_COSMETIC_PROPENSITY[persona_ix] * config.cosmetic_offer_multiplier)
        buy_cosmetic = active & (upgrades >= 2) & (balance >= cosmetic_price) & (draws_cosmetic[day-1] < chance)
        cosmetic_spend = np.where(buy_cosmetic, cosmetic_price, 0.0)
        balance -= cosmetic_spend
        cosmetics[buy_cosmetic] += 1
        emit(buy_cosmetic, day, "cosmetic_purchase", -cosmetic_spend)
        spent = upgrade_spend + cosmetic_spend
        total_spent += spent

        next_upgrade = np.ceil(config.upgrade_base_cost * config.upgrade_price_multiplier *
                               np.power(config.upgrade_cost_growth, np.minimum(upgrades, 30)))
        affordability_gap = active & ~upgrade_eligible  # before purchase; after daily rewards
        stalled = active & (days_since_upgrade >= config.stalled_progression_days)
        surplus = active & (balance >= config.surplus_balance_ratio * next_upgrade)
        hazard = np.minimum(1.0, (PERSONA_CHURN_HAZARD[persona_ix] +
                       stalled.astype(float) * config.stalled_churn_increment +
                       surplus.astype(float) * config.surplus_churn_increment) * config.churn_multiplier)
        churned = preday_alive & (draws_churn[day-1] < hazard)
        alive[churned] = False
        churn_day[churned] = day
        emit(churned, day, "churn")

        daily_rows.append({
            "scenario": config.scenario, "day": day, "cohort_size": p,
            "active_players": active_count, "retention": active_count / p,
            "active_share_of_survivors": active_count / max(1, int(preday_alive.sum())),
            "survivors_end_of_day": int(alive.sum()),
            "earned_coins": float(earned.sum()), "login_source": float(login_income.sum()),
            "quest_source": float(quest_income.sum()), "spent_coins": float(spent.sum()),
            "upgrade_sink": float(upgrade_spend.sum()), "cosmetic_sink": float(cosmetic_spend.sum()),
            "net_flow": float((earned - spent).sum()),
            "cumulative_earned": float(total_earned.sum()), "cumulative_spent": float(total_spent.sum()),
            "total_wallets": float(balance.sum()),
            "median_wallet_survivors": float(np.median(balance[alive])) if alive.any() else 0.0,
            "mean_wallet_survivors": float(np.mean(balance[alive])) if alive.any() else 0.0,
            "upgrade_purchases": int(buy_upgrade.sum()), "cosmetic_purchases": int(buy_cosmetic.sum()),
            "cumulative_upgrades_per_install": float(upgrades.sum() / p),
            "affordability_gap_active_pct": float(affordability_gap.sum() / active_count) if active_count else 0.0,
            "stalled_active_pct": float(stalled.sum() / active_count) if active_count else 0.0,
            "surplus_active_pct": float(surplus.sum() / active_count) if active_count else 0.0,
        })
        for ix, persona in enumerate(PERSONAS):
            group = (persona_ix == ix)
            group_active = group & active
            group_n = int(group_active.sum())
            persona_rows.append({
                "scenario": config.scenario, "day": day, "persona": persona,
                "cohort_size": int(group.sum()), "active_players": group_n,
                "retention": group_n / max(1, int(group.sum())),
                "avg_upgrades_per_install": float(upgrades[group].mean()),
                "median_wallet_survivors": float(np.median(balance[group & alive])) if (group & alive).any() else 0.0,
                "affordability_gap_active_pct": float((group_active & affordability_gap).sum() / group_n) if group_n else 0.0,
                "stalled_active_pct": float((group_active & stalled).sum() / group_n) if group_n else 0.0,
                "surplus_active_pct": float((group_active & surplus).sum() / group_n) if group_n else 0.0,
            })

    daily = pd.DataFrame(daily_rows)
    personas = pd.DataFrame(persona_rows)
    earned_all, spent_all = float(total_earned.sum()), float(total_spent.sum())
    summary = pd.DataFrame([{
        "scenario": config.scenario, "cohort_size": p, "days": d,
        "d1_retention": float(daily.loc[daily.day == 1, "retention"].iloc[0]),
        "d7_retention": float(daily.loc[daily.day == 7, "retention"].iloc[0]),
        "d30_retention": float(daily.loc[daily.day == 30, "retention"].iloc[0]) if d >= 30 else float("nan"),
        "earned_coins": earned_all, "spent_coins": spent_all, "net_coins": earned_all - spent_all,
        "source_to_sink_ratio": earned_all / spent_all if spent_all else float("nan"),
        "sink_utilization": spent_all / earned_all if earned_all else 0,
        "avg_upgrades_per_install": float(upgrades.mean()),
        "avg_cosmetics_per_install": float(cosmetics.mean()),
        "median_wallet_survivors_day_end": float(np.median(balance[alive])) if alive.any() else 0,
        "affordability_gap_active_pct": float((daily.affordability_gap_active_pct * daily.active_players).sum() / max(1, daily.active_players.sum())),
        "stalled_active_pct": float((daily.stalled_active_pct * daily.active_players).sum() / max(1, daily.active_players.sum())),
        "surplus_active_pct": float((daily.surplus_active_pct * daily.active_players).sum() / max(1, daily.active_players.sum())),
        "total_active_player_days": int(player_days_active.sum()),
        "survivors_day_end": int(alive.sum()),
    }])
    # All balances remain in the accounts, even if their players churn.
    # Coins are neither silently created nor removed when a player churns.
    assert np.isclose(balance.sum(), config.initial_coins * p + earned_all - spent_all, atol=1e-5)
    assert (balance >= -1e-7).all()
    players = pd.DataFrame({"scenario": config.scenario, "player_id": player_id,
                            "persona": persona_names, "initial_wallet": config.initial_coins,
                            "ending_wallet": balance, "upgrades_total": upgrades,
                            "cosmetics_total": cosmetics, "active_days": player_days_active,
                            "earned_coins": total_earned, "spent_coins": total_spent,
                            "alive_day_end": alive.astype(int), "churn_day": churn_day})
    if collect_events:
        events = pd.concat(event_frames, ignore_index=True)
        events.insert(0, "event_id", np.arange(1, len(events) + 1, dtype=np.int32))
    else:
        events = pd.DataFrame(columns=["event_id", "scenario", "day", "player_id", "persona",
                                               "event_type", "units", "coin_delta", "level_after"])
    return SimulationResult(daily, summary, personas, players, events)


def simulate(config: EconomyConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    r = simulate_full(config, collect_events=False)
    return r.daily, r.summary, r.personas
