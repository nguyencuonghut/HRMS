from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentTreeNode, DepartmentUpdate
from app.services import department_service

router = APIRouter()


@router.get("", response_model=list[DepartmentRead], summary="Danh sách phòng/ban (phẳng)")
async def list_departments(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái; bỏ trống = lấy tất cả"),
    session: AsyncSession = Depends(get_session),
):
    return await department_service.get_list(session, is_active=is_active)


@router.get("/tree", response_model=list[DepartmentTreeNode], summary="Cây phân cấp phòng/ban")
async def get_department_tree(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái; bỏ trống = lấy tất cả"),
    session: AsyncSession = Depends(get_session),
):
    return await department_service.get_tree(session, is_active=is_active)


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED, summary="Tạo phòng/ban mới")
async def create_department(
    body: DepartmentCreate,
    session: AsyncSession = Depends(get_session),
):
    return await department_service.create(session, body)


@router.get("/{dept_id}", response_model=DepartmentRead, summary="Chi tiết phòng/ban")
async def get_department(
    dept_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await department_service.get_by_id(session, dept_id)


@router.put("/{dept_id}", response_model=DepartmentRead, summary="Cập nhật phòng/ban")
async def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    session: AsyncSession = Depends(get_session),
):
    return await department_service.update(session, dept_id, body)


@router.delete("/{dept_id}", summary="Xóa phòng/ban")
async def delete_department(
    dept_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await department_service.delete(session, dept_id)
