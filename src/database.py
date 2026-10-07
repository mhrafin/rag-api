from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()

# We need async so that FastAPI can handle many requests at the same time.
# Synchronous drivers waits for every database round trip. We don't want that with FastAPI.
async_engine = create_async_engine(settings.database_url)

async_session_maker = async_sessionmaker(bind=async_engine)


async def init_db():
    async with async_engine.begin() as conn:
        # 1. Enable the pgvector extension in PostgreSQL
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))


async def get_session():
    """A generator that creates a fresh session. If exception happens, the session is rolled back else the session is committed.

    Yields:
        AsyncSession: An async session
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
