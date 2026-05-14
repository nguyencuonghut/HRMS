from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.catalog import (
    AddressSystemRead,
    AdministrativeImportBatchRead,
    AdministrativeImportRequest,
    AdministrativeUnitListPage,
    AdministrativeUnitCreate,
    AdministrativeUnitRead,
    AdministrativeUnitUpdate,
    AdministrativeTreeNode,
    ValidateLocationPathRequest,
    ValidateLocationPathResult,
)
from app.services import administrative_unit_service

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
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.create_unit(session, body)


@router.post("/import", summary="Import dữ liệu hành chính")
async def import_admin_units(
    body: AdministrativeImportRequest,
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.run_import(session, body)


@router.get("/import-batches", response_model=list[AdministrativeImportBatchRead], summary="Lịch sử import dữ liệu hành chính")
async def list_import_batches(
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.list_import_batches(session)


@router.get("/{unit_id}", response_model=AdministrativeUnitRead, summary="Chi tiết đơn vị hành chính")
async def get_admin_unit(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.get_by_id(session, unit_id)


@router.put("/{unit_id}", response_model=AdministrativeUnitRead, summary="Cập nhật đơn vị hành chính")
async def update_admin_unit(
    unit_id: int,
    body: AdministrativeUnitUpdate,
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.update_unit(session, unit_id, body)


@router.delete("/{unit_id}", summary="Khóa đơn vị hành chính")
async def delete_admin_unit(
    unit_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.soft_delete_unit(session, unit_id)


@hierarchy_router.get("/tree", response_model=list[AdministrativeTreeNode], summary="Cây phân cấp hành chính")
async def get_admin_hierarchy_tree(
    system_type: str = Query(...),
    is_active: Optional[bool] = Query(True),
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.get_tree(session, system_type=system_type, is_active=is_active)


@lookup_router.get("/address-systems", response_model=list[AddressSystemRead], summary="Danh sách hệ hành chính")
async def list_address_systems():
    return [
        {"code": "old", "label": "Hệ cũ (3 cấp)", "levels": 3},
        {"code": "new", "label": "Hệ mới (2 cấp)", "levels": 2},
    ]


@lookup_router.get("/locations/provinces", response_model=list[AdministrativeUnitRead], summary="Danh sách tỉnh/thành")
async def list_provinces(
    system_type: str = Query(...),
    is_active: Optional[bool] = Query(True),
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
    session: AsyncSession = Depends(get_session),
):
    return await administrative_unit_service.validate_location_path(session, body)
