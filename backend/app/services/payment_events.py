from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models import CryptoInvoiceModel, TransactionModel, UserModel
from backend.app.services.subscription import extend_subscription


async def process_paid_invoice(db: AsyncSession, invoice_id: int) -> CryptoInvoiceModel | None:
    """Credits the wallet for a CryptoPay invoice that's just been reported
    paid, then (if the invoice was for a plan, not a plain coin top-up)
    immediately spends those coins on that plan.

    Idempotent: CryptoPay retries webhooks that don't get a prompt 200, so
    an invoice already marked "paid" is a no-op — returns it unchanged
    instead of crediting twice. Returns None if we have no record of this
    invoice_id (e.g. one created outside our own /payments endpoint).
    """
    result = await db.execute(
        select(CryptoInvoiceModel).where(CryptoInvoiceModel.invoice_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        return None
    if invoice.status == "paid":
        return invoice

    user_result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == invoice.user_id)
    )
    user = user_result.scalar_one()
    wallet = user.wallet

    wallet.balance_coins += invoice.coins
    db.add(TransactionModel(
        sender_wallet_id=None,  # external money in, not from another wallet
        receiver_wallet_id=wallet.wallet_id,
        amount=invoice.coins,
        transaction_type="crypto_deposit",
    ))

    if invoice.plan:
        price = invoice.coins  # the invoice was sized to exactly cover this plan's coin price
        wallet.balance_coins -= price
        extend_subscription(wallet, invoice.plan, invoice.months)
        db.add(TransactionModel(
            sender_wallet_id=wallet.wallet_id,
            receiver_wallet_id=wallet.wallet_id,
            amount=price,
            transaction_type="subscription_buy",
        ))

    invoice.status = "paid"
    invoice.paid_at = datetime.now(timezone.utc)

    await db.commit()
    return invoice
