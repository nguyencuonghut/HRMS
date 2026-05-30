import time

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

logger = structlog.get_logger(__name__)

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

# ── Slow query monitoring ─────────────────────────────────────────────────────
# Dùng sync_engine vì SQLAlchemy cursor events là synchronous
# Threshold cấu hình qua settings.SLOW_QUERY_THRESHOLD_MS (default 500ms)

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("_query_start_time", []).append(time.monotonic())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_execute(conn, cursor, statement, parameters, context, executemany):
    stack = conn.info.get("_query_start_time")
    if not stack:
        return
    elapsed_ms = (time.monotonic() - stack.pop()) * 1000
    threshold = settings.SLOW_QUERY_THRESHOLD_MS
    if elapsed_ms >= threshold:
        # Truncate để tránh log quá dài; loại bỏ whitespace thừa
        stmt_preview = " ".join(statement.split())[:300]
        logger.warning(
            "slow_query",
            duration_ms=int(elapsed_ms),
            threshold_ms=threshold,
            statement=stmt_preview,
        )


async def ping_db() -> None:
    """Kiểm tra kết nối DB khi khởi động. Schema do Alembic quản lý."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
