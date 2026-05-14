from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import admin_units
from app.api.v1.endpoints import departments
from app.api.v1.endpoints import job_titles
from app.api.v1.endpoints import job_positions
from app.api.v1.endpoints import org_history
from app.api.v1.endpoints import users
from app.api.v1.endpoints import roles
from app.api.v1.endpoints import audit_logs

router = APIRouter()
router.include_router(auth.router,          prefix="/auth",          tags=["Xác thực"])
router.include_router(admin_units.router,   prefix="/admin-units",   tags=["Danh mục hành chính"])
router.include_router(admin_units.hierarchy_router, prefix="/admin-hierarchies", tags=["Danh mục hành chính"])
router.include_router(admin_units.lookup_router, tags=["Danh mục hành chính"])
router.include_router(departments.router,   prefix="/departments",   tags=["Cơ cấu tổ chức"])
router.include_router(job_titles.router,    prefix="/job-titles",    tags=["Cơ cấu tổ chức"])
router.include_router(job_positions.router, prefix="/job-positions", tags=["Cơ cấu tổ chức"])
router.include_router(org_history.router,   prefix="/org-history",   tags=["Cơ cấu tổ chức"])
router.include_router(users.router,         prefix="/users",         tags=["Quản lý người dùng"])
router.include_router(roles.router,         prefix="/roles",         tags=["Vai trò & Quyền"])
router.include_router(audit_logs.router,    prefix="/audit-logs",    tags=["Nhật ký hệ thống"])
