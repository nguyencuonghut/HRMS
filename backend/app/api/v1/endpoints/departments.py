from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentHeadRead,
    DepartmentHeadUpsert,
    DepartmentDetailRead,
    DepartmentRead,
    DepartmentTreeNode,
    DepartmentUpdate,
)
from app.schemas.employee_code_rule import EmployeeCodeSequenceRuleRead, EmployeeCodeSequenceRuleUpsert
from app.services import auth_service, department_head_service, department_service, employee_code_rule_service

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


@router.get("/{dept_id}/detail", response_model=DepartmentDetailRead, summary="Chi tiết phòng/ban cho trang detail")
async def get_department_detail(
    dept_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await department_service.get_detail(session, dept_id)


@router.get("/{dept_id}/head", response_model=DepartmentHeadRead | None, summary="Người đứng đầu hiện hành của đơn vị")
async def get_department_head(
    dept_id: int,
    _: User = require_permission("org:view"),
    session: AsyncSession = Depends(get_session),
):
    return await department_head_service.get_current_head(session, dept_id)


@router.put("/{dept_id}/head", response_model=DepartmentHeadRead, summary="Gán hoặc thay đổi người đứng đầu đơn vị")
async def upsert_department_head(
    dept_id: int,
    body: DepartmentHeadUpsert,
    request: Request,
    current_user: User = require_permission("org:edit"),
    session: AsyncSession = Depends(get_session),
):
    result, action, old_data, new_data = await department_head_service.upsert_head(
        session, dept_id, body, current_user.id
    )
    await auth_service.log_audit(
        session,
        current_user.id,
        action,
        entity_type="department_head",
        entity_id=result.id,
        entity_name=result.employee.full_name,
        old_data=old_data,
        new_data=new_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return result


@router.delete("/{dept_id}/head", summary="Gỡ người đứng đầu hiện hành của đơn vị")
async def delete_department_head(
    dept_id: int,
    request: Request,
    current_user: User = require_permission("org:edit"),
    session: AsyncSession = Depends(get_session),
):
    old_data, new_data = await department_head_service.delete_current_head(session, dept_id, current_user.id)
    await auth_service.log_audit(
        session,
        current_user.id,
        "DELETE",
        entity_type="department_head",
        entity_id=old_data["id"],
        entity_name=f"department:{dept_id}",
        old_data=old_data,
        new_data=new_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return {"message": "Đã gỡ người đứng đầu hiện hành"}


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


@router.get(
    "/{dept_id}/employee-code-rule",
    response_model=EmployeeCodeSequenceRuleRead | None,
    summary="Rule hệ mã của phòng/ban",
)
async def get_department_employee_code_rule(
    dept_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.get_department_rule(session, dept_id)


@router.put(
    "/{dept_id}/employee-code-rule",
    response_model=EmployeeCodeSequenceRuleRead,
    summary="Tạo/cập nhật rule hệ mã cho phòng/ban",
)
async def upsert_department_employee_code_rule(
    dept_id: int,
    body: EmployeeCodeSequenceRuleUpsert,
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.upsert_department_rule(session, dept_id, body)


@router.delete(
    "/{dept_id}/employee-code-rule",
    summary="Xóa rule hệ mã của phòng/ban",
)
async def delete_department_employee_code_rule(
    dept_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.delete_department_rule(session, dept_id)
