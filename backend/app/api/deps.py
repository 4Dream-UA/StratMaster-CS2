from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.security import validate_telegram_init_data
from backend.app.db.database import get_db

# Shorthand type alias for DB dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_telegram_user(
    x_init_data: Annotated[Optional[str], Header()] = None,
) -> dict:
    """
    Dependency: validates X-Init-Data header and returns parsed Telegram user data.
    Used on protected endpoints that require an authenticated Telegram user.
    """
    if not x_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Init-Data header is missing",
        )

    data = validate_telegram_init_data(x_init_data)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData signature",
        )

    return data


TelegramUser = Annotated[dict, Depends(get_telegram_user)]


async def get_current_user(
    db: DBSession,
    telegram_user: TelegramUser,
):
    """Resolve the full UserModel (with wallet) for the authenticated Telegram user."""
    from backend.app.db.models import UserModel

    user_data = telegram_user.get("user", {})
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user data")

    result = await db.execute(
        select(UserModel)
        .options(selectinload(UserModel.wallet))
        .where(UserModel.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found. Please authenticate first.")

    return user


CurrentUser = Annotated["UserModel", Depends(get_current_user)]


async def get_optional_user(
    db: DBSession,
    x_init_data: Annotated[Optional[str], Header()] = None,
):
    """
    Dependency: resolves the authenticated UserModel if a valid X-Init-Data
    header is present, otherwise returns None. Never raises — used on public
    endpoints that still need to know "is this a logged-in, subscribed user?".
    """
    if not x_init_data:
        return None

    data = validate_telegram_init_data(x_init_data)
    if data is None:
        return None

    from backend.app.db.models import UserModel

    telegram_id = data.get("user", {}).get("id")
    if not telegram_id:
        return None

    result = await db.execute(
        select(UserModel)
        .options(selectinload(UserModel.wallet))
        .where(UserModel.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


OptionalUser = Annotated["UserModel | None", Depends(get_optional_user)]


async def get_admin_user(current_user: CurrentUser):
    """Dependency: ensures the authenticated user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


AdminUser = Annotated["UserModel", Depends(get_admin_user)]


async def get_premium_user(current_user: CurrentUser):
    """Dependency: ensures the authenticated user has an active subscription."""
    from backend.app.services.strategy import has_active_subscription

    if not has_active_subscription(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active subscription is required",
        )
    return current_user


PremiumUser = Annotated["UserModel", Depends(get_premium_user)]
