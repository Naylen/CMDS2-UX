"""SQLite database setup with async SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from web.backend.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    async with async_session() as session:
        yield session


async def init_db():
    """Create tables on startup."""
    from web.backend.models.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
