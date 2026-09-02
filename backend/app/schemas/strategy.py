import uuid
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from backend.app.db.models import GrenadeTypeEnum, PlantEnum, SideEnum, SpeedEnum
from backend.app.schemas.annotations import Annotations


class MapResponse(BaseModel):
    id: int
    name: str
    cover_image_url: str | None = None
    is_active: bool
    model_config = {"from_attributes": True}


class MapsListResponse(BaseModel):
    total: int
    maps: list[MapResponse]


class BuyTagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class ImageOut(BaseModel):
    id: uuid.UUID
    image_url: str
    order: int
    model_config = {"from_attributes": True}


class TrajectoryPoint(BaseModel):
    """One bend in a grenade's flight, as a percentage of the map image."""
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)


class GrenadeOut(BaseModel):
    id: uuid.UUID
    grenade_type: GrenadeTypeEnum
    target: str
    timing: str
    video_url: str | None = None
    order: int
    from_x: float | None = None
    from_y: float | None = None
    to_x: float | None = None
    to_y: float | None = None
    # Seconds from round start. Null falls back to parsing `timing` with a
    # fixed flight time, so grenades authored before these existed still play.
    throw_at: float | None = Field(None, ge=0)
    lands_at: float | None = Field(None, ge=0)
    # Two or more points lets a throw bank off a wall; null arcs straight
    # from from_/to_ as before.
    trajectory: list[TrajectoryPoint] | None = Field(None, min_length=2)
    model_config = {"from_attributes": True}


class Waypoint(BaseModel):
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)
    t: float = Field(..., ge=0, description="Seconds from round start")


class PlayerPathOut(BaseModel):
    id: uuid.UUID
    label: str
    color: str
    waypoints: list[Waypoint]
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
    # Included so the page doesn't have to pull the entire map list just to
    # turn map_id into a breadcrumb label.
    map_name: str | None = None
    roles_description: str | None = None
    timings_description: str | None = None
    images: list[ImageOut] = []
    grenades: list[GrenadeOut] = []
    player_paths: list[PlayerPathOut] = []
    annotations: Annotations = Annotations()
    created_at: datetime


class StrategiesListResponse(BaseModel):
    total: int
    strategies: list[StrategyPreviewResponse]


class AdminStrategiesListResponse(BaseModel):
    total: int
    strategies: list[StrategyDetailResponse]


# ── Admin / Create schemas ─────────────────────────────────────
class GrenadeCreate(BaseModel):
    grenade_type: GrenadeTypeEnum
    target: str = Field(..., max_length=64)
    timing: str = Field(..., max_length=16)
    video_url: str | None = Field(None, max_length=512)
    order: int = Field(0, ge=0)
    from_x: float | None = Field(None, ge=0, le=100)
    from_y: float | None = Field(None, ge=0, le=100)
    to_x: float | None = Field(None, ge=0, le=100)
    to_y: float | None = Field(None, ge=0, le=100)
    # Seconds from round start. Null falls back to parsing `timing` with a
    # fixed flight time, so grenades authored before these existed still play.
    throw_at: float | None = Field(None, ge=0)
    lands_at: float | None = Field(None, ge=0)
    # Two or more points lets a throw bank off a wall; null arcs straight
    # from from_/to_ as before.
    trajectory: list[TrajectoryPoint] | None = Field(None, min_length=2)


class ImageCreate(BaseModel):
    image_url: str = Field(..., max_length=512)
    order: int = Field(0, ge=0)


class PlayerPathCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=32)
    color: str = Field("#ff9a00", max_length=16)
    waypoints: list[Waypoint] = Field(..., min_length=2)
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
    annotations: Annotations = Annotations()
    buy_tag_ids: list[int] = []
    grenades: list[GrenadeCreate] = []
    images: list[ImageCreate] = []
    player_paths: list[PlayerPathCreate] = []


# StrategyCreate covers full replace-on-edit too — the admin UI always
# submits the complete strategy (incl. grenades/images), so update reuses
# the same shape instead of a separate partial-patch schema.
StrategyUpdate = StrategyCreate


class MapCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    cover_image_url: str | None = Field(None, max_length=512)
    is_active: bool = True


class MapUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    cover_image_url: str | None = Field(None, max_length=512)
    is_active: bool | None = None


class PromoCodeCreate(BaseModel):
    code: str | None = Field(None, min_length=4, max_length=32, description="Leave empty to auto-generate")
    reward_type: str = Field("coins", pattern="^(coins|premium|case)$")
    coin_reward: int = Field(0, ge=0, description="Required (>0) when reward_type is 'coins'")
    premium_days: int | None = Field(None, ge=0, description="Required when reward_type is 'premium'. 0 = lifetime")
    case_id: uuid.UUID | None = Field(None, description="Required when reward_type is 'case'")
    case_quantity: int = Field(1, gt=0)
    activations_limit: int = Field(100, gt=0)

    @model_validator(mode="after")
    def _validate_reward_fields(self):
        if self.reward_type == "coins" and self.coin_reward <= 0:
            raise ValueError("coin_reward must be greater than 0 for a coins reward")
        if self.reward_type == "premium" and self.premium_days is None:
            raise ValueError("premium_days is required for a premium reward")
        if self.reward_type == "case" and self.case_id is None:
            raise ValueError("case_id is required for a case reward")
        return self


class PromoCodeToggle(BaseModel):
    is_active: bool


class PromoCodeOut(BaseModel):
    id: uuid.UUID
    code: str
    reward_type: str
    coin_reward: int
    premium_days: int | None
    case_id: uuid.UUID | None
    case_quantity: int
    case_name: str | None = None
    is_active: bool
    activations_limit: int
    used_count: int
    model_config = {"from_attributes": True}


class PromoCodesListResponse(BaseModel):
    total: int
    promo_codes: list[PromoCodeOut]
    model_config = {"from_attributes": True}