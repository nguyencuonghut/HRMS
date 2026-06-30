"""Endpoint danh sách hợp đồng toàn công ty (4.1)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.employee_contract import ContractListPage
from app.services import access_scope_service, employee_contract_service

router = APIRouter()


@router.get("", response_model=ContractListPage, tags=["Hợp đồng"])
async def list_contracts_global(
    keyword:          Optional[str]  = Query(None, description="Tìm số HĐ hoặc tên nhân viên"),
    employee_id:      Optional[int]  = Query(None),
    document_kind:    Optional[str]  = Query(None, description="labor_contract | contract_appendix"),
    status:           Optional[str]  = Query(None, description="active | expired | terminated | draft"),
    category_id:      Optional[int]  = Query(None),
    expiring_within:  Optional[int]  = Query(None, ge=1, le=365, description="HĐ hết hạn trong N ngày tới"),
    page:             int            = Query(1, ge=1),
    page_size:        int            = Query(25, ge=1, le=200),
    current_user: User = require_permission("contracts:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
):
    if employee_id is not None:
        await access_scope_service.ensure_employee_access(
            session,
            current_user,
            permission_codes=access_scope_service.CONTRACT_SCOPE_PERMISSIONS,
            employee_id=employee_id,
        )
    return await employee_contract_service.list_contracts_global(
        session,
        keyword=keyword,
        employee_id=employee_id,
        document_kind=document_kind,
        status=status,
        category_id=category_id,
        expiring_within=expiring_within,
        allowed_department_ids=allowed_department_ids,
        page=page,
        page_size=page_size,
    )
