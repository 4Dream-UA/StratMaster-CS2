import hashlib
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import AdminUser, DBSession, PremiumUser
from backend.app.core.config import settings
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import (
    REACTION_EMOJIS,
    ForumCategoryModel,
    ForumPostEditModel,
    ForumPostModel,
    ForumPostReactionModel,
    ForumPostReportModel,
    ForumThreadModel,
    ForumThreadReportModel,
    ForumThreadWatcherModel,
    UserModel,
)
from backend.app.schemas.forum import (
    CloseThreadRequest,
    CreatePostRequest,
    CreateThreadRequest,
    ForumCategoryOut,
    ForumPostOut,
    ForumThreadDetail,
    ForumThreadPreview,
    ForumThreadsListResponse,
    PinThreadRequest,
    PostEditOut,
    ReactionSummary,
    ReactorOut,
    ReactorsListResponse,
    ReactRequest,
    ReplyToOut,
    ReportOut,
    ReportPostRequest,
    ShareTokenResponse,
    SharedThreadResponse,
    UpdateCategoryRequest,
    UpdatePostRequest,
    UpdateThreadRequest,
    VisibleToUserOut,
    WatchResponse,
)
from backend.app.services.notifications import send_telegram_message
from backend.app.services.referral import generate_share_token

router = APIRouter()

REPLY_SNIPPET_LEN = 80
MENTION_RE = re.compile(r"@([a-zA-Z0-9_]{3,32})")


async def _get_category(db, key: str) -> ForumCategoryModel:
    result = await db.execute(select(ForumCategoryModel).where(ForumCategoryModel.key == key))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown forum category")
    return category


def _anon_handle(user_id: uuid.UUID) -> str:
    """A stable "Player#12345" stand-in for a hidden username — derived
    from the user's own id, so it's always the same handle for the same
    person (letting readers tell "this is the same poster again" apart
    without it being remotely identifying), not a fresh random one per
    render."""
    digits = int(hashlib.sha256(user_id.bytes).hexdigest(), 16) % 100000
    return f"Player#{digits:05d}"


def _is_hidden_from(author: UserModel, viewer: UserModel) -> bool:
    return author.hide_username_on_forum and not viewer.is_admin and author.id != viewer.id


def _visible_identity(author: UserModel, viewer: UserModel) -> tuple[str | None, str | None]:
    """(username, display_name) as `viewer` should see them — hiding the
    username also replaces the display name with the same anon handle,
    since a self-chosen nickname can be just as identifying as the
    Telegram @username it was meant to stand in for."""
    if _is_hidden_from(author, viewer):
        return None, _anon_handle(author.id)
    return author.username, author.display_name


async def _thread_previews(db, threads: list[ForumThreadModel], viewer: UserModel) -> list[ForumThreadPreview]:
    """Both counts are fetched for the whole page in one grouped query each,
    rather than per thread — a 100-thread page was previously 100 sequential
    COUNT round-trips just to render the reply counter."""
    if not threads:
        return []
    thread_ids = [t.id for t in threads]

    post_counts = dict(
        (
            await db.execute(
                select(ForumPostModel.thread_id, func.count())
                .where(ForumPostModel.thread_id.in_(thread_ids))
                .group_by(ForumPostModel.thread_id)
            )
        ).all()
    )

    report_counts: dict[uuid.UUID, int] = {}
    if viewer.is_admin:
        report_counts = dict(
            (
                await db.execute(
                    select(ForumThreadReportModel.thread_id, func.count())
                    .where(
                        ForumThreadReportModel.thread_id.in_(thread_ids),
                        ForumThreadReportModel.resolved_at.is_(None),
                    )
                    .group_by(ForumThreadReportModel.thread_id)
                )
            ).all()
        )

    previews = []
    for thread in threads:
        username, display_name = _visible_identity(thread.user, viewer)
        previews.append(ForumThreadPreview(
            id=thread.id,
            title=thread.title,
            author_username=username,
            author_display_name=display_name,
            author_avatar_url=thread.user.avatar_url,
            author_id=thread.user_id,
            author_is_admin=thread.user.is_admin,
            is_pinned=thread.is_pinned,
            is_closed=thread.is_closed,
            post_count=post_counts.get(thread.id, 0),
            updated_at=thread.updated_at,
            report_count=report_counts.get(thread.id, 0),
        ))
    return previews


