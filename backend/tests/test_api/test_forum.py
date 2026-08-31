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


async def test_admin_can_close_and_reopen_a_ticket(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    owner = await make_user(db_session, subscribed=True)

    auth_as(owner)
    ticket = (await _open_ticket(client)).json()
    assert ticket["is_closed"] is False

    auth_as(admin)
    close = await client.patch(f"/api/forum/threads/{ticket['id']}/close", json={"is_closed": True})
    assert close.status_code == 200
    assert close.json()["is_closed"] is True

    auth_as(owner)
    forbidden = await client.post(f"/api/forum/threads/{ticket['id']}/posts", json={"body": "still there?"})
    assert forbidden.status_code == 400

    auth_as(admin)
    reopen = await client.patch(f"/api/forum/threads/{ticket['id']}/close", json={"is_closed": False})
    assert reopen.json()["is_closed"] is False

    auth_as(owner)
    now_allowed = await client.post(f"/api/forum/threads/{ticket['id']}/posts", json={"body": "back"})
    assert now_allowed.status_code == 201


async def test_owner_can_close_their_own_thread_but_not_reopen_it(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    close = await client.patch(f"/api/forum/threads/{thread['id']}/close", json={"is_closed": True})
    assert close.status_code == 200
    assert close.json()["is_closed"] is True

    # Closed the door on themselves — only an admin can undo it.
    reopen = await client.patch(f"/api/forum/threads/{thread['id']}/close", json={"is_closed": False})
    assert reopen.status_code == 403

    auth_as(admin)
    admin_reopen = await client.patch(f"/api/forum/threads/{thread['id']}/close", json={"is_closed": False})
    assert admin_reopen.status_code == 200
    assert admin_reopen.json()["is_closed"] is False


async def test_non_owner_cannot_close_someone_elses_thread(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    auth_as(other)
    resp = await client.patch(f"/api/forum/threads/{thread['id']}/close", json={"is_closed": True})
    assert resp.status_code == 403


async def test_creating_a_thread_auto_watches_the_author(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    assert thread["is_watching"] is True


async def test_toggle_watch(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    auth_as(other)
    watch = await client.post(f"/api/forum/threads/{thread['id']}/watch")
    assert watch.json() == {"is_watching": True}

    detail = await client.get(f"/api/forum/threads/{thread['id']}")
    assert detail.json()["is_watching"] is True

    unwatch = await client.post(f"/api/forum/threads/{thread['id']}/watch")
    assert unwatch.json() == {"is_watching": False}


async def test_reply_to_post_is_quoted_and_notifies_original_author(client, db_session, auth_as, monkeypatch):
    sent = []

    async def _fake_notify(telegram_id, text, web_app_url=None):
        sent.append((telegram_id, text, web_app_url))

    monkeypatch.setattr("backend.app.api.routers.forum.send_telegram_message", _fake_notify)

    author = await make_user(db_session, subscribed=True)
    replier = await make_user(db_session, subscribed=True)

    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Original message"})).json()
    original_post_id = thread["posts"][0]["id"]

    auth_as(replier)
    reply = await client.post(
        f"/api/forum/threads/{thread['id']}/posts",
        json={"body": "Replying to you", "reply_to_post_id": original_post_id},
    )
    assert reply.status_code == 201
    posts = reply.json()["posts"]
    assert posts[-1]["reply_to"]["id"] == original_post_id
    assert posts[-1]["reply_to"]["body_snippet"] == "Original message"

    assert len(sent) == 1
    assert sent[0][0] == author.telegram_id


async def test_reply_to_post_in_another_thread_is_rejected(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    thread1 = (await client.post("/api/forum/categories/lounge/threads", json={"title": "A", "body": "..."})).json()
    thread2 = (await client.post("/api/forum/categories/lounge/threads", json={"title": "B", "body": "..."})).json()

    resp = await client.post(
        f"/api/forum/threads/{thread2['id']}/posts",
        json={"body": "x", "reply_to_post_id": thread1["posts"][0]["id"]},
    )
    assert resp.status_code == 400


async def test_share_link_lets_anyone_view_read_only(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    stranger = await make_user(db_session, subscribed=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    share = await client.post(f"/api/forum/threads/{thread['id']}/share")
    assert share.status_code == 200
    token = share.json()["share_token"]

    resp = await client.get(f"/api/forum/shared/{token}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "T"

    revoke = await client.delete(f"/api/forum/threads/{thread['id']}/share")
    assert revoke.status_code == 204
    gone = await client.get(f"/api/forum/shared/{token}")
    assert gone.status_code == 404


async def test_only_owner_or_admin_can_share_a_thread(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    stranger = await make_user(db_session, subscribed=True)
    auth_as(owner)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    auth_as(stranger)
    resp = await client.post(f"/api/forum/threads/{thread['id']}/share")
    assert resp.status_code == 403


async def test_admin_can_update_category_name_and_description(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(admin)
    resp = await client.patch("/api/forum/categories/lounge", json={"name": "Chat", "description": "General chat"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Chat"

    listed = await client.get("/api/forum/categories")
    assert any(c["name"] == "Chat" for c in listed.json())


async def test_non_admin_cannot_update_category(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    resp = await client.patch("/api/forum/categories/lounge", json={"name": "x", "description": "y"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────
#  Emoji reactions
# ─────────────────────────────────────────────

async def test_reacting_to_a_post_adds_it_and_counts_it(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    reactor = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]
    assert thread["posts"][0]["reactions"] == []

    auth_as(reactor)
    resp = await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "❤️"})
    assert resp.status_code == 200
    reactions = resp.json()["posts"][0]["reactions"]
    assert reactions == [{"emoji": "❤️", "count": 1, "reacted_by_me": True}]


async def test_reacting_twice_with_the_same_emoji_toggles_it_off(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "👍"})
    resp = await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "👍"})
    assert resp.json()["posts"][0]["reactions"] == []


async def test_a_user_can_react_with_several_different_emoji_on_one_post(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "🤡"})
    resp = await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "😂"})
    emojis = {r["emoji"] for r in resp.json()["posts"][0]["reactions"]}
    assert emojis == {"🤡", "😂"}


async def test_reactions_from_other_players_dont_show_as_mine(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]
    await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "❤️"})

    auth_as(other)
    resp = await client.get(f"/api/forum/threads/{thread['id']}")
    reaction = resp.json()["posts"][0]["reactions"][0]
    assert reaction == {"emoji": "❤️", "count": 1, "reacted_by_me": False}


async def test_rejects_an_unsupported_emoji(client, db_session, auth_as):
    user = await make_user(db_session, subscribed=True)
    auth_as(user)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    resp = await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "🍕"})
    assert resp.status_code == 400


# ─────────────────────────────────────────────
#  Edit history
# ─────────────────────────────────────────────

async def test_editing_a_post_records_the_previous_body_and_who_edited_it(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Original"})).json()
    post_id = thread["posts"][0]["id"]

    resp = await client.patch(f"/api/forum/posts/{post_id}", json={"body": "Edited by author"})
    post = resp.json()["posts"][0]
    assert post["edited_at"] is not None
    assert post["edited_by_admin"] is False

    auth_as(admin)
    resp = await client.patch(f"/api/forum/posts/{post_id}", json={"body": "Edited by admin"})
    post = resp.json()["posts"][0]
    assert post["edited_by_admin"] is True

    history = await client.get(f"/api/forum/posts/{post_id}/edits")
    assert history.status_code == 200
    bodies = [e["previous_body"] for e in history.json()]
    assert bodies == ["Edited by author", "Original"]
    assert history.json()[0]["editor_is_admin"] is True


async def test_non_admin_cannot_view_edit_history(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    post_id = thread["posts"][0]["id"]
    await client.patch(f"/api/forum/posts/{post_id}", json={"body": "Edited"})

    resp = await client.get(f"/api/forum/posts/{post_id}/edits")
    assert resp.status_code == 403


# ─────────────────────────────────────────────
#  Soft delete / restore / permanent delete
# ─────────────────────────────────────────────

async def test_author_can_delete_own_post_hidden_from_others_visible_to_admin(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Reply below"})).json()
    reply = (await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "delete me"})).json()
    post_id = reply["posts"][-1]["id"]

    resp = await client.delete(f"/api/forum/posts/{post_id}")
    assert resp.status_code == 200

    auth_as(other)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert all(p["id"] != post_id for p in posts)

    auth_as(admin)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    deleted = next(p for p in posts if p["id"] == post_id)
    assert deleted["deleted_at"] is not None
    assert deleted["deleted_by_username"] == author.username
    assert deleted["body"] == "delete me"


async def test_cannot_delete_someone_elses_post(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    post_id = thread["posts"][0]["id"]

    auth_as(other)
    resp = await client.delete(f"/api/forum/posts/{post_id}")
    assert resp.status_code == 403


async def test_admin_can_restore_a_deleted_post(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    post_id = thread["posts"][0]["id"]
    await client.delete(f"/api/forum/posts/{post_id}")

    auth_as(admin)
    resp = await client.post(f"/api/forum/posts/{post_id}/restore")
    assert resp.status_code == 200
    post = next(p for p in resp.json()["posts"] if p["id"] == post_id)
    assert post["deleted_at"] is None

    auth_as(author)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert any(p["id"] == post_id for p in posts)


async def test_admin_can_permanently_erase_a_deleted_post_but_not_a_live_one(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    reply = (await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "temp"})).json()
    post_id = reply["posts"][-1]["id"]

    auth_as(admin)
    live_attempt = await client.delete(f"/api/forum/posts/{post_id}/permanent")
    assert live_attempt.status_code == 400

    await client.delete(f"/api/forum/posts/{post_id}")
    resp = await client.delete(f"/api/forum/posts/{post_id}/permanent")
    assert resp.status_code == 204

    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert all(p["id"] != post_id for p in posts)


# ─────────────────────────────────────────────
#  Whisper / private-to-specific-players posts
# ─────────────────────────────────────────────

async def test_whisper_post_only_visible_to_addressed_players_author_and_admins(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    addressed = await make_user(db_session, subscribed=True)
    outsider = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()

    resp = await client.post(
        f"/api/forum/threads/{thread['id']}/posts",
        json={"body": "psst", "visible_to_user_ids": [str(addressed.id)]},
    )
    assert resp.status_code == 201
    whisper_id = resp.json()["posts"][-1]["id"]

    auth_as(outsider)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert all(p["id"] != whisper_id for p in posts)

    auth_as(addressed)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert any(p["id"] == whisper_id for p in posts)

    auth_as(admin)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    mine = next(p for p in posts if p["id"] == whisper_id)
    assert mine["visible_to"][0]["id"] == str(addressed.id)


async def test_whisper_to_a_nonexistent_player_is_rejected(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    resp = await client.post(
        f"/api/forum/threads/{thread['id']}/posts",
        json={"body": "psst", "visible_to_user_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert resp.status_code == 400


# ─────────────────────────────────────────────
#  Reactor listing
# ─────────────────────────────────────────────

async def test_reactor_listing_is_paginated_and_filtered_by_emoji(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    r1 = await make_user(db_session, subscribed=True)
    r2 = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    post_id = thread["posts"][0]["id"]

    auth_as(r1)
    await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "🔥"})
    auth_as(r2)
    await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "🔥"})
    await client.post(f"/api/forum/posts/{post_id}/react", json={"emoji": "👍"})

    resp = await client.get(f"/api/forum/posts/{post_id}/reactions", params={"emoji": "🔥", "limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["reactors"]) == 1

    resp2 = await client.get(f"/api/forum/posts/{post_id}/reactions", params={"emoji": "👍"})
    assert resp2.json()["total"] == 1


# ─────────────────────────────────────────────
#  Hidden username
# ─────────────────────────────────────────────

async def test_hidden_username_is_masked_from_other_players_but_not_admins_or_self(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    await client.patch("/api/me/forum-privacy", json={"hide_username_on_forum": True})
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()

    auth_as(other)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["author_username"] is None

    auth_as(author)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["author_username"] == author.username

    auth_as(admin)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["author_username"] == author.username


async def test_hidden_username_shows_a_stable_anon_handle_instead_of_the_display_name(client, db_session, auth_as):
    import re

    author = await make_user(db_session, subscribed=True)
    other = await make_user(db_session, subscribed=True)
    auth_as(author)
    await client.patch("/api/me/nickname", json={"nickname": "TotallyIdentifiable"})
    await client.patch("/api/me/forum-privacy", json={"hide_username_on_forum": True})
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "Hi"})).json()
    reply1 = (await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "again"})).json()

    auth_as(other)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    handles = {p["author_display_name"] for p in posts}
    assert len(handles) == 1  # same anon handle both times, not a fresh random one per post
    handle = handles.pop()
    assert re.fullmatch(r"Player#\d{5}", handle)
    assert handle != "TotallyIdentifiable"

    # Quoting a hidden-username post in a reply mustn't leak their real
    # nickname through the quoted snippet either.
    reply2 = await client.post(
        f"/api/forum/threads/{thread['id']}/posts",
        json={"body": "quoting", "reply_to_post_id": reply1["posts"][-1]["id"]},
    )
    quoted = reply2.json()["posts"][-1]["reply_to"]
    assert quoted["author_display_name"] == handle
    assert quoted["author_username"] is None


# ─────────────────────────────────────────────
#  Player-side content reporting
# ─────────────────────────────────────────────

async def test_reporting_a_post_shows_a_count_to_admins_only(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    reporter = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "spam link"})).json()
    post_id = thread["posts"][0]["id"]

    auth_as(reporter)
    resp = await client.post(f"/api/forum/posts/{post_id}/report", json={"reason": "spam"})
    assert resp.status_code == 204

    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["report_count"] == 0  # reporter isn't an admin

    auth_as(admin)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["report_count"] == 1

    reports = (await client.get(f"/api/forum/posts/{post_id}/reports")).json()
    assert len(reports) == 1
    assert reports[0]["reason"] == "spam"
    assert reports[0]["reporter_username"] == reporter.username


async def test_multiple_reports_on_the_same_post_stack_the_count(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    r1 = await make_user(db_session, subscribed=True)
    r2 = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    auth_as(r1)
    await client.post(f"/api/forum/posts/{post_id}/report", json={"reason": None})
    auth_as(r2)
    await client.post(f"/api/forum/posts/{post_id}/report", json={"reason": "rude"})

    auth_as(admin)
    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["report_count"] == 2


async def test_dismissing_reports_clears_the_count(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    reporter = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    auth_as(reporter)
    await client.post(f"/api/forum/posts/{post_id}/report", json={"reason": "spam"})

    auth_as(admin)
    dismiss = await client.post(f"/api/forum/posts/{post_id}/reports/dismiss")
    assert dismiss.status_code == 204

    posts = (await client.get(f"/api/forum/threads/{thread['id']}")).json()["posts"]
    assert posts[0]["report_count"] == 0
    assert (await client.get(f"/api/forum/posts/{post_id}/reports")).json() == []


async def test_non_admin_cannot_list_or_dismiss_reports(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    assert (await client.get(f"/api/forum/posts/{post_id}/reports")).status_code == 403
    assert (await client.post(f"/api/forum/posts/{post_id}/reports/dismiss")).status_code == 403


# ── Thread-level reports ─────────────────────────────────────────────


async def test_reporting_a_thread_surfaces_a_count_to_admins_only(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    reporter = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "Buy gold cheap", "body": "..."})).json()

    auth_as(reporter)
    assert (await client.post(f"/api/forum/threads/{thread['id']}/report", json={"reason": "advertising"})).status_code == 204

    detail = (await client.get(f"/api/forum/threads/{thread['id']}")).json()
    assert detail["report_count"] == 0  # reporter isn't an admin

    auth_as(admin)
    assert (await client.get(f"/api/forum/threads/{thread['id']}")).json()["report_count"] == 1
    reports = (await client.get(f"/api/forum/threads/{thread['id']}/reports")).json()
    assert [r["reason"] for r in reports] == ["advertising"]


async def test_thread_report_count_shows_on_the_thread_list_for_admins(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    reporter = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    auth_as(reporter)
    await client.post(f"/api/forum/threads/{thread['id']}/report", json={"reason": None})

    listed = (await client.get("/api/forum/categories/lounge/threads")).json()["threads"]
    assert all(t["report_count"] == 0 for t in listed)

    auth_as(admin)
    listed = (await client.get("/api/forum/categories/lounge/threads")).json()["threads"]
    assert next(t for t in listed if t["id"] == thread["id"])["report_count"] == 1


async def test_dismissing_thread_reports_clears_the_count(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    reporter = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    auth_as(reporter)
    await client.post(f"/api/forum/threads/{thread['id']}/report", json={"reason": "spam"})

    auth_as(admin)
    assert (await client.post(f"/api/forum/threads/{thread['id']}/reports/dismiss")).status_code == 204
    assert (await client.get(f"/api/forum/threads/{thread['id']}")).json()["report_count"] == 0
    assert (await client.get(f"/api/forum/threads/{thread['id']}/reports")).json() == []


async def test_non_admin_cannot_list_or_dismiss_thread_reports(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()

    assert (await client.get(f"/api/forum/threads/{thread['id']}/reports")).status_code == 403
    assert (await client.post(f"/api/forum/threads/{thread['id']}/reports/dismiss")).status_code == 403


# ── Who can be reported ──────────────────────────────────────────────


async def test_an_admins_post_cannot_be_reported(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    player = await make_user(db_session, subscribed=True)
    auth_as(admin)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "Rules", "body": "read these"})).json()
    post_id = thread["posts"][0]["id"]

    auth_as(player)
    assert (await client.post(f"/api/forum/posts/{post_id}/report", json={"reason": "x"})).status_code == 400


async def test_an_admins_thread_cannot_be_reported(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    player = await make_user(db_session, subscribed=True)
    auth_as(admin)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "Rules", "body": "..."})).json()

    auth_as(player)
    assert (await client.post(f"/api/forum/threads/{thread['id']}/report", json={"reason": "x"})).status_code == 400


async def test_you_cannot_report_your_own_content(client, db_session, auth_as):
    author = await make_user(db_session, subscribed=True)
    auth_as(author)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    post_id = thread["posts"][0]["id"]

    assert (await client.post(f"/api/forum/posts/{post_id}/report", json={"reason": None})).status_code == 400
    assert (await client.post(f"/api/forum/threads/{thread['id']}/report", json={"reason": None})).status_code == 400


async def test_thread_detail_exposes_whether_the_author_is_an_admin(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(admin)
    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "T", "body": "..."})).json()
    assert thread["author_is_admin"] is True
