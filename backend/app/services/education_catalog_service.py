from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import EducationLevel, EducationMajor, EducationalInstitution
from app.seeds.education_catalog import _normalize


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _assert_unique_level(session: AsyncSession, *, code: str, normalized_name: str, rank_no: int, exclude_id: Optional[int] = None) -> None:
    code_query = select(EducationLevel).where(EducationLevel.code == code)
    name_query = select(EducationLevel).where(EducationLevel.normalized_name == normalized_name)
    rank_query = select(EducationLevel).where(EducationLevel.rank_no == rank_no)
    if exclude_id is not None:
        code_query = code_query.where(EducationLevel.id != exclude_id)
        name_query = name_query.where(EducationLevel.id != exclude_id)
        rank_query = rank_query.where(EducationLevel.id != exclude_id)

    if (await session.execute(code_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã trình độ '{code}' đã tồn tại")
    if (await session.execute(name_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Tên trình độ '{normalized_name}' đã tồn tại")
    if (await session.execute(rank_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Thứ bậc '{rank_no}' đã tồn tại")


async def _assert_unique_institution(
    session: AsyncSession,
    *,
    code: Optional[str],
    normalized_name: str,
    exclude_id: Optional[int] = None,
) -> None:
    if code:
        code_query = select(EducationalInstitution).where(EducationalInstitution.code == code)
        if exclude_id is not None:
            code_query = code_query.where(EducationalInstitution.id != exclude_id)
        if (await session.execute(code_query)).scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã trường '{code}' đã tồn tại")

    name_query = select(EducationalInstitution).where(EducationalInstitution.normalized_name == normalized_name)
    if exclude_id is not None:
        name_query = name_query.where(EducationalInstitution.id != exclude_id)
    if (await session.execute(name_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Tên trường đã tồn tại")


async def _assert_unique_major(
    session: AsyncSession,
    *,
    code: Optional[str],
    normalized_name: str,
    exclude_id: Optional[int] = None,
) -> None:
    if code:
        code_query = select(EducationMajor).where(EducationMajor.code == code)
        if exclude_id is not None:
            code_query = code_query.where(EducationMajor.id != exclude_id)
        if (await session.execute(code_query)).scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã chuyên ngành '{code}' đã tồn tại")

    name_query = select(EducationMajor).where(EducationMajor.normalized_name == normalized_name)
    if exclude_id is not None:
        name_query = name_query.where(EducationMajor.id != exclude_id)
    if (await session.execute(name_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Tên chuyên ngành đã tồn tại")


async def get_level_by_id(session: AsyncSession, level_id: int) -> EducationLevel:
    row = await session.get(EducationLevel, level_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy trình độ học vấn")
    return row


async def get_institution_by_id(session: AsyncSession, institution_id: int) -> EducationalInstitution:
    row = await session.get(EducationalInstitution, institution_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy trường học")
    return row


async def get_major_by_id(session: AsyncSession, major_id: int) -> EducationMajor:
    row = await session.get(EducationMajor, major_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chuyên ngành")
    return row


async def list_levels_page(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = []
    if is_active is not None:
        filters.append(EducationLevel.is_active == is_active)
    if keyword:
        normalized = _normalize(keyword)
        filters.append(
            or_(
                EducationLevel.normalized_name.contains(normalized),
                EducationLevel.code.ilike(f"%{keyword.strip()}%"),
            )
        )

    count_query = select(func.count()).select_from(EducationLevel)
    item_query = select(EducationLevel)
    if filters:
        count_query = count_query.where(*filters)
        item_query = item_query.where(*filters)
    item_query = item_query.order_by(EducationLevel.rank_no, EducationLevel.name).offset((page - 1) * page_size).limit(page_size)
    total = (await session.execute(count_query)).scalar_one()
    items = list((await session.execute(item_query)).scalars().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def create_level(session: AsyncSession, data) -> EducationLevel:
    normalized_name = _normalize(data.name)
    await _assert_unique_level(session, code=data.code, normalized_name=normalized_name, rank_no=data.rank_no)
    row = EducationLevel(
        code=data.code,
        name=data.name,
        normalized_name=normalized_name,
        rank_no=data.rank_no,
        is_active=data.is_active,
    )
    session.add(row)
    await session.flush()
    return row


async def update_level(session: AsyncSession, level_id: int, data) -> EducationLevel:
    row = await get_level_by_id(session, level_id)
    provided = data.model_fields_set
    new_name = data.name if "name" in provided and data.name is not None else row.name
    new_rank_no = data.rank_no if "rank_no" in provided and data.rank_no is not None else row.rank_no
    new_normalized_name = _normalize(new_name)
    await _assert_unique_level(session, code=row.code, normalized_name=new_normalized_name, rank_no=new_rank_no, exclude_id=row.id)

    if "name" in provided and data.name is not None:
        row.name = data.name
        row.normalized_name = new_normalized_name
    if "rank_no" in provided and data.rank_no is not None:
        row.rank_no = data.rank_no
    if "is_active" in provided and data.is_active is not None:
        row.is_active = data.is_active
    row.updated_at = _utcnow()
    await session.flush()
    return row


async def soft_delete_level(session: AsyncSession, level_id: int) -> dict:
    row = await get_level_by_id(session, level_id)
    row.is_active = False
    row.updated_at = _utcnow()
    await session.flush()
    return {"message": f"Đã khóa trình độ học vấn '{row.name}'"}


async def lookup_levels(session: AsyncSession, *, keyword: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[EducationLevel]:
    query = select(EducationLevel).where(EducationLevel.is_active == is_active)
    if keyword:
        normalized = _normalize(keyword)
        query = query.where(
            or_(
                EducationLevel.normalized_name.contains(normalized),
                EducationLevel.code.ilike(f"%{keyword.strip()}%"),
            )
        )
    query = query.order_by(EducationLevel.rank_no, EducationLevel.name).limit(limit)
    return list((await session.execute(query)).scalars().all())


async def list_institutions_page(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    institution_type: Optional[str] = None,
    country_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = []
    if is_active is not None:
        filters.append(EducationalInstitution.is_active == is_active)
    if institution_type:
        filters.append(EducationalInstitution.institution_type == institution_type)
    if country_code:
        filters.append(EducationalInstitution.country_code == country_code.strip().upper())
    if keyword:
        normalized = _normalize(keyword)
        filters.append(
            or_(
                EducationalInstitution.normalized_name.contains(normalized),
                EducationalInstitution.code.ilike(f"%{keyword.strip()}%"),
                EducationalInstitution.short_name.ilike(f"%{keyword.strip()}%"),
            )
        )
    count_query = select(func.count()).select_from(EducationalInstitution)
    item_query = select(EducationalInstitution)
    if filters:
        count_query = count_query.where(*filters)
        item_query = item_query.where(*filters)
    item_query = item_query.order_by(EducationalInstitution.name, EducationalInstitution.id).offset((page - 1) * page_size).limit(page_size)
    total = (await session.execute(count_query)).scalar_one()
    items = list((await session.execute(item_query)).scalars().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def create_institution(session: AsyncSession, data) -> EducationalInstitution:
    normalized_name = _normalize(data.name)
    await _assert_unique_institution(session, code=data.code, normalized_name=normalized_name)
    row = EducationalInstitution(
        code=data.code,
        name=data.name,
        normalized_name=normalized_name,
        short_name=data.short_name,
        institution_type=data.institution_type,
        country_code=data.country_code,
        province_code=data.province_code,
        is_active=data.is_active,
    )
    session.add(row)
    await session.flush()
    return row


async def update_institution(session: AsyncSession, institution_id: int, data) -> EducationalInstitution:
    row = await get_institution_by_id(session, institution_id)
    provided = data.model_fields_set
    new_name = data.name if "name" in provided and data.name is not None else row.name
    new_normalized_name = _normalize(new_name)
    await _assert_unique_institution(session, code=row.code, normalized_name=new_normalized_name, exclude_id=row.id)

    if "name" in provided and data.name is not None:
        row.name = data.name
        row.normalized_name = new_normalized_name
    if "short_name" in provided:
        row.short_name = data.short_name
    if "institution_type" in provided:
        row.institution_type = data.institution_type
    if "country_code" in provided:
        row.country_code = data.country_code
    if "province_code" in provided:
        row.province_code = data.province_code
    if "is_active" in provided and data.is_active is not None:
        row.is_active = data.is_active
    row.updated_at = _utcnow()
    await session.flush()
    return row


async def soft_delete_institution(session: AsyncSession, institution_id: int) -> dict:
    row = await get_institution_by_id(session, institution_id)
    row.is_active = False
    row.updated_at = _utcnow()
    await session.flush()
    return {"message": f"Đã khóa trường học '{row.name}'"}


async def lookup_institutions(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    institution_type: Optional[str] = None,
    country_code: Optional[str] = None,
    is_active: bool = True,
    limit: int = 20,
) -> list[EducationalInstitution]:
    query = select(EducationalInstitution).where(EducationalInstitution.is_active == is_active)
    if institution_type:
        query = query.where(EducationalInstitution.institution_type == institution_type)
    if country_code:
        query = query.where(EducationalInstitution.country_code == country_code.strip().upper())
    if keyword:
        normalized = _normalize(keyword)
        query = query.where(
            or_(
                EducationalInstitution.normalized_name.contains(normalized),
                EducationalInstitution.code.ilike(f"%{keyword.strip()}%"),
                EducationalInstitution.short_name.ilike(f"%{keyword.strip()}%"),
            )
        )
    query = query.order_by(EducationalInstitution.name).limit(limit)
    return list((await session.execute(query)).scalars().all())


async def list_majors_page(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    major_group: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = []
    if is_active is not None:
        filters.append(EducationMajor.is_active == is_active)
    if major_group:
        filters.append(EducationMajor.major_group == major_group)
    if keyword:
        normalized = _normalize(keyword)
        filters.append(
            or_(
                EducationMajor.normalized_name.contains(normalized),
                EducationMajor.code.ilike(f"%{keyword.strip()}%"),
            )
        )
    count_query = select(func.count()).select_from(EducationMajor)
    item_query = select(EducationMajor)
    if filters:
        count_query = count_query.where(*filters)
        item_query = item_query.where(*filters)
    item_query = item_query.order_by(EducationMajor.name, EducationMajor.id).offset((page - 1) * page_size).limit(page_size)
    total = (await session.execute(count_query)).scalar_one()
    items = list((await session.execute(item_query)).scalars().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def create_major(session: AsyncSession, data) -> EducationMajor:
    normalized_name = _normalize(data.name)
    await _assert_unique_major(session, code=data.code, normalized_name=normalized_name)
    row = EducationMajor(
        code=data.code,
        name=data.name,
        normalized_name=normalized_name,
        major_group=data.major_group,
        is_active=data.is_active,
    )
    session.add(row)
    await session.flush()
    return row


async def update_major(session: AsyncSession, major_id: int, data) -> EducationMajor:
    row = await get_major_by_id(session, major_id)
    provided = data.model_fields_set
    new_name = data.name if "name" in provided and data.name is not None else row.name
    new_normalized_name = _normalize(new_name)
    await _assert_unique_major(session, code=row.code, normalized_name=new_normalized_name, exclude_id=row.id)

    if "name" in provided and data.name is not None:
        row.name = data.name
        row.normalized_name = new_normalized_name
    if "major_group" in provided:
        row.major_group = data.major_group
    if "is_active" in provided and data.is_active is not None:
        row.is_active = data.is_active
    row.updated_at = _utcnow()
    await session.flush()
    return row


async def soft_delete_major(session: AsyncSession, major_id: int) -> dict:
    row = await get_major_by_id(session, major_id)
    row.is_active = False
    row.updated_at = _utcnow()
    await session.flush()
    return {"message": f"Đã khóa chuyên ngành '{row.name}'"}


async def lookup_majors(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    major_group: Optional[str] = None,
    is_active: bool = True,
    limit: int = 20,
) -> list[EducationMajor]:
    query = select(EducationMajor).where(EducationMajor.is_active == is_active)
    if major_group:
        query = query.where(EducationMajor.major_group == major_group)
    if keyword:
        normalized = _normalize(keyword)
        query = query.where(
            or_(
                EducationMajor.normalized_name.contains(normalized),
                EducationMajor.code.ilike(f"%{keyword.strip()}%"),
            )
        )
    query = query.order_by(EducationMajor.name).limit(limit)
    return list((await session.execute(query)).scalars().all())
