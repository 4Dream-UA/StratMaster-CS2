from datetime import datetime, timedelta, timezone

import backend.app.services.subscription_reminders as reminders_module
from backend.tests.factories import make_user

WEBAPP_URL = "https://example.test/"


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, telegram_id, text, reply_markup=None):
        self.sent.append({"telegram_id": telegram_id, "text": text, "reply_markup": reply_markup})


async def _expiring_soon_user(db_session, **kwargs):
    user = await make_user(db_session, subscribed=True, **kwargs)
    user.wallet.subscription_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    user.wallet.last_plan_months = 1
    await db_session.commit()
    return user


async def test_plain_reminder_sent_when_auto_renew_is_off(db_session):
    user = await _expiring_soon_user(db_session, balance=0)
    bot = FakeBot()

    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)

    assert len(bot.sent) == 1
    assert bot.sent[0]["telegram_id"] == user.telegram_id
    assert "expires in less than 24 hours" in bot.sent[0]["text"]


async def test_mastercoins_auto_renew_charges_balance_and_extends(db_session):
    user = await _expiring_soon_user(db_session, balance=200)
    user.wallet.auto_renew = True
    user.wallet.auto_renew_method = "mastercoins"
    await db_session.commit()
    old_expiry = user.wallet.subscription_expires_at
    bot = FakeBot()

    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)

    await db_session.refresh(user.wallet)
    assert user.wallet.balance_coins == 200 - 99  # 1-month price
    assert user.wallet.subscription_expires_at > old_expiry
    assert "auto-renewed" in bot.sent[0]["text"]


async def test_mastercoins_auto_renew_falls_back_when_balance_too_low(db_session):
    user = await _expiring_soon_user(db_session, balance=10)
    user.wallet.auto_renew = True
    user.wallet.auto_renew_method = "mastercoins"
    await db_session.commit()
    bot = FakeBot()

    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)

    await db_session.refresh(user.wallet)
    assert user.wallet.balance_coins == 10  # untouched
    assert "balance is too low" in bot.sent[0]["text"]


async def test_crypto_auto_renew_attaches_a_pay_now_invoice_link(db_session, monkeypatch):
    async def fake_create_invoice(*, amount_usd, description, payload):
        return {"invoice_id": 999, "status": "active", "mini_app_invoice_url": "https://t.me/CryptoBot/app?startapp=invoice-999"}

    monkeypatch.setattr(reminders_module, "create_invoice", fake_create_invoice)

    user = await _expiring_soon_user(db_session, balance=0)
    user.wallet.auto_renew = True
    user.wallet.auto_renew_method = "crypto"
    await db_session.commit()
    bot = FakeBot()

    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)

    assert len(bot.sent) == 1
    markup = bot.sent[0]["reply_markup"]
    buttons = [b for row in markup.inline_keyboard for b in row]
    pay_button = next(b for b in buttons if "Pay & Renew" in b.text)
    assert pay_button.url == "https://t.me/CryptoBot/app?startapp=invoice-999"

    # Balance must stay untouched — crypto can't be auto-charged.
    await db_session.refresh(user.wallet)
    assert user.wallet.balance_coins == 0


async def test_crypto_auto_renew_falls_back_to_plain_reminder_on_cryptopay_error(db_session, monkeypatch):
    from backend.app.services.crypto import CryptoPayError

    async def failing_create_invoice(*, amount_usd, description, payload):
        raise CryptoPayError(400, "API_ERROR")

    monkeypatch.setattr(reminders_module, "create_invoice", failing_create_invoice)

    user = await _expiring_soon_user(db_session, balance=0)
    user.wallet.auto_renew = True
    user.wallet.auto_renew_method = "crypto"
    await db_session.commit()
    bot = FakeBot()

    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)

    assert len(bot.sent) == 1
    assert "couldn't prepare a renewal invoice" in bot.sent[0]["text"]


async def test_reminder_not_resent_for_the_same_expiry(db_session):
    user = await _expiring_soon_user(db_session, balance=0)
    bot = FakeBot()

    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)
    await reminders_module.send_expiry_reminders(db_session, bot, WEBAPP_URL)

    assert len(bot.sent) == 1
