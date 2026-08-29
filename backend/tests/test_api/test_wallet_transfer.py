from backend.tests.factories import make_user


async def test_transfer_moves_balance_between_wallets(client, db_session, auth_as):
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session, balance=0)
    auth_as(sender)

    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "amount": 30,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["new_balance"] == 70
    assert body["amount"] == 30

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 70


async def test_transfer_is_case_and_whitespace_insensitive_on_wallet_id(client, db_session, auth_as):
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session, balance=0)
    auth_as(sender)

    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": f"  {receiver.wallet.wallet_id.lower()}  ", "amount": 10,
    })
    assert resp.status_code == 200


async def test_transfer_to_nonexistent_wallet_leaves_sender_balance_untouched(client, db_session, auth_as):
    """ТЗ 3.2 acceptance scenario: atomic P2P transfer — if the receiver
    doesn't exist, the sender's coins must not disappear."""
    sender = await make_user(db_session, balance=100)
    auth_as(sender)

    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": "DOESNOTEXIST0001", "amount": 50,
    })
    assert resp.status_code == 404

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 100


async def test_transfer_rejects_self_transfer(client, db_session, auth_as):
    user = await make_user(db_session, balance=100)
    auth_as(user)

    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": user.wallet.wallet_id, "amount": 10,
    })
    assert resp.status_code == 400

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 100


async def test_transfer_fails_on_insufficient_balance(client, db_session, auth_as):
    sender = await make_user(db_session, balance=5)
    receiver = await make_user(db_session, balance=0)
    auth_as(sender)

    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "amount": 10,
    })
    assert resp.status_code == 400

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 5


async def test_transfer_rejects_non_positive_amount(client, db_session, auth_as):
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session, balance=0)
    auth_as(sender)

    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "amount": 0,
    })
    assert resp.status_code == 422  # pydantic gt=0 validation


async def test_gift_subscription_extends_receiver_not_sender(client, db_session, auth_as):
    sender = await make_user(db_session, balance=200)
    receiver = await make_user(db_session, balance=0)
    auth_as(sender)

    resp = await client.post("/api/wallet/gift-subscription", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "plan": "premium", "months": 1,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins_spent"] == 99
    assert body["new_balance"] == 101

    me = await client.get("/api/me")
    assert me.json()["wallet"]["subscription_expires_at"] is None  # sender's own subscription untouched


async def test_gift_subscription_fails_if_receiver_already_lifetime(client, db_session, auth_as):
    sender = await make_user(db_session, balance=10000)
    receiver = await make_user(db_session, balance=10000)

    auth_as(receiver)
    lifetime_purchase = await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})
    assert lifetime_purchase.status_code == 200

    auth_as(sender)
    resp = await client.post("/api/wallet/gift-subscription", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "plan": "premium", "months": 1,
    })
    assert resp.status_code == 400


async def test_gift_subscription_fails_on_insufficient_sender_balance(client, db_session, auth_as):
    sender = await make_user(db_session, balance=10)
    receiver = await make_user(db_session, balance=0)
    auth_as(sender)

    resp = await client.post("/api/wallet/gift-subscription", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "plan": "premium", "months": 1,
    })
    assert resp.status_code == 400

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 10


# ─────────────────────────────────────────────
#  Trade blocking (personal + admin global)
# ─────────────────────────────────────────────

async def test_user_can_block_and_unblock_another_by_wallet_id(client, db_session, auth_as):
    blocker = await make_user(db_session)
    spammer = await make_user(db_session, balance=100)
    auth_as(blocker)

    block = await client.post("/api/wallet/block", json={"wallet_id": spammer.wallet.wallet_id})
    assert block.status_code == 204

    listed = await client.get("/api/wallet/blocked")
    assert listed.json() == [{"wallet_id": spammer.wallet.wallet_id, "username": spammer.username}]

    unblock = await client.delete(f"/api/wallet/block/{spammer.wallet.wallet_id}")
    assert unblock.status_code == 204
    assert (await client.get("/api/wallet/blocked")).json() == []


async def test_blocked_sender_cannot_transfer_to_blocker(client, db_session, auth_as):
    blocker = await make_user(db_session)
    spammer = await make_user(db_session, balance=100)

    auth_as(blocker)
    await client.post("/api/wallet/block", json={"wallet_id": spammer.wallet.wallet_id})

    auth_as(spammer)
    resp = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": blocker.wallet.wallet_id, "amount": 10,
    })
    assert resp.status_code == 403

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 100  # untouched


