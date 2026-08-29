import logging
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import AdminUser, DBSession
from backend.app.db.models import (
    BuyTagModel,
    GrenadeModel,
    ImageModel,
    MapModel,
    PlayerPathModel,
    PromoCodeModel,
    StrategyModel,
    TransactionModel,
    UserModel,
    WalletModel,
)
from backend.app.schemas.strategy import (
    AdminStrategiesListResponse,
    MapCreate,
    MapResponse,
    MapsListResponse,
    MapUpdate,
    PromoCodeCreate,
    PromoCodeOut,
    PromoCodesListResponse,
    PromoCodeToggle,
    StrategyCreate,
    StrategyDetailResponse,
    StrategyUpdate,
)
from backend.app.schemas.user import AdminGrantSubscriptionRequest, SetAdminRequest, UserAdminOut, UsersListResponse
from backend.app.schemas.wallet import TransactionsListResponse
from backend.app.services.notifications import notify_favorited_map_users
from backend.app.services.referral import generate_promo_code
from backend.app.services.subscription import extend_subscription

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin/stats")
async def get_admin_stats(db: DBSession, admin_user: AdminUser) -> dict:
    """High-level counts for the admin dashboard tiles."""
    users_count = (await db.execute(select(func.count()).select_from(UserModel))).scalar() or 0
    strategies_count = (await db.execute(select(func.count()).select_from(StrategyModel))).scalar() or 0
    maps_count = (await db.execute(select(func.count()).select_from(MapModel))).scalar() or 0
    transactions_count = (await db.execute(select(func.count()).select_from(TransactionModel))).scalar() or 0

    now = datetime.now(timezone.utc)
    active_subscriptions_count = (
        await db.execute(
            select(func.count()).select_from(WalletModel).where(
                or_(WalletModel.is_lifetime.is_(True), WalletModel.subscription_expires_at > now)
            )
        )
    ).scalar() or 0

    return {
        "users_count": users_count,
        "strategies_count": strategies_count,
        "maps_count": maps_count,
        "transactions_count": transactions_count,
        "active_subscriptions_count": active_subscriptions_count,
    }


# ─────────────────────────────────────────────
#  Maps
# ─────────────────────────────────────────────

