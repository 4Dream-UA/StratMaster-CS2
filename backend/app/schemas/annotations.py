from pydantic import BaseModel, Field


class DrawingPoint(BaseModel):
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)


class Drawing(BaseModel):
    points: list[DrawingPoint] = Field(..., min_length=2)
    color: str = Field("#ff9a00", max_length=16)


class MapNote(BaseModel):
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)
    text: str = Field(..., min_length=1, max_length=200)


class BombMarker(BaseModel):
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)
    # When the bomb is planted, in seconds from round start. Null means it
    # was authored before this field existed and shows for the whole replay;
    # a C4 sitting on the site from second zero is wrong for every strategy
    # that isn't a post-plant.
    t: float | None = Field(None, ge=0)


class Annotations(BaseModel):
    """Freeform overlay on top of the structured paths/grenades — arbitrary
    lines, text notes, and a single C4 marker. Shared between admin-authored
    strategies and personal boards, both of which embed one of these."""
    drawings: list[Drawing] = []
    notes: list[MapNote] = []
    bomb: BombMarker | None = None
