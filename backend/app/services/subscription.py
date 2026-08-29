from datetime import datetime, timedelta, timezone

# MasterCoins price table — kept in sync with the plan cards on
# frontend/src/pages/Pricing.vue (PREMIUM_DURATIONS / LIFETIME).
PREMIUM_PRICES_MC = {1: 99, 3: 255, 6: 499, 12: 999}
LIFETIME_PRICE_MC = 4999
LIFETIME_YEARS = 100  # "lifetime" is modeled as a far-future subscription expiry

REFERRAL_DISCOUNT_PERCENT = 25

# Fixed peg (ТЗ 5.1: "1 MasterCoin = $0.01") — every crypto payment converts
# to coins at this rate, which is also what the existing MC price table
# already implies (e.g. 99 MC premium-month == $0.99).
COIN_USD_RATE = 0.01
MIN_COIN_PURCHASE = 10  # ТЗ 5.1: "Минимальная покупка: 10 коинов"


def usd_for_coins(coins: int) -> float:
    return round(coins * COIN_USD_RATE, 2)


def price_for(plan: str, months: int | None) -> int:
    """Base MasterCoins price for a plan, before any discount. Raises ValueError if invalid."""
    if plan == "lifetime":
        return LIFETIME_PRICE_MC
    if plan == "premium":
        if months not in PREMIUM_PRICES_MC:
            raise ValueError("Invalid duration for the premium plan")
        return PREMIUM_PRICES_MC[months]
    raise ValueError("Unknown plan")


def has_active_referral_discount(wallet) -> bool:
    exp = wallet.ref_discount_expires_at
    return exp is not None and exp > datetime.now(timezone.utc)


def apply_discount(price_mc: int, wallet) -> int:
    if has_active_referral_discount(wallet):
        return round(price_mc * (1 - REFERRAL_DISCOUNT_PERCENT / 100))
    return price_mc


def assert_purchasable(wallet) -> None:
    """Raises ValueError if the wallet already has lifetime access — buying
    anything else (premium or lifetime again) would be a pointless duplicate."""
    if wallet.is_lifetime:
        raise ValueError("You already have lifetime access — no need to buy anything else")


def has_active_subscription(wallet) -> bool:
    exp = wallet.subscription_expires_at
    return exp is not None and exp > datetime.now(timezone.utc)


def extend_subscription(wallet, plan: str, months: int | None) -> datetime:
    """Extends from the later of "now" and the current expiry, then returns the new expiry."""
    now = datetime.now(timezone.utc)
    base = wallet.subscription_expires_at if (wallet.subscription_expires_at and wallet.subscription_expires_at > now) else now

    if plan == "lifetime":
        new_expiry = now + timedelta(days=365 * LIFETIME_YEARS)
        wallet.is_lifetime = True
        wallet.last_plan_months = None
    else:
        new_expiry = base + timedelta(days=30 * months)
        wallet.last_plan_months = months

    wallet.subscription_expires_at = new_expiry
    # A fresh (or extended) expiry means the 24h-out reminder needs to be
    # able to fire again for this new date.
    wallet.reminder_sent_for_expiry = None
    return new_expiry


def grant_premium_days(wallet, days: int) -> datetime:
    """Day-granularity variant of extend_subscription, used by promo code
    rewards. days == 0 means lifetime access, matching the ТЗ (any number
    of days, 0 = forever)."""
    now = datetime.now(timezone.utc)
    if days == 0:
        new_expiry = now + timedelta(days=365 * LIFETIME_YEARS)
        wallet.is_lifetime = True
        wallet.last_plan_months = None
    else:
        base = wallet.subscription_expires_at if (wallet.subscription_expires_at and wallet.subscription_expires_at > now) else now
        new_expiry = base + timedelta(days=days)

    wallet.subscription_expires_at = new_expiry
    wallet.reminder_sent_for_expiry = None
    return new_expiry
