"""Endpoints Báo cáo Hợp đồng (11.5)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.contract_report import (
    ContractSummaryOut,
    ContractExpiringPage,
    ContractByTypeOut,
    ContractForecastOut,
    ContractHistoryOut,
)
from app.services import access_scope_service, contract_export_service, contract_report_service

router = APIRouter()


@router.get("/summary", response_model=ContractSummaryOut)
async def get_summary(
    department_id: Optional[int] = Query(None),
    current_user: User = require_permission("contracts:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> ContractSummaryOut:
    """Lấy dữ liệu chỉ số KPI tổng hợp cho hợp đồng lao động."""
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.CONTRACT_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    return await contract_report_service.get_summary(
        session,
        department_id=department_id,
        allowed_department_ids=None if department_id is not None else allowed_department_ids,
    )


@router.get("/expiring", response_model=ContractExpiringPage)
async def get_expiring(
    days_ahead: int = Query(90, ge=1, le=365),
    department_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = require_permission("contracts:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> ContractExpiringPage:
    """Lấy danh sách các hợp đồng lao động sắp hết hạn (có phân trang và tìm kiếm)."""
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.CONTRACT_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    return await contract_report_service.get_expiring(
        session,
        days_ahead=days_ahead,
        department_id=department_id,
        keyword=keyword,
        allowed_department_ids=None if department_id is not None else allowed_department_ids,
        page=page,
        page_size=page_size,
    )


@router.get("/by-type", response_model=ContractByTypeOut)
async def get_by_type(
    department_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: User = require_permission("contracts:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> ContractByTypeOut:
    """Lấy thống kê cơ cấu loại hợp đồng lao động."""
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.CONTRACT_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    return await contract_report_service.get_by_type(
        session,
        department_id=department_id,
        year=year,
        allowed_department_ids=None if department_id is not None else allowed_department_ids,
    )


@router.get("/expiry-forecast", response_model=ContractForecastOut)
async def get_expiry_forecast(
    months_ahead: int = Query(12, ge=1, le=24),
    _current_user: User = require_permission("contracts:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> ContractForecastOut:
    """Dự báo số lượng hợp đồng hết hạn trong 12 hoặc 24 tháng tới."""
    return await contract_report_service.get_expiry_forecast(
        session,
        months_ahead=months_ahead,
        allowed_department_ids=allowed_department_ids,
    )


@router.get("/history", response_model=ContractHistoryOut)
async def get_history(
    employee_id: int = Query(...),
    current_user: User = require_permission("contracts:view"),
    _: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> ContractHistoryOut:
    """Tra cứu lịch sử toàn bộ các hợp đồng và phụ lục của nhân viên."""
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=access_scope_service.CONTRACT_SCOPE_PERMISSIONS,
        employee_id=employee_id,
    )
    return await contract_report_service.get_history(
        session,
        employee_id=employee_id,
    )


@router.get("/export")
async def export_contracts(
    department_id: Optional[int] = Query(None),
    status: str = Query("active", pattern="^(active|expired|all)$"),
    days_ahead: Optional[int] = Query(None, ge=1, le=365),
    current_user: User = require_permission("contracts:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.CONTRACT_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Xuất danh sách hợp đồng ra file Excel có định dạng màu sắc cảnh báo theo urgency."""
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.CONTRACT_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    buf = await contract_export_service.export_contracts_xlsx(
        session,
        department_id=department_id,
        status=status,
        days_ahead=days_ahead,
        allowed_department_ids=None if department_id is not None else allowed_department_ids,
    )
    filename = "bao_cao_hop_dong.xlsx"
    if days_ahead is not None:
        filename = f"hop_dong_sap_het_han_{days_ahead}_ngay.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
