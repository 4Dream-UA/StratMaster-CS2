from backend.tests.factories import make_user


async def test_purchase_premium_month_deducts_balance_and_extends_subscription(client, db_session, auth_as):
    user = await make_user(db_session, balance=200)
    auth_as(user)

    resp = await client.post("/api/subscription/purchase", json={"plan": "premium", "months": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins_spent"] == 99
    assert body["new_balance"] == 101


async def test_purchase_applies_active_referral_discount(client, db_session, auth_as):
    user = await make_user(db_session, balance=200, ref_discount=True)
    auth_as(user)

    resp = await client.post("/api/subscription/purchase", json={"plan": "premium", "months": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins_spent"] == 74  # 99 * 0.75 rounded
    assert body["new_balance"] == 126


async def test_purchase_fails_on_insufficient_balance_without_mutating_wallet(client, db_session, auth_as):
    user = await make_user(db_session, balance=10)
    auth_as(user)

    resp = await client.post("/api/subscription/purchase", json={"plan": "premium", "months": 1})
    assert resp.status_code == 400

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 10


async def test_purchase_premium_requires_months(client, db_session, auth_as):
    user = await make_user(db_session, balance=200)
    auth_as(user)

    resp = await client.post("/api/subscription/purchase", json={"plan": "premium", "months": None})
    assert resp.status_code == 400


async def test_purchase_lifetime(client, db_session, auth_as):
    user = await make_user(db_session, balance=5000)
    auth_as(user)

    resp = await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins_spent"] == 4999
    assert body["new_balance"] == 1

    me = await client.get("/api/me")
    assert me.json()["wallet"]["is_lifetime"] is True


async def test_cannot_buy_lifetime_twice(client, db_session, auth_as):
    user = await make_user(db_session, balance=10000)
    auth_as(user)

    first = await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})
    assert first.status_code == 200

    second = await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})
    assert second.status_code == 400

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 10000 - 4999  # second attempt didn't charge anything


async def test_cannot_buy_premium_while_lifetime_is_active(client, db_session, auth_as):
    user = await make_user(db_session, balance=10000)
    auth_as(user)

    await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})

    resp = await client.post("/api/subscription/purchase", json={"plan": "premium", "months": 1})
    assert resp.status_code == 400


async def test_purchase_records_last_plan_months_for_renewal(client, db_session, auth_as):
    user = await make_user(db_session, balance=300)
    auth_as(user)

    resp = await client.post("/api/subscription/purchase", json={"plan": "premium", "months": 3})
    assert resp.status_code == 200

    me = await client.get("/api/me")
    assert me.json()["wallet"]["last_plan_months"] == 3


async def test_toggle_auto_renew(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.patch("/api/subscription/auto-renew", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["auto_renew"] is True

    me = await client.get("/api/me")
    assert me.json()["wallet"]["auto_renew"] is True

    resp = await client.patch("/api/subscription/auto-renew", json={"enabled": False})
    assert resp.json()["auto_renew"] is False
