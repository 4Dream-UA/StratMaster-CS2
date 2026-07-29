from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.db.models import PromoCodeModel, PromoRedemptionModel, TransactionModel, WalletModel

router = APIRouter()


class PromoRedeemRequest(BaseModel):
    code: str


@router.post("/promo/redeem")
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

    wallet.balance_coins += promo.coin_reward
    promo.used_count += 1

    db.add(PromoRedemptionModel(
        user_id=current_user.id,
        promo_code_id=promo.id,
    ))

    db.add(TransactionModel(
        sender_wallet_id=None,
        receiver_wallet_id=wallet.wallet_id,
        amount=promo.coin_reward,
        transaction_type="promo_code",
    ))

    await db.commit()

    return {
        "success": True,
        "coins_awarded": promo.coin_reward,
        "new_balance": wallet.balance_coins,
    }