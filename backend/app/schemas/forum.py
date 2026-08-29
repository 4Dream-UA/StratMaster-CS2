import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ForumCategoryOut(BaseModel):
    key: str
    name: str
    description: str
    model_config = {"from_attributes": True}


class UpdateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=256)


class ReplyToOut(BaseModel):
    """A short quoted snippet of the post being replied to, so the frontend
    doesn't need a second lookup just to show "replying to @x: ...."."""
    id: uuid.UUID
    author_username: str | None = None
    body_snippet: str


class ForumPostOut(BaseModel):
    id: uuid.UUID
    author_username: str | None = None
    author_avatar_url: str | None = None
    author_id: uuid.UUID
    author_is_admin: bool = False
    body: str
    reply_to: ReplyToOut | None = None
    created_at: datetime


class ForumThreadPreview(BaseModel):
    id: uuid.UUID
    title: str
    author_username: str | None = None
    author_avatar_url: str | None = None
    author_id: uuid.UUID
    author_is_admin: bool = False
    is_pinned: bool = False
    is_closed: bool = False
    post_count: int
    updated_at: datetime


class ForumThreadsListResponse(BaseModel):
    total: int
    threads: list[ForumThreadPreview]


class ForumThreadDetail(BaseModel):
    id: uuid.UUID
    category_key: str
    title: str
    author_id: uuid.UUID
    is_pinned: bool = False
    is_closed: bool = False
    is_watching: bool = False
    share_token: str | None = None
    posts: list[ForumPostOut]


class CreateThreadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    body: str = Field(..., min_length=1, max_length=4000)


class CreatePostRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    reply_to_post_id: uuid.UUID | None = None


class UpdateThreadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)


class UpdatePostRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class PinThreadRequest(BaseModel):
    is_pinned: bool


class CloseThreadRequest(BaseModel):
    is_closed: bool


class WatchResponse(BaseModel):
    is_watching: bool


class ShareTokenResponse(BaseModel):
    share_token: str


class SharedThreadResponse(ForumThreadDetail):
    """Same shape as a normal thread detail, for the public unauthenticated
    share-link viewer."""
    pass
