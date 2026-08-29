import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models import GrenadeTypeEnum
from backend.app.schemas.annotations import Annotations
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
    annotations: Annotations = Annotations()


# Same full-replace-on-edit shape as StrategyCreate/StrategyUpdate.
BoardUpdate = PersonalBoardCreate


class PersonalBoardPreview(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID  # the owner — lets the frontend tell "mine" from "shared with me"
    map_id: int
    title: str
    updated_at: datetime
    model_config = {"from_attributes": True}


class PersonalBoardDetail(PersonalBoardPreview):
    created_at: datetime
    share_token: str | None = None
    paths: list[BoardPathOut] = []
    grenades: list[BoardGrenadeOut] = []
    annotations: Annotations = Annotations()


class PersonalBoardsListResponse(BaseModel):
    total: int
    boards: list[PersonalBoardPreview]


class CollaboratorOut(BaseModel):
    id: uuid.UUID
    username: str | None = None
    model_config = {"from_attributes": True}


class AddCollaboratorRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=16)


class ShareTokenResponse(BaseModel):
    share_token: str


class SharedBoardResponse(PersonalBoardDetail):
    """Same shape as a normal board detail, plus the map's name and cover
    image — the public viewer is unauthenticated and has no other way to
    look those up."""
    map_name: str = ""              # filled in by the router after model_validate(board)
    map_cover_image_url: str | None = None
