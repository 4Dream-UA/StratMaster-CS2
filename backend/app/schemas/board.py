import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models import GrenadeTypeEnum
from backend.app.schemas.strategy import Waypoint


class BoardGrenadeCreate(BaseModel):
    grenade_type: GrenadeTypeEnum
    target: str = Field(..., min_length=1, max_length=64)
    order: int = Field(0, ge=0)
    from_x: float | None = Field(None, ge=0, le=100)
    from_y: float | None = Field(None, ge=0, le=100)
    to_x: float | None = Field(None, ge=0, le=100)
    to_y: float | None = Field(None, ge=0, le=100)


class BoardGrenadeOut(BoardGrenadeCreate):
    id: uuid.UUID
    model_config = {"from_attributes": True}


class BoardPathCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=32)
    color: str = Field("#ff9a00", max_length=16)
    waypoints: list[Waypoint] = Field(..., min_length=2)
    order: int = Field(0, ge=0)


class BoardPathOut(BoardPathCreate):
    id: uuid.UUID
    model_config = {"from_attributes": True}


class PersonalBoardCreate(BaseModel):
    map_id: int
    title: str = Field(..., min_length=1, max_length=64)
    paths: list[BoardPathCreate] = []
    grenades: list[BoardGrenadeCreate] = []


# Same full-replace-on-edit shape as StrategyCreate/StrategyUpdate.
BoardUpdate = PersonalBoardCreate


class PersonalBoardPreview(BaseModel):
    id: uuid.UUID
    map_id: int
    title: str
    updated_at: datetime
    model_config = {"from_attributes": True}


class PersonalBoardDetail(PersonalBoardPreview):
    created_at: datetime
    paths: list[BoardPathOut] = []
    grenades: list[BoardGrenadeOut] = []


class PersonalBoardsListResponse(BaseModel):
    total: int
    boards: list[PersonalBoardPreview]
