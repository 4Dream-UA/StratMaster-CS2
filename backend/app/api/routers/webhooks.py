import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from backend.app.api.deps import DBSession
from backend.app.core.security import validate_cryptopay_webhook
from backend.app.services.payment_events import process_paid_invoice

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/cryptopay")
async def cryptopay_webhook(
    request: Request,
    db: DBSession,
    signature: str | None = Header(None, alias="crypto-pay-api-signature"),
):
    """Receives CryptoPay's `invoice_paid` callback. Verified by HMAC
    signature, not by any application-level auth — this endpoint has no
    Telegram/admin dependency, since CryptoPay's own server is the caller.
    """
    raw_body = await request.body()

    if not validate_cryptopay_webhook(raw_body, signature or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        data = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    if data.get("update_type") != "invoice_paid":
        # Other update types exist (e.g. future ones CryptoPay adds) — 200
        # so they don't get endlessly retried; we just have nothing to do.
        return {"ok": True}

    invoice_id = (data.get("payload") or {}).get("invoice_id")
    if invoice_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payload.invoice_id")

    invoice = await process_paid_invoice(db, invoice_id)
    if invoice is None:
        logger.warning("CryptoPay webhook for unknown invoice_id=%s — ignoring", invoice_id)

    return {"ok": True}
