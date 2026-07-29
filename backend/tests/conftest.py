import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.api import deps
from backend.app.db.database import Base, get_db
from backend.app.main_api import app

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
    "promo_codes", "wallets", "users",
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


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Every test starts from an empty database — the ТЗ-mandated 'rollback after each run', implemented as a truncate since the app and the test setup use independent DB sessions."""
    yield
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {', '.join(ALL_TABLES)} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_as():
    """Bypass Telegram initData signing — impersonate a given UserModel for the request's lifetime."""
    def _apply(user):
        app.dependency_overrides[deps.get_current_user] = lambda: user
        app.dependency_overrides[deps.get_optional_user] = lambda: user
        return user

    yield _apply
    app.dependency_overrides.pop(deps.get_current_user, None)
    app.dependency_overrides.pop(deps.get_optional_user, None)
