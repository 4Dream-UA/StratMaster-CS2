from redis.asyncio import Redis, from_url

from backend.app.core.config import settings

_redis_client: Redis | None = None


def get_redis() -> Redis:
    """FastAPI dependency — a shared async Redis client. Overridden in tests
    (backend/tests/conftest.py) to point at an isolated DB slot instead of
    the app's real one."""
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(settings.redis_url, decode_responses=True)
    return _redis_client
