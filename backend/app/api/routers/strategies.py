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
    MapResponse, StrategyDetailResponse, StrategiesListResponse, StrategyPreviewResponse, ImageOut, GrenadeOut
)
from backend.app.services.strategy import has_active_subscription

router = APIRouter()


@router.get("/maps", response_model=List[MapResponse])
async def get_maps(db: DBSession):
    result = await db.execute(select(MapModel).where(MapModel.is_active == True).order_by(MapModel.id))
    return result.scalars().all()


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
):
    query = (
        select(StrategyModel)
        .options(
            selectinload(StrategyModel.buy_tags),
            selectinload(StrategyModel.images),
        )
        .order_by(StrategyModel.created_at.desc())
    )

    if map_id is not None: query = query.where(StrategyModel.map_id == map_id)
    if side: query = query.where(StrategyModel.side.in_(side))
    if plant: query = query.where(StrategyModel.plant.in_(plant))
    if speed: query = query.where(StrategyModel.speed.in_(speed))
    if is_free is not None: query = query.where(StrategyModel.is_free == is_free)
    if search: query = query.where(StrategyModel.title.ilike(f"%{search}%"))

    if buy_tags:
        query = query.join(StrategyModel.buy_tags).where(BuyTagModel.name.in_(buy_tags))

    result = await db.execute(query)
    strategies = result.scalars().unique().all()

    out = []
    for s in strategies:
        sorted_images = sorted(s.images, key=lambda i: i.order)
        preview = StrategyPreviewResponse.model_validate(s)
        preview.main_image_url = sorted_images[0].image_url if sorted_images else None
        out.append(preview)

    return StrategiesListResponse(total=len(out), strategies=out)


@router.get("/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy_detail(strategy_id: uuid.UUID, db: DBSession, current_user: OptionalUser):
    result = await db.execute(
        select(StrategyModel)
        .options(
            selectinload(StrategyModel.buy_tags),
            selectinload(StrategyModel.images),
            selectinload(StrategyModel.grenades),
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

    return detail