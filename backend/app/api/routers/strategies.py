import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.api.deps import DBSession, OptionalUser
from backend.app.db.models import (
    BuyTagModel, StrategyModel, MapModel, SideEnum, SpeedEnum, PlantEnum
)
from backend.app.schemas.strategy import (
    MapResponse, MapsListResponse, StrategyDetailResponse, StrategiesListResponse, StrategyPreviewResponse,
    ImageOut, GrenadeOut, PlayerPathOut,
)
from backend.app.services.strategy import has_active_subscription

router = APIRouter()


@router.get("/maps", response_model=MapsListResponse)
async def get_maps(
        db: DBSession,
        search: str | None = Query(None),
        limit: int = Query(5, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    query = select(MapModel).where(MapModel.is_active == True)
    count_query = select(func.count()).select_from(MapModel).where(MapModel.is_active == True)

    if search:
        query = query.where(MapModel.name.ilike(f"%{search}%"))
        count_query = count_query.where(MapModel.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(MapModel.id).limit(limit).offset(offset))
    return MapsListResponse(total=total, maps=result.scalars().all())


@router.get("/strategies/count")
async def get_strategies_count(db: DBSession) -> dict:
    result = await db.execute(select(func.count()).select_from(StrategyModel))
    return {"count": result.scalar()}


@router.get("/strategies", response_model=StrategiesListResponse)
async def get_strategies_list(
        db: DBSession,
        map_id: int | None = Query(None),
        side: List[str] = Query(default=[]),
        plant: List[str] = Query(default=[]),
        speed: List[str] = Query(default=[]),
        buy_tags: List[str] = Query(default=[]),
        is_free: bool | None = Query(None),
        search: str | None = Query(None),
        limit: int = Query(5, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    query = (
        select(StrategyModel)
        .options(
            selectinload(StrategyModel.buy_tags),
            selectinload(StrategyModel.images),
        )
        .order_by(StrategyModel.created_at.desc())
    )
    count_query = select(func.count(func.distinct(StrategyModel.id))).select_from(StrategyModel)

    if map_id is not None:
        query = query.where(StrategyModel.map_id == map_id)
        count_query = count_query.where(StrategyModel.map_id == map_id)
    if side:
        query = query.where(StrategyModel.side.in_(side))
        count_query = count_query.where(StrategyModel.side.in_(side))
    if plant:
        query = query.where(StrategyModel.plant.in_(plant))
        count_query = count_query.where(StrategyModel.plant.in_(plant))
    if speed:
        query = query.where(StrategyModel.speed.in_(speed))
        count_query = count_query.where(StrategyModel.speed.in_(speed))
    if is_free is not None:
        query = query.where(StrategyModel.is_free == is_free)
        count_query = count_query.where(StrategyModel.is_free == is_free)
    if search:
        query = query.where(StrategyModel.title.ilike(f"%{search}%"))
        count_query = count_query.where(StrategyModel.title.ilike(f"%{search}%"))

    if buy_tags:
        query = query.join(StrategyModel.buy_tags).where(BuyTagModel.name.in_(buy_tags))
        count_query = count_query.join(StrategyModel.buy_tags).where(BuyTagModel.name.in_(buy_tags))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    strategies = result.scalars().unique().all()

    out = []
    for s in strategies:
        sorted_images = sorted(s.images, key=lambda i: i.order)
        preview = StrategyPreviewResponse.model_validate(s)
        preview.main_image_url = sorted_images[0].image_url if sorted_images else None
        out.append(preview)

    return StrategiesListResponse(total=total, strategies=out)


@router.get("/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy_detail(strategy_id: uuid.UUID, db: DBSession, current_user: OptionalUser):
    result = await db.execute(
        select(StrategyModel)
        .options(
            selectinload(StrategyModel.buy_tags),
            selectinload(StrategyModel.images),
            selectinload(StrategyModel.grenades),
            selectinload(StrategyModel.player_paths),
        )
        .where(StrategyModel.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if not strategy.is_free:
        if current_user is None:
            raise HTTPException(
                status_code=401,
                detail="Sign in to view this strategy",
            )
        if not has_active_subscription(current_user):
            raise HTTPException(
                status_code=403,
                detail="An active subscription is required to view this strategy",
            )

    sorted_images = sorted(strategy.images, key=lambda i: i.order)
    detail = StrategyDetailResponse.model_validate(strategy)
    detail.main_image_url = sorted_images[0].image_url if sorted_images else None
    detail.images = [ImageOut.model_validate(i) for i in sorted_images]
    detail.grenades = [GrenadeOut.model_validate(g) for g in sorted(strategy.grenades, key=lambda g: g.order)]
    detail.player_paths = [PlayerPathOut.model_validate(p) for p in sorted(strategy.player_paths, key=lambda p: p.order)]

    return detail