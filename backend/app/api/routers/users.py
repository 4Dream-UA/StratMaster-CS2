from datetime import datetime, timedelta, timezone

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import CurrentUser, DBSession, PremiumUser, TelegramUser
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import TransactionModel, UserModel, WalletModel
from backend.app.schemas.user import (
    AuthRequest,
    PublicProfileResponse,
    SetNicknameRequest,
    UpdateAvatarRequest,
    UpdateForumPrivacyRequest,
    UpdateProfileInfoRequest,
    UserResponse,
    UserSearchResult,
)
from backend.app.services.referral import generate_wallet_id

router = APIRouter()

REFERRAL_BONUS_COINS = 10
REFERRAL_DISCOUNT_HOURS = 24


@router.post(
    "/auth",
    response_model=UserResponse,
    dependencies=[Depends(rate_limit("auth", max_requests=20, window_seconds=60, identity_source="ip"))],
)
async def auth(
        request: AuthRequest,
        db: DBSession,
):
    from backend.app.core.security import validate_telegram_init_data

    data = validate_telegram_init_data(request.init_data)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData signature",
        )

    user_data = data.get("user", {})
    telegram_id = user_data.get("id")
    username = user_data.get("username")

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data",
        )

    result = await db.execute(
        select(UserModel)
        .options(selectinload(UserModel.wallet))
        .where(UserModel.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user is not None and user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has been banned.")

    if user is None:
        # ── Resolve referrer (if a valid ref_wallet_id was passed) ──
        referrer_wallet = None
        if request.ref_wallet_id:
            result = await db.execute(
                select(WalletModel).where(WalletModel.wallet_id == request.ref_wallet_id)
            )
            referrer_wallet = result.scalar_one_or_none()

        user = UserModel(
            telegram_id=telegram_id,
            username=username,
            referred_by_id=referrer_wallet.user_id if referrer_wallet else None,
        )
        db.add(user)
        await db.flush()

        wallet = WalletModel(
            user_id=user.id,
            wallet_id=generate_wallet_id(),
            balance_coins=0,
        )

        # New user gets a 25% discount for 24h if they came via referral
        if referrer_wallet:
            wallet.ref_discount_expires_at = datetime.now(timezone.utc) + timedelta(hours=REFERRAL_DISCOUNT_HOURS)

        db.add(wallet)
        await db.flush()

        # Credit the referrer with bonus coins
        if referrer_wallet:
            referrer_wallet.balance_coins += REFERRAL_BONUS_COINS
            db.add(TransactionModel(
                sender_wallet_id=None,
                receiver_wallet_id=referrer_wallet.wallet_id,
                amount=REFERRAL_BONUS_COINS,
                transaction_type="referral_bonus",
            ))

        await db.commit()
        user.wallet = wallet

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me/avatar", response_model=UserResponse)
async def update_avatar(payload: UpdateAvatarRequest, db: DBSession, current_user: PremiumUser):
    """Premium-only — uploads go through POST /forum/uploads (same
    validation, already premium-gated), this just attaches the resulting
    URL to the account. avatar_url=None clears back to the generated
    initials avatar."""
    current_user.avatar_url = payload.avatar_url
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/nickname", response_model=UserResponse)
async def update_nickname(payload: SetNicknameRequest, db: DBSession, current_user: CurrentUser):
    """Open to every user, not just premium — the display name is a free
    cosmetic, unlike avatar uploads which cost storage."""
    current_user.display_name = payload.nickname
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/profile-info", response_model=UserResponse)
async def update_profile_info(payload: UpdateProfileInfoRequest, db: DBSession, current_user: CurrentUser):
    """Every field optional — an empty string is treated the same as
    unset, so clearing a field in the form actually removes it rather than
    saving a blank line on the public popup."""
    data = {k: (v.strip() or None if isinstance(v, str) else v) for k, v in payload.model_dump().items()}
    current_user.profile_info = data if any(data.values()) else None
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/forum-privacy", response_model=UserResponse)
async def update_forum_privacy(payload: UpdateForumPrivacyRequest, db: DBSession, current_user: CurrentUser):
    current_user.hide_username_on_forum = payload.hide_username_on_forum
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/users/search", response_model=list[UserSearchResult])
async def search_users(db: DBSession, current_user: CurrentUser, q: str = Query(..., min_length=1, max_length=32)):
    """Username-prefix search that powers the forum @mention autocomplete
    and the whisper-recipient picker. Deliberately not gated by
    hide_username_on_forum — that flag only affects how a name is
    *displayed* in posts, not whether the player can be found by name."""
    result = await db.execute(
        select(UserModel)
        .where(UserModel.username.ilike(f"{q}%"), UserModel.id != current_user.id)
        .order_by(UserModel.username)
        .limit(10)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/public-profile", response_model=PublicProfileResponse)
async def get_public_profile(user_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    username = user.username
    if user.hide_username_on_forum and not current_user.is_admin and user.id != current_user.id:
        username = None

    return PublicProfileResponse(
        id=user.id, username=username, display_name=user.display_name,
        avatar_url=user.avatar_url, is_admin=user.is_admin, profile_info=user.profile_info,
    )
