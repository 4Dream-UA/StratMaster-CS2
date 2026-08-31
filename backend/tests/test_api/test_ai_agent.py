"""The AI support assistant.

The model call itself is always stubbed — these cover when the assistant is
allowed to speak and what happens to its reply, which is the part that can
actually go wrong. `complete()` is the single seam every test patches.

Most tests go through the real endpoints rather than calling the service:
opening a ticket schedules the reply as a FastAPI background task, and the
test client runs those, so the assertion is on what a player would actually
end up seeing.
"""
import pytest

from backend.app.core.config import settings as app_config
from backend.app.services import ai_agent
from backend.tests.conftest import TestSessionLocal
from backend.tests.factories import make_ai_agent_user, make_user


@pytest.fixture(autouse=True)
def agent_env(monkeypatch):
    """The service opens its own session (it normally runs as a background
    task, after the request that scheduled it has closed its own), so it has
    to be pointed at the test engine. An API key is set so `is_configured()`
    passes without one ever being used — `complete` is stubbed per test."""
    monkeypatch.setattr(ai_agent, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(app_config, "openai_api_key", "test-key-not-used")


def stub_reply(monkeypatch, text="Cases have no refunds, sorry."):
    calls = []

    async def _complete(messages):
        calls.append(messages)
        return text

    monkeypatch.setattr(ai_agent, "complete", _complete)
    return calls


async def open_ticket(client, title="Where did my case go", body="I bought one and it vanished."):
    return (await client.post("/api/forum/categories/support/threads", json={"title": title, "body": body})).json()


async def get_thread(client, thread_id):
    return (await client.get(f"/api/forum/threads/{thread_id}")).json()


def ai_posts(thread):
    return [p for p in thread["posts"] if p["author_is_ai"]]


# ── When it speaks ───────────────────────────────────────────────────


async def test_it_answers_a_new_support_ticket(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    calls = stub_reply(monkeypatch)

    thread = await open_ticket(client)
    detail = await get_thread(client, thread["id"])

    assert len(detail["posts"]) == 2
    reply = detail["posts"][1]
    assert reply["author_is_ai"] is True
    assert reply["author_is_admin"] is False
    assert "Cases have no refunds" in reply["body"]
    # Always says what it is — a player must never read it as the team.
    assert "Automated first reply" in reply["body"]

    # The ticket's own text reaches the model, under the system prompt.
    assert calls[0][0]["role"] == "system"
    assert any("vanished" in m["content"] for m in calls[0])


async def test_it_stays_out_of_the_lounge(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    stub_reply(monkeypatch)

    thread = (await client.post("/api/forum/categories/lounge/threads", json={"title": "hi", "body": "hello"})).json()
    assert ai_posts(await get_thread(client, thread["id"])) == []


async def test_it_backs_off_once_an_admin_has_replied(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(player)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    assert len(ai_posts(await get_thread(client, thread["id"]))) == 1

    auth_as(admin)
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "Looking into it."})

    # A human owns this conversation now — the assistant must not talk over
    # them, however many more times the player writes.
    auth_as(player)
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "Any news?"})
    assert len(ai_posts(await get_thread(client, thread["id"]))) == 1


async def test_it_never_answers_itself_twice_in_a_row(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    # Nothing new has been said since its reply, so there is nothing to answer.
    assert await ai_agent.reply_to_ticket(thread["id"]) is False
    assert len(ai_posts(await get_thread(client, thread["id"]))) == 1


async def test_it_stops_after_the_configured_number_of_replies(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    stub_reply(monkeypatch)
    monkeypatch.setattr(app_config, "ai_agent_max_replies_per_thread", 2)

    thread = await open_ticket(client)  # reply 1
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "Still broken"})  # reply 2
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "Hello?"})  # capped

    assert len(ai_posts(await get_thread(client, thread["id"]))) == 2


