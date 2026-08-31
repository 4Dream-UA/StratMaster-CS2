from datetime import datetime, timedelta, timezone

import pytest

from backend.app.services.subscription import (
    LIFETIME_PRICE_MC,
    PREMIUM_PRICES_MC,
    apply_discount,
    assert_purchasable,
    extend_subscription,
    grant_premium_days,
    has_active_referral_discount,
    price_for,
)


class FakeWallet:
    def __init__(self, ref_discount_expires_at=None, subscription_expires_at=None, is_lifetime=False):
        self.ref_discount_expires_at = ref_discount_expires_at
        self.subscription_expires_at = subscription_expires_at
        self.is_lifetime = is_lifetime


def test_price_for_premium_durations():
    for months, mc in PREMIUM_PRICES_MC.items():
        assert price_for("premium", months) == mc


def test_price_for_lifetime():
    assert price_for("lifetime", None) == LIFETIME_PRICE_MC


def test_price_for_invalid_duration_raises():
    with pytest.raises(ValueError):
        price_for("premium", 7)


def test_price_for_unknown_plan_raises():
    with pytest.raises(ValueError):
        price_for("yearly", None)


def test_discount_applies_within_24h_window():
    wallet = FakeWallet(ref_discount_expires_at=datetime.now(timezone.utc) + timedelta(hours=23))
    assert has_active_referral_discount(wallet) is True
    assert apply_discount(100, wallet) == 75


def test_discount_does_not_apply_after_expiry():
    wallet = FakeWallet(ref_discount_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    assert has_active_referral_discount(wallet) is False
    assert apply_discount(100, wallet) == 100


def test_discount_does_not_apply_when_never_set():
    wallet = FakeWallet(ref_discount_expires_at=None)
    assert apply_discount(100, wallet) == 100


def test_extend_subscription_from_now_when_no_prior_expiry():
    wallet = FakeWallet(subscription_expires_at=None)
    before = datetime.now(timezone.utc)
    new_expiry = extend_subscription(wallet, "premium", 1)
    assert new_expiry - before >= timedelta(days=29, hours=23)
    assert wallet.subscription_expires_at == new_expiry


def test_extend_subscription_sets_the_bought_duration_rather_than_stacking():
    # A plan is "you have N months of premium", not "N months are added to
    # your pile" — buying 1 month leaves exactly 1 month, whatever was there.
    current_expiry = datetime.now(timezone.utc) + timedelta(days=10)
    wallet = FakeWallet(subscription_expires_at=current_expiry)
    before = datetime.now(timezone.utc)
    new_expiry = extend_subscription(wallet, "premium", 1)
    assert timedelta(days=29, hours=23) <= new_expiry - before <= timedelta(days=30, hours=1)


def test_extend_subscription_can_shorten_a_longer_running_subscription():
    current_expiry = datetime.now(timezone.utc) + timedelta(days=300)
    wallet = FakeWallet(subscription_expires_at=current_expiry)
    new_expiry = extend_subscription(wallet, "premium", 1)
    assert new_expiry < current_expiry


def test_extend_subscription_ignores_expired_subscription_and_extends_from_now():
    expired = datetime.now(timezone.utc) - timedelta(days=5)
    wallet = FakeWallet(subscription_expires_at=expired)
    before = datetime.now(timezone.utc)
    new_expiry = extend_subscription(wallet, "premium", 1)
    assert new_expiry - before >= timedelta(days=29, hours=23)


def test_grant_premium_days_sets_exactly_the_granted_days():
    wallet = FakeWallet(subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=5))
    before = datetime.now(timezone.utc)
    new_expiry = grant_premium_days(wallet, 31)
    assert timedelta(days=30, hours=23) <= new_expiry - before <= timedelta(days=31, hours=1)


def test_grant_premium_days_zero_means_lifetime():
    wallet = FakeWallet(subscription_expires_at=None)
    grant_premium_days(wallet, 0)
    assert wallet.is_lifetime is True


def test_extend_subscription_lifetime_is_far_future():
    wallet = FakeWallet(subscription_expires_at=None)
    new_expiry = extend_subscription(wallet, "lifetime", None)
    assert new_expiry > datetime.now(timezone.utc) + timedelta(days=365 * 50)


def test_extend_subscription_lifetime_sets_is_lifetime_flag():
    wallet = FakeWallet(subscription_expires_at=None)
    extend_subscription(wallet, "lifetime", None)
    assert wallet.is_lifetime is True


def test_extend_subscription_premium_records_last_plan_months():
    wallet = FakeWallet(subscription_expires_at=None)
    extend_subscription(wallet, "premium", 3)
    assert wallet.last_plan_months == 3


def test_assert_purchasable_allows_non_lifetime_wallet():
    wallet = FakeWallet(is_lifetime=False)
    assert_purchasable(wallet)  # does not raise


def test_assert_purchasable_rejects_lifetime_wallet():
    wallet = FakeWallet(is_lifetime=True)
    with pytest.raises(ValueError):
        assert_purchasable(wallet)
