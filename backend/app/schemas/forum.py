import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ForumCategoryOut(BaseModel):
    key: str
    name: str
    description: str
    model_config = {"from_attributes": True}


class ForumPostOut(BaseModel):
    id: uuid.UUID
    author_username: str | None = None
    author_id: uuid.UUID
    body: str
    created_at: datetime


class ForumThreadPreview(BaseModel):
    id: uuid.UUID
    title: str
    author_username: str | None = None
    author_id: uuid.UUID
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
    posts: list[ForumPostOut]


class CreateThreadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    body: str = Field(..., min_length=1, max_length=4000)


class CreatePostRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
