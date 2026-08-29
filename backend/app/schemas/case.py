import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CaseRewardOut(BaseModel):
    coins: int
    chance_percent: float


class CaseOut(BaseModel):
    id: uuid.UUID
    name: str
    cost_coins: int
    rewards: list[CaseRewardOut]
    model_config = {"from_attributes": True}


class CaseBuyRequest(BaseModel):
    quantity: int = Field(1, ge=1, le=50)


class CaseBuyResponse(BaseModel):
    case_id: uuid.UUID
    quantity: int
    new_balance: int


class CaseInventoryItem(BaseModel):
    case_id: uuid.UUID
    case_name: str
    count: int


class CaseOpenBulkRequest(BaseModel):
    case_id: uuid.UUID
    quantity: int = Field(..., description="How many owned cases of this type to open at once — 1, 2 or 5")


class CaseOpenBulkResponse(BaseModel):
    rewards: list[int]
    total_won: int
    total_spent: int
    new_balance: int


class CaseOpeningHistoryItem(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    case_name: str
    coins_spent: int
    coins_won: int
    created_at: datetime


class CaseOpeningHistoryResponse(BaseModel):
    openings: list[CaseOpeningHistoryItem]


class CaseGiftRequest(BaseModel):
    receiver_wallet_id: str = Field(..., min_length=1, max_length=16)
    case_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=50)


class CaseSaleRequest(BaseModel):
    receiver_wallet_id: str = Field(..., min_length=1, max_length=16)
    case_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=50)
    price_coins: int = Field(..., ge=1)


class CaseOfferOut(BaseModel):
    id: uuid.UUID
    sender_wallet_id: str
    sender_username: str | None = None
    receiver_wallet_id: str
    receiver_username: str | None = None
    case_id: uuid.UUID
    case_name: str
    quantity: int
    price_coins: int
    offer_type: str
    status: str
    created_at: datetime
