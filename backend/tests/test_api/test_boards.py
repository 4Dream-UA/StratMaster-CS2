from backend.tests.factories import make_map, make_user


def _payload(map_id, title="My Board"):
    return {
        "map_id": map_id,
        "title": title,
        "paths": [
            {"label": "Entry", "color": "#ff9a00", "order": 0, "waypoints": [
                {"x": 10, "y": 10, "t": 0}, {"x": 50, "y": 50, "t": 3},
            ]},
        ],
        "grenades": [
            {"grenade_type": "Smoke", "target": "Window", "order": 0,
             "from_x": 5, "from_y": 5, "to_x": 20, "to_y": 20},
        ],
    }


async def test_board_annotations_round_trip(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    map_ = await make_map(db_session)
    auth_as(user)

    annotations = {
        "drawings": [{"points": [{"x": 5, "y": 5}, {"x": 40, "y": 40}], "color": "#00ff00"}],
        "notes": [{"x": 60, "y": 20, "text": "Fake here"}],
        "bomb": {"x": 30, "y": 80},
    }
    payload = {**_payload(map_.id), "annotations": annotations}
    create = await client.post("/api/boards", json=payload)
    assert create.status_code == 201
    assert create.json()["annotations"] == annotations

    board_id = create.json()["id"]
    fetched = await client.get(f"/api/boards/{board_id}")
    assert fetched.json()["annotations"] == annotations

    cleared = await client.patch(f"/api/boards/{board_id}", json=_payload(map_.id))
    assert cleared.json()["annotations"] == {"drawings": [], "notes": [], "bomb": None}


async def test_non_premium_user_cannot_create_board(client, db_session, auth_as):
    user = await make_user(db_session)  # no subscription
    map_ = await make_map(db_session)
    auth_as(user)

    resp = await client.post("/api/boards", json=_payload(map_.id))
    assert resp.status_code == 403


async def test_anonymous_cannot_reach_boards(client, db_session):
    resp = await client.get("/api/boards")
    assert resp.status_code == 401


async def test_premium_user_can_create_and_list_board(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    map_ = await make_map(db_session)
    auth_as(user)

    create = await client.post("/api/boards", json=_payload(map_.id))
    assert create.status_code == 201
    body = create.json()
    assert body["title"] == "My Board"
    assert len(body["paths"]) == 1
    assert len(body["grenades"]) == 1

    listed = await client.get("/api/boards")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["boards"][0]["id"] == body["id"]


async def test_board_is_scoped_to_owner(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    map_ = await make_map(db_session)

    auth_as(owner)
    create = await client.post("/api/boards", json=_payload(map_.id))
    board_id = create.json()["id"]

    auth_as(other)
    get_resp = await client.get(f"/api/boards/{board_id}")
    assert get_resp.status_code == 404

    list_resp = await client.get("/api/boards")
    assert list_resp.json()["total"] == 0


async def test_update_board_replaces_paths_and_grenades(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    map_ = await make_map(db_session)
    auth_as(user)

    create = await client.post("/api/boards", json=_payload(map_.id))
    board_id = create.json()["id"]

    updated_payload = _payload(map_.id, title="Renamed")
    updated_payload["paths"] = []
    updated_payload["grenades"] = []
    resp = await client.patch(f"/api/boards/{board_id}", json=updated_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Renamed"
    assert body["paths"] == []
    assert body["grenades"] == []


async def test_delete_board(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    map_ = await make_map(db_session)
    auth_as(user)

    create = await client.post("/api/boards", json=_payload(map_.id))
    board_id = create.json()["id"]

    resp = await client.delete(f"/api/boards/{board_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/boards/{board_id}")
    assert get_resp.status_code == 404


async def test_boards_are_paginated(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    map_ = await make_map(db_session)
    auth_as(user)

    for i in range(6):
        resp = await client.post("/api/boards", json=_payload(map_.id, title=f"Board {i}"))
        assert resp.status_code == 201

    listed = await client.get("/api/boards")
    body = listed.json()
    assert body["total"] == 6
    assert len(body["boards"]) == 5
