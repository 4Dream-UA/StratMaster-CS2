from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.deps import DBSession, TelegramUser
from backend.app.db.models import UserModel, WalletModel
from backend.app.schemas.user import AuthRequest, UserResponse
from backend.app.services.referral import generate_wallet_id

router = APIRouter()


@router.post("/auth", response_model=UserResponse)
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

    if user is None:
        user = UserModel(
            telegram_id=telegram_id,
            username=username,
        )
        db.add(user)
        await db.flush()

        wallet = WalletModel(
            user_id=user.id,
            wallet_id=generate_wallet_id(),
            balance_coins=0,
        )
        db.add(wallet)
        await db.commit()

        user.wallet = wallet

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
        db: DBSession,
        telegram_user: TelegramUser,
):
    user_data = telegram_user.get("user", {})
    telegram_id = user_data.get("id")

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

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
