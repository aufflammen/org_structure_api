from dotenv import load_dotenv

load_dotenv(".env.test")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_config
from app.core.database import get_session
from app.enums.env import Env
from app.main import app
from app.models.base import Base


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    """Create schema once per test session using ORM metadata."""
    config = get_config()
    assert config.env == Env.TEST

    test_engine = create_async_engine(config.db.url, pool_pre_ping=True)
    async with test_engine.begin() as connect:
        await connect.run_sync(Base.metadata.drop_all)
        await connect.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as connect:
        await connect.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def reset_tables(engine: AsyncEngine) -> AsyncGenerator[None]:
    """Truncate data after each test for isolation."""
    yield
    async with engine.begin() as connect:
        await connect.execute(text("TRUNCATE departments RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient]:
    """HTTP client with DB session override wired to the test engine."""

    async def _session_override() -> AsyncGenerator[AsyncSession]:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session_override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
