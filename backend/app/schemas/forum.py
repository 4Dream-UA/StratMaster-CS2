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
    author_display_name: str | None = None
    body_snippet: str


class ReactionSummary(BaseModel):
    emoji: str
    count: int
    reacted_by_me: bool = False


class VisibleToUserOut(BaseModel):
    id: uuid.UUID
    username: str | None = None
    display_name: str | None = None


class ForumPostOut(BaseModel):
    id: uuid.UUID
    author_username: str | None = None
    author_display_name: str | None = None
    author_avatar_url: str | None = None
    author_id: uuid.UUID
    author_is_admin: bool = False
    # Written by the AI support assistant, not a person — the forum labels
    # these so nobody mistakes an automated first pass for the team's answer.
    author_is_ai: bool = False
    body: str
    reply_to: ReplyToOut | None = None
    reactions: list[ReactionSummary] = []
    created_at: datetime
    edited_at: datetime | None = None
    edited_by_admin: bool = False
    # Only populated for the author and admins — who this whisper is
    # restricted to. Empty/absent means it's a normal, thread-wide post.
    visible_to: list[VisibleToUserOut] = []
    # Soft-delete fields — only ever populated for admins; a deleted post
    # is simply omitted from the list for everyone else.
    deleted_at: datetime | None = None
    deleted_by_username: str | None = None
    # Count of unresolved reports — only ever populated for admins.
    report_count: int = 0


class ReactRequest(BaseModel):
    emoji: str


class ReportPostRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class ReportOut(BaseModel):
    reporter_username: str | None = None
    reporter_display_name: str | None = None
    reason: str | None = None
    created_at: datetime


class PostEditOut(BaseModel):
    previous_body: str
    editor_username: str | None = None
    editor_is_admin: bool = False
    edited_at: datetime


class ReactorOut(BaseModel):
    user_id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False


class ReactorsListResponse(BaseModel):
    total: int
    reactors: list[ReactorOut]


class ForumThreadPreview(BaseModel):
    id: uuid.UUID
    title: str
    author_username: str | None = None
    author_display_name: str | None = None
    author_avatar_url: str | None = None
    author_id: uuid.UUID
    author_is_admin: bool = False
    is_pinned: bool = False
    is_closed: bool = False
    post_count: int
    updated_at: datetime
    # Always 0 for non-admin viewers — reporting is invisible to everyone
    # but the admins who act on it.
    report_count: int = 0


class ForumThreadsListResponse(BaseModel):
    total: int
    threads: list[ForumThreadPreview]


class ForumThreadDetail(BaseModel):
    id: uuid.UUID
    category_key: str
    title: str
    author_id: uuid.UUID
    author_is_admin: bool = False
    is_pinned: bool = False
    is_closed: bool = False
    is_watching: bool = False
    share_token: str | None = None
    report_count: int = 0
    posts: list[ForumPostOut]


class CreateThreadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    body: str = Field(..., min_length=1, max_length=4000)


class CreatePostRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    reply_to_post_id: uuid.UUID | None = None
    # Non-empty = a whisper, visible only to these players (plus the
    # author and any admin) instead of the whole thread.
    visible_to_user_ids: list[uuid.UUID] | None = None


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


# ── Admin moderation queues ──────────────────────────────────────────
# The forum surfaces reports one thread at a time, which is fine when you
# already know where to look and useless as a work queue. These back the
# admin panel's cross-forum lists.


class ReporterOut(BaseModel):
    reporter_username: str | None = None
    reporter_display_name: str | None = None
    reason: str | None = None
    created_at: datetime


class AdminReportOut(BaseModel):
    """One *reported item* — not one report row. Dismissing resolves every
    open report on a post or thread at once, so grouping them here is what
    makes the queue match what the button actually does; three people
    flagging the same message is one job, not three."""
    target_kind: str  # 'post' | 'thread'
    target_id: uuid.UUID
    thread_id: uuid.UUID
    thread_title: str
    category_key: str
    # What was reported: the post body for a post report, the title again
    # for a thread report.
    excerpt: str
    author_username: str | None = None
    author_display_name: str | None = None
    author_id: uuid.UUID
    reports: list[ReporterOut]
    # Most recent of the grouped reports — what the queue sorts on.
    last_reported_at: datetime


class AdminReportsListResponse(BaseModel):
    total: int
    reports: list[AdminReportOut]


class AdminTicketOut(BaseModel):
    id: uuid.UUID
    title: str
    is_closed: bool
    author_id: uuid.UUID
    author_username: str | None = None
    author_display_name: str | None = None
    post_count: int
    # Whether the player wrote the most recent message — i.e. whether the
    # ticket is waiting on a human. The assistant having replied does not
    # clear this: it is not the team.
    awaiting_reply: bool
    # Whether the assistant has already had a go at this one.
    ai_handled: bool = False
    created_at: datetime
    updated_at: datetime


class AdminTicketsListResponse(BaseModel):
    total: int
    tickets: list[AdminTicketOut]
