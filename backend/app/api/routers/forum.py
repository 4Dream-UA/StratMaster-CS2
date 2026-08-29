import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import AdminUser, DBSession, PremiumUser
from backend.app.core.config import settings
from backend.app.db.models import ForumCategoryModel, ForumPostModel, ForumThreadModel, ForumThreadWatcherModel
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
    ReplyToOut,
    ShareTokenResponse,
    SharedThreadResponse,
    UpdateCategoryRequest,
    UpdatePostRequest,
    UpdateThreadRequest,
    WatchResponse,
)
from backend.app.services.notifications import send_telegram_message
from backend.app.services.referral import generate_share_token

router = APIRouter()

REPLY_SNIPPET_LEN = 80


async def _get_category(db, key: str) -> ForumCategoryModel:
    result = await db.execute(select(ForumCategoryModel).where(ForumCategoryModel.key == key))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown forum category")
    return category


async def _thread_preview(db, thread: ForumThreadModel) -> ForumThreadPreview:
    post_count = (
        await db.execute(select(func.count()).select_from(ForumPostModel).where(ForumPostModel.thread_id == thread.id))
    ).scalar() or 0
    return ForumThreadPreview(
        id=thread.id,
        title=thread.title,
        author_username=thread.user.username,
        author_id=thread.user_id,
        author_is_admin=thread.user.is_admin,
        is_pinned=thread.is_pinned,
        is_closed=thread.is_closed,
        post_count=post_count,
        updated_at=thread.updated_at,
    )


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

    return ForumThreadsListResponse(total=total, threads=[await _thread_preview(db, t) for t in threads])


@router.post("/forum/categories/{key}/threads", response_model=ForumThreadDetail, status_code=status.HTTP_201_CREATED)
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


def _post_out(p: ForumPostModel) -> ForumPostOut:
    reply_to = None
    if p.reply_to is not None:
        snippet = p.reply_to.body[:REPLY_SNIPPET_LEN]
        if len(p.reply_to.body) > REPLY_SNIPPET_LEN:
            snippet += "…"
        reply_to = ReplyToOut(id=p.reply_to.id, author_username=p.reply_to.user.username, body_snippet=snippet)
    return ForumPostOut(
        id=p.id, author_username=p.user.username, author_id=p.user_id,
        author_is_admin=p.user.is_admin, body=p.body, reply_to=reply_to, created_at=p.created_at,
    )


async def _get_thread_detail(db, thread_id: uuid.UUID, user) -> ForumThreadDetail:
    result = await db.execute(
        select(ForumThreadModel)
        .options(
            selectinload(ForumThreadModel.category),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.user),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.reply_to).selectinload(ForumPostModel.user),
        )
        .where(ForumThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if thread is None or not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    return ForumThreadDetail(
        id=thread.id,
        category_key=thread.category.key,
        title=thread.title,
        author_id=thread.user_id,
        is_pinned=thread.is_pinned,
        is_closed=thread.is_closed,
        is_watching=await _is_watching(db, thread.id, user.id),
        share_token=thread.share_token,
        posts=[_post_out(p) for p in thread.posts],
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
async def close_thread(thread_id: uuid.UUID, payload: CloseThreadRequest, db: DBSession, admin_user: AdminUser):
    thread = await _get_thread_or_404(db, thread_id)
    thread.is_closed = payload.is_closed
    await db.commit()
    return await _get_thread_detail(db, thread_id, admin_user)


@router.post("/forum/threads/{thread_id}/watch", response_model=WatchResponse)
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


@router.post("/forum/threads/{thread_id}/posts", response_model=ForumThreadDetail, status_code=status.HTTP_201_CREATED)
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

    db.add(ForumPostModel(
        thread_id=thread.id, user_id=user.id, body=payload.body,
        reply_to_post_id=payload.reply_to_post_id,
    ))
    thread.updated_at = datetime.now(timezone.utc)
    await _auto_watch(db, thread.id, user.id)
    await db.commit()

    await _notify_new_post(db, thread, user, reply_to_post)

    return await _get_thread_detail(db, thread_id, user)


@router.patch("/forum/posts/{post_id}", response_model=ForumThreadDetail)
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

    post.body = payload.body
    await db.commit()

    return await _get_thread_detail(db, post.thread_id, user)


# ─────────────────────────────────────────────
#  Sharing: public link
# ─────────────────────────────────────────────

@router.post("/forum/threads/{thread_id}/share", response_model=ShareTokenResponse)
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
        )
        .where(ForumThreadModel.share_token == share_token)
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This share link is invalid or was revoked")

    return SharedThreadResponse(
        id=thread.id,
        category_key=thread.category.key,
        title=thread.title,
        author_id=thread.user_id,
        is_pinned=thread.is_pinned,
        is_closed=thread.is_closed,
        is_watching=False,
        share_token=thread.share_token,
        posts=[_post_out(p) for p in thread.posts],
    )
