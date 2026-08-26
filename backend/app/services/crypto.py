import httpx

from backend.app.core.config import settings

CRYPTOPAY_BASE_URL = "https://pay.crypt.bot/api"


class CryptoPayError(Exception):
    """Raised when CryptoPay's API responds with ok: false."""

    def __init__(self, code: int, name: str):
        self.code = code
        self.name = name
        super().__init__(f"CryptoPay error {code}: {name}")


async def create_invoice(*, amount_usd: float, description: str, payload: str) -> dict:
    """Creates a fiat-denominated (USD) CryptoPay invoice — the payer picks
    which crypto to settle in on CryptoPay's side. Returns the raw `result`
    object from the API (has invoice_id, status, and one or more pay-link
    fields depending on API version)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{CRYPTOPAY_BASE_URL}/createInvoice",
            headers={"Crypto-Pay-API-Token": settings.cryptopay_token},
            json={
                "currency_type": "fiat",
                "fiat": "USD",
                "amount": f"{amount_usd:.2f}",
                "description": description,
                "payload": payload,
                "expires_in": 3600,
            },
        )
    data = response.json()
    if not data.get("ok"):
        error = data.get("error", {})
        raise CryptoPayError(error.get("code", 0), error.get("name", "UNKNOWN_ERROR"))
    return data["result"]


def invoice_pay_url(invoice: dict) -> str | None:
    """Best available payment link across CryptoPay API versions."""
    for key in ("mini_app_invoice_url", "web_app_invoice_url", "bot_invoice_url", "pay_url"):
        if invoice.get(key):
            return invoice[key]
    return None
