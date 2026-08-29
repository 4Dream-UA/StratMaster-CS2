from backend.app.db.models import GrenadeModel, ImageModel
from backend.tests.factories import make_case, make_map, make_strategy, make_user
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


async def test_strategy_annotations_round_trip(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    map_ = await make_map(db_session)

    annotations = {
        "drawings": [{"points": [{"x": 10, "y": 10}, {"x": 20, "y": 20}], "color": "#ff0000"}],
        "notes": [{"x": 50, "y": 50, "text": "Rotate here after 20s"}],
        "bomb": {"x": 75, "y": 75},
    }
    payload = {
        "map_id": map_.id, "title": "B Default", "side": "T_side", "plant": "B", "speed": "medium",
        "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "grenades": [],
        "annotations": annotations,
    }
    create = await client.post("/api/admin/strategies", json=payload)
    assert create.status_code == 201
    assert create.json()["annotations"] == annotations

    strategy_id = create.json()["id"]
    fetched = await client.get(f"/api/strategies/{strategy_id}")
    assert fetched.json()["annotations"] == annotations

    # Defaults to empty when omitted, never a validation error.
    payload2 = {**payload, "title": "No annotations"}
    del payload2["annotations"]
    create2 = await client.post("/api/admin/strategies", json=payload2)
    assert create2.status_code == 201
    assert create2.json()["annotations"] == {"drawings": [], "notes": [], "bomb": None}


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


async def test_admin_generates_premium_promo_code(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.post(
        "/api/admin/promo-codes",
        json={"code": "PREMDAYS", "reward_type": "premium", "premium_days": 14, "activations_limit": 10},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["reward_type"] == "premium"
    assert body["premium_days"] == 14
    assert body["coin_reward"] == 0


async def test_admin_generates_case_promo_code(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    case = await make_case(db_session, name="Giveaway Case")

    resp = await client.post(
        "/api/admin/promo-codes",
        json={"code": "CASEDROP", "reward_type": "case", "case_id": str(case.id), "case_quantity": 3, "activations_limit": 10},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["reward_type"] == "case"
    assert body["case_id"] == str(case.id)
    assert body["case_name"] == "Giveaway Case"
    assert body["case_quantity"] == 3


async def test_admin_promo_code_requires_matching_reward_fields(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.post(
        "/api/admin/promo-codes",
        json={"code": "BADPREM", "reward_type": "premium", "activations_limit": 10},
    )
    assert resp.status_code == 422


async def test_admin_promo_code_rejects_missing_case(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.post(
        "/api/admin/promo-codes",
        json={"code": "NOSUCHCASE", "reward_type": "case", "case_id": fake_id, "case_quantity": 1, "activations_limit": 10},
    )
    assert resp.status_code == 404


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


async def test_admin_grants_fixed_term_subscription(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    other = await make_user(db_session)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{other.id}/subscription", json={"months": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["wallet"]["is_lifetime"] is False
    assert body["wallet"]["subscription_expires_at"] is not None


async def test_admin_grants_lifetime_with_zero_months(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    other = await make_user(db_session)
    auth_as(admin)

    resp = await client.patch(f"/api/admin/users/{other.id}/subscription", json={"months": 0})
    assert resp.status_code == 200
    assert resp.json()["wallet"]["is_lifetime"] is True


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


async def test_stats_counts_active_subscriptions_only(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    await make_user(db_session, subscribed=True)  # active premium
    await make_user(db_session)  # never subscribed

    auth_as(admin)
    lifetime_user = await make_user(db_session, balance=10000)
    auth_as(lifetime_user)
    await client.post("/api/subscription/purchase", json={"plan": "lifetime", "months": None})

    auth_as(admin)
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 200
    assert resp.json()["active_subscriptions_count"] == 2  # the premium one + the lifetime one


async def test_creating_strategy_notifies_favorited_map_users(client, db_session, auth_as, monkeypatch):
    sent = []

    async def _fake_notify(db, map_id, map_name, title):
        sent.append((map_id, map_name, title))

    monkeypatch.setattr("backend.app.api.routers.admin.notify_favorited_map_users", _fake_notify)

    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session, name="Anubis")
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "B Default Execute", "side": "T_side", "plant": "B", "speed": "medium",
        "difficulty_stars": 4, "success_rate": 70, "is_free": False,
        "buy_tag_ids": [], "images": [], "grenades": [],
    }
    resp = await client.post("/api/admin/strategies", json=payload)
    assert resp.status_code == 201
    assert sent == [(map_.id, "Anubis", "B Default Execute")]
