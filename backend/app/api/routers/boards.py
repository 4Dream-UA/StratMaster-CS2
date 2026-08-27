import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import DBSession, PremiumUser
from backend.app.db.models import (
    MapModel,
    PersonalBoardGrenadeModel,
    PersonalBoardModel,
    PersonalBoardPathModel,
    UserModel,
    WalletModel,
    personal_board_collaborator_link,
)
from backend.app.schemas.board import (
    AddCollaboratorRequest,
    BoardUpdate,
    CollaboratorOut,
    PersonalBoardCreate,
    PersonalBoardDetail,
    PersonalBoardsListResponse,
    SharedBoardResponse,
    ShareTokenResponse,
)
from backend.app.services.referral import generate_share_token

router = APIRouter()


def _board_detail_query():
    return select(PersonalBoardModel).options(
        selectinload(PersonalBoardModel.paths),
        selectinload(PersonalBoardModel.grenades),
        selectinload(PersonalBoardModel.collaborators),
    )


async def _get_owned_board(db: DBSession, user, board_id: uuid.UUID) -> PersonalBoardModel:
    """Strict: owner only. Used for delete + anything that manages sharing."""
    result = await db.execute(_board_detail_query().where(PersonalBoardModel.id == board_id))
    board = result.scalar_one_or_none()
    if board is None or board.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


async def _get_accessible_board(db: DBSession, user, board_id: uuid.UUID) -> PersonalBoardModel:
    """Owner or an invited collaborator. Used for viewing/editing content."""
    result = await db.execute(_board_detail_query().where(PersonalBoardModel.id == board_id))
    board = result.scalar_one_or_none()
    if board is None or (board.user_id != user.id and user.id not in {c.id for c in board.collaborators}):
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


@router.get("/boards/shared-with-me", response_model=PersonalBoardsListResponse)
async def list_boards_shared_with_me(
    db: DBSession,
    user: PremiumUser,
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = (
        select(PersonalBoardModel)
        .join(personal_board_collaborator_link)
        .where(personal_board_collaborator_link.c.user_id == user.id)
        .order_by(PersonalBoardModel.updated_at.desc())
    )
    count_query = (
        select(func.count())
        .select_from(personal_board_collaborator_link)
        .where(personal_board_collaborator_link.c.user_id == user.id)
    )

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    return PersonalBoardsListResponse(total=total, boards=result.scalars().all())


@router.get("/boards/shared/{share_token}", response_model=SharedBoardResponse)
async def get_shared_board(share_token: str, db: DBSession):
    """Public, unauthenticated — anyone with the link can view (read-only)."""
    result = await db.execute(_board_detail_query().where(PersonalBoardModel.share_token == share_token))
    board = result.scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This share link is invalid or was revoked")

    map_ = await db.get(MapModel, board.map_id)
    detail = SharedBoardResponse.model_validate(board)
    detail.map_name = map_.name if map_ else "Unknown map"
    return detail


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
    return await _get_accessible_board(db, user, board_id)


@router.patch("/boards/{board_id}", response_model=PersonalBoardDetail)
async def update_board(board_id: uuid.UUID, payload: BoardUpdate, db: DBSession, user: PremiumUser):
    board = await _get_accessible_board(db, user, board_id)

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

    return await _get_accessible_board(db, user, board_id)


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(board_id: uuid.UUID, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)
    await db.delete(board)
    await db.commit()


# ─────────────────────────────────────────────
#  Sharing: public link
# ─────────────────────────────────────────────

@router.post("/boards/{board_id}/share", response_model=ShareTokenResponse)
async def create_share_link(board_id: uuid.UUID, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)
    board.share_token = generate_share_token()
    await db.commit()
    return ShareTokenResponse(share_token=board.share_token)


@router.delete("/boards/{board_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(board_id: uuid.UUID, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)
    board.share_token = None
    await db.commit()


# ─────────────────────────────────────────────
#  Sharing: collaborators (edit access by wallet ID)
# ─────────────────────────────────────────────

@router.get("/boards/{board_id}/collaborators", response_model=list[CollaboratorOut])
async def list_collaborators(board_id: uuid.UUID, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)
    return board.collaborators


@router.post("/boards/{board_id}/collaborators", response_model=list[CollaboratorOut], status_code=status.HTTP_201_CREATED)
async def add_collaborator(board_id: uuid.UUID, payload: AddCollaboratorRequest, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)

    wallet_id = payload.wallet_id.strip().upper()
    result = await db.execute(
        select(UserModel).join(UserModel.wallet).where(WalletModel.wallet_id == wallet_id)
    )
    collaborator = result.scalar_one_or_none()
    if collaborator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user found with that Wallet ID")
    if collaborator.id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already own this board")

    if collaborator.id not in {c.id for c in board.collaborators}:
        board.collaborators.append(collaborator)
        await db.commit()
        await db.refresh(board)

    return board.collaborators


@router.delete("/boards/{board_id}/collaborators/{user_id}", response_model=list[CollaboratorOut])
async def remove_collaborator(board_id: uuid.UUID, user_id: uuid.UUID, db: DBSession, user: PremiumUser):
    board = await _get_owned_board(db, user, board_id)
    board.collaborators = [c for c in board.collaborators if c.id != user_id]
    await db.commit()
    await db.refresh(board)
    return board.collaborators
