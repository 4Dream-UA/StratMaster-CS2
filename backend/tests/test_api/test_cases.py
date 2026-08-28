from backend.tests.factories import make_case, make_user


async def test_list_cases_returns_only_active(client, db_session):
    active = await make_case(db_session, name="Active Case")
    await make_case(db_session, name="Hidden Case", is_active=False)

    resp = await client.get("/api/cases")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == str(active.id)
    assert body[0]["rewards"] == [
        {"coins": 5, "chance_percent": 50},
        {"coins": 100, "chance_percent": 50},
    ]


async def test_open_case_deducts_cost_and_credits_a_valid_reward(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=100)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/open")
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins_spent"] == 49
    assert body["reward_coins"] in (5, 100)
    assert body["new_balance"] == 100 - 49 + body["reward_coins"]


async def test_open_case_rejects_insufficient_balance(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=10)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/open")
    assert resp.status_code == 400
    assert "Not enough MasterCoins" in resp.json()["detail"]


async def test_open_unknown_case_is_404(client, db_session, auth_as):
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    resp = await client.post("/api/cases/00000000-0000-0000-0000-000000000000/open")
    assert resp.status_code == 404


async def test_open_inactive_case_is_404(client, db_session, auth_as):
    case_ = await make_case(db_session, is_active=False)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/open")
    assert resp.status_code == 404


async def test_opening_records_history_and_transactions(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=100)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/open")

    history = await client.get("/api/cases/openings/history")
    assert history.status_code == 200
    openings = history.json()["openings"]
    assert len(openings) == 1
    assert openings[0]["case_name"] == case_.name
    assert openings[0]["coins_spent"] == 49


async def test_weighted_distribution_is_reasonably_close_over_many_opens(client, db_session, auth_as):
    # Not a statistical proof — just a sanity check that both reward tiers
    # get selected at all (catches a totally broken weighting, e.g. always
    # picking rewards[0]) without being flaky under normal variance.
    case_ = await make_case(db_session, cost_coins=1, rewards=[
        {"coins": 1, "chance_percent": 50},
        {"coins": 2, "chance_percent": 50},
    ])
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    # Stay under the endpoint's own rate limit (20 requests/60s).
    seen = set()
    for _ in range(15):
        resp = await client.post(f"/api/cases/{case_.id}/open")
        seen.add(resp.json()["reward_coins"])

    assert seen == {1, 2}
