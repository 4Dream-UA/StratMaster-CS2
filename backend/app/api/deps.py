from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import validate_telegram_init_data
from backend.app.db.database import get_db


async def get_current_user_data(
    x_init_data: Annotated[str | None, Header()] = None,
) -> dict:
    """
    Validates Telegram initData from the X-Init-Data request header.
    Returns parsed user data dict.
    """
    if not x_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Init-Data header",
        )

    data = validate_telegram_init_data(x_init_data)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData signature",
        )

    return data


# Convenient type aliases for route signatures
DBSession = Annotated[AsyncSession, Depends(get_db)]
TelegramUser = Annotated[dict, Depends(get_current_user_data)]