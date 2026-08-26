import hashlib

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from backend.app.core.redis import get_redis


def rate_limit(bucket: str, max_requests: int, window_seconds: int, identity_source: str = "header"):
    """FastAPI dependency factory — a fixed-window counter in Redis, keyed
    by (bucket, caller identity). `identity_source`:
      - "header": the X-Init-Data header (present on every authenticated
        request the frontend makes) — hashed so raw Telegram initData never
        ends up as a Redis key.
      - "ip": the client's IP, for endpoints called before we have any
        identity yet (e.g. /auth itself).
    """

    async def _dependency(request: Request, redis: Redis = Depends(get_redis)):
        if identity_source == "ip":
            identity = request.client.host if request.client else "unknown"
        else:
            identity = request.headers.get("x-init-data") or (
                request.client.host if request.client else "unknown"
            )
        identity_hash = hashlib.sha256(identity.encode()).hexdigest()[:16]
        redis_key = f"ratelimit:{bucket}:{identity_hash}"

        current = await redis.incr(redis_key)
        if current == 1:
            await redis.expire(redis_key, window_seconds)

        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please slow down and try again shortly.",
            )

    return _dependency
