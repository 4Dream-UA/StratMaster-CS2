from datetime import datetime, timezone


def has_active_subscription(user) -> bool:
    """True if the user has a wallet with a non-expired subscription."""
    if user is None or user.wallet is None:
        return False
    expires_at = user.wallet.subscription_expires_at
    return expires_at is not None and expires_at > datetime.now(timezone.utc)
