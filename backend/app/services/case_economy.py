"""Shared case-economy "instrument": one running spent/paid ledger every
case type draws against, so the payout rate self-corrects toward a target
RTP instead of each case's odds table being the only thing keeping it honest.
"""
import random

from backend.app.db.models import AppSettingsModel

# 1000 paid out per 1250 spent, on average, across every case combined.
TARGET_RTP = 0.8

# Once the running ledger has paid out this many coins (coin-equivalent, for
# premium-day tiers) more than the target ratio implies it should have, any
# tier worth more than the case's own target average is cut from the draw
# for the next spin — pulling the ledger back toward the target instead of
# letting a hot streak compound.
SUPPRESS_MARGIN_COINS = 200

# Coin-equivalent value of a premium-days tier, for the shared ledger only —
# what actually gets granted is real subscription days, never coins. Pegged
# to the real premium price table (PREMIUM_PRICES_MC in subscription.py) for
# the exact month marks; the odd day counts are pro-rated off the 1-month price.
PREMIUM_DAY_VALUE_COINS = {0: 0, 7: 23, 14: 46, 31: 102, 90: 255, 180: 499, 360: 999}


def reward_value(reward: dict) -> int:
    """Coin-equivalent value of one reward tier, for the ledger only."""
    if "premium_days" in reward:
        days = reward["premium_days"]
        return PREMIUM_DAY_VALUE_COINS.get(days, round(99 * days / 30))
    return reward.get("coins", 0)


async def _get_settings_row(db) -> AppSettingsModel:
    row = await db.get(AppSettingsModel, 1)
    if row is None:
        row = AppSettingsModel(id=1)
        db.add(row)
        await db.flush()
    return row


async def record_spend(db, amount: int) -> None:
    row = await _get_settings_row(db)
    row.case_total_spent_coins += amount


async def record_payout(db, amount: int) -> None:
    row = await _get_settings_row(db)
    row.case_total_paid_coins += amount


async def current_surplus(db) -> int:
    """How far actual payouts are running ahead of the target ratio, in
    coins. Positive means the economy is running hot and top tiers should
    be throttled back; not clamped at zero, so a cold streak needs to fully
    recover before suppression kicks in again."""
    row = await _get_settings_row(db)
    return round(row.case_total_paid_coins - row.case_total_spent_coins * TARGET_RTP)


def pick_reward(rewards: list[dict], cost_coins: int, surplus: int) -> dict:
    """The shared weighted-random draw every case open goes through. Once
    `surplus` clears SUPPRESS_MARGIN_COINS, any tier worth more than this
    case's own target average (cost * TARGET_RTP) is excluded from the pool
    for this one spin — never emptied entirely, so the case can't jam."""
    pool = rewards
    if surplus > SUPPRESS_MARGIN_COINS:
        expected_value = cost_coins * TARGET_RTP
        throttled = [r for r in rewards if reward_value(r) <= expected_value]
        if throttled:
            pool = throttled
    return random.choices(pool, weights=[r["chance_percent"] for r in pool], k=1)[0]
