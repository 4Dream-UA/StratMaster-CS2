import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from backend.app.db.models import GrenadeTypeEnum, PlantEnum, SideEnum, SpeedEnum


class MapResponse(BaseModel):
    id: int
    name: str
    cover_image_url: str | None = None
    is_active: bool
    model_config = {"from_attributes": True}


class BuyTagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class ImageOut(BaseModel):
    id: uuid.UUID
    image_url: str
    order: int
    model_config = {"from_attributes": True}


class GrenadeOut(BaseModel):
    id: uuid.UUID
    grenade_type: GrenadeTypeEnum
    target: str
    timing: str
    video_url: str | None = None
    order: int
    model_config = {"from_attributes": True}


class StrategyPreviewResponse(BaseModel):
    id: uuid.UUID
    title: str
    side: SideEnum
    plant: PlantEnum
    speed: SpeedEnum
    difficulty_stars: int
    success_rate: int
    is_free: bool
    author: str | None = None
    map_id: int
    buy_tags: list[BuyTagOut] = []
    main_image_url: str | None = None
    model_config = {"from_attributes": True}


class StrategyDetailResponse(StrategyPreviewResponse):
    roles_description: str | None = None
    timings_description: str | None = None
    images: list[ImageOut] = []
    grenades: list[GrenadeOut] = []
    created_at: datetime


class StrategiesListResponse(BaseModel):
    total: int
    strategies: list[StrategyPreviewResponse]


# ── Admin / Create schemas ─────────────────────────────────────
class GrenadeCreate(BaseModel):
    grenade_type: GrenadeTypeEnum
    target: str = Field(..., max_length=64)
    timing: str = Field(..., max_length=16)
    video_url: str | None = Field(None, max_length=512)
    order: int = Field(0, ge=0)


class StrategyCreate(BaseModel):
    map_id: int
    title: str = Field(..., min_length=1, max_length=128)
    side: SideEnum
    plant: PlantEnum
    speed: SpeedEnum
    difficulty_stars: int = Field(..., ge=1, le=5)
    success_rate: int = Field(..., ge=1, le=100)
    author: str | None = Field(None, max_length=64)
    is_free: bool = False
    roles_description: str | None = None
    timings_description: str | None = None
    buy_tag_ids: list[int] = []
    grenades: list[GrenadeCreate] = []