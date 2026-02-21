import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db, settings

settings.api_key = "test-api-key"   # override before any tests run


# --- Test database setup ---

# StaticPool keeps a single in-memory SQLite connection alive for the
# whole session. Without it, each connection would get a fresh empty DB.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    # tells pytest-asyncio which event loop policy to use
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session",  loop_scope="session")
async def test_engine():
    """
    Creates a single async SQLite engine for the whole test session.
    scope="session" means this runs once and is reused across all tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # required for SQLite
        poolclass=StaticPool,                        # single connection, stays alive
    )

    # Create all tables — equivalent to running alembic upgrade head
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine  # hand the engine to whoever requested this fixture

    # Teardown — drop all tables when the session ends
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Provides a clean database session for each test using transaction rollback.
    scope is per-test by default (no scope= argument).

    The trick: we open a transaction, run the test, then roll it back.
    The next test starts with a completely clean database.
    """
    async with test_engine.connect() as conn:
        await conn.begin()                          # open a transaction

        # Create a session bound to this connection
        session_factory = async_sessionmaker(conn, expire_on_commit=False)
        session = session_factory()

        yield session                               # hand the session to the test

        await session.close()
        await conn.rollback()                       # undo everything the test did


@pytest_asyncio.fixture
async def client(db_session):
    """
    Provides an async HTTP test client with the test DB wired in.

    app.dependency_overrides swaps get_db() for a function that returns
    our test session instead of a real Postgres session.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()               # clean up after test


@pytest.fixture
def auth_headers():
    """
    Returns headers with a valid API key.
    Tests that need auth request this fixture.
    """
    return {"X-API-Key": "test-api-key"}