from backend.tests.factories import make_map, make_strategy, make_user


async def test_add_and_list_favorite_strategy(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, title="A Split via Connector")
    auth_as(user)

    add_resp = await client.post(f"/api/favorites/strategies/{strategy.id}")
    assert add_resp.status_code == 201
    assert add_resp.json() == {"strategy_id": str(strategy.id), "favorited": True}

    list_resp = await client.get("/api/favorites/strategies")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert len(body) == 1
    assert body[0]["id"] == str(strategy.id)
    assert body[0]["title"] == "A Split via Connector"


async def test_adding_the_same_favorite_strategy_twice_is_idempotent(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id)
    auth_as(user)

    await client.post(f"/api/favorites/strategies/{strategy.id}")
    second = await client.post(f"/api/favorites/strategies/{strategy.id}")
    assert second.status_code == 201

    body = (await client.get("/api/favorites/strategies")).json()
    assert len(body) == 1


async def test_remove_favorite_strategy(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id)
    auth_as(user)

    await client.post(f"/api/favorites/strategies/{strategy.id}")
    remove_resp = await client.delete(f"/api/favorites/strategies/{strategy.id}")
    assert remove_resp.status_code == 200
    assert remove_resp.json() == {"strategy_id": str(strategy.id), "favorited": False}

    body = (await client.get("/api/favorites/strategies")).json()
    assert body == []


async def test_removing_a_non_favorited_strategy_is_a_no_op(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id)
    auth_as(user)

    resp = await client.delete(f"/api/favorites/strategies/{strategy.id}")
    assert resp.status_code == 200
    assert resp.json()["favorited"] is False


async def test_favoriting_unknown_strategy_returns_404(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.post("/api/favorites/strategies/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_favorite_strategies_are_scoped_per_user(client, db_session, auth_as):
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id)

    auth_as(user_a)
    await client.post(f"/api/favorites/strategies/{strategy.id}")

    auth_as(user_b)
    body = (await client.get("/api/favorites/strategies")).json()
    assert body == []


async def test_deleting_strategy_cascades_to_favorites(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id)

    auth_as(user)
    await client.post(f"/api/favorites/strategies/{strategy.id}")

    auth_as(admin)
    delete_resp = await client.delete(f"/api/admin/strategies/{strategy.id}")
    assert delete_resp.status_code == 204

    auth_as(user)
    body = (await client.get("/api/favorites/strategies")).json()
    assert body == []
