from backend.tests.factories import make_map, make_user


def _payload(map_id, **overrides):
    base = {
        "map_id": map_id, "title": "Tactics Test", "side": "T_side", "plant": "A", "speed": "fast",
        "difficulty_stars": 3, "success_rate": 80, "is_free": True,
        "buy_tag_ids": [], "images": [], "grenades": [], "player_paths": [],
    }
    base.update(overrides)
    return base


async def test_create_strategy_with_grenade_trajectory(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = _payload(map_.id, grenades=[{
        "grenade_type": "Smoke", "target": "Window", "timing": "0:08", "video_url": None, "order": 0,
        "from_x": 20.0, "from_y": 80.0, "to_x": 55.0, "to_y": 30.0,
    }])
    resp = await client.post("/api/admin/strategies", json=payload)
    assert resp.status_code == 201
    grenade = resp.json()["grenades"][0]
    assert grenade["from_x"] == 20.0 and grenade["to_y"] == 30.0


async def test_create_strategy_with_player_path(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = _payload(map_.id, player_paths=[{
        "label": "Entry",
        "color": "#ff9a00",
        "waypoints": [{"x": 10, "y": 90, "t": 0}, {"x": 40, "y": 60, "t": 5}, {"x": 60, "y": 30, "t": 12}],
        "order": 0,
    }])
    resp = await client.post("/api/admin/strategies", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["player_paths"]) == 1
    assert body["player_paths"][0]["label"] == "Entry"
    assert len(body["player_paths"][0]["waypoints"]) == 3


async def test_player_path_requires_at_least_two_waypoints(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = _payload(map_.id, player_paths=[{
        "label": "Entry", "color": "#ff9a00", "waypoints": [{"x": 10, "y": 90, "t": 0}], "order": 0,
    }])
    resp = await client.post("/api/admin/strategies", json=payload)
    assert resp.status_code == 422


async def test_waypoint_coordinates_must_be_within_percent_bounds(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = _payload(map_.id, player_paths=[{
        "label": "Entry", "color": "#ff9a00",
        "waypoints": [{"x": 10, "y": 90, "t": 0}, {"x": 140, "y": 60, "t": 5}],
        "order": 0,
    }])
    resp = await client.post("/api/admin/strategies", json=payload)
    assert resp.status_code == 422


async def test_strategy_detail_includes_player_paths(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    create_resp = await client.post("/api/admin/strategies", json=_payload(map_.id, player_paths=[{
        "label": "AWP", "color": "#7fa8ff",
        "waypoints": [{"x": 5, "y": 5, "t": 0}, {"x": 50, "y": 50, "t": 10}],
        "order": 0,
    }]))
    strategy_id = create_resp.json()["id"]

    detail = await client.get(f"/api/strategies/{strategy_id}")
    assert detail.status_code == 200
    assert detail.json()["player_paths"][0]["label"] == "AWP"


async def test_updating_strategy_replaces_player_paths(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    create_resp = await client.post("/api/admin/strategies", json=_payload(map_.id, player_paths=[{
        "label": "Entry", "color": "#ff9a00",
        "waypoints": [{"x": 10, "y": 90, "t": 0}, {"x": 40, "y": 60, "t": 5}],
        "order": 0,
    }]))
    strategy_id = create_resp.json()["id"]

    update_resp = await client.patch(f"/api/admin/strategies/{strategy_id}", json=_payload(map_.id, player_paths=[]))
    assert update_resp.status_code == 200
    assert update_resp.json()["player_paths"] == []
