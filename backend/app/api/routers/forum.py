import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import AdminUser, DBSession, PremiumUser
from backend.app.db.models import ForumCategoryModel, ForumPostModel, ForumThreadModel
from backend.app.schemas.forum import (
    CreatePostRequest,
    CreateThreadRequest,
    ForumCategoryOut,
    ForumPostOut,
    ForumThreadDetail,
    ForumThreadPreview,
    ForumThreadsListResponse,
    PinThreadRequest,
    UpdatePostRequest,
    UpdateThreadRequest,
)

router = APIRouter()


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


@router.get("/forum/categories", response_model=list[ForumCategoryOut])
async def list_categories(db: DBSession, user: PremiumUser):
    result = await db.execute(select(ForumCategoryModel).order_by(ForumCategoryModel.key))
    return result.scalars().all()


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
    await db.commit()

    return await _get_thread_detail(db, thread.id, user)


async def _get_thread_detail(db, thread_id: uuid.UUID, user) -> ForumThreadDetail:
    result = await db.execute(
        select(ForumThreadModel)
        .options(selectinload(ForumThreadModel.category), selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.user))
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
        posts=[
            ForumPostOut(
                id=p.id, author_username=p.user.username, author_id=p.user_id,
                author_is_admin=p.user.is_admin, body=p.body, created_at=p.created_at,
            )
            for p in thread.posts
        ],
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

    db.add(ForumPostModel(thread_id=thread.id, user_id=user.id, body=payload.body))
    thread.updated_at = datetime.now(timezone.utc)
    await db.commit()

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
