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
    avatar_url: str | None = None
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
    avatar_url: str | None = None
    is_admin: bool
    is_banned: bool = False
    is_trade_banned: bool = False
    created_at: datetime
    wallet: WalletResponse

    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    total: int
    users: list[UserAdminOut]


class SetAdminRequest(BaseModel):
    is_admin: bool


class SetBannedRequest(BaseModel):
    is_banned: bool


class SetTradeBannedRequest(BaseModel):
    is_trade_banned: bool


class AdminGrantSubscriptionRequest(BaseModel):
    months: int = Field(..., ge=0, le=120, description="0 grants lifetime access")


class UpdateAvatarRequest(BaseModel):
    avatar_url: str | None = None


class BlockedUserOut(BaseModel):
    wallet_id: str
    username: str | None = None


class BlockUserRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=16)
