import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


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
    display_name: str | None = None
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
    display_name: str | None = None
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


class SetNicknameRequest(BaseModel):
    nickname: str | None = Field(None, max_length=32)

    @field_validator("nickname")
    @classmethod
    def _blank_becomes_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class AdminGrantCoinsRequest(BaseModel):
    amount: int = Field(..., gt=0, le=1_000_000)


class AdminSetPremiumRequest(BaseModel):
    """Sets the wallet's premium expiry to an ABSOLUTE value (now + duration),
    overwriting whatever time was left — unlike /subscription, which extends."""
    unit: Literal["forever", "month", "hour", "minute"]
    amount: int | None = Field(None, ge=1, le=1000)

    @model_validator(mode="after")
    def _amount_required_unless_forever(self):
        if self.unit != "forever" and self.amount is None:
            raise ValueError("amount is required unless unit is 'forever'")
        return self


class BlockedUserOut(BaseModel):
    wallet_id: str
    username: str | None = None


class BlockUserRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=16)