async def test_it_stays_quiet_on_a_closed_ticket(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(player)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    auth_as(admin)
    await client.patch(f"/api/forum/threads/{thread['id']}/close", json={"is_closed": True})

    assert await ai_agent.reply_to_ticket(thread["id"]) is False


async def test_admins_can_switch_it_off(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    stub_reply(monkeypatch)

    auth_as(admin)
    updated = (await client.patch("/api/admin/settings", json={"logo_url": None, "ai_agent_enabled": False})).json()
    assert updated["ai_agent_enabled"] is False

    auth_as(player)
    thread = await open_ticket(client)
    assert ai_posts(await get_thread(client, thread["id"])) == []


async def test_it_does_nothing_without_an_api_key(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    stub_reply(monkeypatch)
    monkeypatch.setattr(app_config, "openai_api_key", "")

    thread = await open_ticket(client)
    assert ai_posts(await get_thread(client, thread["id"])) == []


async def test_a_missing_agent_user_is_not_a_crash(client, db_session, auth_as, monkeypatch):
    """The migration seeds the row; if it somehow isn't there the ticket just
    waits for a human, rather than blowing up the request that opened it."""
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    assert ai_posts(await get_thread(client, thread["id"])) == []


async def test_an_empty_or_failed_completion_posts_nothing(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)

    async def _no_answer(messages):
        return None

    monkeypatch.setattr(ai_agent, "complete", _no_answer)

    thread = await open_ticket(client)
    detail = await get_thread(client, thread["id"])
    assert len(detail["posts"]) == 1


async def test_complete_swallows_a_broken_api_call(monkeypatch):
    """A provider outage must never surface as an exception in the caller —
    every failure has to look like "no answer"."""
    class _Boom:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            raise RuntimeError("connection reset")

    monkeypatch.setattr(ai_agent.httpx, "AsyncClient", lambda **kw: _Boom())
    assert await ai_agent.complete([{"role": "user", "content": "hi"}]) is None


# ── How it shows up elsewhere ────────────────────────────────────────


async def test_its_reply_does_not_count_as_the_team_answering(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(player)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)

    auth_as(admin)
    ticket = (await client.get("/api/admin/tickets")).json()["tickets"][0]
    assert ticket["ai_handled"] is True
    assert ticket["post_count"] == 2
    # The assistant had the last word, so nobody is being kept waiting — but
    # the ticket stays open and in the queue for a human to look over.
    assert ticket["awaiting_reply"] is False
    assert ticket["is_closed"] is False


async def test_a_player_replying_after_the_assistant_puts_it_back_in_the_queue(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(player)
    # Capped at one so the assistant doesn't answer the follow-up too, which
    # is what this test is actually about.
    monkeypatch.setattr(app_config, "ai_agent_max_replies_per_thread", 1)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "That didn't help"})

    auth_as(admin)
    ticket = (await client.get("/api/admin/tickets")).json()["tickets"][0]
    assert ticket["awaiting_reply"] is True


async def test_settings_expose_the_switch_without_leaking_the_key(client, db_session):
    body = (await client.get("/api/settings")).json()
    assert body["ai_agent_enabled"] is True
    assert body["ai_agent_configured"] is True
    assert body["ai_agent_model"] == app_config.ai_agent_model
    assert "test-key-not-used" not in str(body)


async def test_saving_the_logo_alone_leaves_the_switch_alone(client, db_session, auth_as):
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(admin)

    await client.patch("/api/admin/settings", json={"logo_url": None, "ai_agent_enabled": False})
    after = (await client.patch("/api/admin/settings", json={"logo_url": "/uploads/x.png"})).json()
    assert after["ai_agent_enabled"] is False


async def test_the_agent_user_is_not_an_admin(client, db_session):
    agent = await make_ai_agent_user(db_session)
    assert agent.is_admin is False
    assert agent.is_ai_agent is True
    # It can't be dragged into trades even if something tried.
    assert agent.is_trade_banned is True


# ── The wire format ──────────────────────────────────────────────────
# These pin the request body itself. Every other test stubs `complete()`,
# so nothing above would have caught the real API rejecting the payload —
# which is exactly what happened: the GPT-5.x family 400s on `max_tokens`
# and on any temperature but its own default.


def test_request_body_uses_max_completion_tokens_not_max_tokens(monkeypatch):
    monkeypatch.setattr(app_config, "ai_agent_model", "gpt-5.6-luna")
    monkeypatch.setattr(app_config, "ai_agent_max_tokens", 800)
    body = ai_agent._request_body([{"role": "user", "content": "hi"}])

    assert body["max_completion_tokens"] == 800
    assert "max_tokens" not in body
    assert body["model"] == "gpt-5.6-luna"


def test_request_body_omits_temperature_unless_it_is_configured(monkeypatch):
    monkeypatch.setattr(app_config, "ai_agent_temperature", None)
    assert "temperature" not in ai_agent._request_body([{"role": "user", "content": "hi"}])

    monkeypatch.setattr(app_config, "ai_agent_temperature", 0.3)
    assert ai_agent._request_body([{"role": "user", "content": "hi"}])["temperature"] == 0.3


async def test_every_reply_is_marked_automated_in_both_languages(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    player = await make_user(db_session, subscribed=True)
    auth_as(player)
    stub_reply(monkeypatch, "Ответ на русском.")

    thread = await open_ticket(client)
    body = ai_posts(await get_thread(client, thread["id"]))[0]["body"]
    assert "Automated first reply" in body
    assert "Автоматический первый ответ" in body


async def test_it_answers_an_admin_who_opens_their_own_ticket(client, db_session, auth_as, monkeypatch):
    """Being staff doesn't stop you having a question. The "don't talk over
    the team" rule is about staff joining someone else's ticket, and reading
    it as "never answer an admin" left admins unable to use the assistant at
    all — including to check that it works."""
    await make_ai_agent_user(db_session)
    admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(admin)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    assert len(ai_posts(await get_thread(client, thread["id"]))) == 1


async def test_a_second_admin_joining_still_silences_it(client, db_session, auth_as, monkeypatch):
    await make_ai_agent_user(db_session)
    owner = await make_user(db_session, subscribed=True, is_admin=True)
    other_admin = await make_user(db_session, subscribed=True, is_admin=True)
    auth_as(owner)
    stub_reply(monkeypatch)

    thread = await open_ticket(client)
    assert len(ai_posts(await get_thread(client, thread["id"]))) == 1

    auth_as(other_admin)
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "I'll take this."})
    auth_as(owner)
    await client.post(f"/api/forum/threads/{thread['id']}/posts", json={"body": "Thanks"})

    assert len(ai_posts(await get_thread(client, thread["id"]))) == 1
