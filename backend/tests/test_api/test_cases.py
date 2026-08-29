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


async def test_buy_case_deducts_cost_and_adds_to_inventory(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=100)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 2})
    assert resp.status_code == 201
    body = resp.json()
    assert body["quantity"] == 2
    assert body["new_balance"] == 100 - 49 * 2

    inv = await client.get("/api/cases/inventory")
    assert inv.json() == [{"case_id": str(case_.id), "case_name": case_.name, "count": 2}]


async def test_buy_case_rejects_insufficient_balance(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=10)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    assert resp.status_code == 400
    assert "Not enough MasterCoins" in resp.json()["detail"]


async def test_buy_unknown_case_is_404(client, db_session, auth_as):
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    resp = await client.post("/api/cases/00000000-0000-0000-0000-000000000000/buy", json={"quantity": 1})
    assert resp.status_code == 404


async def test_buy_inactive_case_is_404(client, db_session, auth_as):
    case_ = await make_case(db_session, is_active=False)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    assert resp.status_code == 404


async def test_open_requires_owning_enough_inventory(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 5})
    assert resp.status_code == 400
    assert "only own 1" in resp.json()["detail"]


async def test_open_rejects_invalid_quantity(client, db_session, auth_as):
    case_ = await make_case(db_session)
    user = await make_user(db_session, balance=1000)
    auth_as(user)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 3})

    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 3})
    assert resp.status_code == 400
    assert "must be 1, 2 or 5" in resp.json()["detail"]


async def test_buy_then_open_x1_resolves_reward_and_clears_inventory(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=100)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rewards"]) == 1
    assert body["rewards"][0] in (5, 100)
    assert body["total_won"] == body["rewards"][0]
    assert body["new_balance"] == 100 - 49 + body["total_won"]

    inv = await client.get("/api/cases/inventory")
    assert inv.json() == []


async def test_buy_then_open_x5_resolves_five_independent_rewards(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 5})
    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rewards"]) == 5
    assert body["total_won"] == sum(body["rewards"])
    assert all(r in (5, 100) for r in body["rewards"])

    inv = await client.get("/api/cases/inventory")
    assert inv.json() == []


async def test_opening_records_one_history_row_per_case(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 2})
    await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 2})

    history = await client.get("/api/cases/openings/history")
    assert history.status_code == 200
    openings = history.json()["openings"]
    assert len(openings) == 2
    assert all(o["case_name"] == case_.name and o["coins_spent"] == 49 for o in openings)


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

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 15})

    seen = set()
    for _ in range(15):
        resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 1})
        seen.add(resp.json()["rewards"][0])

    assert seen == {1, 2}
