"""Shared case-economy "instrument": one running spent/paid ledger every
case type draws against, so the payout rate self-corrects toward a target
RTP instead of each case's odds table being the only thing keeping it honest.
"""
import random

from backend.app.db.models import AppSettingsModel

# 1000 paid out per 1250 spent, on average, across every case combined. The
# odds tables themselves are already hand-tuned to land on this on their
# own (see the 0027 migration) — the throttle below is a safety net for a
# hot streak, not the thing doing the actual balancing, so it needs to stay
# rare and mild or it ends up dragging the realized rate well *under*
# target instead of just capping it.
TARGET_RTP = 0.8

# Scales with total volume instead of a flat number — a single big win
# (an 800-coin Mega legendary on its own clears any small flat margin)
# shouldn't be enough to trip this; it should take a *sustained* lead over
# the target pace. 12% of everything spent so far, floored so it still
# means something before much volume has accumulated.
SUPPRESS_MARGIN_BASE_COINS = 500
SUPPRESS_MARGIN_RATIO = 0.12

# When triggered, only tiers worth more than this multiple of the case's
# own target average get cut — i.e. just the handful of biggest possible
# wins, not "everything better than typical." A 1x cutoff (the old
# behavior) excludes roughly the whole upper half of most tables, which
# over-corrects hard enough to pull realized payout far below target
# instead of gently capping it.
SUPPRESS_VALUE_MULTIPLIER = 2.0


def suppress_margin(total_spent_coins: int) -> int:
    return max(SUPPRESS_MARGIN_BASE_COINS, round(total_spent_coins * SUPPRESS_MARGIN_RATIO))

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


async def current_surplus(db) -> tuple[int, int]:
    """(surplus, total_spent) — surplus is how far actual payouts are
    running ahead of the target ratio, in coins. Positive means the economy
    is running hot and the biggest tiers should be throttled back; not
    clamped at zero, so a cold streak needs to fully recover before
    suppression kicks in again. total_spent is returned alongside it since
    the suppression margin scales with it."""
    row = await _get_settings_row(db)
    surplus = round(row.case_total_paid_coins - row.case_total_spent_coins * TARGET_RTP)
    return surplus, row.case_total_spent_coins


def pick_reward(rewards: list[dict], cost_coins: int, surplus: int, total_spent_coins: int) -> dict:
    """The shared weighted-random draw every case open goes through. Once
    `surplus` clears the volume-scaled suppress_margin, tiers worth more
    than SUPPRESS_VALUE_MULTIPLIER times this case's own target average are
    excluded from the pool for this one spin — just the biggest possible
    wins, never emptied entirely, so the case can't jam."""
    pool = rewards
    if surplus > suppress_margin(total_spent_coins):
        ceiling = cost_coins * TARGET_RTP * SUPPRESS_VALUE_MULTIPLIER
        throttled = [r for r in rewards if reward_value(r) <= ceiling]
        if throttled:
            pool = throttled
    return random.choices(pool, weights=[r["chance_percent"] for r in pool], k=1)[0]
