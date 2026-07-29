from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.db.models import TransactionModel, UserModel, WalletModel

router = APIRouter()

REFERRAL_BONUS_COINS = 10
REFERRAL_DISCOUNT_PERCENT = 25
REFERRAL_DISCOUNT_HOURS = 24


class ReferralApplyRequest(BaseModel):
    code: str


@router.get("/referral/stats")
async def get_referral_stats(db: DBSession, current_user: CurrentUser) -> dict:
    """
    Returns the current user's referral code (= wallet_id), how many people
    they've referred, total MasterCoins earned, and whether they can still
    redeem someone else's code (only once, ever — no time limit).
    """
    result = await db.execute(
        select(func.count()).select_from(UserModel).where(UserModel.referred_by_id == current_user.id)
    )
    referred_count = result.scalar() or 0

    result = await db.execute(
        select(func.coalesce(func.sum(TransactionModel.amount), 0))
        .where(
            TransactionModel.receiver_wallet_id == current_user.wallet.wallet_id,
            TransactionModel.transaction_type == "referral_bonus",
        )
    )
    total_earned = result.scalar() or 0

    already_used_code = current_user.referred_by_id is not None

    return {
        "referral_code": current_user.wallet.wallet_id,
        "referred_count": referred_count,
        "total_earned_coins": total_earned,
        "bonus_per_referral": REFERRAL_BONUS_COINS,
        "referral_discount_percent": REFERRAL_DISCOUNT_PERCENT,
        "can_apply_code": not already_used_code,
        "already_used_code": already_used_code,
    }


@router.post("/referral/apply")
async def apply_referral_code(
    request: ReferralApplyRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """
    Redeem a friend's referral code. Usable at any time, but only once
    per account (referred_by_id must still be null).
    """
    if current_user.referred_by_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You've already used a referral code",
        )

    code = request.code.strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a referral code")

    # Case/whitespace-insensitive match — protects against codes typed or
    # stored with different casing.
    result = await db.execute(
        select(WalletModel).where(func.upper(func.trim(WalletModel.wallet_id)) == code)
    )
    referrer_wallet = result.scalar_one_or_none()

    if referrer_wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral code not found")

    if referrer_wallet.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't use your own referral code")

    now = datetime.now(timezone.utc)

    current_user.referred_by_id = referrer_wallet.user_id
    current_user.wallet.ref_discount_expires_at = now + timedelta(hours=REFERRAL_DISCOUNT_HOURS)

    referrer_wallet.balance_coins += REFERRAL_BONUS_COINS
    db.add(TransactionModel(
        sender_wallet_id=None,
        receiver_wallet_id=referrer_wallet.wallet_id,
        amount=REFERRAL_BONUS_COINS,
        transaction_type="referral_bonus",
    ))

    await db.commit()

    return {
        "success": True,
        "discount_percent": REFERRAL_DISCOUNT_PERCENT,
        "discount_expires_at": current_user.wallet.ref_discount_expires_at.isoformat(),
    }