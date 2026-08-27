import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.app.api.deps import AdminUser
from backend.app.core.config import UPLOAD_DIR

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("/admin/uploads", status_code=status.HTTP_201_CREATED)
async def upload_image(admin_user: AdminUser, file: UploadFile = File(...)):
    ext = EXTENSION_BY_CONTENT_TYPE.get(file.content_type)
    if ext is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG, PNG, WEBP or GIF images are allowed")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be under 5 MB")

    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / filename).write_bytes(contents)

    return {"url": f"/uploads/{filename}"}
