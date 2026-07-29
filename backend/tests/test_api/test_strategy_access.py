import pytest

from backend.tests.factories import make_map, make_strategy, make_user


async def test_premium_strategy_requires_auth(client, db_session):
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, is_free=False)

    resp = await client.get(f"/api/strategies/{strategy.id}")
    assert resp.status_code == 401


async def test_premium_strategy_forbidden_without_subscription(client, db_session, auth_as):
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, is_free=False)
    user = await make_user(db_session, subscribed=False)
    auth_as(user)

    resp = await client.get(f"/api/strategies/{strategy.id}")
    assert resp.status_code == 403


async def test_premium_strategy_ok_with_active_subscription(client, db_session, auth_as):
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, is_free=False, with_children=True)
    user = await make_user(db_session, subscribed=True)
    auth_as(user)

    resp = await client.get(f"/api/strategies/{strategy.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(strategy.id)
    assert len(body["grenades"]) == 1


async def test_free_strategy_ok_without_subscription(client, db_session, auth_as):
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, is_free=True)
    user = await make_user(db_session, subscribed=False)
    auth_as(user)

    resp = await client.get(f"/api/strategies/{strategy.id}")
    assert resp.status_code == 200


async def test_free_strategy_ok_anonymous(client, db_session):
    map_ = await make_map(db_session)
    strategy = await make_strategy(db_session, map_id=map_.id, is_free=True)

    resp = await client.get(f"/api/strategies/{strategy.id}")
    assert resp.status_code == 200
