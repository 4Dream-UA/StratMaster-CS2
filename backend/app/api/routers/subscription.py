from fastapi import APIRouter, HTTPException, status

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.db.models import TransactionModel
from backend.app.schemas.subscription import (
    AutoRenewRequest,
    AutoRenewResponse,
    SubscriptionPurchaseRequest,
    SubscriptionPurchaseResponse,
)
from backend.app.services.subscription import apply_discount, assert_purchasable, extend_subscription, price_for

router = APIRouter()


@router.post("/subscription/purchase", response_model=SubscriptionPurchaseResponse)
async def purchase_subscription(
    request: SubscriptionPurchaseRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Buy (or extend) premium/lifetime access by spending MasterCoins."""
    if request.plan == "premium" and request.months is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="months is required for the premium plan")

    wallet = current_user.wallet
    try:
        assert_purchasable(wallet)
        base_price = price_for(request.plan, request.months)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    price = apply_discount(base_price, wallet)

    if wallet.balance_coins < price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough MasterCoins — need {price}, have {wallet.balance_coins}",
        )

    wallet.balance_coins -= price
    new_expiry = extend_subscription(wallet, request.plan, request.months)

    db.add(TransactionModel(
        sender_wallet_id=wallet.wallet_id,
        receiver_wallet_id=wallet.wallet_id,
        amount=price,
        transaction_type="subscription_buy",
    ))

    await db.commit()

    return SubscriptionPurchaseResponse(
        success=True,
        coins_spent=price,
        new_balance=wallet.balance_coins,
        subscription_expires_at=new_expiry,
    )


@router.patch("/subscription/auto-renew", response_model=AutoRenewResponse)
async def set_auto_renew(
    request: AutoRenewRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Opt in/out of auto-renew and pick how it pays. The 24h-before-expiry
    Telegram reminder is sent either way:
    - "mastercoins": auto-charges the balance directly.
    - "crypto": can't be auto-charged (no pull payments over crypto), so the
      reminder instead attaches a ready-to-pay invoice for the exact renewal
      amount — one tap instead of a manual checkout.
    """
    current_user.wallet.auto_renew = request.enabled
    current_user.wallet.auto_renew_method = request.method
    await db.commit()
    return AutoRenewResponse(
        auto_renew=current_user.wallet.auto_renew,
        auto_renew_method=current_user.wallet.auto_renew_method,
    )
