from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CryptoInvoiceRequest(BaseModel):
    """Either buy a plan directly with crypto (plan set) or top up raw
    MasterCoins (coins set) — exactly one of the two."""
    plan: Literal["premium", "lifetime"] | None = None
    months: Literal[1, 3, 6, 12] | None = None
    coins: int | None = Field(None, gt=0)

    @model_validator(mode="after")
    def _exactly_one_purchase_kind(self):
        if bool(self.plan) == bool(self.coins):
            raise ValueError("Provide either plan (+months) or coins, not both")
        if self.plan == "premium" and self.months is None:
            raise ValueError("months is required for the premium plan")
        return self


class CryptoInvoiceResponse(BaseModel):
    invoice_id: int
    pay_url: str
    amount_usd: float
    coins: int
    status: str


class CryptoInvoiceStatusResponse(BaseModel):
    invoice_id: int
    status: Literal["active", "paid", "expired"]
    paid_at: datetime | None = None
