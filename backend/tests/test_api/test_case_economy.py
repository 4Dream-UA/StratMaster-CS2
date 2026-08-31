import importlib
import random

import pytest

from backend.app.db.models import AppSettingsModel
from backend.app.services.case_economy import (
    TARGET_RTP,
    current_surplus,
    pick_reward,
    record_payout,
    record_spend,
    reward_value,
    suppress_margin,
)
from backend.tests.factories import make_case, make_user
from sqlalchemy import select

# The live reward tables, read straight out of the migration that seeds
# them, so these tests fail if a rebalance drifts off the 80% target rather
# than re-asserting a copy that was kept in step by hand. (importlib, not a
# plain import — the module name starts with a digit.)
_rebalance = importlib.import_module("backend.alembic.versions.0027_case_economy_rebalance")

SEEDED_CASES = [
    ("MasterCoins Case", 49, _rebalance.MASTERCOINS_REWARDS),
    ("Mega Master Coin Case", 199, _rebalance.MEGA_REWARDS),
    ("Premium Case", 99, _rebalance.PREMIUM_REWARDS),
]


def _expected_value(rewards: list[dict]) -> float:
    return sum(reward_value(r) * r["chance_percent"] for r in rewards) / 100


def test_reward_value_reads_coins_directly():
    assert reward_value({"coins": 50, "chance_percent": 10}) == 50


def test_reward_value_looks_up_premium_days_table():
    assert reward_value({"premium_days": 90, "chance_percent": 10}) == 255
    assert reward_value({"premium_days": 0, "chance_percent": 10}) == 0


def test_reward_value_prorates_an_unlisted_day_count():
    # Not one of the seeded tiers — falls back to the 99 MC / 30 day rate.
    assert reward_value({"premium_days": 15, "chance_percent": 10}) == round(99 * 15 / 30)


def test_pick_reward_uses_full_pool_when_surplus_is_low():
    rewards = [
        {"coins": 10, "chance_percent": 50},
        {"coins": 1000, "chance_percent": 50},
    ]
    # Surplus well under the margin — both tiers must still be reachable.
    seen = {pick_reward(rewards, cost_coins=50, surplus=0, total_spent_coins=0)["coins"] for _ in range(200)}
    assert seen == {10, 1000}


def test_pick_reward_excludes_the_biggest_tiers_once_surplus_is_hot():
    rewards = [
        {"coins": 10, "chance_percent": 50},    # under 2x the 50*TARGET_RTP average — stays in the pool
        {"coins": 1000, "chance_percent": 50},  # far above it — must be cut
    ]
    hot_surplus = suppress_margin(total_spent_coins=0) + 1
    seen = {pick_reward(rewards, cost_coins=50, surplus=hot_surplus, total_spent_coins=0)["coins"] for _ in range(50)}
    assert seen == {10}


def test_pick_reward_never_empties_the_pool_even_when_every_tier_is_above_average():
    # A single-tier case where that one tier is itself the only option —
    # throttling must fall back to the full pool rather than crash on an
    # empty weights list.
    rewards = [{"coins": 1000, "chance_percent": 100}]
    hot_surplus = suppress_margin(total_spent_coins=0) + 1
    chosen = pick_reward(rewards, cost_coins=50, surplus=hot_surplus, total_spent_coins=0)
    assert chosen["coins"] == 1000


def test_suppress_margin_scales_with_volume_but_has_a_floor():
    assert suppress_margin(0) == 500
    assert suppress_margin(1000) == 500  # 12% of 1000 is still under the floor
    assert suppress_margin(10000) == 1200


async def test_current_surplus_reflects_the_target_ratio(db_session):
    surplus, spent = await current_surplus(db_session)
    assert (surplus, spent) == (0, 0)

    await record_spend(db_session, 1250)
    await db_session.commit()
    # Nothing paid out yet — running "ahead" is negative (a credit, not a surplus).
    surplus, spent = await current_surplus(db_session)
    assert surplus == round(0 - 1250 * TARGET_RTP)
    assert spent == 1250

    await record_payout(db_session, 1000)
    await db_session.commit()
    # 1250 spent, 1000 paid — exactly on the 80% target ratio.
    surplus, spent = await current_surplus(db_session)
    assert surplus == 0
    assert spent == 1250


# ── The "1250 spent → 1000 paid out" promise, per case and combined ──


@pytest.mark.parametrize("name,cost,rewards", SEEDED_CASES, ids=[c[0] for c in SEEDED_CASES])
def test_every_seeded_case_pays_out_the_target_rate_on_its_own(name, cost, rewards):
    """Not just "all cases together average 80%" — each one has to hit it
    by itself, or a player who only ever opens one type is playing a
    different game from the published number."""
    assert sum(r["chance_percent"] for r in rewards) == pytest.approx(100)
    rtp = _expected_value(rewards) / cost
    assert rtp == pytest.approx(TARGET_RTP, abs=0.005), f"{name} pays {rtp:.1%}, target {TARGET_RTP:.0%}"


@pytest.mark.parametrize("name,cost,rewards", SEEDED_CASES, ids=[c[0] for c in SEEDED_CASES])
def test_simulated_openings_land_near_the_target_without_the_throttle(name, cost, rewards):
    """The odds tables are what actually does the balancing — the surplus
    throttle is only a safety net — so a cold ledger (surplus 0, nothing
    suppressed) must already produce ~80% on its own."""
    # pick_reward draws from the `random` module directly, so seeding it is
    # what makes this deterministic; the previous state is put back so a
    # seeded run here can't quietly fix the ordering of any other test.
    state = random.getstate()
    random.seed(1234)
    try:
        spins = 40_000
        paid = sum(
            reward_value(pick_reward(rewards, cost, surplus=0, total_spent_coins=0))
            for _ in range(spins)
        )
    finally:
        random.setstate(state)
    realized = paid / (spins * cost)
    assert realized == pytest.approx(TARGET_RTP, abs=0.02), f"{name} realized {realized:.1%}"


def test_combined_spend_of_1250_pays_out_about_1000():
    """The headline promise, across all three cases in proportion."""
    total_cost = sum(cost for _, cost, _ in SEEDED_CASES)
    total_ev = sum(_expected_value(rewards) for _, _, rewards in SEEDED_CASES)
    assert total_ev / total_cost == pytest.approx(TARGET_RTP, abs=0.005)
    # Restated in the units the promise is written in.
    assert round(1250 * (total_ev / total_cost)) == pytest.approx(1000, abs=10)


async def test_buying_and_opening_a_case_updates_the_shared_ledger(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49, rewards=[{"coins": 30, "chance_percent": 100, "tier": "grey"}])
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    row = (await db_session.execute(select(AppSettingsModel).where(AppSettingsModel.id == 1))).scalar_one()
    assert row.case_total_spent_coins == 49

    await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 1})
    await db_session.refresh(row)
    assert row.case_total_paid_coins == 30
