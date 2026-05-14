from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.catalog import AdministrativeHierarchy, AdministrativeImportBatch, AdministrativeUnit
from app.schemas.catalog import AdministrativeImportRequest, AdministrativeTreeNode, ValidateLocationPathRequest
from app.services import administrative_import_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize(value: str) -> str:
    return administrative_import_service.normalize_text(value)


def _system_membership_clause(system_type: str, is_active: Optional[bool] = None):
    hierarchy_filters = [AdministrativeHierarchy.system_type == system_type]
    if is_active is not None:
        hierarchy_filters.append(AdministrativeHierarchy.is_active == is_active)

    return exists(
        select(1)
        .select_from(AdministrativeHierarchy)
        .where(
            *hierarchy_filters,
            or_(
                AdministrativeHierarchy.parent_unit_id == AdministrativeUnit.id,
                AdministrativeHierarchy.child_unit_id == AdministrativeUnit.id,
            ),
        )
    )


async def get_by_id(session: AsyncSession, unit_id: int) -> AdministrativeUnit:
    unit = await session.get(AdministrativeUnit, unit_id)
    if not unit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn vị hành chính")
    return unit


async def list_units(
    session: AsyncSession,
    *,
    is_active: Optional[bool] = None,
    unit_type: Optional[str] = None,
    province_code: Optional[str] = None,
    keyword: Optional[str] = None,
    system_type: Optional[str] = None,
) -> list[AdministrativeUnit]:
    q = select(AdministrativeUnit)
    if is_active is not None:
        q = q.where(AdministrativeUnit.is_active == is_active)
    if system_type:
        q = q.where(_system_membership_clause(system_type, is_active))
    if unit_type:
        q = q.where(AdministrativeUnit.unit_type == unit_type)
    if province_code:
        q = q.where(AdministrativeUnit.province_code == province_code)
    if keyword:
        normalized = _normalize(keyword)
        q = q.where(
            or_(
                AdministrativeUnit.normalized_name.contains(normalized),
                AdministrativeUnit.code.ilike(f"%{keyword.strip()}%"),
            )
        )
    q = q.order_by(AdministrativeUnit.unit_type, AdministrativeUnit.name)
    result = await session.execute(q)
    return list(result.scalars().all())


