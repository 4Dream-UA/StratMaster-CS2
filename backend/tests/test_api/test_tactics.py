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


# ── Grenade timing and bounced trajectories ──────────────────────────


async def test_grenade_keeps_its_throw_and_land_times_and_bounce_points(client, db_session, auth_as):
    """A throw that banks off a wall needs more than two points, and a
    lineup that hangs in the air needs its own flight length — one free-text
    label plus a fixed flight can express neither."""
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "Bounced smoke", "side": "T_side", "plant": "A",
        "speed": "fast", "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "player_paths": [],
        "grenades": [{
            "grenade_type": "Smoke", "target": "CT", "timing": "0:08", "order": 0,
            "throw_at": 8, "lands_at": 11.5,
            "trajectory": [{"x": 10, "y": 90}, {"x": 45, "y": 30}, {"x": 70, "y": 55}],
        }],
    }
    created = (await client.post("/api/admin/strategies", json=payload)).json()
    g = created["grenades"][0]

    assert g["throw_at"] == 8
    assert g["lands_at"] == 11.5
    assert [(p["x"], p["y"]) for p in g["trajectory"]] == [(10, 90), (45, 30), (70, 55)]

    fetched = (await client.get(f"/api/strategies/{created['id']}")).json()["grenades"][0]
    assert len(fetched["trajectory"]) == 3


async def test_a_grenade_without_the_new_fields_still_saves(client, db_session, auth_as):
    """Everything authored before 0037 has neither times nor a trajectory —
    the replay falls back to the label, so they must stay valid."""
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "Old style", "side": "T_side", "plant": "A",
        "speed": "fast", "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "player_paths": [],
        "grenades": [{
            "grenade_type": "Flashbang", "target": "Palace", "timing": "0:12", "order": 0,
            "from_x": 10, "from_y": 90, "to_x": 70, "to_y": 20,
        }],
    }
    g = (await client.post("/api/admin/strategies", json=payload)).json()["grenades"][0]
    assert g["throw_at"] is None
    assert g["lands_at"] is None
    assert g["trajectory"] is None
    assert (g["from_x"], g["to_y"]) == (10, 20)


async def test_a_one_point_trajectory_is_rejected(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "Broken", "side": "T_side", "plant": "A",
        "speed": "fast", "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "player_paths": [],
        "grenades": [{
            "grenade_type": "Smoke", "target": "CT", "timing": "0:08", "order": 0,
            "trajectory": [{"x": 10, "y": 90}],
        }],
    }
    assert (await client.post("/api/admin/strategies", json=payload)).status_code == 422


async def test_the_c4_can_carry_a_plant_time(client, db_session, auth_as):
    """A bomb with no time sits on the site from second zero, which is wrong
    for anything that isn't already a post-plant."""
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "Plant at 45", "side": "T_side", "plant": "A",
        "speed": "fast", "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "grenades": [], "player_paths": [],
        "annotations": {"drawings": [], "notes": [], "bomb": {"x": 50, "y": 50, "t": 45}},
    }
    created = (await client.post("/api/admin/strategies", json=payload)).json()
    assert created["annotations"]["bomb"]["t"] == 45

    # And a bomb without one stays valid — that's every strategy authored before.
    payload["title"] = "No plant time"
    payload["annotations"]["bomb"] = {"x": 50, "y": 50}
    other = (await client.post("/api/admin/strategies", json=payload)).json()
    assert other["annotations"]["bomb"]["t"] is None


async def test_a_grenade_can_carry_its_own_arrival_circle(client, db_session, auth_as):
    """The radius is per grenade and off by default — a hard-coded per-type
    one was tried and covered a fifth of the map."""
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "Circle", "side": "T_side", "plant": "A",
        "speed": "fast", "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "player_paths": [],
        "grenades": [
            {"grenade_type": "Smoke", "target": "CT", "timing": "0:08", "order": 0,
             "from_x": 10, "from_y": 90, "to_x": 60, "to_y": 30, "effect_radius": 6},
            {"grenade_type": "HE", "target": "Site", "timing": "0:10", "order": 1,
             "from_x": 10, "from_y": 90, "to_x": 55, "to_y": 35},
        ],
    }
    grenades = (await client.post("/api/admin/strategies", json=payload)).json()["grenades"]
    by_type = {g["grenade_type"]: g for g in grenades}
    assert by_type["Smoke"]["effect_radius"] == 6
    assert by_type["HE"]["effect_radius"] is None


async def test_an_absurd_arrival_circle_is_rejected(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    payload = {
        "map_id": map_.id, "title": "Too big", "side": "T_side", "plant": "A",
        "speed": "fast", "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "player_paths": [],
        "grenades": [{"grenade_type": "Smoke", "target": "CT", "timing": "0:08", "order": 0,
                      "effect_radius": 80}],
    }
    assert (await client.post("/api/admin/strategies", json=payload)).status_code == 422


async def test_admin_can_find_a_strategy_by_its_id(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    map_ = await make_map(db_session)
    auth_as(admin)

    base = {
        "map_id": map_.id, "side": "T_side", "plant": "A", "speed": "fast",
        "difficulty_stars": 3, "success_rate": 70, "is_free": True,
        "buy_tag_ids": [], "images": [], "grenades": [], "player_paths": [],
    }
    wanted = (await client.post("/api/admin/strategies", json={**base, "title": "Needle"})).json()
    await client.post("/api/admin/strategies", json={**base, "title": "Haystack"})

    by_id = (await client.get(f"/api/admin/strategies?search={wanted['id']}")).json()
    assert [s["title"] for s in by_id["strategies"]] == ["Needle"]

    # A fragment works too — an id copied out of a URL is often partial.
    by_fragment = (await client.get(f"/api/admin/strategies?search={wanted['id'][:8]}")).json()
    assert [s["title"] for s in by_fragment["strategies"]] == ["Needle"]

    by_title = (await client.get("/api/admin/strategies?search=Haystack")).json()
    assert [s["title"] for s in by_title["strategies"]] == ["Haystack"]


async def test_admin_can_find_a_user_by_telegram_id_or_uuid(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    target = await make_user(db_session, telegram_id=555000111)
    auth_as(admin)

    by_tg = (await client.get("/api/admin/users?search=555000111")).json()
    assert [u["id"] for u in by_tg["users"]] == [str(target.id)]

    by_uuid = (await client.get(f"/api/admin/users?search={target.id}")).json()
    assert [u["id"] for u in by_uuid["users"]] == [str(target.id)]

    by_name = (await client.get(f"/api/admin/users?search={target.username}")).json()
    assert [u["id"] for u in by_name["users"]] == [str(target.id)]
