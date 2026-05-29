from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# ssl=False: tắt SSL negotiation — asyncpg mặc định dùng sslmode=prefer,
# uvloop's C-level DNS resolver có thể fail khi resolve Docker internal hostname qua SSL path.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"ssl": False},
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_timeout=30,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def ping_db() -> None:
    """Kiểm tra kết nối DB khi khởi động. Schema do Alembic quản lý."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
