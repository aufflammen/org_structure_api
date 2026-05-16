from dotenv import load_dotenv

load_dotenv(".env.test")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_config
from app.core.database import get_session
from app.main import app
from app.models.base import Base
from app.enums.env import Env


@pytest.fixture(scope="session")
async def engine():
    """Create schema once per test session using ORM metadata."""
    config = get_config()
    assert config.env == Env.TEST

    engine = create_async_engine(config.db.url, pool_pre_ping=True)
    async with engine.begin() as connect:  # type: ignore
        await connect.run_sync(Base.metadata.drop_all)
        await connect.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as connect:  # type: ignore
        await connect.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
async def reset_tables(engine):
    """Truncate data between tests for isolation."""
    yield
    async with engine.begin() as connect:  # type: ignore
        await connect.execute(text("TRUNCATE departments RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client(engine):
    """HTTP client with DB session override wired to the test engine."""

    async def _session_override():
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
