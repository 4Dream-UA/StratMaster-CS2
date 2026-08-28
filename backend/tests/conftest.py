import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from backend.app.api import deps
from backend.app.core.redis import get_redis
from backend.app.db.database import Base, get_db
from backend.app.db.models import UserModel
from backend.app.main_api import app

# DB 15 — isolated from whatever the app itself uses (DB 0), so rate-limit
# counters from a test run never bleed into (or get confused by) real data.
TEST_REDIS_URL = "redis://localhost:6379/15"

# A dedicated role + database on the same Postgres instance as dev
# (docker-compose publishes it on localhost:5433) — deliberately NOT the
# app's own credentials, so tests never depend on (or risk) real secrets,
# and never touch stratmaster_db itself. Provision once with:
#   docker exec stratmaster_db psql -U stratmaster -d postgres \
#     -c "CREATE ROLE stratmaster_test_role LOGIN PASSWORD 'localtestonly';" \
#     -c "CREATE DATABASE stratmaster_test OWNER stratmaster_test_role;"
TEST_DATABASE_URL = "postgresql+asyncpg://stratmaster_test_role:localtestonly@localhost:5433/stratmaster_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

ALL_TABLES = (
    "promo_redemptions", "transactions", "grenades", "images",
    "strategy_buy_tag_link", "strategies", "buy_tags", "maps",
    "promo_codes", "wallets", "users", "cases",
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    global _test_redis_client
    if _test_redis_client is not None:
        await _test_redis_client.aclose()
        _test_redis_client = None


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Every test starts from an empty database — the ТЗ-mandated 'rollback after each run', implemented as a truncate since the app and the test setup use independent DB sessions."""
    yield
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {', '.join(ALL_TABLES)} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture(autouse=True)
async def _clean_redis():
    """Flushes the isolated test Redis DB after each test so rate-limit
    counters from one test never affect the next."""
    yield
    redis = redis_from_url(TEST_REDIS_URL, decode_responses=True)
    await redis.flushdb()
    await redis.aclose()


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


_test_redis_client = None


def _override_get_redis():
    global _test_redis_client
    if _test_redis_client is None:
        _test_redis_client = redis_from_url(TEST_REDIS_URL, decode_responses=True)
    return _test_redis_client


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_redis, None)


@pytest.fixture
def auth_as():
    """Bypass Telegram initData signing — impersonate a given UserModel for
    the request's lifetime.

    Re-queries the user by id on every call (via the request's own `db`
    dependency) instead of returning the original object from the test's
    `db_session` fixture. That object lives in a different, long-lived
    session — mutating it inside an endpoint (e.g. deducting a balance)
    would never actually flush to the database, and a *different* request
    right after would silently read stale state back out. Matching the
    app's own session per request is what makes multi-request test
    scenarios (buy, then check balance in a follow-up call) trustworthy.
    """
    def _apply(user):
        user_id = user.id

        async def _override(db: deps.DBSession):
            result = await db.execute(
                select(UserModel)
                .options(selectinload(UserModel.wallet))
                .where(UserModel.id == user_id)
            )
            return result.scalar_one()

        app.dependency_overrides[deps.get_current_user] = _override
        app.dependency_overrides[deps.get_optional_user] = _override
        return user

    yield _apply
    app.dependency_overrides.pop(deps.get_current_user, None)
    app.dependency_overrides.pop(deps.get_optional_user, None)
