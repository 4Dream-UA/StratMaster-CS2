import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CoinTransferRequest(BaseModel):
    receiver_wallet_id: str = Field(..., min_length=1, max_length=16)
    amount: int = Field(..., gt=0)


class CoinTransferResponse(BaseModel):
    success: bool
    amount: int
    new_balance: int
    receiver_wallet_id: str


class GiftSubscriptionRequest(BaseModel):
    receiver_wallet_id: str = Field(..., min_length=1, max_length=16)
    plan: Literal["premium", "lifetime"]
    months: Literal[1, 3, 6, 12] | None = None


class GiftSubscriptionResponse(BaseModel):
    success: bool
    coins_spent: int
    new_balance: int
    receiver_wallet_id: str
    receiver_subscription_expires_at: datetime


class TransactionOut(BaseModel):
    id: uuid.UUID
    sender_wallet_id: str | None
    receiver_wallet_id: str
    amount: int
    transaction_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionsListResponse(BaseModel):
    total: int
    transactions: list[TransactionOut]
