from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import departments

router = APIRouter()
router.include_router(auth.router,        prefix="/auth",        tags=["Xác thực"])
router.include_router(departments.router, prefix="/departments", tags=["Cơ cấu tổ chức"])
