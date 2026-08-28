import uuid
from datetime import datetime

from pydantic import BaseModel


class CaseRewardOut(BaseModel):
    coins: int
    chance_percent: float


class CaseOut(BaseModel):
    id: uuid.UUID
    name: str
    cost_coins: int
    rewards: list[CaseRewardOut]
    model_config = {"from_attributes": True}


class CaseOpenResponse(BaseModel):
    reward_coins: int
    coins_spent: int
    new_balance: int


class CaseOpeningHistoryItem(BaseModel):
    id: uuid.UUID
    case_name: str
    coins_spent: int
    coins_won: int
    created_at: datetime


class CaseOpeningHistoryResponse(BaseModel):
    openings: list[CaseOpeningHistoryItem]
