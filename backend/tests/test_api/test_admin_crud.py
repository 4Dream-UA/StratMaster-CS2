from backend.app.db.models import GrenadeModel, ImageModel
from backend.tests.factories import make_map, make_strategy, make_user
from sqlalchemy import select


async def test_non_admin_cannot_reach_admin_endpoints(client, db_session, auth_as):
    user = await make_user(db_session, is_admin=False)
    auth_as(user)

    resp = await client.get("/api/admin/maps")
    assert resp.status_code == 403


async def test_admin_can_create_and_toggle_map(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    create = await client.post("/api/admin/maps", json={"name": "Anubis", "cover_image_url": None, "is_active": True})
    assert create.status_code == 201
    map_id = create.json()["id"]

    toggle = await client.patch(f"/api/admin/maps/{map_id}", json={"is_active": False})
    assert toggle.status_code == 200
    assert toggle.json()["is_active"] is False


async def test_admin_create_strategy_with_grenades_and_images(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    map_ = await make_map(db_session)

    payload = {
        "map_id": map_.id, "title": "A Split", "side": "T_side", "plant": "A", "speed": "fast",
        "difficulty_stars": 3, "success_rate": 80, "is_free": False,
        "buy_tag_ids": [],
        "images": [{"image_url": "https://example.com/main.png", "order": 0}],
        "grenades": [{"grenade_type": "Smoke", "target": "Window", "timing": "0:08", "video_url": None, "order": 0}],
    }
    resp = await client.post("/api/admin/strategies", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["images"]) == 1
    assert len(body["grenades"]) == 1


async def test_deleting_strategy_cascades_to_grenades_and_images(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, with_children=True)
    strategy_id = strategy.id

    resp = await client.delete(f"/api/admin/strategies/{strategy_id}")
    assert resp.status_code == 204

    images = (await db_session.execute(select(ImageModel).where(ImageModel.strategy_id == strategy_id))).scalars().all()
    grenades = (await db_session.execute(select(GrenadeModel).where(GrenadeModel.strategy_id == strategy_id))).scalars().all()
    assert images == []
    assert grenades == []


async def test_admin_generates_promo_code(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.post("/api/admin/promo-codes", json={"code": None, "coin_reward": 50, "activations_limit": 10})
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["code"]) == 8
    assert body["coin_reward"] == 50


async def test_admin_cannot_revoke_own_admin_access(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{admin.id}/admin", json={"is_admin": False})
    assert resp.status_code == 400


async def test_admin_can_promote_another_user(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    other = await make_user(db_session, is_admin=False)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{other.id}/admin", json={"is_admin": True})
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


async def test_admin_lists_transactions_filtered_by_type_and_wallet(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session, balance=0)

    auth_as(sender)
    await client.post("/api/wallet/transfer", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "amount": 25,
    })

    auth_as(admin)
    all_tx = await client.get("/api/admin/transactions")
    assert all_tx.status_code == 200
    assert all_tx.json()["total"] >= 1

    p2p_only = await client.get("/api/admin/transactions", params={"transaction_type": "p2p_transfer"})
    assert all(t["transaction_type"] == "p2p_transfer" for t in p2p_only.json()["transactions"])

    by_wallet = await client.get("/api/admin/transactions", params={"wallet_id": sender.wallet.wallet_id})
    assert all(
        t["sender_wallet_id"] == sender.wallet.wallet_id or t["receiver_wallet_id"] == sender.wallet.wallet_id
        for t in by_wallet.json()["transactions"]
    )
