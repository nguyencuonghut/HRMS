from contextlib import asynccontextmanager
from sqlalchemy import text

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.database import AsyncSessionLocal, ping_db
from app.core.rate_limit import limiter
from app.core.storage import ensure_bucket
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.api.v1.router import router as api_v1_router
from app.seeds import rbac as rbac_seed
from app.seeds import notification_templates as notif_seed


async def seed_rbac_if_possible() -> None:
    """Auto-seed RBAC only after auth tables exist."""
    async with AsyncSessionLocal() as session:
        users_table_exists = (await session.execute(
            text("SELECT to_regclass('users') IS NOT NULL")
        )).scalar()
        if not users_table_exists:
            return

        user_count = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar()
        if user_count == 0:
            await rbac_seed.run(session)


async def seed_notifications_if_possible() -> None:
    """Auto-seed notification templates nếu table đã tồn tại."""
    async with AsyncSessionLocal() as session:
        table_exists = (await session.execute(
            text("SELECT to_regclass('notification_templates') IS NOT NULL")
        )).scalar()
        if not table_exists:
            return
        await notif_seed.seed_notification_templates(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket()
    await ping_db()
    await seed_rbac_if_possible()
    await seed_notifications_if_possible()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Forwarded-For"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
