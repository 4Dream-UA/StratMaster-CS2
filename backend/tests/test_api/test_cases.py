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
        {"coins": 5, "premium_days": None, "tier": "grey", "chance_percent": 50},
        {"coins": 100, "premium_days": None, "tier": "grey", "chance_percent": 50},
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
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 4})

    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 4})
    assert resp.status_code == 400
    assert "must be 1, 3 or 5" in resp.json()["detail"]


async def test_buy_then_open_x1_resolves_reward_and_clears_inventory(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=100)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rewards"]) == 1
    assert body["rewards"][0]["coins"] in (5, 100)
    assert body["rewards"][0]["premium_days"] is None
    assert body["total_won"] == body["rewards"][0]["coins"]
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
    assert body["total_won"] == sum(r["coins"] for r in body["rewards"])
    assert all(r["coins"] in (5, 100) for r in body["rewards"])

    inv = await client.get("/api/cases/inventory")
    assert inv.json() == []


async def test_opening_records_one_history_row_per_case(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=49)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 3})
    await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 3})

    history = await client.get("/api/cases/openings/history")
    assert history.status_code == 200
    openings = history.json()["openings"]
    assert len(openings) == 3
    assert all(o["case_name"] == case_.name and o["coins_spent"] == 49 for o in openings)


async def test_buy_case_quantity_above_50_is_rejected(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=1)
    user = await make_user(db_session, balance=1000)
    auth_as(user)

    resp = await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 51})
    assert resp.status_code == 422


# ─────────────────────────────────────────────
#  Premium-days case rewards (a case doesn't have to pay out in coins)
# ─────────────────────────────────────────────

async def test_open_premium_case_lands_a_voucher_instead_of_granting_days_instantly(client, db_session, auth_as):
    case_ = await make_case(db_session, name="Premium Case", cost_coins=99, rewards=[
        {"premium_days": 14, "chance_percent": 100, "tier": "blue"},
    ])
    user = await make_user(db_session, balance=200)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rewards"] == [{"coins": 0, "premium_days": 14}]
    assert body["total_won"] == 0  # no coins changed hands
    assert body["new_balance"] == 200 - 99  # only the purchase cost left the wallet

    me = await client.get("/api/me")
    assert me.json()["wallet"]["subscription_expires_at"] is None  # not applied yet

    vouchers = (await client.get("/api/cases/vouchers")).json()
    assert len(vouchers) == 1
    assert vouchers[0]["days"] == 14

    activate = await client.post(f"/api/cases/vouchers/{vouchers[0]['id']}/activate")
    assert activate.status_code == 200
    assert activate.json()["premium_expires_at"] is not None

    me = await client.get("/api/me")
    assert me.json()["wallet"]["subscription_expires_at"] == activate.json()["premium_expires_at"]
    assert (await client.get("/api/cases/vouchers")).json() == []


async def test_open_premium_case_nothing_tier_lands_no_voucher(client, db_session, auth_as):
    case_ = await make_case(db_session, name="Premium Case", cost_coins=99, rewards=[
        {"premium_days": 0, "chance_percent": 100, "tier": "grey"},
    ])
    user = await make_user(db_session, balance=200)
    auth_as(user)

    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    resp = await client.post("/api/cases/inventory/open", json={"case_id": str(case_.id), "quantity": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rewards"] == [{"coins": 0, "premium_days": 0}]
    assert body["new_balance"] == 200 - 99

    me = await client.get("/api/me")
    assert me.json()["wallet"]["subscription_expires_at"] is None
    assert (await client.get("/api/cases/vouchers")).json() == []


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
        seen.add(resp.json()["rewards"][0]["coins"])

    assert seen == {1, 2}


# ─────────────────────────────────────────────
#  P2P case gifting + sales
# ─────────────────────────────────────────────

async def test_gift_case_escrows_immediately_and_notifies(client, db_session, auth_as, monkeypatch):
    sent = []
    async def _fake_notify(telegram_id, text, web_app_url=None):
        sent.append((telegram_id, text))
    monkeypatch.setattr("backend.app.api.routers.cases.send_telegram_message", _fake_notify)

    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 2})

    resp = await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 2,
    })
    assert resp.status_code == 201
    offer = resp.json()
    assert offer["status"] == "pending"
    assert offer["offer_type"] == "gift"
    assert offer["price_coins"] == 0

    # Escrowed immediately — sender's inventory is empty while pending.
    inv = await client.get("/api/cases/inventory")
    assert inv.json() == []
    assert len(sent) == 1
    assert sent[0][0] == receiver.telegram_id


