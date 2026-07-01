from fastapi import APIRouter, Depends
from sqlalchemy import select
from typing import List

from backend.app.api.deps import DBSession
from backend.app.db.models import MapModel, StrategyModel, ImageModel
from backend.app.schemas.strategy import MapResponse, StrategyPreviewResponse

router = APIRouter()


@router.get("/maps", response_model=List[MapResponse])
async def get_maps(db: DBSession):
    """
    Fetch all active maps for the frontend grid.
    """
    result = await db.execute(
        select(MapModel).where(MapModel.is_active == True)
    )
    return result.scalars().all()


@router.get("", response_model=List[StrategyPreviewResponse])
async def get_strategies(
        db: DBSession,
        map_id: int | None = None,
        side: str | None = None,
):
    """
    Fetch strategies feed with optional filters (map_id, side).
    """
    query = select(StrategyModel)

    if map_id:
        query = query.where(StrategyModel.map_id == map_id)
    if side:
        query = query.where(StrategyModel.side == side)

    result = await db.execute(query)
    strategies = result.scalars().all()

    # TODO: In the future, optimize this with selectinload for main_image_url
    return strategies
