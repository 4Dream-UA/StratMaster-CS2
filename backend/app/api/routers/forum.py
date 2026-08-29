import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import DBSession, PremiumUser
from backend.app.db.models import ForumCategoryModel, ForumPostModel, ForumThreadModel
from backend.app.schemas.forum import (
    CreatePostRequest,
    CreateThreadRequest,
    ForumCategoryOut,
    ForumPostOut,
    ForumThreadDetail,
    ForumThreadPreview,
    ForumThreadsListResponse,
)

router = APIRouter()

SUPPORT_TICKET_TITLE = "Support ticket"


async def _get_category(db, key: str) -> ForumCategoryModel:
    result = await db.execute(select(ForumCategoryModel).where(ForumCategoryModel.key == key))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown forum category")
    return category


async def _get_or_create_own_support_thread(db, category: ForumCategoryModel, user) -> ForumThreadModel:
    result = await db.execute(
        select(ForumThreadModel).where(
            ForumThreadModel.category_id == category.id,
            ForumThreadModel.user_id == user.id,
        )
    )
    thread = result.scalar_one_or_none()
    if thread is not None:
        return thread

    thread = ForumThreadModel(category_id=category.id, user_id=user.id, title=SUPPORT_TICKET_TITLE)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


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
        post_count=post_count,
        updated_at=thread.updated_at,
    )


def _can_access_thread(thread: ForumThreadModel, category: ForumCategoryModel, user) -> bool:
    if category.key != "support":
        return True
    return user.is_admin or thread.user_id == user.id


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

    if category.key == "support" and not user.is_admin:
        # Not a real "list" for a regular user — just their own auto-created
        # ticket, wrapped in the same shape so the frontend can reuse one
        # list->detail flow for both categories.
        thread = await _get_or_create_own_support_thread(db, category, user)
        thread = (await db.execute(
            select(ForumThreadModel).options(selectinload(ForumThreadModel.user)).where(ForumThreadModel.id == thread.id)
        )).scalar_one()
        return ForumThreadsListResponse(total=1, threads=[await _thread_preview(db, thread)])

    query = (
        select(ForumThreadModel)
        .options(selectinload(ForumThreadModel.user))
        .where(ForumThreadModel.category_id == category.id)
        .order_by(ForumThreadModel.updated_at.desc())
    )
    count_query = select(func.count()).select_from(ForumThreadModel).where(ForumThreadModel.category_id == category.id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    threads = result.scalars().all()

    return ForumThreadsListResponse(total=total, threads=[await _thread_preview(db, t) for t in threads])


@router.post("/forum/categories/{key}/threads", response_model=ForumThreadDetail, status_code=status.HTTP_201_CREATED)
async def create_thread(key: str, payload: CreateThreadRequest, db: DBSession, user: PremiumUser):
    category = await _get_category(db, key)
    if category.key == "support":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support tickets are created automatically — just open the Support category.",
        )

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


@router.post("/forum/threads/{thread_id}/posts", response_model=ForumThreadDetail, status_code=status.HTTP_201_CREATED)
async def add_post(thread_id: uuid.UUID, payload: CreatePostRequest, db: DBSession, user: PremiumUser):
    result = await db.execute(
        select(ForumThreadModel).options(selectinload(ForumThreadModel.category)).where(ForumThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if thread is None or not _can_access_thread(thread, thread.category, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    db.add(ForumPostModel(thread_id=thread.id, user_id=user.id, body=payload.body))
    thread.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return await _get_thread_detail(db, thread_id, user)