async def test_gift_requires_owning_enough_cases(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})

    resp = await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 5,
    })
    assert resp.status_code == 400


async def test_receiver_accepts_gift_and_it_lands_in_their_inventory(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    offer = (await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1,
    })).json()

    auth_as(receiver)
    accept = await client.post(f"/api/cases/offers/{offer['id']}/accept")
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    inv = await client.get("/api/cases/inventory")
    assert inv.json() == [{"case_id": str(case_.id), "case_name": case_.name, "count": 1}]


async def test_receiver_declines_gift_and_it_returns_to_sender(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    offer = (await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1,
    })).json()

    auth_as(receiver)
    decline = await client.post(f"/api/cases/offers/{offer['id']}/decline")
    assert decline.status_code == 200
    assert decline.json()["status"] == "declined"

    auth_as(sender)
    inv = await client.get("/api/cases/inventory")
    assert inv.json() == [{"case_id": str(case_.id), "case_name": case_.name, "count": 1}]


async def test_sender_can_cancel_a_pending_offer(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    offer = (await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1,
    })).json()

    cancel = await client.post(f"/api/cases/offers/{offer['id']}/cancel")
    assert cancel.status_code == 200
    inv = await client.get("/api/cases/inventory")
    assert inv.json() == [{"case_id": str(case_.id), "case_name": case_.name, "count": 1}]


async def test_only_receiver_can_accept_or_decline(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    stranger = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    offer = (await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1,
    })).json()

    auth_as(stranger)
    assert (await client.post(f"/api/cases/offers/{offer['id']}/accept")).status_code == 403
    assert (await client.post(f"/api/cases/offers/{offer['id']}/decline")).status_code == 403


async def test_sell_case_charges_buyer_and_pays_seller(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    seller = await make_user(db_session, balance=100)
    buyer = await make_user(db_session, balance=500)
    auth_as(seller)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    offer = (await client.post("/api/cases/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1, "price_coins": 200,
    })).json()
    assert offer["offer_type"] == "sale"
    assert offer["price_coins"] == 200

    auth_as(buyer)
    accept = await client.post(f"/api/cases/offers/{offer['id']}/accept")
    assert accept.status_code == 200

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 300  # 500 - 200

    inv = await client.get("/api/cases/inventory")
    assert inv.json() == [{"case_id": str(case_.id), "case_name": case_.name, "count": 1}]


async def test_sell_case_rejects_insufficient_buyer_balance(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    seller = await make_user(db_session, balance=100)
    buyer = await make_user(db_session, balance=5)
    auth_as(seller)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})
    offer = (await client.post("/api/cases/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1, "price_coins": 200,
    })).json()

    auth_as(buyer)
    resp = await client.post(f"/api/cases/offers/{offer['id']}/accept")
    assert resp.status_code == 400


async def test_offer_blocked_by_personal_block(client, db_session, auth_as):
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})

    auth_as(receiver)
    await client.post("/api/wallet/block", json={"wallet_id": sender.wallet.wallet_id})

    auth_as(sender)
    resp = await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1,
    })
    assert resp.status_code == 403
    # Not consumed by the rejected offer.
    inv = await client.get("/api/cases/inventory")
    assert inv.json() == [{"case_id": str(case_.id), "case_name": case_.name, "count": 1}]


