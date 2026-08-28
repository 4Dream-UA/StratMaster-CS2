import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WalletResponse(BaseModel):
    id: uuid.UUID
    wallet_id: str
    balance_coins: int
    subscription_expires_at: datetime | None
    ref_discount_expires_at: datetime | None
    is_lifetime: bool
    last_plan_months: int | None
    auto_renew: bool
    auto_renew_method: str

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
    ref_wallet_id: Optional[str] = None


class UserAdminOut(BaseModel):
    """User row for the admin users list — same as UserResponse, kept separate
    so the admin listing shape can evolve independently of the auth response."""
    id: uuid.UUID
    telegram_id: int
    username: str | None
    is_admin: bool
    created_at: datetime
    wallet: WalletResponse

    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    total: int
    users: list[UserAdminOut]


class SetAdminRequest(BaseModel):
    is_admin: bool
