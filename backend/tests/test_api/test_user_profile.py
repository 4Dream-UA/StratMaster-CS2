from backend.tests.factories import make_user


async def test_update_profile_info_stores_only_filled_fields(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.patch("/api/me/profile-info", json={"steam": "steamcommunity.com/id/x", "location": "  Kyiv  "})
    assert resp.status_code == 200
    body = resp.json()["profile_info"]
    assert body["steam"] == "steamcommunity.com/id/x"
    assert body["location"] == "Kyiv"
    assert body["discord"] is None


async def test_blanking_out_all_fields_clears_profile_info(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    await client.patch("/api/me/profile-info", json={"steam": "x"})

    resp = await client.patch("/api/me/profile-info", json={"steam": "  "})
    assert resp.json()["profile_info"] is None


async def test_public_profile_hides_username_when_hidden_for_non_admin_viewer(client, db_session, auth_as):
    target = await make_user(db_session)
    viewer = await make_user(db_session)
    admin = await make_user(db_session, is_admin=True)

    auth_as(target)
    await client.patch("/api/me/forum-privacy", json={"hide_username_on_forum": True})
    await client.patch("/api/me/profile-info", json={"twitch": "twitch.tv/x"})

    auth_as(viewer)
    resp = await client.get(f"/api/users/{target.id}/public-profile")
    assert resp.status_code == 200
    assert resp.json()["username"] is None
    assert resp.json()["profile_info"]["twitch"] == "twitch.tv/x"

    auth_as(admin)
    resp = await client.get(f"/api/users/{target.id}/public-profile")
    assert resp.json()["username"] == target.username

    auth_as(target)
    resp = await client.get(f"/api/users/{target.id}/public-profile")
    assert resp.json()["username"] == target.username


async def test_public_profile_404s_for_unknown_user(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    resp = await client.get("/api/users/00000000-0000-0000-0000-000000000000/public-profile")
    assert resp.status_code == 404


async def test_user_search_matches_by_username_prefix_excludes_self(client, db_session, auth_as):
    user = await make_user(db_session, telegram_id=111)
    match = await make_user(db_session, telegram_id=222)
    match.username = "zzz_special_name"
    await db_session.commit()
    auth_as(user)

    resp = await client.get("/api/users/search", params={"q": "zzz_special"})
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert str(match.id) in ids
    assert str(user.id) not in ids


async def test_user_search_requires_a_query(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    resp = await client.get("/api/users/search")
    assert resp.status_code == 422
