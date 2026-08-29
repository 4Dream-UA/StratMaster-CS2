from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import CaseInventoryModel, CaseModel, PromoCodeModel, PromoRedemptionModel, TransactionModel, WalletModel
from backend.app.services.subscription import grant_premium_days

router = APIRouter()


class PromoRedeemRequest(BaseModel):
    code: str


@router.post(
    "/promo/redeem",
    dependencies=[Depends(rate_limit("promo_redeem", max_requests=15, window_seconds=60))],
)
async def redeem_promo_code(
    request: PromoRedeemRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    code = request.code.strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a promo code")

    # Case/whitespace-insensitive match — protects against codes typed or
    # stored (e.g. via manual SQL insert) with different casing/spacing.
    result = await db.execute(
        select(PromoCodeModel).where(func.upper(func.trim(PromoCodeModel.code)) == code)
    )
    promo = result.scalar_one_or_none()

    if promo is None or not promo.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found or inactive")

    # ── Enforce one redemption per user per code ──
    result = await db.execute(
        select(PromoRedemptionModel).where(
            PromoRedemptionModel.user_id == current_user.id,
            PromoRedemptionModel.promo_code_id == promo.id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You've already used this promo code")

    if promo.activations_limit is not None and promo.used_count >= promo.activations_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promo code activation limit reached")

    result = await db.execute(
        select(WalletModel).where(WalletModel.id == current_user.wallet.id)
    )
    wallet = result.scalar_one()

    case = None
    if promo.reward_type == "case":
        if promo.case_id is not None:
            case = await db.get(CaseModel, promo.case_id)
        if case is None or not case.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This promo code's reward is no longer available")

    response: dict = {"success": True, "reward_type": promo.reward_type}

    if promo.reward_type == "premium":
        new_expiry = grant_premium_days(wallet, promo.premium_days)
        response["premium_days"] = promo.premium_days
        response["new_subscription_expires_at"] = new_expiry.isoformat()
        response["is_lifetime"] = wallet.is_lifetime
    elif promo.reward_type == "case":
        for _ in range(promo.case_quantity):
            db.add(CaseInventoryModel(user_id=current_user.id, case_id=case.id))
        response["case_name"] = case.name
        response["case_quantity"] = promo.case_quantity
    else:
        wallet.balance_coins += promo.coin_reward
        response["coins_awarded"] = promo.coin_reward
        response["new_balance"] = wallet.balance_coins

    promo.used_count += 1
    if promo.activations_limit is not None and promo.used_count >= promo.activations_limit:
        promo.is_active = False

    db.add(PromoRedemptionModel(
        user_id=current_user.id,
        promo_code_id=promo.id,
    ))

    db.add(TransactionModel(
        sender_wallet_id=None,
        receiver_wallet_id=wallet.wallet_id,
        amount=promo.coin_reward if promo.reward_type == "coins" else 0,
        transaction_type="promo_code",
    ))

    await db.commit()

    return response