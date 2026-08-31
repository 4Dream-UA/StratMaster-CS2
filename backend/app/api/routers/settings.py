from fastapi import APIRouter

from backend.app.api.deps import AdminUser, DBSession
from backend.app.core.config import settings as app_config
from backend.app.db.models import AppSettingsModel
from backend.app.schemas.settings import AppSettingsOut, AppSettingsUpdate
from backend.app.services import ai_agent

router = APIRouter()


async def _get_or_create_settings(db: DBSession) -> AppSettingsModel:
    settings = await db.get(AppSettingsModel, 1)
    if settings is None:
        settings = AppSettingsModel(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


def _out(row: AppSettingsModel) -> AppSettingsOut:
    return AppSettingsOut(
        logo_url=row.logo_url,
        ai_agent_enabled=row.ai_agent_enabled,
        ai_agent_configured=ai_agent.is_configured(),
        ai_agent_model=app_config.ai_agent_model if ai_agent.is_configured() else "",
    )


@router.get("/settings", response_model=AppSettingsOut)
async def get_settings(db: DBSession):
    """Public — the frontend needs this before the user is authenticated
    (it renders the header/logo on every page, including the login gate).
    Only the model *name* is exposed, never the key."""
    return _out(await _get_or_create_settings(db))


@router.patch("/admin/settings", response_model=AppSettingsOut)
async def update_settings(payload: AppSettingsUpdate, db: DBSession, admin_user: AdminUser):
    row = await _get_or_create_settings(db)
    row.logo_url = payload.logo_url
    if payload.ai_agent_enabled is not None:
        row.ai_agent_enabled = payload.ai_agent_enabled
    await db.commit()
    await db.refresh(row)
    return _out(row)
