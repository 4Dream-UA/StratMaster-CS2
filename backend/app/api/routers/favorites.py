import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.db.models import FavoriteMapModel, FavoriteStrategyModel, MapModel, StrategyModel
from backend.app.schemas.strategy import MapResponse, StrategyPreviewResponse

router = APIRouter()


class FavoriteToggleResponse(BaseModel):
    map_id: int
    favorited: bool


class FavoriteStrategyToggleResponse(BaseModel):
    strategy_id: uuid.UUID
    favorited: bool


@router.get("/favorites", response_model=List[MapResponse])
async def list_favorite_maps(db: DBSession, current_user: CurrentUser):
    result = await db.execute(
        select(MapModel)
        .join(FavoriteMapModel, FavoriteMapModel.map_id == MapModel.id)
        .where(FavoriteMapModel.user_id == current_user.id)
        .order_by(MapModel.name)
    )
    return result.scalars().all()


@router.post("/favorites/{map_id}", response_model=FavoriteToggleResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite_map(map_id: int, db: DBSession, current_user: CurrentUser):
    map_ = await db.get(MapModel, map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")

    existing = await db.execute(
        select(FavoriteMapModel).where(
            FavoriteMapModel.user_id == current_user.id, FavoriteMapModel.map_id == map_id
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(FavoriteMapModel(user_id=current_user.id, map_id=map_id))
        await db.commit()

    return FavoriteToggleResponse(map_id=map_id, favorited=True)


@router.delete("/favorites/{map_id}", response_model=FavoriteToggleResponse)
async def remove_favorite_map(map_id: int, db: DBSession, current_user: CurrentUser):
    result = await db.execute(
        select(FavoriteMapModel).where(
            FavoriteMapModel.user_id == current_user.id, FavoriteMapModel.map_id == map_id
        )
    )
    favorite = result.scalar_one_or_none()
    if favorite is not None:
        await db.delete(favorite)
        await db.commit()

    return FavoriteToggleResponse(map_id=map_id, favorited=False)


# ─────────────────────────────────────────────
#  Favorite strategies (separate from favorite maps — you might bookmark
#  one specific execute without following the whole map)
# ─────────────────────────────────────────────

@router.get("/favorites/strategies", response_model=List[StrategyPreviewResponse])
async def list_favorite_strategies(db: DBSession, current_user: CurrentUser):
    result = await db.execute(
        select(StrategyModel)
        .join(FavoriteStrategyModel, FavoriteStrategyModel.strategy_id == StrategyModel.id)
        .where(FavoriteStrategyModel.user_id == current_user.id)
        .options(selectinload(StrategyModel.buy_tags), selectinload(StrategyModel.images))
        .order_by(FavoriteStrategyModel.created_at.desc())
    )
    strategies = result.scalars().unique().all()

    out = []
    for s in strategies:
        sorted_images = sorted(s.images, key=lambda i: i.order)
        preview = StrategyPreviewResponse.model_validate(s)
        preview.main_image_url = sorted_images[0].image_url if sorted_images else None
        out.append(preview)
    return out


@router.post(
    "/favorites/strategies/{strategy_id}",
    response_model=FavoriteStrategyToggleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite_strategy(strategy_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    strategy = await db.get(StrategyModel, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    existing = await db.execute(
        select(FavoriteStrategyModel).where(
            FavoriteStrategyModel.user_id == current_user.id, FavoriteStrategyModel.strategy_id == strategy_id
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(FavoriteStrategyModel(user_id=current_user.id, strategy_id=strategy_id))
        await db.commit()

    return FavoriteStrategyToggleResponse(strategy_id=strategy_id, favorited=True)


@router.delete("/favorites/strategies/{strategy_id}", response_model=FavoriteStrategyToggleResponse)
async def remove_favorite_strategy(strategy_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    result = await db.execute(
        select(FavoriteStrategyModel).where(
            FavoriteStrategyModel.user_id == current_user.id, FavoriteStrategyModel.strategy_id == strategy_id
        )
    )
    favorite = result.scalar_one_or_none()
    if favorite is not None:
        await db.delete(favorite)
        await db.commit()

    return FavoriteStrategyToggleResponse(strategy_id=strategy_id, favorited=False)
