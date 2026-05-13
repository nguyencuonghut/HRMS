from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import AsyncSessionLocal, ping_db
from app.core.storage import ensure_bucket
from app.api.v1.router import router as api_v1_router
from app.seeds import rbac as rbac_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket()
    await ping_db()
    # Auto-seed RBAC nếu chưa có user nào (first boot)
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        count = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar()
        if count == 0:
            await rbac_seed.run(session)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
