import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db.models import CryptoInvoiceModel, TransactionModel, WalletModel
from backend.app.services.crypto import CryptoPayError, create_invoice, invoice_pay_url
from backend.app.services.subscription import apply_discount, extend_subscription, price_for, usd_for_coins

logger = logging.getLogger(__name__)

REMINDER_WINDOW = timedelta(hours=24)


async def _find_wallets_needing_reminder(db):
    now = datetime.now(timezone.utc)
    horizon = now + REMINDER_WINDOW
    result = await db.execute(
        select(WalletModel)
        .options(selectinload(WalletModel.user))
        .where(
            WalletModel.is_lifetime.is_(False),
            WalletModel.subscription_expires_at.isnot(None),
            WalletModel.subscription_expires_at > now,
            WalletModel.subscription_expires_at <= horizon,
        )
    )
    wallets = result.scalars().all()
    # Only wallets whose reminder wasn't already sent for *this* expiry —
    # a renewal resets subscription_expires_at, which naturally re-arms this.
    return [w for w in wallets if w.reminder_sent_for_expiry != w.subscription_expires_at]


async def _notify(bot, telegram_id: int, text: str, webapp_url: str | None = None, pay_url: str | None = None) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    buttons = []
    if pay_url:
        # A plain link button, not web_app — CryptoPay's pay_url is often a
        # t.me/CryptoBot deep link, which a web_app button can't open.
        buttons.append([InlineKeyboardButton(text="💳 Pay & Renew Now", url=pay_url)])
    if webapp_url:
        buttons.append([InlineKeyboardButton(text="Renew in StratMaster", web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/pricing"))])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    try:
        await bot.send_message(telegram_id, text, reply_markup=markup)
    except Exception:
        logger.exception("Failed to send renewal reminder to telegram_id=%s", telegram_id)


async def _auto_renew_with_mastercoins(db, wallet: WalletModel, bot, webapp_url, plan_months, price) -> None:
    user = wallet.user
    if wallet.balance_coins >= price:
        wallet.balance_coins -= price
        new_expiry = extend_subscription(wallet, "premium", plan_months)
        db.add(TransactionModel(
            sender_wallet_id=wallet.wallet_id,
            receiver_wallet_id=wallet.wallet_id,
            amount=price,
            transaction_type="subscription_buy",
        ))
        await db.commit()
        await _notify(
            bot, user.telegram_id,
            f"✅ Your StratMaster Premium was auto-renewed for {plan_months} month(s) — "
            f"{price} MC charged. New expiry: {new_expiry:%Y-%m-%d}.",
        )
        return

    # Auto-renew is on but the balance can't cover it — fall back to a
    # manual reminder instead of silently failing to renew.
    wallet.reminder_sent_for_expiry = wallet.subscription_expires_at
    await db.commit()
    await _notify(
        bot, user.telegram_id,
        "⚠️ Auto-renew is on, but your MasterCoins balance is too low to renew Premium. "
        "Top up or renew manually in the next 24 hours to keep your access.",
        webapp_url,
    )


async def _auto_renew_with_crypto(db, wallet: WalletModel, bot, webapp_url, plan_months, price) -> None:
    # Crypto payments can't be pulled from a user's wallet without them
    # signing each transaction — there is no "auto-charge" here. The best
    # available substitute: pre-generate the exact invoice for this renewal
    # so paying it is one tap instead of a manual checkout.
    user = wallet.user
    amount_usd = usd_for_coins(price)
    pay_url = None
    try:
        invoice = await create_invoice(
            amount_usd=amount_usd,
            description=f"StratMaster CS2 — premium ({plan_months}mo) auto-renew",
            payload=str(user.id),
        )
        pay_url = invoice_pay_url(invoice)
        if pay_url:
            db.add(CryptoInvoiceModel(
                invoice_id=invoice["invoice_id"],
                user_id=user.id,
                coins=price,
                plan="premium",
                months=plan_months,
                amount_usd=f"{amount_usd:.2f}",
                status="active",
            ))
    except CryptoPayError:
        logger.exception("Failed to create renewal invoice for user_id=%s", user.id)

    wallet.reminder_sent_for_expiry = wallet.subscription_expires_at
    await db.commit()

    if pay_url:
        await _notify(
            bot, user.telegram_id,
            "⏳ Your StratMaster Premium expires in less than 24 hours.\n\n"
            f"Auto-renew is set to Crypto — tap below to pay ${amount_usd:.2f} and renew instantly.",
            webapp_url, pay_url=pay_url,
        )
    else:
        await _notify(
            bot, user.telegram_id,
            "⏳ Your StratMaster Premium expires in less than 24 hours. "
            "We couldn't prepare a renewal invoice — renew manually to keep uninterrupted access.",
            webapp_url,
        )


async def _process_wallet(db, wallet: WalletModel, bot, webapp_url: str | None) -> None:
    user = wallet.user
    plan_months = wallet.last_plan_months or 1

    if wallet.auto_renew:
        price = apply_discount(price_for("premium", plan_months), wallet)
        if wallet.auto_renew_method == "crypto":
            await _auto_renew_with_crypto(db, wallet, bot, webapp_url, plan_months, price)
        else:
            await _auto_renew_with_mastercoins(db, wallet, bot, webapp_url, plan_months, price)
        return

    wallet.reminder_sent_for_expiry = wallet.subscription_expires_at
    await db.commit()
    await _notify(
        bot, user.telegram_id,
        "⏳ Your StratMaster Premium expires in less than 24 hours. "
        "Renew now to keep uninterrupted access to every map and lineup.",
        webapp_url,
    )


async def send_expiry_reminders(db, bot, webapp_url: str | None) -> None:
    """Finds wallets whose premium expires within 24h and haven't been
    notified for this expiry yet — auto-renews them if opted in and able to
    pay, otherwise sends a Telegram reminder they can act on manually.

    Takes `db` as a parameter (rather than opening its own session) so it
    can run against a test session directly — the caller (the bot's
    reminder loop) owns the session lifecycle."""
    wallets = await _find_wallets_needing_reminder(db)
    for wallet in wallets:
        await _process_wallet(db, wallet, bot, webapp_url)
