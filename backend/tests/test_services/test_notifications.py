from backend.app.services.notifications import notify_favorited_map_users
from backend.tests.factories import make_map, make_user
from backend.app.db.models import FavoriteMapModel


async def _favorite(db_session, user, map_):
    db_session.add(FavoriteMapModel(user_id=user.id, map_id=map_.id))
    await db_session.commit()


async def test_notifies_only_users_who_favorited_the_map(db_session, monkeypatch):
    sent = []

    async def _fake_send(telegram_id, text, web_app_url=None):
        sent.append((telegram_id, text))

    monkeypatch.setattr("backend.app.services.notifications.send_telegram_message", _fake_send)

    map_ = await make_map(db_session, name="Mirage")
    other_map = await make_map(db_session, name="Inferno")
    fan = await make_user(db_session, telegram_id=111)
    stranger = await make_user(db_session, telegram_id=222)

    await _favorite(db_session, fan, map_)
    await _favorite(db_session, stranger, other_map)  # favorited a *different* map

    await notify_favorited_map_users(db_session, map_.id, map_.name, "A Split via Connector")

    assert sent == [(111, "🔥 New strategy on <b>Mirage</b>: A Split via Connector")]


async def test_no_favorites_means_no_calls(db_session, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "backend.app.services.notifications.send_telegram_message",
        lambda *a, **k: sent.append(a),
    )

    map_ = await make_map(db_session)
    await notify_favorited_map_users(db_session, map_.id, map_.name, "Some Strategy")

    assert sent == []
