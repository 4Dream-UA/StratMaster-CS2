from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import CryptoInvoiceModel
from backend.app.schemas.payment import (
    CryptoInvoiceRequest,
    CryptoInvoiceResponse,
    CryptoInvoiceStatusResponse,
)
from backend.app.services.crypto import CryptoPayError, create_invoice, invoice_pay_url
from backend.app.services.subscription import (
    MIN_COIN_PURCHASE,
    apply_discount,
    assert_purchasable,
    price_for,
    usd_for_coins,
)

router = APIRouter()


@router.post(
    "/payments/crypto/invoice",
    response_model=CryptoInvoiceResponse,
    dependencies=[Depends(rate_limit("crypto_invoice", max_requests=10, window_seconds=60))],
)
async def create_crypto_invoice(
    request: CryptoInvoiceRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Creates a CryptoPay invoice — either to buy a plan directly with
    crypto, or to top up raw MasterCoins (ТЗ 5.1, min 10 coins). Payment
    itself is confirmed asynchronously via the signed webhook."""
    wallet = current_user.wallet

    if request.plan:
        try:
            assert_purchasable(wallet)
            coins = apply_discount(price_for(request.plan, request.months), wallet)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        description = f"StratMaster CS2 — {request.plan}" + (f" ({request.months}mo)" if request.months else "")
    else:
        if request.coins < MIN_COIN_PURCHASE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum purchase is {MIN_COIN_PURCHASE} MasterCoins",
            )
        coins = request.coins
        description = f"StratMaster CS2 — {coins} MasterCoins"

    amount_usd = usd_for_coins(coins)

    try:
        invoice = await create_invoice(
            amount_usd=amount_usd,
            description=description,
            payload=str(current_user.id),
        )
    except CryptoPayError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"CryptoPay: {exc.name}")

    pay_url = invoice_pay_url(invoice)
    if pay_url is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="CryptoPay did not return a payment link")

    db.add(CryptoInvoiceModel(
        invoice_id=invoice["invoice_id"],
        user_id=current_user.id,
        coins=coins,
        plan=request.plan,
        months=request.months,
        amount_usd=f"{amount_usd:.2f}",
        status="active",
    ))
    await db.commit()

    return CryptoInvoiceResponse(
        invoice_id=invoice["invoice_id"],
        pay_url=pay_url,
        amount_usd=amount_usd,
        coins=coins,
        status="active",
    )


@router.get("/payments/crypto/invoice/{invoice_id}", response_model=CryptoInvoiceStatusResponse)
async def get_crypto_invoice_status(
    invoice_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Lets the frontend poll while the CryptoPay checkout is open, so it
    can refresh the wallet the moment the webhook marks the invoice paid."""
    result = await db.execute(
        select(CryptoInvoiceModel).where(
            CryptoInvoiceModel.invoice_id == invoice_id,
            CryptoInvoiceModel.user_id == current_user.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return CryptoInvoiceStatusResponse(invoice_id=invoice.invoice_id, status=invoice.status, paid_at=invoice.paid_at)
