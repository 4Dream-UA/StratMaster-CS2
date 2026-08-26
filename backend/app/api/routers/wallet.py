from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import TransactionModel
from backend.app.schemas.wallet import (
    CoinTransferRequest,
    CoinTransferResponse,
    GiftSubscriptionRequest,
    GiftSubscriptionResponse,
)
from backend.app.services.subscription import assert_purchasable, extend_subscription, price_for
from backend.app.services.wallet import assert_transferable, get_wallet_by_id

router = APIRouter()


@router.post(
    "/wallet/transfer",
    response_model=CoinTransferResponse,
    dependencies=[Depends(rate_limit("wallet_transfer", max_requests=20, window_seconds=60))],
)
async def transfer_coins(
    request: CoinTransferRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Atomic P2P MasterCoins transfer by wallet ID (ТЗ 5.1). Validation runs
    before any balance mutation, and both balances are updated in the same
    DB transaction — if the receiver wallet doesn't exist, the sender's
    balance is left completely untouched."""
    sender = current_user.wallet
    receiver = await get_wallet_by_id(db, request.receiver_wallet_id)

    try:
        assert_transferable(sender, receiver, request.amount)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    sender.balance_coins -= request.amount
    receiver.balance_coins += request.amount

    db.add(TransactionModel(
        sender_wallet_id=sender.wallet_id,
        receiver_wallet_id=receiver.wallet_id,
        amount=request.amount,
        transaction_type="p2p_transfer",
    ))

    await db.commit()

    return CoinTransferResponse(
        success=True,
        amount=request.amount,
        new_balance=sender.balance_coins,
        receiver_wallet_id=receiver.wallet_id,
    )


@router.post(
    "/wallet/gift-subscription",
    response_model=GiftSubscriptionResponse,
    dependencies=[Depends(rate_limit("wallet_gift", max_requests=15, window_seconds=60))],
)
async def gift_subscription(
    request: GiftSubscriptionRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Buy premium/lifetime access for another player, paid from your own
    MasterCoins balance (ТЗ 5.1 — "дарить подписки другим пользователям").
    Charged at full price: referral discounts are personal to the account
    making its own first purchase and don't carry over to a gift."""
    if request.plan == "premium" and request.months is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="months is required for the premium plan")

    sender = current_user.wallet
    receiver = await get_wallet_by_id(db, request.receiver_wallet_id)

    if receiver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No wallet found with this ID")
    if receiver.id == sender.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use the shop to buy your own subscription")

    try:
        assert_purchasable(receiver)
        price = price_for(request.plan, request.months)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if sender.balance_coins < price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough MasterCoins — need {price}, have {sender.balance_coins}",
        )

    sender.balance_coins -= price
    new_expiry = extend_subscription(receiver, request.plan, request.months)

    db.add(TransactionModel(
        sender_wallet_id=sender.wallet_id,
        receiver_wallet_id=receiver.wallet_id,
        amount=price,
        transaction_type="subscription_buy",
    ))

    await db.commit()

    return GiftSubscriptionResponse(
        success=True,
        coins_spent=price,
        new_balance=sender.balance_coins,
        receiver_wallet_id=receiver.wallet_id,
        receiver_subscription_expires_at=new_expiry,
    )
