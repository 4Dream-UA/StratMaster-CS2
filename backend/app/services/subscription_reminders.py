import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import TransactionModel, WalletModel
from backend.app.services.subscription import apply_discount, extend_subscription, price_for

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


async def _notify(bot, telegram_id: int, text: str, webapp_url: str | None = None) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    markup = None
    if webapp_url:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Renew in StratMaster", web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/pricing")),
        ]])
    try:
        await bot.send_message(telegram_id, text, reply_markup=markup)
    except Exception:
        logger.exception("Failed to send renewal reminder to telegram_id=%s", telegram_id)


async def _process_wallet(db, wallet: WalletModel, bot, webapp_url: str | None) -> None:
    user = wallet.user
    plan_months = wallet.last_plan_months or 1

    if wallet.auto_renew:
        price = apply_discount(price_for("premium", plan_months), wallet)

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
        return

    wallet.reminder_sent_for_expiry = wallet.subscription_expires_at
    await db.commit()
    await _notify(
        bot, user.telegram_id,
        "⏳ Your StratMaster Premium expires in less than 24 hours. "
        "Renew now to keep uninterrupted access to every map and lineup.",
        webapp_url,
    )


async def send_expiry_reminders(bot, webapp_url: str | None) -> None:
    """Finds wallets whose premium expires within 24h and haven't been
    notified for this expiry yet — auto-renews them if opted in and able to
    pay, otherwise sends a Telegram reminder they can act on manually."""
    async with AsyncSessionLocal() as db:
        wallets = await _find_wallets_needing_reminder(db)
        for wallet in wallets:
            await _process_wallet(db, wallet, bot, webapp_url)
