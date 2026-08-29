from backend.tests.factories import make_user


async def test_public_settings_default_to_no_logo(client, db_session):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["logo_url"] is None


async def test_non_admin_cannot_update_settings(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    resp = await client.patch("/api/admin/settings", json={"logo_url": "/uploads/x.png"})
    assert resp.status_code == 403


async def test_admin_updates_logo_and_public_endpoint_reflects_it(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.patch("/api/admin/settings", json={"logo_url": "/uploads/newlogo.png"})
    assert resp.status_code == 200
    assert resp.json()["logo_url"] == "/uploads/newlogo.png"

    public = await client.get("/api/settings")
    assert public.json()["logo_url"] == "/uploads/newlogo.png"
