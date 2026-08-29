from fastapi import APIRouter

from backend.app.api.deps import AdminUser, DBSession
from backend.app.db.models import AppSettingsModel
from backend.app.schemas.settings import AppSettingsOut, AppSettingsUpdate

router = APIRouter()


async def _get_or_create_settings(db: DBSession) -> AppSettingsModel:
    settings = await db.get(AppSettingsModel, 1)
    if settings is None:
        settings = AppSettingsModel(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/settings", response_model=AppSettingsOut)
async def get_settings(db: DBSession):
    """Public — the frontend needs this before the user is authenticated
    (it renders the header/logo on every page, including the login gate)."""
    return await _get_or_create_settings(db)


@router.patch("/admin/settings", response_model=AppSettingsOut)
async def update_settings(payload: AppSettingsUpdate, db: DBSession, admin_user: AdminUser):
    settings = await _get_or_create_settings(db)
    settings.logo_url = payload.logo_url
    await db.commit()
    await db.refresh(settings)
    return settings