@router.get("/admin/maps", response_model=MapsListResponse)
async def admin_list_maps(
    db: DBSession,
    admin_user: AdminUser,
    search: str | None = Query(None),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = select(MapModel)
    count_query = select(func.count()).select_from(MapModel)

    if search:
        query = query.where(MapModel.name.ilike(f"%{search}%"))
        count_query = count_query.where(MapModel.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(MapModel.id).limit(limit).offset(offset))
    return MapsListResponse(total=total, maps=result.scalars().all())


@router.post("/admin/maps", response_model=MapResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_map(payload: MapCreate, db: DBSession, admin_user: AdminUser):
    existing = await db.execute(select(MapModel).where(MapModel.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A map with this name already exists")

    map_ = MapModel(**payload.model_dump())
    db.add(map_)
    await db.commit()
    await db.refresh(map_)
    return map_


@router.patch("/admin/maps/{map_id}", response_model=MapResponse)
async def admin_update_map(map_id: int, payload: MapUpdate, db: DBSession, admin_user: AdminUser):
    map_ = await db.get(MapModel, map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(map_, field, value)

    await db.commit()
    await db.refresh(map_)
    return map_


# ─────────────────────────────────────────────
#  Strategies
# ─────────────────────────────────────────────

async def _resolve_buy_tags(db, tag_ids: list[int]) -> list[BuyTagModel]:
    if not tag_ids:
        return []
    result = await db.execute(select(BuyTagModel).where(BuyTagModel.id.in_(tag_ids)))
    tags = result.scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more buy_tag_ids are invalid")
    return tags


def _strategy_detail_query():
    return select(StrategyModel).options(
        selectinload(StrategyModel.buy_tags),
        selectinload(StrategyModel.images),
        selectinload(StrategyModel.grenades),
        selectinload(StrategyModel.player_paths),
    )


def _hydrate_preview(strategy: StrategyModel) -> StrategyDetailResponse:
    sorted_images = sorted(strategy.images, key=lambda i: i.order)
    detail = StrategyDetailResponse.model_validate(strategy)
    detail.main_image_url = sorted_images[0].image_url if sorted_images else None
    return detail


@router.get("/admin/strategies", response_model=AdminStrategiesListResponse)
async def admin_list_strategies(
    db: DBSession,
    admin_user: AdminUser,
    map_id: int | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = _strategy_detail_query().order_by(StrategyModel.created_at.desc())
    count_query = select(func.count()).select_from(StrategyModel)

    if map_id is not None:
        query = query.where(StrategyModel.map_id == map_id)
        count_query = count_query.where(StrategyModel.map_id == map_id)
    if search:
        query = query.where(StrategyModel.title.ilike(f"%{search}%"))
        count_query = count_query.where(StrategyModel.title.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    strategies = result.scalars().unique().all()
    return AdminStrategiesListResponse(total=total, strategies=[_hydrate_preview(s) for s in strategies])


@router.post("/admin/strategies", response_model=StrategyDetailResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_strategy(payload: StrategyCreate, db: DBSession, admin_user: AdminUser):
    map_ = await db.get(MapModel, payload.map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="map_id does not exist")

    buy_tags = await _resolve_buy_tags(db, payload.buy_tag_ids)

    strategy = StrategyModel(
        map_id=payload.map_id,
        title=payload.title,
        side=payload.side,
        plant=payload.plant,
        speed=payload.speed,
        difficulty_stars=payload.difficulty_stars,
        success_rate=payload.success_rate,
        author=payload.author,
        is_free=payload.is_free,
        roles_description=payload.roles_description,
        timings_description=payload.timings_description,
        annotations=payload.annotations.model_dump(),
        buy_tags=buy_tags,
        grenades=[GrenadeModel(**g.model_dump()) for g in payload.grenades],
        images=[ImageModel(**i.model_dump()) for i in payload.images],
        player_paths=[PlayerPathModel(**p.model_dump()) for p in payload.player_paths],
    )
    db.add(strategy)
    await db.commit()

    try:
        await notify_favorited_map_users(db, map_.id, map_.name, strategy.title)
    except Exception:
        logger.exception("Failed to notify favorited-map users for strategy_id=%s", strategy.id)

    result = await db.execute(_strategy_detail_query().where(StrategyModel.id == strategy.id))
    return _hydrate_preview(result.scalar_one())


@router.patch("/admin/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def admin_update_strategy(strategy_id: uuid.UUID, payload: StrategyUpdate, db: DBSession, admin_user: AdminUser):
    result = await db.execute(_strategy_detail_query().where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    map_ = await db.get(MapModel, payload.map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="map_id does not exist")

    buy_tags = await _resolve_buy_tags(db, payload.buy_tag_ids)

    strategy.map_id = payload.map_id
    strategy.title = payload.title
    strategy.side = payload.side
    strategy.plant = payload.plant
    strategy.speed = payload.speed
    strategy.difficulty_stars = payload.difficulty_stars
    strategy.success_rate = payload.success_rate
    strategy.author = payload.author
    strategy.is_free = payload.is_free
    strategy.roles_description = payload.roles_description
    strategy.timings_description = payload.timings_description
    strategy.annotations = payload.annotations.model_dump()
    strategy.buy_tags = buy_tags
    # Reassigning the collections triggers delete-orphan cleanup on the rows
    # that dropped out, and inserts the new ones — a full replace per submit.
    strategy.grenades = [GrenadeModel(**g.model_dump()) for g in payload.grenades]
    strategy.images = [ImageModel(**i.model_dump()) for i in payload.images]
    strategy.player_paths = [PlayerPathModel(**p.model_dump()) for p in payload.player_paths]

    await db.commit()

    result = await db.execute(_strategy_detail_query().where(StrategyModel.id == strategy_id))
    return _hydrate_preview(result.scalar_one())


@router.delete("/admin/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_strategy(strategy_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    strategy = await db.get(StrategyModel, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    await db.delete(strategy)
    await db.commit()


@router.get("/admin/buy-tags")
async def admin_list_buy_tags(db: DBSession, admin_user: AdminUser):
    result = await db.execute(select(BuyTagModel).order_by(BuyTagModel.id))
    return [{"id": t.id, "name": t.name} for t in result.scalars().all()]


# ─────────────────────────────────────────────
#  Promo codes
# ─────────────────────────────────────────────

@router.get("/admin/promo-codes", response_model=PromoCodesListResponse)
async def admin_list_promo_codes(
    db: DBSession,
    admin_user: AdminUser,
    search: str | None = Query(None, description="Matches the promo code"),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = select(PromoCodeModel)
    count_query = select(func.count()).select_from(PromoCodeModel)

    if search:
        query = query.where(PromoCodeModel.code.ilike(f"%{search}%"))
        count_query = count_query.where(PromoCodeModel.code.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(PromoCodeModel.code).limit(limit).offset(offset))
    return PromoCodesListResponse(total=total, promo_codes=result.scalars().all())


@router.post("/admin/promo-codes", response_model=PromoCodeOut, status_code=status.HTTP_201_CREATED)
async def admin_create_promo_code(payload: PromoCodeCreate, db: DBSession, admin_user: AdminUser):
    code = (payload.code or generate_promo_code()).strip().upper()

    existing = await db.execute(select(PromoCodeModel).where(PromoCodeModel.code == code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This code already exists")

    promo = PromoCodeModel(
        code=code,
        coin_reward=payload.coin_reward,
        activations_limit=payload.activations_limit,
        is_active=True,
        used_count=0,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


@router.patch("/admin/promo-codes/{promo_id}", response_model=PromoCodeOut)
async def admin_toggle_promo_code(promo_id: uuid.UUID, payload: PromoCodeToggle, db: DBSession, admin_user: AdminUser):
    promo = await db.get(PromoCodeModel, promo_id)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    promo.is_active = payload.is_active
    await db.commit()
    await db.refresh(promo)
    return promo


# ─────────────────────────────────────────────
#  Users
# ─────────────────────────────────────────────

@router.get("/admin/users", response_model=UsersListResponse)
async def admin_list_users(
    db: DBSession,
    admin_user: AdminUser,
    search: str | None = Query(None, description="Matches username or wallet ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(UserModel).options(selectinload(UserModel.wallet)).order_by(UserModel.created_at.desc())
    count_query = select(func.count()).select_from(UserModel)

    if search:
        query = query.join(UserModel.wallet).where(
            or_(UserModel.username.ilike(f"%{search}%"), WalletModel.wallet_id.ilike(f"%{search}%"))
        )
        count_query = count_query.join(UserModel.wallet).where(
            or_(UserModel.username.ilike(f"%{search}%"), WalletModel.wallet_id.ilike(f"%{search}%"))
        )

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    users = result.scalars().all()

    return UsersListResponse(total=total, users=users)


@router.patch("/admin/users/{user_id}/admin", response_model=UserAdminOut)
async def admin_set_user_admin(user_id: uuid.UUID, payload: SetAdminRequest, db: DBSession, admin_user: AdminUser):
    if user_id == admin_user.id and not payload.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't remove your own admin access")

    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_admin = payload.is_admin
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/subscription", response_model=UserAdminOut)
async def admin_grant_subscription(
    user_id: uuid.UUID, payload: AdminGrantSubscriptionRequest, db: DBSession, admin_user: AdminUser
):
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.months == 0:
        extend_subscription(user.wallet, "lifetime", None)
    else:
        extend_subscription(user.wallet, "premium", payload.months)

    await db.commit()
    await db.refresh(user)
    return user


# ─────────────────────────────────────────────
#  Transactions (P2P monitoring, MasterCoins stats)
# ─────────────────────────────────────────────

@router.get("/admin/transactions", response_model=TransactionsListResponse)
async def admin_list_transactions(
    db: DBSession,
    admin_user: AdminUser,
    transaction_type: str | None = Query(None, description="Filter by type, e.g. p2p_transfer"),
    wallet_id: str | None = Query(None, description="Matches either side of the transfer"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(TransactionModel).order_by(TransactionModel.created_at.desc())
    count_query = select(func.count()).select_from(TransactionModel)

    if transaction_type:
        query = query.where(TransactionModel.transaction_type == transaction_type)
        count_query = count_query.where(TransactionModel.transaction_type == transaction_type)
    if wallet_id:
        wid = wallet_id.strip().upper()
        condition = or_(TransactionModel.sender_wallet_id == wid, TransactionModel.receiver_wallet_id == wid)
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    transactions = result.scalars().all()

    return TransactionsListResponse(total=total, transactions=transactions)
