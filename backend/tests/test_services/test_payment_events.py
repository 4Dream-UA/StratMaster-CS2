from backend.app.db.models import CryptoInvoiceModel
from backend.app.services.payment_events import process_paid_invoice
from backend.tests.factories import make_user


async def _make_invoice(db_session, user, *, coins, plan=None, months=None, invoice_id):
    invoice = CryptoInvoiceModel(
        invoice_id=invoice_id, user_id=user.id, coins=coins,
        plan=plan, months=months, amount_usd=f"{coins * 0.01:.2f}", status="active",
    )
    db_session.add(invoice)
    await db_session.commit()
    return invoice


async def test_plain_coin_topup_credits_balance_only(db_session):
    user = await make_user(db_session, balance=0)
    await _make_invoice(db_session, user, coins=500, invoice_id=1001)

    invoice = await process_paid_invoice(db_session, 1001)
    assert invoice.status == "paid"

    await db_session.refresh(user.wallet)
    assert user.wallet.balance_coins == 500
    assert user.wallet.subscription_expires_at is None


async def test_plan_invoice_credits_then_auto_spends(db_session):
    user = await make_user(db_session, balance=0)
    await _make_invoice(db_session, user, coins=99, plan="premium", months=1, invoice_id=1002)

    await process_paid_invoice(db_session, 1002)

    await db_session.refresh(user.wallet)
    assert user.wallet.balance_coins == 0  # credited 99, then spent 99
    assert user.wallet.subscription_expires_at is not None


async def test_lifetime_invoice_sets_is_lifetime(db_session):
    user = await make_user(db_session, balance=0)
    await _make_invoice(db_session, user, coins=4999, plan="lifetime", months=None, invoice_id=1003)

    await process_paid_invoice(db_session, 1003)

    await db_session.refresh(user.wallet)
    assert user.wallet.is_lifetime is True


async def test_processing_is_idempotent_on_retry(db_session):
    """CryptoPay retries webhooks that don't get a prompt 200 — must not double-credit."""
    user = await make_user(db_session, balance=0)
    await _make_invoice(db_session, user, coins=200, invoice_id=1004)

    await process_paid_invoice(db_session, 1004)
    await process_paid_invoice(db_session, 1004)  # simulate a retry

    await db_session.refresh(user.wallet)
    assert user.wallet.balance_coins == 200


async def test_unknown_invoice_id_returns_none(db_session):
    result = await process_paid_invoice(db_session, 999999)
    assert result is None