async def test_admin_can_globally_trade_ban_a_user(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    banned = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)

    auth_as(admin)
    resp = await client.patch(f"/api/admin/users/{banned.id}/trade-ban", json={"is_trade_banned": True})
    assert resp.status_code == 200
    assert resp.json()["is_trade_banned"] is True

    auth_as(banned)
    transfer = await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "amount": 10,
    })
    assert transfer.status_code == 403


# ─────────────────────────────────────────────
#  Full account ban
# ─────────────────────────────────────────────

async def test_admin_can_ban_and_unban_a_user(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session)

    auth_as(admin)
    ban = await client.patch(f"/api/admin/users/{target.id}/ban", json={"is_banned": True})
    assert ban.status_code == 200
    assert ban.json()["is_banned"] is True

    auth_as(target)
    resp = await client.get("/api/me")
    assert resp.status_code == 403

    auth_as(admin)
    unban = await client.patch(f"/api/admin/users/{target.id}/ban", json={"is_banned": False})
    assert unban.status_code == 200

    auth_as(target)
    resp2 = await client.get("/api/me")
    assert resp2.status_code == 200


async def test_admin_cannot_ban_own_account(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    resp = await client.patch(f"/api/admin/users/{admin.id}/ban", json={"is_banned": True})
    assert resp.status_code == 400


# ─────────────────────────────────────────────
#  Admin per-player overrides: nickname, avatar, absolute premium set
# ─────────────────────────────────────────────

async def test_admin_can_set_and_clear_a_users_nickname(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/nickname", json={"nickname": "Top Fragger"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Top Fragger"

    cleared = await client.patch(f"/api/admin/users/{target.id}/nickname", json={"nickname": None})
    assert cleared.json()["display_name"] is None


async def test_admin_can_clear_a_users_avatar(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session, subscribed=True)
    auth_as(target)
    await client.patch("/api/me/avatar", json={"avatar_url": "/uploads/x.png"})

    auth_as(admin)
    resp = await client.delete(f"/api/admin/users/{target.id}/avatar")
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] is None


async def test_admin_can_set_a_users_avatar_directly(client, db_session, auth_as):
    """Not just clearing — an admin can also set (e.g. after uploading a
    replacement image) any player's avatar, even a non-premium one's."""
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session)  # no subscription
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/avatar", json={"avatar_url": "/uploads/new.png"})
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] == "/uploads/new.png"


async def test_admin_set_premium_forever_grants_lifetime(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/premium", json={"unit": "forever"})
    assert resp.status_code == 200
    assert resp.json()["wallet"]["is_lifetime"] is True


async def test_admin_set_premium_overwrites_existing_time_left(client, db_session, auth_as):
    """A user with a month left set to 1 minute ends up with ~1 minute, not
    31 days — /premium is an absolute set, unlike /subscription which extends."""
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session, subscribed=True)  # already has time left
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/premium", json={"unit": "minute", "amount": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["wallet"]["is_lifetime"] is False
    from datetime import datetime, timezone
    expiry = datetime.fromisoformat(body["wallet"]["subscription_expires_at"].replace("Z", "+00:00"))
    remaining_seconds = (expiry - datetime.now(timezone.utc)).total_seconds()
    assert 0 < remaining_seconds < 120  # ~1 minute, nowhere near a month


async def test_admin_set_premium_requires_amount_unless_forever(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/premium", json={"unit": "hour"})
    assert resp.status_code == 422


async def test_admin_can_grant_coins_to_a_player(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session, balance=50)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/coins", json={"amount": 250})
    assert resp.status_code == 200
    assert resp.json()["wallet"]["balance_coins"] == 300

    tx = await client.get("/api/admin/transactions", params={"transaction_type": "admin_grant"})
    txs = tx.json()["transactions"]
    assert any(t["amount"] == 250 and t["receiver_wallet_id"] == target.wallet.wallet_id for t in txs)


async def test_admin_grant_coins_rejects_non_positive_amount(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{target.id}/coins", json={"amount": 0})
    assert resp.status_code == 422
