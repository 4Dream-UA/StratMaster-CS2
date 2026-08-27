import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import DBSession, PremiumUser
from backend.app.db.models import MapModel, PersonalBoardGrenadeModel, PersonalBoardModel, PersonalBoardPathModel
from backend.app.schemas.board import (
    BoardUpdate,
    PersonalBoardCreate,
    PersonalBoardDetail,
    PersonalBoardsListResponse,
)

router = APIRouter()


def _board_detail_query():
    return select(PersonalBoardModel).options(
        selectinload(PersonalBoardModel.paths),
        selectinload(PersonalBoardModel.grenades),
    )


async def _get_owned_board(db: DBSession, user, board_id: uuid.UUID) -> PersonalBoardModel:
    result = await db.execute(_board_detail_query().where(PersonalBoardModel.id == board_id))
    board = result.scalar_one_or_none()
    if board is None or board.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


@router.get("/boards", response_model=PersonalBoardsListResponse)
async def list_boards(
    db: DBSession,
    user: PremiumUser,
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = (
        select(PersonalBoardModel)
        .where(PersonalBoardModel.user_id == user.id)
        .order_by(PersonalBoardModel.updated_at.desc())
    )
    count_query = select(func.count()).select_from(PersonalBoardModel).where(PersonalBoardModel.user_id == user.id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    return PersonalBoardsListResponse(total=total, boards=result.scalars().all())


@router.post("/boards", response_model=PersonalBoardDetail, status_code=status.HTTP_201_CREATED)
async def create_board(payload: PersonalBoardCreate, db: DBSession, user: PremiumUser):
    map_ = await db.get(MapModel, payload.map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="map_id does not exist")

    board = PersonalBoardModel(
        user_id=user.id,
        map_id=payload.map_id,
        title=payload.title,
        paths=[PersonalBoardPathModel(**p.model_dump()) for p in payload.paths],
        grenades=[PersonalBoardGrenadeModel(**g.model_dump()) for g in payload.grenades],
    )
    db.add(board)
    await db.commit()

    return await _get_owned_board(db, user, board.id)


@router.get("/boards/{board_id}", response_model=PersonalBoardDetail)
async def get_board(board_id: uuid.UUID, db: DBSession, user: PremiumUser):
    return await _get_owned_board(db, user, board_id)


@router.patch("/boards/{board_id}", response_model=PersonalBoardDetail)
async def update_board(board_id: uuid.UUID, payload: BoardUpdate, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)

    map_ = await db.get(MapModel, payload.map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="map_id does not exist")

    board.map_id = payload.map_id
    board.title = payload.title
    # Reassigning the collections triggers delete-orphan cleanup on the rows
    # that dropped out, and inserts the new ones — a full replace per submit,
    # same pattern as admin_update_strategy.
    board.paths = [PersonalBoardPathModel(**p.model_dump()) for p in payload.paths]
    board.grenades = [PersonalBoardGrenadeModel(**g.model_dump()) for g in payload.grenades]
    await db.commit()

    return await _get_owned_board(db, user, board_id)


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(board_id: uuid.UUID, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)
    await db.delete(board)
    await db.commit()
