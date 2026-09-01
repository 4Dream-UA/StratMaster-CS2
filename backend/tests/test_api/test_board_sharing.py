from backend.tests.factories import make_user


BOARD_IMAGE = "https://example.com/radar.png"


def _payload(title="Shared Board"):
    return {"image_url": BOARD_IMAGE, "title": title, "paths": [], "grenades": []}


async def test_owner_can_create_and_revoke_share_link(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload())).json()["id"]

    share = await client.post(f"/api/boards/{board_id}/share")
    assert share.status_code == 200
    token = share.json()["share_token"]
    assert token

    revoke = await client.delete(f"/api/boards/{board_id}/share")
    assert revoke.status_code == 204


async def test_anyone_can_view_a_shared_board_without_auth(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload(title="Public Board"))).json()["id"]
    token = (await client.post(f"/api/boards/{board_id}/share")).json()["share_token"]

    resp = await client.get(f"/api/boards/shared/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Public Board"
    # The board carries its own backdrop, so the public viewer needs nothing
    # else looked up for it — it used to be handed the map's name and cover.
    assert body["image_url"] == BOARD_IMAGE


async def test_unknown_share_token_is_404(client, db_session):
    resp = await client.get("/api/boards/shared/does-not-exist")
    assert resp.status_code == 404


async def test_revoked_share_link_stops_working(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload())).json()["id"]
    token = (await client.post(f"/api/boards/{board_id}/share")).json()["share_token"]

    await client.delete(f"/api/boards/{board_id}/share")

    resp = await client.get(f"/api/boards/shared/{token}")
    assert resp.status_code == 404


async def test_owner_can_add_collaborator_by_wallet_id(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    friend = await make_user(db_session, subscribed=True)

    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload())).json()["id"]

    add = await client.post(f"/api/boards/{board_id}/collaborators", json={"wallet_id": friend.wallet.wallet_id})
    assert add.status_code == 201
    assert len(add.json()) == 1
    assert add.json()[0]["id"] == str(friend.id)


async def test_collaborator_can_view_and_edit_but_not_delete(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    friend = await make_user(db_session, subscribed=True)

    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload())).json()["id"]
    await client.post(f"/api/boards/{board_id}/collaborators", json={"wallet_id": friend.wallet.wallet_id})

    auth_as(friend)
    get_resp = await client.get(f"/api/boards/{board_id}")
    assert get_resp.status_code == 200

    update_payload = _payload(title="Edited by friend")
    patch_resp = await client.patch(f"/api/boards/{board_id}", json=update_payload)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Edited by friend"

    delete_resp = await client.delete(f"/api/boards/{board_id}")
    assert delete_resp.status_code == 404  # not the owner — board stays invisible to this action

    # And a stranger with no invite still can't see it at all.
    stranger = await make_user(db_session, subscribed=True)
    auth_as(stranger)
    assert (await client.get(f"/api/boards/{board_id}")).status_code == 404


async def test_add_collaborator_rejects_unknown_wallet_id(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload())).json()["id"]

    resp = await client.post(f"/api/boards/{board_id}/collaborators", json={"wallet_id": "NOSUCHWALLET1234"})
    assert resp.status_code == 404


async def test_owner_can_remove_collaborator(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    friend = await make_user(db_session, subscribed=True)

    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload())).json()["id"]
    await client.post(f"/api/boards/{board_id}/collaborators", json={"wallet_id": friend.wallet.wallet_id})

    resp = await client.delete(f"/api/boards/{board_id}/collaborators/{friend.id}")
    assert resp.status_code == 200
    assert resp.json() == []

    auth_as(friend)
    assert (await client.get(f"/api/boards/{board_id}")).status_code == 404


async def test_boards_shared_with_me_endpoint(client, db_session, auth_as):
    owner = await make_user(db_session, subscribed=True)
    friend = await make_user(db_session, subscribed=True)

    auth_as(owner)
    board_id = (await client.post("/api/boards", json=_payload(title="Invited Board"))).json()["id"]
    await client.post(f"/api/boards/{board_id}/collaborators", json={"wallet_id": friend.wallet.wallet_id})

    auth_as(friend)
    resp = await client.get("/api/boards/shared-with-me")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["boards"][0]["title"] == "Invited Board"

    # It must not also show up in friend's own /api/boards list.
    own_list = await client.get("/api/boards")
    assert own_list.json()["total"] == 0
