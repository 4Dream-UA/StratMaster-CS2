import os

from backend.app.core.config import UPLOAD_DIR
from backend.tests.factories import make_user


async def test_admin_can_upload_image(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.post(
        "/api/admin/uploads",
        files={"file": ("cover.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png")},
    )
    assert resp.status_code == 201
    url = resp.json()["url"]
    assert url.startswith("/uploads/")
    assert url.endswith(".png")

    saved_path = UPLOAD_DIR / url.removeprefix("/uploads/")
    assert saved_path.exists()
    os.remove(saved_path)


async def test_upload_rejects_non_image_content_type(client, db_session, auth_as):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)

    resp = await client.post(
        "/api/admin/uploads",
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert resp.status_code == 400


async def test_upload_rejects_oversized_file(client, db_session, auth_as, monkeypatch):
    admin = await make_user(db_session, is_admin=True)
    auth_as(admin)
    monkeypatch.setattr("backend.app.api.routers.uploads.MAX_UPLOAD_BYTES", 10)

    resp = await client.post(
        "/api/admin/uploads",
        files={"file": ("big.png", b"0" * 20, "image/png")},
    )
    assert resp.status_code == 400


async def test_upload_requires_admin(client, db_session, auth_as):
    user = await make_user(db_session, is_admin=False)
    auth_as(user)

    resp = await client.post(
        "/api/admin/uploads",
        files={"file": ("a.png", b"x", "image/png")},
    )
    assert resp.status_code == 403