async def test_offer_blocked_when_sender_is_trade_banned(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    case_ = await make_case(db_session, cost_coins=10)
    sender = await make_user(db_session, balance=100)
    receiver = await make_user(db_session)
    auth_as(sender)
    await client.post(f"/api/cases/{case_.id}/buy", json={"quantity": 1})

    auth_as(admin)
    ban = await client.patch(f"/api/admin/users/{sender.id}/trade-ban", json={"is_trade_banned": True})
    assert ban.status_code == 200

    auth_as(sender)
    resp = await client.post("/api/cases/gift", json={
        "receiver_wallet_id": receiver.wallet.wallet_id, "case_id": str(case_.id), "quantity": 1,
    })
    assert resp.status_code == 403


# ─────────────────────────────────────────────
#  Premium vouchers
# ─────────────────────────────────────────────

async def _make_voucher(db_session, user, days=14):
    from backend.app.db.models import PremiumVoucherModel
    voucher = PremiumVoucherModel(user_id=user.id, days=days)
    db_session.add(voucher)
    await db_session.commit()
    await db_session.refresh(voucher)
    return voucher


async def test_gift_voucher_transfers_it_instantly_no_accept_needed(client, db_session, auth_as):
    sender = await make_user(db_session)
    receiver = await make_user(db_session)
    voucher = await _make_voucher(db_session, sender, days=31)
    auth_as(sender)

    resp = await client.post(f"/api/cases/vouchers/{voucher.id}/gift", json={"receiver_wallet_id": receiver.wallet.wallet_id})
    assert resp.status_code == 204

    assert (await client.get("/api/cases/vouchers")).json() == []
    auth_as(receiver)
    got = (await client.get("/api/cases/vouchers")).json()
    assert len(got) == 1 and got[0]["days"] == 31


async def test_cannot_gift_someone_elses_voucher(client, db_session, auth_as):
    owner = await make_user(db_session)
    other = await make_user(db_session)
    receiver = await make_user(db_session)
    voucher = await _make_voucher(db_session, owner)
    auth_as(other)

    resp = await client.post(f"/api/cases/vouchers/{voucher.id}/gift", json={"receiver_wallet_id": receiver.wallet.wallet_id})
    assert resp.status_code == 404


async def test_sell_voucher_full_accept_flow_transfers_coins_and_voucher(client, db_session, auth_as):
    seller = await make_user(db_session)
    buyer = await make_user(db_session, balance=100)
    voucher = await _make_voucher(db_session, seller, days=90)
    auth_as(seller)

    sell = await client.post(f"/api/cases/vouchers/{voucher.id}/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "price_coins": 60,
    })
    assert sell.status_code == 201
    offer_id = sell.json()["id"]
    # Escrowed off the seller immediately.
    assert (await client.get("/api/cases/vouchers")).json() == []

    auth_as(buyer)
    accept = await client.post(f"/api/cases/voucher-offers/{offer_id}/accept")
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    vouchers = (await client.get("/api/cases/vouchers")).json()
    assert len(vouchers) == 1 and vouchers[0]["days"] == 90

    me = await client.get("/api/me")
    assert me.json()["wallet"]["balance_coins"] == 100 - 60


async def test_sell_voucher_rejects_when_buyer_cant_afford_it(client, db_session, auth_as):
    seller = await make_user(db_session)
    buyer = await make_user(db_session, balance=10)
    voucher = await _make_voucher(db_session, seller)
    auth_as(seller)
    sell = await client.post(f"/api/cases/vouchers/{voucher.id}/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "price_coins": 60,
    })
    offer_id = sell.json()["id"]

    auth_as(buyer)
    resp = await client.post(f"/api/cases/voucher-offers/{offer_id}/accept")
    assert resp.status_code == 400


async def test_decline_voucher_offer_returns_it_to_the_seller(client, db_session, auth_as):
    seller = await make_user(db_session)
    buyer = await make_user(db_session, balance=100)
    voucher = await _make_voucher(db_session, seller, days=7)
    auth_as(seller)
    sell = await client.post(f"/api/cases/vouchers/{voucher.id}/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "price_coins": 10,
    })
    offer_id = sell.json()["id"]

    auth_as(buyer)
    decline = await client.post(f"/api/cases/voucher-offers/{offer_id}/decline")
    assert decline.status_code == 200
    assert decline.json()["status"] == "declined"

    auth_as(seller)
    vouchers = (await client.get("/api/cases/vouchers")).json()
    assert len(vouchers) == 1 and vouchers[0]["days"] == 7


async def test_cancel_voucher_offer_returns_it_to_the_seller(client, db_session, auth_as):
    seller = await make_user(db_session)
    buyer = await make_user(db_session)
    voucher = await _make_voucher(db_session, seller)
    auth_as(seller)
    sell = await client.post(f"/api/cases/vouchers/{voucher.id}/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "price_coins": 10,
    })
    offer_id = sell.json()["id"]

    cancel = await client.post(f"/api/cases/voucher-offers/{offer_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert len((await client.get("/api/cases/vouchers")).json()) == 1


async def test_voucher_offer_blocked_when_sender_is_trade_banned(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    seller = await make_user(db_session)
    buyer = await make_user(db_session)
    voucher = await _make_voucher(db_session, seller)

    auth_as(admin)
    await client.patch(f"/api/admin/users/{seller.id}/trade-ban", json={"is_trade_banned": True})

    auth_as(seller)
    resp = await client.post(f"/api/cases/vouchers/{voucher.id}/sell", json={
        "receiver_wallet_id": buyer.wallet.wallet_id, "price_coins": 10,
    })
    assert resp.status_code == 403
