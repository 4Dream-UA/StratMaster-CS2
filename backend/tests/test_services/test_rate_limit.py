from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from backend.app.core.rate_limit import rate_limit
from backend.app.core.redis import get_redis
from backend.tests.conftest import _override_get_redis

# A throwaway app exercising the rate limiter in isolation — no Telegram
# auth involved, so the tests below are purely about the limiter's own
# counting/bucketing behavior against a real Redis (the isolated test DB).
_probe_app = FastAPI()
_probe_app.dependency_overrides[get_redis] = _override_get_redis


@_probe_app.get("/header-limited", dependencies=[Depends(rate_limit("probe_header", max_requests=3, window_seconds=60))])
async def _header_limited():
    return {"ok": True}


@_probe_app.get(
    "/ip-limited",
    dependencies=[Depends(rate_limit("probe_ip", max_requests=2, window_seconds=60, identity_source="ip"))],
)
async def _ip_limited():
    return {"ok": True}


async def _probe_client():
    transport = ASGITransport(app=_probe_app)
    return AsyncClient(transport=transport, base_url="http://probe")


async def test_allows_requests_under_the_limit():
    async with await _probe_client() as client:
        headers = {"x-init-data": "user-a"}
        for _ in range(3):
            resp = await client.get("/header-limited", headers=headers)
            assert resp.status_code == 200


async def test_blocks_requests_over_the_limit():
    async with await _probe_client() as client:
        headers = {"x-init-data": "user-b"}
        for _ in range(3):
            await client.get("/header-limited", headers=headers)
        resp = await client.get("/header-limited", headers=headers)
        assert resp.status_code == 429


async def test_different_identities_get_independent_buckets():
    async with await _probe_client() as client:
        for _ in range(3):
            assert (await client.get("/header-limited", headers={"x-init-data": "user-c"})).status_code == 200
        # A different caller isn't affected by user-c's usage.
        resp = await client.get("/header-limited", headers={"x-init-data": "user-d"})
        assert resp.status_code == 200


async def test_ip_identity_source_ignores_the_header():
    async with await _probe_client() as client:
        # Same test client => same source IP regardless of header value, so
        # these two "different users" share one IP-keyed bucket.
        await client.get("/ip-limited", headers={"x-init-data": "user-e"})
        await client.get("/ip-limited", headers={"x-init-data": "user-f"})
        resp = await client.get("/ip-limited", headers={"x-init-data": "user-g"})
        assert resp.status_code == 429
