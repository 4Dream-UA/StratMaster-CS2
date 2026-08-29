from backend.tests.factories import make_user


async def test_premium_user_can_set_and_clear_avatar(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)

    resp = await client.patch("/api/me/avatar", json={"avatar_url": "/uploads/avatar123.png"})
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] == "/uploads/avatar123.png"

    cleared = await client.patch("/api/me/avatar", json={"avatar_url": None})
    assert cleared.json()["avatar_url"] is None


async def test_non_premium_user_cannot_set_avatar(client, db_session, auth_as):
    user = await make_user(db_session)  # no subscription
    auth_as(user)

    resp = await client.patch("/api/me/avatar", json={"avatar_url": "/uploads/x.png"})
    assert resp.status_code == 403
