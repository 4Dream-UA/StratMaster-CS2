from backend.app.db.models import AppSettingsModel
from backend.app.services.case_economy import (
    SUPPRESS_MARGIN_COINS,
    TARGET_RTP,
    current_surplus,
    pick_reward,
    record_payout,
    record_spend,
    reward_value,
)
from backend.tests.factories import make_case, make_user
from sqlalchemy import select


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
    seen = {pick_reward(rewards, cost_coins=50, surplus=0)["coins"] for _ in range(200)}
    assert seen == {10, 1000}


def test_pick_reward_excludes_above_average_tiers_once_surplus_is_hot():
    rewards = [
        {"coins": 10, "chance_percent": 50},   # at/under a 50*TARGET_RTP average — stays in the pool
        {"coins": 1000, "chance_percent": 50},  # far above it — must be cut
    ]
    hot_surplus = SUPPRESS_MARGIN_COINS + 1
    seen = {pick_reward(rewards, cost_coins=50, surplus=hot_surplus)["coins"] for _ in range(50)}
    assert seen == {10}


def test_pick_reward_never_empties_the_pool_even_when_every_tier_is_above_average():
    # A single-tier case where that one tier is itself the only option —
    # throttling must fall back to the full pool rather than crash on an
    # empty weights list.
    rewards = [{"coins": 1000, "chance_percent": 100}]
    hot_surplus = SUPPRESS_MARGIN_COINS + 1
    chosen = pick_reward(rewards, cost_coins=50, surplus=hot_surplus)
    assert chosen["coins"] == 1000


async def test_current_surplus_reflects_the_target_ratio(db_session):
    assert await current_surplus(db_session) == 0

    await record_spend(db_session, 1250)
    await db_session.commit()
    # Nothing paid out yet — running "ahead" is negative (a credit, not a surplus).
    assert await current_surplus(db_session) == round(0 - 1250 * TARGET_RTP)

    await record_payout(db_session, 1000)
    await db_session.commit()
    # 1250 spent, 1000 paid — exactly on the 80% target ratio.
    assert await current_surplus(db_session) == 0


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
