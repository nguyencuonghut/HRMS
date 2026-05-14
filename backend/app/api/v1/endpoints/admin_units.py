from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.catalog import (
    AddressSystemRead,
    AdministrativeImportBatchRead,
    AdministrativeImportRequest,
    AdministrativeUnitListPage,
    AdministrativeUnitCreate,
    AdministrativeUnitRead,
    AdministrativeUnitUpdate,
    AdministrativeTreeNode,
    ValidateDualLocationPathsRequest,
    ValidateDualLocationPathsResult,
    ValidateLocationPathRequest,
    ValidateLocationPathResult,
)
from app.services import administrative_unit_service, auth_service

router = APIRouter()
hierarchy_router = APIRouter()
lookup_router = APIRouter()


@router.get("", response_model=AdministrativeUnitListPage, summary="Danh sách đơn vị hành chính")
async def list_admin_units(
    system_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    unit_type: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.list_units_page(
        session,
        system_type=system_type,
        is_active=is_active,
        unit_type=unit_type,
        province_code=province_code,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AdministrativeUnitRead, status_code=status.HTTP_201_CREATED, summary="Tạo đơn vị hành chính")
async def create_admin_unit(
    body: AdministrativeUnitCreate,
    request: Request,
    current_user: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    unit = await administrative_unit_service.create_unit(session, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "CREATE",
        entity_type="administrative_unit",
        entity_id=unit.id,
        entity_name=unit.name,
        new_data={
            "code": unit.code,
            "source_code": unit.source_code,
            "unit_type": unit.unit_type,
            "province_code": unit.province_code,
            "is_active": unit.is_active,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(unit)
    return unit


@router.post("/import", summary="Import dữ liệu hành chính")
async def import_admin_units(
    body: AdministrativeImportRequest,
    request: Request,
    current_user: User = require_permission("catalog:import"),
    session: AsyncSession = Depends(get_session),
):
    payload = body.model_copy(
        update={"imported_by": body.imported_by if body.imported_by is not None else current_user.id}
    )
    result = await administrative_unit_service.run_import(session, payload)
    await auth_service.log_audit(
        session,
        current_user.id,
        "IMPORT",
        entity_type="administrative_import_batch",
        entity_id=result.batch_id,
        entity_name=f"{payload.source_name}:{payload.source_version}",
        new_data={
            "system_type": payload.system_type,
            "mode": payload.mode,
            "source_name": payload.source_name,
            "source_version": payload.source_version,
            "batch_status": result.batch_status,
            "total_rows": result.total_rows,
            "success_rows": result.success_rows,
            "failed_rows": result.failed_rows,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return result


@router.get("/import-batches", response_model=list[AdministrativeImportBatchRead], summary="Lịch sử import dữ liệu hành chính")
async def list_import_batches(
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.list_import_batches(session)


@router.get("/{unit_id}", response_model=AdministrativeUnitRead, summary="Chi tiết đơn vị hành chính")
async def get_admin_unit(
    unit_id: int,
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.get_by_id(session, unit_id)


@router.put("/{unit_id}", response_model=AdministrativeUnitRead, summary="Cập nhật đơn vị hành chính")
async def update_admin_unit(
    unit_id: int,
    body: AdministrativeUnitUpdate,
    request: Request,
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    existing = await administrative_unit_service.get_by_id(session, unit_id)
    old_data = {
        "name": existing.name,
        "official_name": existing.official_name,
        "province_code": existing.province_code,
        "is_active": existing.is_active,
        "effective_from": existing.effective_from.isoformat() if existing.effective_from else None,
        "effective_to": existing.effective_to.isoformat() if existing.effective_to else None,
    }
    unit = await administrative_unit_service.update_unit(session, unit_id, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "UPDATE",
        entity_type="administrative_unit",
        entity_id=unit.id,
        entity_name=unit.name,
        old_data=old_data,
        new_data={
            "name": unit.name,
            "official_name": unit.official_name,
            "province_code": unit.province_code,
            "is_active": unit.is_active,
            "effective_from": unit.effective_from.isoformat() if unit.effective_from else None,
            "effective_to": unit.effective_to.isoformat() if unit.effective_to else None,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(unit)
    return unit


@router.delete("/{unit_id}", summary="Khóa đơn vị hành chính")
async def delete_admin_unit(
    unit_id: int,
    request: Request,
    current_user: User = require_permission("catalog:edit", "catalog:delete"),
    session: AsyncSession = Depends(get_session),
):
    unit = await administrative_unit_service.get_by_id(session, unit_id)
    result = await administrative_unit_service.soft_delete_unit(session, unit_id)
    await auth_service.log_audit(
        session,
        current_user.id,
        "DELETE",
        entity_type="administrative_unit",
        entity_id=unit.id,
        entity_name=unit.name,
        old_data={"is_active": True},
        new_data={"is_active": False},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return result


@hierarchy_router.get("/tree", response_model=list[AdministrativeTreeNode], summary="Cây phân cấp hành chính")
async def get_admin_hierarchy_tree(
    system_type: str = Query(...),
    is_active: Optional[bool] = Query(True),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.get_tree(session, system_type=system_type, is_active=is_active)


@lookup_router.get("/address-systems", response_model=list[AddressSystemRead], summary="Danh sách hệ hành chính")
async def list_address_systems(
    _: User = Depends(get_current_active_user),
):
    return [
        {"code": "old", "label": "Hệ cũ (3 cấp)", "levels": 3},
        {"code": "new", "label": "Hệ mới (2 cấp)", "levels": 2},
    ]


@lookup_router.get("/locations/provinces", response_model=list[AdministrativeUnitRead], summary="Danh sách tỉnh/thành")
async def list_provinces(
    system_type: str = Query(...),
    is_active: Optional[bool] = Query(True),
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.list_provinces(
        session,
        system_type=system_type,
        is_active=is_active,
    )


@lookup_router.get("/locations/children", response_model=list[AdministrativeUnitRead], summary="Danh sách cấp con")
async def list_children(
    system_type: str = Query(...),
    parent_id: int = Query(...),
    is_active: Optional[bool] = Query(True),
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.list_children(
        session,
        system_type=system_type,
        parent_id=parent_id,
        is_active=is_active,
    )


@lookup_router.get("/locations/search", response_model=list[AdministrativeUnitRead], summary="Tìm kiếm địa danh")
async def search_locations(
    system_type: str = Query(...),
    keyword: str = Query(...),
    unit_type: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.search_locations(
        session,
        keyword=keyword,
        system_type=system_type,
        unit_type=unit_type,
        province_code=province_code,
        is_active=is_active,
    )


@lookup_router.post("/locations/validate-path", response_model=ValidateLocationPathResult, summary="Kiểm tra đường dẫn địa chỉ")
async def validate_location_path(
    body: ValidateLocationPathRequest,
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.validate_location_path(session, body)


@lookup_router.post(
    "/locations/validate-dual-paths",
    response_model=ValidateDualLocationPathsResult,
    summary="Kiểm tra đồng thời địa chỉ hệ cũ và hệ mới",
)
async def validate_dual_location_paths(
    body: ValidateDualLocationPathsRequest,
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.validate_dual_location_paths(session, body)
