import hashlib
import hmac
import json

import backend.app.api.routers.payments as payments_module
from backend.app.core.config import settings
from backend.tests.factories import make_user


async def _fake_create_invoice(*, amount_usd, description, payload):
    """Stands in for the real CryptoPay API call — tests must never hit the
    live network (this project's CRYPTOPAY_TOKEN is a real, live token)."""
    return {
        "invoice_id": 42424242,
        "status": "active",
        "mini_app_invoice_url": "https://t.me/CryptoBot/app?startapp=invoice-42424242",
    }


def _sign(body: bytes) -> str:
    secret = hashlib.sha256(settings.cryptopay_token.encode()).digest()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


async def test_create_crypto_invoice_for_premium_plan(client, db_session, auth_as, monkeypatch):
    monkeypatch.setattr(payments_module, "create_invoice", _fake_create_invoice)
    user = await make_user(db_session, balance=0)
    auth_as(user)

    resp = await client.post("/api/payments/crypto/invoice", json={"plan": "premium", "months": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins"] == 99
    assert body["amount_usd"] == 0.99
    assert body["pay_url"].startswith("https://t.me/")


async def test_create_crypto_invoice_for_coin_topup(client, db_session, auth_as, monkeypatch):
    monkeypatch.setattr(payments_module, "create_invoice", _fake_create_invoice)
    user = await make_user(db_session, balance=0)
    auth_as(user)

    resp = await client.post("/api/payments/crypto/invoice", json={"coins": 500})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins"] == 500
    assert body["amount_usd"] == 5.0


async def test_create_crypto_invoice_rejects_below_minimum_coins(client, db_session, auth_as, monkeypatch):
    monkeypatch.setattr(payments_module, "create_invoice", _fake_create_invoice)
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.post("/api/payments/crypto/invoice", json={"coins": 5})
    assert resp.status_code == 400


async def test_create_crypto_invoice_rejects_both_plan_and_coins(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.post("/api/payments/crypto/invoice", json={"plan": "premium", "months": 1, "coins": 100})
    assert resp.status_code == 422


async def test_create_crypto_invoice_rejects_neither_plan_nor_coins(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.post("/api/payments/crypto/invoice", json={})
    assert resp.status_code == 422


async def test_create_crypto_invoice_rejects_lifetime_holder_buying_more(client, db_session, auth_as, monkeypatch):
    monkeypatch.setattr(payments_module, "create_invoice", _fake_create_invoice)
    user = await make_user(db_session, balance=10000)
    auth_as(user)
    await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})

    resp = await client.post("/api/payments/crypto/invoice", json={"plan": "premium", "months": 1})
    assert resp.status_code == 400


async def test_webhook_credits_wallet_on_valid_signature(client, db_session, auth_as, monkeypatch):
    monkeypatch.setattr(payments_module, "create_invoice", _fake_create_invoice)
    user = await make_user(db_session, balance=0)
    auth_as(user)

    create_resp = await client.post("/api/payments/crypto/invoice", json={"coins": 300})
    invoice_id = create_resp.json()["invoice_id"]

    body = json.dumps({
        "update_type": "invoice_paid",
        "payload": {"invoice_id": invoice_id, "status": "paid"},
    }).encode()

    webhook_resp = await client.post(
        "/api/webhooks/cryptopay",
        content=body,
        headers={"content-type": "application/json", "crypto-pay-api-signature": _sign(body)},
    )
    assert webhook_resp.status_code == 200

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 300


async def test_webhook_retry_does_not_double_credit(client, db_session, auth_as, monkeypatch):
    monkeypatch.setattr(payments_module, "create_invoice", _fake_create_invoice)
    user = await make_user(db_session, balance=0)
    auth_as(user)

    create_resp = await client.post("/api/payments/crypto/invoice", json={"coins": 150})
    invoice_id = create_resp.json()["invoice_id"]

    body = json.dumps({
        "update_type": "invoice_paid",
        "payload": {"invoice_id": invoice_id, "status": "paid"},
    }).encode()
    headers = {"content-type": "application/json", "crypto-pay-api-signature": _sign(body)}

    await client.post("/api/webhooks/cryptopay", content=body, headers=headers)
    await client.post("/api/webhooks/cryptopay", content=body, headers=headers)  # CryptoPay-style retry

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 150


async def test_webhook_rejects_bad_signature(client):
    resp = await client.post(
        "/api/webhooks/cryptopay",
        content=b'{"update_type":"invoice_paid","payload":{"invoice_id":1}}',
        headers={"content-type": "application/json", "crypto-pay-api-signature": "bogus"},
    )
    assert resp.status_code == 401


async def test_webhook_ignores_unknown_update_type(client):
    body = b'{"update_type":"invoice_expired","payload":{"invoice_id":1}}'
    resp = await client.post(
        "/api/webhooks/cryptopay",
        content=body,
        headers={"content-type": "application/json", "crypto-pay-api-signature": _sign(body)},
    )
    assert resp.status_code == 200
