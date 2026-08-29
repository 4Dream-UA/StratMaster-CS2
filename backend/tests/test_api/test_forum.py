from backend.tests.factories import make_user


async def test_categories_require_premium(client, db_session, auth_as):
    user = await make_user(db_session)  # no subscription
    auth_as(user)
    resp = await client.get("/api/forum/categories")
    assert resp.status_code == 403


async def test_categories_require_auth(client, db_session):
    resp = await client.get("/api/forum/categories")
    assert resp.status_code == 401


async def test_list_categories(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    resp = await client.get("/api/forum/categories")
    assert resp.status_code == 200
    keys = {c["key"] for c in resp.json()}
    assert keys == {"lounge", "support"}


async def test_lounge_create_thread_and_reply(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)

    auth_as(owner)
    create = await client.post("/api/forum/categories/lounge/threads", json={"title": "Best AWP spots?", "body": "Discuss."})
    assert create.status_code == 201
    thread_id = create.json()["id"]
    assert len(create.json()["posts"]) == 1

    # Any premium user can view and reply — lounge is open.
    auth_as(other)
    get_resp = await client.get(f"/api/forum/threads/{thread_id}")
    assert get_resp.status_code == 200

    reply = await client.post(f"/api/forum/threads/{thread_id}/posts", json={"body": "Mid window on Mirage."})
    assert reply.status_code == 201
    assert len(reply.json()["posts"]) == 2

    listed = await client.get("/api/forum/categories/lounge/threads")
    assert listed.json()["total"] == 1
    assert listed.json()["threads"][0]["post_count"] == 2


async def test_lounge_pagination(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    for i in range(6):
        resp = await client.post("/api/forum/categories/lounge/threads", json={"title": f"Thread {i}", "body": "..."})
        assert resp.status_code == 201

    listed = await client.get("/api/forum/categories/lounge/threads")
    body = listed.json()
    assert body["total"] == 6
    assert len(body["threads"]) == 5


async def test_cannot_create_thread_in_support(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    resp = await client.post("/api/forum/categories/support/threads", json={"title": "x", "body": "y"})
    assert resp.status_code == 400


async def test_support_ticket_auto_created_and_reused(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)

    first = await client.get("/api/forum/categories/support/threads")
    assert first.status_code == 200
    assert first.json()["total"] == 1
    ticket_id = first.json()["threads"][0]["id"]

    second = await client.get("/api/forum/categories/support/threads")
    assert second.json()["threads"][0]["id"] == ticket_id  # same ticket, not recreated


async def test_support_ticket_is_private_to_owner(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    stranger = await make_user(db_session, subscribed=True)

    auth_as(owner)
    ticket = (await client.get("/api/forum/categories/support/threads")).json()["threads"][0]

    auth_as(stranger)
    resp = await client.get(f"/api/forum/threads/{ticket['id']}")
    assert resp.status_code == 404

    reply = await client.post(f"/api/forum/threads/{ticket['id']}/posts", json={"body": "snooping"})
    assert reply.status_code == 404


async def test_admin_sees_all_support_tickets_and_can_reply(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    user1 = await make_user(db_session, subscribed=True)
    user2 = await make_user(db_session, subscribed=True)

    auth_as(user1)
    ticket1 = (await client.get("/api/forum/categories/support/threads")).json()["threads"][0]
    auth_as(user2)
    ticket2 = (await client.get("/api/forum/categories/support/threads")).json()["threads"][0]

    auth_as(admin)
    listed = await client.get("/api/forum/categories/support/threads")
    assert listed.json()["total"] == 2
    ids = {t["id"] for t in listed.json()["threads"]}
    assert ids == {ticket1["id"], ticket2["id"]}

    reply = await client.post(f"/api/forum/threads/{ticket1['id']}/posts", json={"body": "How can we help?"})
    assert reply.status_code == 201

    # The owner sees the admin's reply in their own ticket.
    auth_as(user1)
    detail = await client.get(f"/api/forum/threads/{ticket1['id']}")
    assert any(p["body"] == "How can we help?" for p in detail.json()["posts"])
