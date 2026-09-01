import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.app.api.deps import AdminUser, PremiumUser
from backend.app.core.config import UPLOAD_DIR

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def _save_upload(file: UploadFile) -> str:
    """Validates and writes an uploaded image, returning its served URL.
    Shared by every upload endpoint regardless of who's allowed to call it."""
    ext = EXTENSION_BY_CONTENT_TYPE.get(file.content_type)
    if ext is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG, PNG, WEBP or GIF images are allowed")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be under 5 MB")

    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / filename).write_bytes(contents)

    return f"/uploads/{filename}"


@router.post("/admin/uploads", status_code=status.HTTP_201_CREATED)
async def upload_image(admin_user: AdminUser, file: UploadFile = File(...)):
    return {"url": await _save_upload(file)}


@router.post("/forum/uploads", status_code=status.HTTP_201_CREATED)
async def upload_forum_image(user: PremiumUser, file: UploadFile = File(...)):
    """Same validation as the admin upload — any premium user can attach an
    image to a forum post, but only to a forum post (this endpoint's URL
    isn't wired into any admin content field)."""
    return {"url": await _save_upload(file)}


@router.post("/boards/uploads", status_code=status.HTTP_201_CREATED)
async def upload_board_image(user: PremiumUser, file: UploadFile = File(...)):
    """The backdrop for a personal tactics board. Its own route rather than
    reusing the forum one purely so the permission each endpoint grants stays
    readable from its URL."""
    return {"url": await _save_upload(file)}
