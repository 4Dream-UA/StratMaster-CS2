from backend.tests.factories import make_map, make_strategy, make_user


async def test_public_maps_are_paginated_with_default_page_size(client, db_session):
    for i in range(7):
        await make_map(db_session, name=f"Map {i}")

    first_page = await client.get("/api/maps")
    assert first_page.status_code == 200
    body = first_page.json()
    assert body["total"] == 7
    assert len(body["maps"]) == 5  # default limit

    second_page = await client.get("/api/maps", params={"limit": 5, "offset": 5})
    assert len(second_page.json()["maps"]) == 2


async def test_public_maps_search_filters_by_name(client, db_session):
    await make_map(db_session, name="Dust2")
    await make_map(db_session, name="Mirage")

    resp = await client.get("/api/maps", params={"search": "dust"})
    body = resp.json()
    assert body["total"] == 1
    assert body["maps"][0]["name"] == "Dust2"


async def test_public_strategies_are_paginated_with_default_page_size(client, db_session):
    map_ = await make_map(db_session)
    for i in range(6):
        await make_strategy(db_session, map_id=map_.id, is_free=True, title=f"Strat {i}")

    resp = await client.get("/api/strategies")
    body = resp.json()
    assert body["total"] == 6
    assert len(body["strategies"]) == 5

    resp2 = await client.get("/api/strategies", params={"limit": 5, "offset": 5})
    assert len(resp2.json()["strategies"]) == 1


async def test_admin_maps_are_paginated_and_searchable(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    for i in range(6):
        await make_map(db_session, name=f"AdminMap {i}")

    resp = await client.get("/api/admin/maps")
    body = resp.json()
    assert body["total"] == 6
    assert len(body["maps"]) == 5

    searched = await client.get("/api/admin/maps", params={"search": "AdminMap 3"})
    assert searched.json()["total"] == 1


async def test_admin_strategies_are_paginated(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    map_ = await make_map(db_session)
    for i in range(6):
        await make_strategy(db_session, map_id=map_.id, title=f"Admin Strat {i}")

    resp = await client.get("/api/admin/strategies")
    body = resp.json()
    assert body["total"] == 6
    assert len(body["strategies"]) == 5

    resp2 = await client.get("/api/admin/strategies", params={"limit": 5, "offset": 5})
    assert len(resp2.json()["strategies"]) == 1


async def test_admin_promo_codes_are_paginated_and_searchable(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    for _ in range(6):
        resp = await client.post("/api/admin/promo-codes", json={"code": None, "coin_reward": 10, "activations_limit": 5})
        assert resp.status_code == 201

    listed = await client.get("/api/admin/promo-codes")
    body = listed.json()
    assert body["total"] == 6
    assert len(body["promo_codes"]) == 5

    one_code = body["promo_codes"][0]["code"]
    searched = await client.get("/api/admin/promo-codes", params={"search": one_code})
    assert searched.json()["total"] == 1
