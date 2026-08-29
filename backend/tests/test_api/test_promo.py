from backend.app.db.models import CaseInventoryModel, PromoCodeModel
from backend.tests.factories import make_case, make_user
from sqlalchemy import select


async def _make_promo(db_session, *, code="WELCOME25", coin_reward=25, activations_limit=100):
    promo = PromoCodeModel(code=code, coin_reward=coin_reward, activations_limit=activations_limit, used_count=0)
    db_session.add(promo)
    await db_session.commit()
    return promo


async def test_redeem_promo_code_credits_balance(client, db_session, auth_as):
    user = await make_user(db_session, balance=10)
    auth_as(user)
    await _make_promo(db_session, coin_reward=25)

    resp = await client.post("/api/promo/redeem", json={"code": "welcome25"})  # lowercase — must still match
    assert resp.status_code == 200
    body = resp.json()
    assert body["coins_awarded"] == 25
    assert body["new_balance"] == 35


async def test_redeem_same_code_twice_is_rejected(client, db_session, auth_as):
    user = await make_user(db_session, balance=0)
    auth_as(user)
    await _make_promo(db_session, coin_reward=10)

    first = await client.post("/api/promo/redeem", json={"code": "WELCOME25"})
    assert first.status_code == 200

    second = await client.post("/api/promo/redeem", json={"code": "WELCOME25"})
    assert second.status_code == 400


async def test_redeem_unknown_code_returns_404(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)

    resp = await client.post("/api/promo/redeem", json={"code": "DOESNOTEXIST"})
    assert resp.status_code == 404


async def test_redeem_respects_activation_limit(client, db_session, auth_as):
    await _make_promo(db_session, code="LIMITED", coin_reward=5, activations_limit=1)

    first_user = await make_user(db_session)
    auth_as(first_user)
    first = await client.post("/api/promo/redeem", json={"code": "LIMITED"})
    assert first.status_code == 200

    second_user = await make_user(db_session)
    auth_as(second_user)
    second = await client.post("/api/promo/redeem", json={"code": "LIMITED"})
    # The first redemption already exhausted and deactivated the code, so
    # this now hits the is_active check (404) rather than the activations
    # limit check (400) — both are "you can't use this code" from the
    # caller's perspective.
    assert second.status_code == 404


async def test_redeem_deactivates_code_once_limit_is_reached(client, db_session, auth_as):
    promo = await _make_promo(db_session, code="ONESHOT", coin_reward=5, activations_limit=1)
    assert promo.is_active is True

    user = await make_user(db_session)
    auth_as(user)
    resp = await client.post("/api/promo/redeem", json={"code": "ONESHOT"})
    assert resp.status_code == 200

    await db_session.refresh(promo)
    assert promo.is_active is False


async def test_redeem_premium_days_promo_extends_subscription(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    promo = PromoCodeModel(code="PREMIUM30", coin_reward=0, reward_type="premium", premium_days=30, activations_limit=100, used_count=0)
    db_session.add(promo)
    await db_session.commit()

    resp = await client.post("/api/promo/redeem", json={"code": "PREMIUM30"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reward_type"] == "premium"
    assert body["premium_days"] == 30
    assert body["is_lifetime"] is False
    assert body["new_subscription_expires_at"] is not None


async def test_redeem_zero_days_premium_promo_grants_lifetime(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    promo = PromoCodeModel(code="FOREVER", coin_reward=0, reward_type="premium", premium_days=0, activations_limit=100, used_count=0)
    db_session.add(promo)
    await db_session.commit()

    resp = await client.post("/api/promo/redeem", json={"code": "FOREVER"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_lifetime"] is True


async def test_redeem_case_promo_adds_to_inventory(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    case = await make_case(db_session, name="Promo Case")
    promo = PromoCodeModel(
        code="FREECASE", coin_reward=0, reward_type="case", case_id=case.id, case_quantity=2,
        activations_limit=100, used_count=0,
    )
    db_session.add(promo)
    await db_session.commit()

    resp = await client.post("/api/promo/redeem", json={"code": "FREECASE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reward_type"] == "case"
    assert body["case_quantity"] == 2
    assert body["case_name"] == "Promo Case"

    result = await db_session.execute(
        select(CaseInventoryModel).where(CaseInventoryModel.user_id == user.id, CaseInventoryModel.case_id == case.id)
    )
    assert len(result.scalars().all()) == 2


async def test_redeem_case_promo_rejects_when_case_deactivated(client, db_session, auth_as):
    user = await make_user(db_session)
    auth_as(user)
    case = await make_case(db_session, name="Retired Case", is_active=False)
    promo = PromoCodeModel(
        code="DEADCASE", coin_reward=0, reward_type="case", case_id=case.id, case_quantity=1,
        activations_limit=100, used_count=0,
    )
    db_session.add(promo)
    await db_session.commit()

    resp = await client.post("/api/promo/redeem", json={"code": "DEADCASE"})
    assert resp.status_code == 400
