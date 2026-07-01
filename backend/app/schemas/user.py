import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class WalletResponse(BaseModel):
    id: uuid.UUID
    wallet_id: str
    balance_coins: int
    subscription_expires_at: datetime | None
    ref_discount_expires_at: datetime | None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    username: str | None
    is_admin: bool
    created_at: datetime
    wallet: WalletResponse

    class Config:
        from_attributes = True


class AuthRequest(BaseModel):
    init_data: str = Field(..., description="Telegram WebApp initData string")
