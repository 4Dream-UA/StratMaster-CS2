from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.api.deps import AdminUser, DBSession, OptionalUser
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import ErrorLogModel

router = APIRouter()


class ReportErrorRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    stack: str | None = Field(None, max_length=8000)
    url: str | None = Field(None, max_length=512)


class ErrorLogOut(BaseModel):
    id: str
    source: str
    message: str
    stack: str | None = None
    url: str | None = None
    username: str | None = None
    created_at: datetime


@router.post(
    "/errors", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("error_report", max_requests=20, window_seconds=60, identity_source="ip"))],
)
async def report_frontend_error(payload: ReportErrorRequest, db: DBSession, current_user: OptionalUser):
    """Best-effort — no auth required (a broken auth flow is exactly the
    kind of thing worth logging), rate-limited by IP since there's no
    reliable identity for a caller that may not be logged in yet."""
    db.add(ErrorLogModel(
        source="frontend", message=payload.message, stack=payload.stack, url=payload.url,
        user_id=current_user.id if current_user else None,
    ))
    await db.commit()


@router.get("/admin/errors", response_model=list[ErrorLogOut])
async def list_error_logs(db: DBSession, admin_user: AdminUser, limit: int = 50):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(ErrorLogModel)
        .options(selectinload(ErrorLogModel.user))
        .order_by(ErrorLogModel.created_at.desc())
        .limit(min(limit, 200))
    )
    return [
        ErrorLogOut(
            id=str(e.id), source=e.source, message=e.message, stack=e.stack, url=e.url,
            username=e.user.username if e.user else None, created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]
