from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.db.models import FavoriteMapModel, MapModel
from backend.app.schemas.strategy import MapResponse

router = APIRouter()


class FavoriteToggleResponse(BaseModel):
    map_id: int
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
