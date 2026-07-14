from contextlib import asynccontextmanager
from sqlalchemy import text

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.database import AsyncSessionLocal, ping_db
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.core.storage import ensure_bucket
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.backup_readonly import BackupReadOnlyMiddleware
from app.api.v1.router import router as api_v1_router
from app.seeds import rbac as rbac_seed
from app.seeds import notification_templates as notif_seed

# ── Structured logging (setup before everything else) ─────────────────────────
setup_logging(debug=settings.DEBUG)

# ── Sentry error monitoring ────────────────────────────────────────────────────
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.05,
        send_default_pii=False,
    )


async def seed_rbac_if_possible() -> None:
    """Auto-seed local RBAC users only in explicit local/dev environments."""
    if settings.ENVIRONMENT.lower() not in {"development", "dev", "local", "test"}:
        return

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
    """Auto-seed notification templates only in explicit local/dev environments."""
    if settings.ENVIRONMENT.lower() not in {"development", "dev", "local", "test"}:
        return

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
app.add_middleware(RequestIDMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(BackupReadOnlyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Forwarded-For"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
    max_age=600,
)

app.include_router(api_v1_router, prefix="/api/v1")


async def _run_dependency_checks() -> tuple[dict[str, str], bool]:
    """Chạy tất cả dependency checks, trả về (checks dict, all_ok)."""
    import redis.asyncio as aioredis

    checks: dict[str, str] = {}
    all_ok = True

    # Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        all_ok = False

    # Redis
    try:
        r = aioredis.from_url(settings.effective_redis_url, socket_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        all_ok = False

    # MinIO
    try:
        from app.core.storage import _client, bucket_name
        _client().bucket_exists(bucket_name())
        checks["minio"] = "ok"
    except Exception as exc:
        checks["minio"] = f"error: {exc}"
        all_ok = False

    return checks, all_ok


@app.get("/health/live", tags=["System"], summary="Liveness probe")
async def liveness() -> dict:
    """Kubernetes liveness probe — app còn sống, không check dependencies.
    Nếu endpoint này không trả về 200, k8s sẽ restart container.
    """
    return {"status": "alive", "version": settings.APP_VERSION}


@app.get("/health/ready", tags=["System"], summary="Readiness probe")
async def readiness():
    """Kubernetes readiness probe — kiểm tra DB + Redis + MinIO.
    Trả về 503 nếu bất kỳ dependency nào fail → k8s ngừng route traffic vào.
    """
    from fastapi.responses import JSONResponse

    checks, all_ok = await _run_dependency_checks()
    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status":      "ready" if all_ok else "not_ready",
            "version":     settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks":      checks,
        },
    )


@app.get("/health", tags=["System"], summary="Health check (full)")
async def health_check():
    """Backward-compat health check — tương đương /health/ready nhưng luôn trả 200."""
    from fastapi.responses import JSONResponse

    checks, all_ok = await _run_dependency_checks()
    return JSONResponse(
        status_code=200,   # luôn 200 để không break monitoring cũ
        content={
            "status":      "ok" if all_ok else "degraded",
            "version":     settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks":      checks,
        },
    )
