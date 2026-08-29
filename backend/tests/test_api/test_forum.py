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


async def _open_ticket(client, title="Payment issue", body="My card was charged twice."):
    return await client.post("/api/forum/categories/support/threads", json={"title": title, "body": body})


async def test_user_can_open_a_support_ticket(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)

    create = await _open_ticket(client)
    assert create.status_code == 201

    listed = await client.get("/api/forum/categories/support/threads")
    assert listed.json()["total"] == 1
    assert listed.json()["threads"][0]["id"] == create.json()["id"]


async def test_user_can_open_multiple_support_tickets(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)

    first = await _open_ticket(client, title="Payment issue")
    second = await _open_ticket(client, title="Bug report")
    assert first.json()["id"] != second.json()["id"]

    listed = await client.get("/api/forum/categories/support/threads")
    assert listed.json()["total"] == 2


async def test_support_ticket_is_private_to_owner(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    stranger = await make_user(db_session, subscribed=True)

    auth_as(owner)
    ticket = (await _open_ticket(client)).json()

    auth_as(stranger)
    resp = await client.get(f"/api/forum/threads/{ticket['id']}")
    assert resp.status_code == 404

    reply = await client.post(f"/api/forum/threads/{ticket['id']}/posts", json={"body": "snooping"})
    assert reply.status_code == 404

    # A stranger's own ticket list never shows another user's tickets.
    listed = await client.get("/api/forum/categories/support/threads")
    assert listed.json()["total"] == 0


async def test_admin_sees_all_support_tickets_and_can_reply(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    user1 = await make_user(db_session, subscribed=True)
    user2 = await make_user(db_session, subscribed=True)

    auth_as(user1)
    ticket1 = (await _open_ticket(client)).json()
    auth_as(user2)
    ticket2 = (await _open_ticket(client)).json()

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


async def test_pinned_threads_sort_first(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(user)

    older = await client.post("/api/forum/categories/lounge/threads", json={"title": "Older", "body": "..."})
    newer = await client.post("/api/forum/categories/lounge/threads", json={"title": "Newer", "body": "..."})

    auth_as(admin)
    pin = await client.patch(f"/api/forum/threads/{older.json()['id']}/pin", json={"is_pinned": True})
    assert pin.status_code == 200
    assert pin.json()["is_pinned"] is True

    listed = await client.get("/api/forum/categories/lounge/threads")
    ids = [t["id"] for t in listed.json()["threads"]]
    assert ids[0] == older.json()["id"]  # pinned wins even though it's older
    assert ids[1] == newer.json()["id"]


async def test_only_admin_can_pin_a_thread(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    auth_as(owner)
    thread = await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})

    resp = await client.patch(f"/api/forum/threads/{thread.json()['id']}/pin", json={"is_pinned": True})
    assert resp.status_code == 403


async def test_owner_can_edit_and_delete_own_thread(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    stranger = await make_user(db_session, subscribed=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "Old title", "body": "..."})).json()

    edit = await client.patch(f"/api/forum/threads/{thread['id']}", json={"title": "New title"})
    assert edit.status_code == 200
    assert edit.json()["title"] == "New title"

    auth_as(stranger)
    forbidden = await client.patch(f"/api/forum/threads/{thread['id']}", json={"title": "Hijacked"})
    assert forbidden.status_code == 403
    forbidden_delete = await client.delete(f"/api/forum/threads/{thread['id']}")
    assert forbidden_delete.status_code == 403

    auth_as(owner)
    delete = await client.delete(f"/api/forum/threads/{thread['id']}")
    assert delete.status_code == 204
    gone = await client.get(f"/api/forum/threads/{thread['id']}")
    assert gone.status_code == 404


async def test_admin_can_edit_and_delete_others_thread(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    auth_as(admin)
    edit = await client.patch(f"/api/forum/threads/{thread['id']}", json={"title": "Moderated title"})
    assert edit.status_code == 200

    delete = await client.delete(f"/api/forum/threads/{thread['id']}")
    assert delete.status_code == 204


async def test_author_can_edit_own_post_but_not_others(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Original"})).json()
    post_id = thread["posts"][0]["id"]

    edit = await client.patch(f"/api/forum/posts/{post_id}", json={"body": "Edited"})
    assert edit.status_code == 200
    assert edit.json()["posts"][0]["body"] == "Edited"

    auth_as(other)
    forbidden = await client.patch(f"/api/forum/posts/{post_id}", json={"body": "Hijacked"})
    assert forbidden.status_code == 403
