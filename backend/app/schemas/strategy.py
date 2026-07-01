import uuid
from pydantic import BaseModel
from typing import List, Optional
from backend.app.db.models import SideEnum, SpeedEnum


class MapResponse(BaseModel):
    id: int
    name: str
    is_active: bool

    class Config:
        from_attributes = True


class StrategyPreviewResponse(BaseModel):
    id: uuid.UUID
    map_id: int
    title: str
    side: SideEnum
    speed: SpeedEnum
    main_image_url: Optional[str] = None

    class Config:
        from_attributes = True