async def list_units_page(
    session: AsyncSession,
    *,
    is_active: Optional[bool] = None,
    unit_type: Optional[str] = None,
    province_code: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    system_type: Optional[str] = None,
) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 200))

    filters = []
    if is_active is not None:
        filters.append(AdministrativeUnit.is_active == is_active)
    if system_type:
        filters.append(_system_membership_clause(system_type, is_active))
    if unit_type:
        filters.append(AdministrativeUnit.unit_type == unit_type)
    if province_code:
        filters.append(AdministrativeUnit.province_code == province_code)
    if keyword:
        normalized = _normalize(keyword)
        filters.append(
            or_(
                AdministrativeUnit.normalized_name.contains(normalized),
                AdministrativeUnit.code.ilike(f"%{keyword.strip()}%"),
            )
        )

    count_query = select(func.count()).select_from(AdministrativeUnit)
    item_query = select(AdministrativeUnit)
    if filters:
        count_query = count_query.where(*filters)
        item_query = item_query.where(*filters)

    item_query = (
        item_query
        .order_by(AdministrativeUnit.unit_type, AdministrativeUnit.name, AdministrativeUnit.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    total = (await session.execute(count_query)).scalar_one()
    items = list((await session.execute(item_query)).scalars().all())
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def create_unit(session: AsyncSession, data) -> AdministrativeUnit:
    existing = await session.execute(select(AdministrativeUnit).where(AdministrativeUnit.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã đơn vị '{data.code}' đã tồn tại")

    unit = AdministrativeUnit(
        code=data.code,
        name=data.name,
        normalized_name=_normalize(data.name),
        unit_type=data.unit_type,
        official_name=data.official_name or data.name,
        province_code=data.province_code,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        source_name=data.source_name,
        source_version=data.source_version,
        is_active=data.is_active,
    )
    session.add(unit)
    await session.flush()
    await _sync_new_system_hierarchy_for_unit(session, unit)
    await session.commit()
    await session.refresh(unit)
    return unit


async def update_unit(session: AsyncSession, unit_id: int, data) -> AdministrativeUnit:
    unit = await get_by_id(session, unit_id)
    provided = data.model_fields_set

    if "name" in provided and data.name is not None:
        unit.name = data.name
        unit.normalized_name = _normalize(data.name)
    if "official_name" in provided:
        unit.official_name = data.official_name
    if "province_code" in provided:
        unit.province_code = data.province_code
    if "effective_from" in provided:
        unit.effective_from = data.effective_from
    if "effective_to" in provided:
        unit.effective_to = data.effective_to
    if "is_active" in provided and data.is_active is not None:
        unit.is_active = data.is_active

    unit.updated_at = _utcnow()
    await _sync_new_system_hierarchy_for_unit(session, unit)
    await session.commit()
    await session.refresh(unit)
    return unit


async def soft_delete_unit(session: AsyncSession, unit_id: int) -> dict:
    unit = await get_by_id(session, unit_id)
    unit.is_active = False
    unit.updated_at = _utcnow()
    await session.commit()
    return {"message": f"Đã khóa đơn vị hành chính '{unit.name}'"}


async def list_import_batches(session: AsyncSession) -> list[AdministrativeImportBatch]:
    result = await session.execute(
        select(AdministrativeImportBatch).order_by(AdministrativeImportBatch.imported_at.desc())
    )
    return list(result.scalars().all())


async def _sync_new_system_hierarchy_for_unit(session: AsyncSession, unit: AdministrativeUnit) -> None:
    if unit.unit_type != "ward" or not unit.province_code:
        return

    province_result = await session.execute(
        select(AdministrativeUnit).where(
            AdministrativeUnit.code == unit.province_code,
            AdministrativeUnit.unit_type == "province",
        )
    )
    province = province_result.scalar_one_or_none()
    if not province:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tỉnh/thành với mã '{unit.province_code}'",
        )

    existing_result = await session.execute(
        select(AdministrativeHierarchy).where(
            AdministrativeHierarchy.child_unit_id == unit.id,
            AdministrativeHierarchy.system_type == "new",
        )
    )
    existing = existing_result.scalars().all()
    for row in existing:
        await session.delete(row)

    session.add(AdministrativeHierarchy(
        system_type="new",
        parent_unit_id=province.id,
        child_unit_id=unit.id,
        level_depth=2,
        effective_from=unit.effective_from,
        effective_to=unit.effective_to,
        is_active=unit.is_active,
    ))


async def run_import(session: AsyncSession, data: AdministrativeImportRequest):
    if data.system_type != "new":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Hiện chỉ hỗ trợ import hệ hành chính mới")
    return await administrative_import_service.import_new_system_from_json(
        session,
        json_path=data.json_path or settings.ADMINISTRATIVE_WARDS_JSON_PATH,
        source_name=data.source_name,
        source_version=data.source_version,
        file_name=data.file_name,
        imported_by=data.imported_by,
        mode=data.mode,
    )


async def get_tree(
    session: AsyncSession,
    *,
    system_type: str,
    is_active: Optional[bool] = True,
) -> list[AdministrativeTreeNode]:
    unit_query = select(AdministrativeUnit).where(_system_membership_clause(system_type, is_active))
    if is_active is not None:
        unit_query = unit_query.where(AdministrativeUnit.is_active == is_active)
    units = list((await session.execute(unit_query)).scalars().all())
    if not units:
        return []

    child_query = (
        select(AdministrativeHierarchy, AdministrativeUnit)
        .join(AdministrativeUnit, AdministrativeUnit.id == AdministrativeHierarchy.child_unit_id)
        .where(AdministrativeHierarchy.system_type == system_type)
    )
    if is_active is not None:
        child_query = child_query.where(
            and_(
                AdministrativeHierarchy.is_active == is_active,
                AdministrativeUnit.is_active == is_active,
            )
        )
    rows = (await session.execute(child_query)).all()

    nodes = {u.id: AdministrativeTreeNode.model_validate(u) for u in units}
    child_ids: set[int] = set()
    for hierarchy, child in rows:
        parent = nodes.get(hierarchy.parent_unit_id)
        child_node = nodes.get(child.id)
        if parent and child_node:
            parent.children.append(child_node)
            child_ids.add(child.id)

    roots = [node for node in nodes.values() if node.unit_type == "province" and node.id not in child_ids]

    def _sort(items: list[AdministrativeTreeNode]):
        items.sort(key=lambda x: (x.name,))
        for item in items:
            _sort(item.children)

    _sort(roots)
    return roots


async def list_provinces(
    session: AsyncSession,
    *,
    system_type: str,
    is_active: Optional[bool] = True,
) -> list[AdministrativeUnit]:
    return await list_units(session, is_active=is_active, unit_type="province", system_type=system_type)


async def list_children(
    session: AsyncSession,
    *,
    system_type: str,
    parent_id: int,
    is_active: Optional[bool] = True,
) -> list[AdministrativeUnit]:
    q = (
        select(AdministrativeUnit)
        .join(AdministrativeHierarchy, AdministrativeHierarchy.child_unit_id == AdministrativeUnit.id)
        .where(
            AdministrativeHierarchy.system_type == system_type,
            AdministrativeHierarchy.parent_unit_id == parent_id,
        )
        .order_by(AdministrativeUnit.name)
    )
    if is_active is not None:
        q = q.where(
            AdministrativeHierarchy.is_active == is_active,
            AdministrativeUnit.is_active == is_active,
        )
    return list((await session.execute(q)).scalars().all())


async def search_locations(
    session: AsyncSession,
    *,
    keyword: str,
    system_type: str,
    unit_type: Optional[str] = None,
    province_code: Optional[str] = None,
    is_active: Optional[bool] = True,
) -> list[AdministrativeUnit]:
    q = select(AdministrativeUnit)
    if is_active is not None:
        q = q.where(AdministrativeUnit.is_active == is_active)
    q = q.where(_system_membership_clause(system_type, is_active))
    if unit_type:
        q = q.where(AdministrativeUnit.unit_type == unit_type)
    if province_code:
        q = q.where(AdministrativeUnit.province_code == province_code)

    normalized = _normalize(keyword)
    q = q.where(
        or_(
            AdministrativeUnit.normalized_name.contains(normalized),
            AdministrativeUnit.code.ilike(f"%{keyword.strip()}%"),
        )
    )
    if system_type == "new":
        q = q.where(AdministrativeUnit.unit_type.in_(["province", "ward"]))
    q = q.order_by(AdministrativeUnit.unit_type, AdministrativeUnit.name)
    return list((await session.execute(q)).scalars().all())


async def validate_location_path(
    session: AsyncSession,
    data: ValidateLocationPathRequest,
) -> dict:
    province = await get_by_id(session, data.province_unit_id)
    ward = await get_by_id(session, data.ward_unit_id)

    if data.system_type == "new":
        q = select(AdministrativeHierarchy).where(
            AdministrativeHierarchy.system_type == "new",
            AdministrativeHierarchy.parent_unit_id == province.id,
            AdministrativeHierarchy.child_unit_id == ward.id,
            AdministrativeHierarchy.is_active == True,
        )
        match = (await session.execute(q)).scalar_one_or_none()
        if match:
            return {"valid": True, "message": "Đường dẫn địa chỉ hợp lệ"}
        return {"valid": False, "message": "Xã/phường không thuộc tỉnh/thành đã chọn"}

    if data.district_unit_id is None:
        return {"valid": False, "message": "Hệ cũ yêu cầu district_unit_id"}

    district = await get_by_id(session, data.district_unit_id)
    province_district = (await session.execute(
        select(AdministrativeHierarchy).where(
            AdministrativeHierarchy.system_type == "old",
            AdministrativeHierarchy.parent_unit_id == province.id,
            AdministrativeHierarchy.child_unit_id == district.id,
            AdministrativeHierarchy.is_active == True,
        )
    )).scalar_one_or_none()
    district_ward = (await session.execute(
        select(AdministrativeHierarchy).where(
            AdministrativeHierarchy.system_type == "old",
            AdministrativeHierarchy.parent_unit_id == district.id,
            AdministrativeHierarchy.child_unit_id == ward.id,
            AdministrativeHierarchy.is_active == True,
        )
    )).scalar_one_or_none()
    if province_district and district_ward:
        return {"valid": True, "message": "Đường dẫn địa chỉ hợp lệ"}
    return {"valid": False, "message": "Đường dẫn địa chỉ không hợp lệ"}
