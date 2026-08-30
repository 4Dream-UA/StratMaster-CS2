from backend.tests.factories import make_user


async def test_reporting_an_error_requires_no_auth(client, db_session):
    resp = await client.post("/api/errors", json={"message": "boom", "stack": "at x.js:1", "url": "/forum"})
    assert resp.status_code == 204


async def test_reporting_an_error_while_authenticated_records_the_user(client, db_session, auth_as):
    user = await make_user(db_session, is_admin=True)
    auth_as(user)
    await client.post("/api/errors", json={"message": "boom while logged in"})

    logs = (await client.get("/api/admin/errors")).json()
    assert any(e["message"] == "boom while logged in" and e["username"] == user.username for e in logs)


async def test_error_log_requires_a_message(client, db_session):
    resp = await client.post("/api/errors", json={"stack": "no message here"})
    assert resp.status_code == 422


async def test_admin_can_list_recent_errors(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    await client.post("/api/errors", json={"message": "first error"})
    await client.post("/api/errors", json={"message": "second error"})

    auth_as(admin)
    logs = (await client.get("/api/admin/errors")).json()
    messages = [e["message"] for e in logs]
    assert "first error" in messages
    assert "second error" in messages
    assert all(e["source"] == "frontend" for e in logs)


async def test_non_admin_cannot_list_errors(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    resp = await client.get("/api/admin/errors")
    assert resp.status_code == 403