def _can_access_thread(thread: ForumThreadModel, category: ForumCategoryModel, user) -> bool:
    if category.key != "support":
        return True
    return user.is_admin or thread.user_id == user.id


def _can_modify(owner_user_id: uuid.UUID, user) -> bool:
    """Edit/delete permission: the author, or an admin."""
    return user.is_admin or owner_user_id == user.id


async def _is_watching(db, thread_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(ForumThreadWatcherModel).where(
            ForumThreadWatcherModel.thread_id == thread_id, ForumThreadWatcherModel.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def _auto_watch(db, thread_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Starting a thread or replying to it implicitly opts you into
    notifications for it — same "auto-track" behavior most forums default
    to. Silently a no-op if already watching."""
    if await _is_watching(db, thread_id, user_id):
        return
    db.add(ForumThreadWatcherModel(thread_id=thread_id, user_id=user_id))


def _thread_link(thread_id: uuid.UUID) -> str | None:
    if not settings.webapp_url:
        return None
    return f"{settings.webapp_url.rstrip('/')}/forum?thread={thread_id}"


async def _notify_new_post(db, thread: ForumThreadModel, poster, reply_to_post: ForumPostModel | None) -> None:
    """Best-effort Telegram notifications: everyone watching the thread
    (except whoever just posted), plus — if this was a reply to a specific
    post — that post's author, even if they aren't (yet) a watcher."""
    link = _thread_link(thread.id)

    result = await db.execute(
        select(ForumThreadWatcherModel.user_id).where(
            ForumThreadWatcherModel.thread_id == thread.id, ForumThreadWatcherModel.user_id != poster.id
        )
    )
    watcher_ids = {row[0] for row in result.all()}

    notify_ids = set(watcher_ids)
    reply_target_user = None
    if reply_to_post is not None and reply_to_post.user_id != poster.id:
        reply_target_user = reply_to_post.user
        notify_ids.add(reply_to_post.user_id)

    if not notify_ids:
        return

    from backend.app.db.models import UserModel
    result = await db.execute(select(UserModel).where(UserModel.id.in_(notify_ids)))
    users_by_id = {u.id: u for u in result.scalars().all()}

    poster_name = f"@{poster.username}" if poster.username else "Someone"
    for user_id in notify_ids:
        target = users_by_id.get(user_id)
        if target is None:
            continue
        if reply_target_user is not None and user_id == reply_to_post.user_id:
            text = f"💬 {poster_name} replied to your message in <b>{thread.title}</b>"
        else:
            text = f"💬 New reply in <b>{thread.title}</b> from {poster_name}"
        await send_telegram_message(target.telegram_id, text, web_app_url=link)


@router.get("/forum/categories", response_model=list[ForumCategoryOut])
async def list_categories(db: DBSession, user: PremiumUser):
    result = await db.execute(select(ForumCategoryModel).order_by(ForumCategoryModel.key))
    return result.scalars().all()


@router.patch("/forum/categories/{key}", response_model=ForumCategoryOut)
async def update_category(key: str, payload: UpdateCategoryRequest, db: DBSession, admin_user: AdminUser):
    category = await _get_category(db, key)
    category.name = payload.name
    category.description = payload.description
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/forum/categories/{key}/threads", response_model=ForumThreadsListResponse)
async def list_threads(
    key: str,
    db: DBSession,
    user: PremiumUser,
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    category = await _get_category(db, key)

    query = (
        select(ForumThreadModel)
        .options(selectinload(ForumThreadModel.user))
        .where(ForumThreadModel.category_id == category.id)
    )
    count_query = select(func.count()).select_from(ForumThreadModel).where(ForumThreadModel.category_id == category.id)

    if category.key == "support" and not user.is_admin:
        # Tickets are private — a regular user only ever sees their own,
        # same as everyone else does for the Lounge minus the "everyone".
        query = query.where(ForumThreadModel.user_id == user.id)
        count_query = count_query.where(ForumThreadModel.user_id == user.id)

    query = query.order_by(ForumThreadModel.is_pinned.desc(), ForumThreadModel.updated_at.desc())

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    threads = result.scalars().all()

    return ForumThreadsListResponse(total=total, threads=await _thread_previews(db, list(threads), user))


@router.post(
    "/forum/categories/{key}/threads", response_model=ForumThreadDetail, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("forum_post", max_requests=10, window_seconds=60))],
)
async def create_thread(key: str, payload: CreateThreadRequest, db: DBSession, user: PremiumUser):
    category = await _get_category(db, key)

    thread = ForumThreadModel(
        category_id=category.id,
        user_id=user.id,
        title=payload.title,
        posts=[ForumPostModel(user_id=user.id, body=payload.body)],
    )
    db.add(thread)
    await db.flush()
    await _auto_watch(db, thread.id, user.id)
    await db.commit()

    return await _get_thread_detail(db, thread.id, user)


def _reaction_summary(p: ForumPostModel, viewer_id: uuid.UUID | None) -> list[ReactionSummary]:
    counts: dict[str, int] = {}
    mine: set[str] = set()
    for r in p.reactions:
        counts[r.emoji] = counts.get(r.emoji, 0) + 1
        if viewer_id is not None and r.user_id == viewer_id:
            mine.add(r.emoji)
    # Stable order (REACTION_EMOJIS, not insertion order) so the row of
    # emoji buttons doesn't jump around as counts change.
    return [
        ReactionSummary(emoji=e, count=counts[e], reacted_by_me=e in mine)
        for e in REACTION_EMOJIS if e in counts
    ]


def _post_visible_to(p: ForumPostModel, viewer: UserModel) -> bool:
    """Whisper posts are only shown to the players they were addressed to,
    plus the author and any admin — everyone else shouldn't even know the
    post exists, not just have its body hidden."""
    if not p.visible_to_user_ids:
        return True
    if viewer.is_admin or p.user_id == viewer.id:
        return True
    return str(viewer.id) in p.visible_to_user_ids


def _post_out(
    p: ForumPostModel, viewer: UserModel | None = None, users_by_id: dict[uuid.UUID, UserModel] | None = None,
) -> ForumPostOut:
    users_by_id = users_by_id or {}
    viewer_id = viewer.id if viewer is not None else None
    is_admin_viewer = viewer is not None and viewer.is_admin
    is_author_viewer = viewer is not None and viewer.id == p.user_id

    def identity_for(author: UserModel) -> tuple[str | None, str | None]:
        # No viewer (anonymous share link): never privileged, never the
        # author — same as _visible_identity's "everyone else" branch.
        if viewer is None:
            if author.hide_username_on_forum:
                return None, _anon_handle(author.id)
            return author.username, author.display_name
        return _visible_identity(author, viewer)

    author_username, author_display_name = identity_for(p.user)

    reply_to = None
    if p.reply_to is not None:
        snippet = p.reply_to.body[:REPLY_SNIPPET_LEN]
        if len(p.reply_to.body) > REPLY_SNIPPET_LEN:
            snippet += "…"
        quoted_username, quoted_display_name = identity_for(p.reply_to.user)
        reply_to = ReplyToOut(
            id=p.reply_to.id, author_username=quoted_username,
            author_display_name=quoted_display_name, body_snippet=snippet,
        )

    visible_to = []
    if (is_admin_viewer or is_author_viewer) and p.visible_to_user_ids:
        for uid_str in p.visible_to_user_ids:
            u = users_by_id.get(uuid.UUID(uid_str))
            if u is not None:
                visible_to.append(VisibleToUserOut(id=u.id, username=u.username, display_name=u.display_name))

    deleted_by = users_by_id.get(p.deleted_by_id) if p.deleted_by_id else None

    return ForumPostOut(
        id=p.id, author_username=author_username, author_display_name=author_display_name,
        author_avatar_url=p.user.avatar_url, author_id=p.user_id,
        author_is_admin=p.user.is_admin,
        body="[deleted]" if p.deleted_at and not is_admin_viewer else p.body,
        reply_to=reply_to,
        reactions=_reaction_summary(p, viewer_id), created_at=p.created_at,
        edited_at=p.edited_at, edited_by_admin=bool(p.edited_by_id and p.edited_by_id != p.user_id),
        visible_to=visible_to,
        deleted_at=p.deleted_at if is_admin_viewer else None,
        deleted_by_username=(deleted_by.username if is_admin_viewer and deleted_by else None),
        report_count=(sum(1 for r in p.reports if r.resolved_at is None) if is_admin_viewer else 0),
    )


async def _users_lookup_for_posts(db, posts: list[ForumPostModel]) -> dict[uuid.UUID, UserModel]:
    """Batch-fetch every user referenced only by ID on these posts (whisper
    recipients, who-deleted-this) — a handful of extra rows beat N+1
    queries per post."""
    ids: set[uuid.UUID] = set()
    for p in posts:
        if p.deleted_by_id:
            ids.add(p.deleted_by_id)
        for uid_str in (p.visible_to_user_ids or []):
            ids.add(uuid.UUID(uid_str))
    if not ids:
        return {}
    result = await db.execute(select(UserModel).where(UserModel.id.in_(ids)))
    return {u.id: u for u in result.scalars().all()}


async def _get_thread_detail(db, thread_id: uuid.UUID, user) -> ForumThreadDetail:
    result = await db.execute(
        select(ForumThreadModel)
        .options(
            selectinload(ForumThreadModel.category),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.user),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.reply_to).selectinload(ForumPostModel.user),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.reactions),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.reports),
            selectinload(ForumThreadModel.user),
            selectinload(ForumThreadModel.reports),
        )
        .where(ForumThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if thread is None or not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    visible_posts = [p for p in thread.posts if _post_visible_to(p, user) and (not p.deleted_at or user.is_admin)]
    users_by_id = await _users_lookup_for_posts(db, visible_posts)

    return ForumThreadDetail(
        id=thread.id,
        category_key=thread.category.key,
        title=thread.title,
        author_id=thread.user_id,
        author_is_admin=thread.user.is_admin,
        is_pinned=thread.is_pinned,
        is_closed=thread.is_closed,
        is_watching=await _is_watching(db, thread.id, user.id),
        share_token=thread.share_token,
        report_count=(sum(1 for r in thread.reports if r.resolved_at is None) if user.is_admin else 0),
        posts=[_post_out(p, user, users_by_id) for p in visible_posts],
    )


@router.get("/forum/threads/{thread_id}", response_model=ForumThreadDetail)
async def get_thread(thread_id: uuid.UUID, db: DBSession, user: PremiumUser):
    return await _get_thread_detail(db, thread_id, user)


async def _get_thread_or_404(db, thread_id: uuid.UUID) -> ForumThreadModel:
    result = await db.execute(
        select(ForumThreadModel).options(selectinload(ForumThreadModel.category)).where(ForumThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


@router.patch("/forum/threads/{thread_id}", response_model=ForumThreadDetail)
async def update_thread(thread_id: uuid.UUID, payload: UpdateThreadRequest, db: DBSession, user: PremiumUser):
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user) or not _can_modify(thread.user_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't edit this thread")

    thread.title = payload.title
    await db.commit()
    return await _get_thread_detail(db, thread_id, user)


@router.patch("/forum/threads/{thread_id}/pin", response_model=ForumThreadDetail)
async def pin_thread(thread_id: uuid.UUID, payload: PinThreadRequest, db: DBSession, admin_user: AdminUser):
    thread = await _get_thread_or_404(db, thread_id)
    thread.is_pinned = payload.is_pinned
    await db.commit()
    return await _get_thread_detail(db, thread_id, admin_user)


@router.patch("/forum/threads/{thread_id}/close", response_model=ForumThreadDetail)
async def close_thread(thread_id: uuid.UUID, payload: CloseThreadRequest, db: DBSession, user: PremiumUser):
    """Admins can close/reopen any thread (e.g. resolving a support
    ticket); a regular player can only close their own thread — making it
    view-only for everyone else — and can't reopen it themselves once
    closed, so it stays a one-way "lock" from their side."""
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    if not user.is_admin:
        if thread.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't close this thread")
        if thread.is_closed and not payload.is_closed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an admin can reopen a closed thread")

    thread.is_closed = payload.is_closed
    await db.commit()
    return await _get_thread_detail(db, thread_id, user)


@router.post(
    "/forum/threads/{thread_id}/watch", response_model=WatchResponse,
    dependencies=[Depends(rate_limit("forum_watch", max_requests=30, window_seconds=60))],
)
async def toggle_watch(thread_id: uuid.UUID, db: DBSession, user: PremiumUser):
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    if await _is_watching(db, thread_id, user.id):
        result = await db.execute(
            select(ForumThreadWatcherModel).where(
                ForumThreadWatcherModel.thread_id == thread_id, ForumThreadWatcherModel.user_id == user.id
            )
        )
        row = result.scalar_one()
        await db.delete(row)
        await db.commit()
        return WatchResponse(is_watching=False)

    db.add(ForumThreadWatcherModel(thread_id=thread_id, user_id=user.id))
    await db.commit()
    return WatchResponse(is_watching=True)


@router.delete("/forum/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(thread_id: uuid.UUID, db: DBSession, user: PremiumUser):
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user) or not _can_modify(thread.user_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't delete this thread")

    await db.delete(thread)
    await db.commit()


async def _notify_mentions(db, thread: ForumThreadModel, poster, body: str, already_notified: set[uuid.UUID]) -> None:
    """Best-effort: @username pings send the same kind of Telegram nudge as
    a direct reply, minus anyone already notified for this post (the reply
    target, or the poster themselves)."""
    handles = set(MENTION_RE.findall(body))
    if not handles:
        return
    result = await db.execute(select(UserModel).where(UserModel.username.in_(handles)))
    mentioned = [u for u in result.scalars().all() if u.id != poster.id and u.id not in already_notified]
    if not mentioned:
        return
    link = _thread_link(thread.id)
    poster_name = f"@{poster.username}" if poster.username else "Someone"
    for target in mentioned:
        await send_telegram_message(target.telegram_id, f"📣 {poster_name} mentioned you in <b>{thread.title}</b>", web_app_url=link)


@router.post(
    "/forum/threads/{thread_id}/posts", response_model=ForumThreadDetail, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("forum_post", max_requests=20, window_seconds=60))],
)
async def add_post(thread_id: uuid.UUID, payload: CreatePostRequest, db: DBSession, user: PremiumUser):
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if thread.is_closed and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This thread is closed")

    reply_to_post = None
    if payload.reply_to_post_id is not None:
        result = await db.execute(
            select(ForumPostModel).options(selectinload(ForumPostModel.user)).where(
                ForumPostModel.id == payload.reply_to_post_id, ForumPostModel.thread_id == thread_id,
            )
        )
        reply_to_post = result.scalar_one_or_none()
        if reply_to_post is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That message isn't in this thread")

    visible_to_ids: list[str] | None = None
    if payload.visible_to_user_ids:
        result = await db.execute(select(UserModel.id).where(UserModel.id.in_(payload.visible_to_user_ids)))
        found = {row[0] for row in result.all()}
        missing = set(payload.visible_to_user_ids) - found
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One of those players couldn't be found")
        visible_to_ids = [str(uid) for uid in payload.visible_to_user_ids]

    db.add(ForumPostModel(
        thread_id=thread.id, user_id=user.id, body=payload.body,
        reply_to_post_id=payload.reply_to_post_id, visible_to_user_ids=visible_to_ids,
    ))
    thread.updated_at = datetime.now(timezone.utc)
    await _auto_watch(db, thread.id, user.id)
    await db.commit()

    already_notified = {user.id}
    if reply_to_post is not None:
        already_notified.add(reply_to_post.user_id)
    await _notify_new_post(db, thread, user, reply_to_post)
    await _notify_mentions(db, thread, user, payload.body, already_notified)

    return await _get_thread_detail(db, thread_id, user)


@router.patch(
    "/forum/posts/{post_id}", response_model=ForumThreadDetail,
    dependencies=[Depends(rate_limit("forum_post", max_requests=20, window_seconds=60))],
)
async def update_post(post_id: uuid.UUID, payload: UpdatePostRequest, db: DBSession, user: PremiumUser):
    result = await db.execute(
        select(ForumPostModel)
        .options(selectinload(ForumPostModel.thread).selectinload(ForumThreadModel.category))
        .where(ForumPostModel.id == post_id)
    )
    post = result.scalar_one_or_none()
    if post is None or not _can_access_thread(post.thread, post.thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not _can_modify(post.user_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't edit this post")

    db.add(ForumPostEditModel(post_id=post.id, editor_id=user.id, previous_body=post.body))
    post.body = payload.body
    post.edited_at = datetime.now(timezone.utc)
    post.edited_by_id = user.id
    await db.commit()

    return await _get_thread_detail(db, post.thread_id, user)


@router.post(
    "/forum/posts/{post_id}/react", response_model=ForumThreadDetail,
    dependencies=[Depends(rate_limit("forum_react", max_requests=60, window_seconds=60))],
)
async def react_to_post(post_id: uuid.UUID, payload: ReactRequest, db: DBSession, user: PremiumUser):
    """Toggles one of a fixed emoji set on a post — sending the same emoji
    again removes it. Allowed even on a closed thread; closing only stops
    new replies, not lightweight reactions to what's already there."""
    if payload.emoji not in REACTION_EMOJIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported reaction")

    result = await db.execute(
        select(ForumPostModel)
        .options(selectinload(ForumPostModel.thread).selectinload(ForumThreadModel.category))
        .where(ForumPostModel.id == post_id)
    )
    post = result.scalar_one_or_none()
    if post is None or not _can_access_thread(post.thread, post.thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = await db.execute(
        select(ForumPostReactionModel).where(
            ForumPostReactionModel.post_id == post_id,
            ForumPostReactionModel.user_id == user.id,
            ForumPostReactionModel.emoji == payload.emoji,
        )
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
    else:
        db.add(ForumPostReactionModel(post_id=post_id, user_id=user.id, emoji=payload.emoji))
    await db.commit()

    return await _get_thread_detail(db, post.thread_id, user)


def _assert_reportable(author_id: uuid.UUID, author_is_admin: bool, reporter: UserModel) -> None:
    """Reports route to the admins, so there's nothing for one to do about
    an admin's own content — and reporting yourself is never meaningful.
    The frontend hides the button in both cases; this is what makes it
    actually true rather than just invisible."""
    if author_is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin content can't be reported — open a support ticket instead",
        )
    if author_id == reporter.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't report your own content")


@router.post(
    "/forum/posts/{post_id}/report", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("forum_report", max_requests=10, window_seconds=60))],
)
async def report_post(post_id: uuid.UUID, payload: ReportPostRequest, db: DBSession, user: PremiumUser):
    """Flags a post for admin review — doesn't hide it or notify anyone in
    real time, just surfaces a report count to admins on the post itself
    (see ForumPostOut.report_count) until dismissed."""
    result = await db.execute(
        select(ForumPostModel)
        .options(
            selectinload(ForumPostModel.thread).selectinload(ForumThreadModel.category),
            selectinload(ForumPostModel.user),
        )
        .where(ForumPostModel.id == post_id)
    )
    post = result.scalar_one_or_none()
    if post is None or not _can_access_thread(post.thread, post.thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _assert_reportable(post.user_id, post.user.is_admin, user)

    db.add(ForumPostReportModel(post_id=post_id, reporter_id=user.id, reason=payload.reason))
    await db.commit()


@router.get("/forum/posts/{post_id}/reports", response_model=list[ReportOut])
async def list_post_reports(post_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(ForumPostReportModel)
        .options(selectinload(ForumPostReportModel.reporter))
        .where(ForumPostReportModel.post_id == post_id, ForumPostReportModel.resolved_at.is_(None))
        .order_by(ForumPostReportModel.created_at.desc())
    )
    return [
        ReportOut(
            reporter_username=r.reporter.username, reporter_display_name=r.reporter.display_name,
            reason=r.reason, created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


@router.post("/forum/posts/{post_id}/reports/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_post_reports(post_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(ForumPostReportModel).where(
            ForumPostReportModel.post_id == post_id, ForumPostReportModel.resolved_at.is_(None)
        )
    )
    now = datetime.now(timezone.utc)
    for report in result.scalars().all():
        report.resolved_at = now
    await db.commit()


# ── Thread-level reports — the same three operations as above, flagging a
#    whole thread (its topic/title) rather than one message inside it. ──


@router.post(
    "/forum/threads/{thread_id}/report", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("forum_report", max_requests=10, window_seconds=60))],
)
async def report_thread(thread_id: uuid.UUID, payload: ReportPostRequest, db: DBSession, user: PremiumUser):
    result = await db.execute(
        select(ForumThreadModel)
        .options(selectinload(ForumThreadModel.category), selectinload(ForumThreadModel.user))
        .where(ForumThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if thread is None or not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    _assert_reportable(thread.user_id, thread.user.is_admin, user)

    db.add(ForumThreadReportModel(thread_id=thread_id, reporter_id=user.id, reason=payload.reason))
    await db.commit()


@router.get("/forum/threads/{thread_id}/reports", response_model=list[ReportOut])
async def list_thread_reports(thread_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(ForumThreadReportModel)
        .options(selectinload(ForumThreadReportModel.reporter))
        .where(ForumThreadReportModel.thread_id == thread_id, ForumThreadReportModel.resolved_at.is_(None))
        .order_by(ForumThreadReportModel.created_at.desc())
    )
    return [
        ReportOut(
            reporter_username=r.reporter.username, reporter_display_name=r.reporter.display_name,
            reason=r.reason, created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


@router.post("/forum/threads/{thread_id}/reports/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_thread_reports(thread_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(ForumThreadReportModel).where(
            ForumThreadReportModel.thread_id == thread_id, ForumThreadReportModel.resolved_at.is_(None)
        )
    )
    now = datetime.now(timezone.utc)
    for report in result.scalars().all():
        report.resolved_at = now
    await db.commit()


async def _get_post_or_404(db, post_id: uuid.UUID, user) -> ForumPostModel:
    result = await db.execute(
        select(ForumPostModel)
        .options(selectinload(ForumPostModel.thread).selectinload(ForumThreadModel.category))
        .where(ForumPostModel.id == post_id)
    )
    post = result.scalar_one_or_none()
    if post is None or not _can_access_thread(post.thread, post.thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.delete(
    "/forum/posts/{post_id}", response_model=ForumThreadDetail,
    dependencies=[Depends(rate_limit("forum_post", max_requests=20, window_seconds=60))],
)
async def delete_post(post_id: uuid.UUID, db: DBSession, user: PremiumUser):
    """Soft delete — the author (or an admin) can remove their own message
    from view, but the row and its body stick around until an admin
    permanently erases it (or restores it)."""
    post = await _get_post_or_404(db, post_id, user)
    if not _can_modify(post.user_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't delete this post")

    post.deleted_at = datetime.now(timezone.utc)
    post.deleted_by_id = user.id
    await db.commit()
    return await _get_thread_detail(db, post.thread_id, user)


@router.post("/forum/posts/{post_id}/restore", response_model=ForumThreadDetail)
async def restore_post(post_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    post = await _get_post_or_404(db, post_id, admin_user)
    post.deleted_at = None
    post.deleted_by_id = None
    await db.commit()
    return await _get_thread_detail(db, post.thread_id, admin_user)


@router.delete("/forum/posts/{post_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanently_delete_post(post_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    post = await _get_post_or_404(db, post_id, admin_user)
    if post.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only an already-deleted post can be permanently erased")
    await db.delete(post)
    await db.commit()


@router.get("/forum/posts/{post_id}/edits", response_model=list[PostEditOut])
async def get_post_edits(post_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(ForumPostEditModel)
        .options(selectinload(ForumPostEditModel.editor))
        .where(ForumPostEditModel.post_id == post_id)
        .order_by(ForumPostEditModel.edited_at.desc())
    )
    edits = result.scalars().all()
    return [
        PostEditOut(
            previous_body=e.previous_body,
            editor_username=e.editor.username if e.editor else None,
            editor_is_admin=bool(e.editor and e.editor.is_admin),
            edited_at=e.edited_at,
        )
        for e in edits
    ]


@router.get("/forum/posts/{post_id}/reactions", response_model=ReactorsListResponse)
async def get_post_reactors(
    post_id: uuid.UUID, db: DBSession, user: PremiumUser,
    emoji: str = Query(...), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
):
    await _get_post_or_404(db, post_id, user)
    if emoji not in REACTION_EMOJIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported reaction")

    base = select(ForumPostReactionModel).where(
        ForumPostReactionModel.post_id == post_id, ForumPostReactionModel.emoji == emoji,
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0
    result = await db.execute(
        select(ForumPostReactionModel)
        .options(selectinload(ForumPostReactionModel.user))
        .where(ForumPostReactionModel.post_id == post_id, ForumPostReactionModel.emoji == emoji)
        .order_by(ForumPostReactionModel.created_at)
        .limit(limit).offset(offset)
    )
    rows = result.scalars().all()
    return ReactorsListResponse(
        total=total,
        reactors=[
            ReactorOut(
                user_id=r.user.id, username=r.user.username, display_name=r.user.display_name,
                avatar_url=r.user.avatar_url, is_admin=r.user.is_admin,
            )
            for r in rows
        ],
    )


# ─────────────────────────────────────────────
#  Sharing: public link
# ─────────────────────────────────────────────

@router.post(
    "/forum/threads/{thread_id}/share", response_model=ShareTokenResponse,
    dependencies=[Depends(rate_limit("forum_share", max_requests=10, window_seconds=60))],
)
async def create_share_link(thread_id: uuid.UUID, db: DBSession, user: PremiumUser):
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user) or not _can_modify(thread.user_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't share this thread")

    thread.share_token = generate_share_token()
    await db.commit()
    return ShareTokenResponse(share_token=thread.share_token)


@router.delete("/forum/threads/{thread_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(thread_id: uuid.UUID, db: DBSession, user: PremiumUser):
    thread = await _get_thread_or_404(db, thread_id)
    if not _can_access_thread(thread, thread.category, user) or not _can_modify(thread.user_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't manage this thread's share link")

    thread.share_token = None
    await db.commit()


@router.get("/forum/shared/{share_token}", response_model=SharedThreadResponse)
async def get_shared_thread(share_token: str, db: DBSession):
    """Public, unauthenticated — anyone with the link can view (read-only),
    same pattern as personal-board share links."""
    result = await db.execute(
        select(ForumThreadModel)
        .options(
            selectinload(ForumThreadModel.category),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.user),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.reply_to).selectinload(ForumPostModel.user),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.reactions),
        )
        .where(ForumThreadModel.share_token == share_token)
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This share link is invalid or was revoked")

    # Anonymous viewer: no whisper posts, no deleted posts, no username-hide
    # exemption — same as any logged-out player would see.
    visible_posts = [p for p in thread.posts if not p.visible_to_user_ids and not p.deleted_at]

    return SharedThreadResponse(
        id=thread.id,
        category_key=thread.category.key,
        title=thread.title,
        author_id=thread.user_id,
        is_pinned=thread.is_pinned,
        is_closed=thread.is_closed,
        is_watching=False,
        share_token=thread.share_token,
        posts=[_post_out(p) for p in visible_posts],
    )
