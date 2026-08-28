from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SubscriptionPurchaseRequest(BaseModel):
    plan: Literal["premium", "lifetime"]
    months: Literal[1, 3, 6, 12] | None = None


class SubscriptionPurchaseResponse(BaseModel):
    success: bool
    coins_spent: int
    new_balance: int
    subscription_expires_at: datetime


class AutoRenewRequest(BaseModel):
    enabled: bool
    method: Literal["mastercoins", "crypto"] = "mastercoins"


class AutoRenewResponse(BaseModel):
    auto_renew: bool
    auto_renew_method: str
