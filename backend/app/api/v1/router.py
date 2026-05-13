from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import departments
from app.api.v1.endpoints import job_titles
from app.api.v1.endpoints import job_positions
from app.api.v1.endpoints import org_history

router = APIRouter()
router.include_router(auth.router,          prefix="/auth",          tags=["Xác thực"])
router.include_router(departments.router,   prefix="/departments",   tags=["Cơ cấu tổ chức"])
router.include_router(job_titles.router,    prefix="/job-titles",    tags=["Cơ cấu tổ chức"])
router.include_router(job_positions.router, prefix="/job-positions", tags=["Cơ cấu tổ chức"])
router.include_router(org_history.router,   prefix="/org-history",   tags=["Cơ cấu tổ chức"])
