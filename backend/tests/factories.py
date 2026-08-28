import uuid
from datetime import datetime, timedelta, timezone

from backend.app.db.models import CaseModel, MapModel, StrategyModel, UserModel, WalletModel
from backend.app.services.referral import generate_wallet_id


async def make_user(db_session, *, telegram_id=None, is_admin=False, subscribed=False, ref_discount=False, balance=0):
    user = UserModel(
        telegram_id=telegram_id or int(uuid.uuid4().int % 10**9),
        username=f"user_{uuid.uuid4().hex[:8]}",
        is_admin=is_admin,
    )
    db_session.add(user)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    wallet = WalletModel(
        user_id=user.id,
        wallet_id=generate_wallet_id(),
        balance_coins=balance,
        subscription_expires_at=(now + timedelta(days=30)) if subscribed else None,
        ref_discount_expires_at=(now + timedelta(hours=24)) if ref_discount else None,
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(user)
    user.wallet = wallet
    return user


async def make_map(db_session, *, name=None, is_active=True):
    map_ = MapModel(name=name or f"Map_{uuid.uuid4().hex[:6]}", is_active=is_active)
    db_session.add(map_)
    await db_session.commit()
    await db_session.refresh(map_)
    return map_


async def make_strategy(db_session, *, map_id, is_free=False, title=None, with_children=False):
    strategy = StrategyModel(
        map_id=map_id,
        title=title or f"Strategy {uuid.uuid4().hex[:6]}",
        side="T_side",
        plant="A",
        speed="fast",
        difficulty_stars=3,
        success_rate=80,
        is_free=is_free,
    )
    if with_children:
        from backend.app.db.models import GrenadeModel, ImageModel
        strategy.images = [ImageModel(image_url="https://example.com/main.png", order=0)]
        strategy.grenades = [GrenadeModel(grenade_type="Smoke", target="Window", timing="0:08", order=0)]

    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


async def make_case(db_session, *, name="Test Case", cost_coins=49, rewards=None, is_active=True):
    case_ = CaseModel(
        name=name,
        cost_coins=cost_coins,
        is_active=is_active,
        rewards=rewards or [
            {"coins": 5, "chance_percent": 50},
            {"coins": 100, "chance_percent": 50},
        ],
    )
    db_session.add(case_)
    await db_session.commit()
    await db_session.refresh(case_)
    return case_
