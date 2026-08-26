from backend.tests.factories import make_map, make_user


async def test_add_and_list_favorite_map(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session, name="Mirage")
    auth_as(user)

    add_resp = await client.post(f"/api/favorites/{map_.id}")
    assert add_resp.status_code == 201
    assert add_resp.json() == {"map_id": map_.id, "favorited": True}

    list_resp = await client.get("/api/favorites")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert len(body) == 1
    assert body[0]["id"] == map_.id


async def test_adding_the_same_favorite_twice_is_idempotent(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    auth_as(user)

    await client.post(f"/api/favorites/{map_.id}")
    second = await client.post(f"/api/favorites/{map_.id}")
    assert second.status_code == 201

    body = (await client.get("/api/favorites")).json()
    assert len(body) == 1


async def test_remove_favorite_map(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    auth_as(user)

    await client.post(f"/api/favorites/{map_.id}")
    remove_resp = await client.delete(f"/api/favorites/{map_.id}")
    assert remove_resp.status_code == 200
    assert remove_resp.json() == {"map_id": map_.id, "favorited": False}

    body = (await client.get("/api/favorites")).json()
    assert body == []


async def test_removing_a_non_favorited_map_is_a_no_op(client, db_session, auth_as):
    user = await make_user(db_session)
    map_ = await make_map(db_session)
    auth_as(user)

    resp = await client.delete(f"/api/favorites/{map_.id}")
    assert resp.status_code == 200
    assert resp.json() == {"map_id": map_.id, "favorited": False}


async def test_favoriting_unknown_map_returns_404(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.post("/api/favorites/999999")
    assert resp.status_code == 404


async def test_favorites_are_scoped_per_user(client, db_session, auth_as):
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    map_ = await make_map(db_session)

    auth_as(user_a)
    await client.post(f"/api/favorites/{map_.id}")

    auth_as(user_b)
    body = (await client.get("/api/favorites")).json()
    assert body == []
