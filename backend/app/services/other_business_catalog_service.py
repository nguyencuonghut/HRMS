from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    Bank,
    Certificate,
    ContractCategory,
    ContractTemplate,
    ContractTemplatePlaceholder,
    Ethnicity,
    LeaveType,
    Nationality,
    Religion,
    Skill,
)
from app.services.contract_template_docx import (
    DOCX_MIME,
    SUPPORTED_TEMPLATE_FIELDS,
    extract_docx_placeholder_summary,
    resolve_template_storage_path,
)
from app.services.administrative_import_service import normalize_text


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize(value: str) -> str:
    return normalize_text(value)


async def _assert_unique_code_name(
    session: AsyncSession,
    *,
    model,
    code: str,
    normalized_name: str,
    code_label: str,
    name_label: str,
    exclude_id: Optional[int] = None,
) -> None:
    code_query = select(model).where(model.code == code)
    name_query = select(model).where(model.normalized_name == normalized_name)
    if exclude_id is not None:
        code_query = code_query.where(model.id != exclude_id)
        name_query = name_query.where(model.id != exclude_id)
    if (await session.execute(code_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{code_label} '{code}' đã tồn tại")
    if (await session.execute(name_query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{name_label} '{normalized_name}' đã tồn tại")


async def _list_basic_page(
    session: AsyncSession,
    *,
    model,
    keyword: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    extra_filters: Optional[list] = None,
    order_by=None,
) -> dict:
    filters = list(extra_filters or [])
    if is_active is not None:
        filters.append(model.is_active == is_active)
    if keyword:
        normalized = _normalize(keyword)
        filters.append(
            or_(
                model.normalized_name.contains(normalized),
                model.code.ilike(f"%{keyword.strip()}%"),
            )
        )
    count_query = select(func.count()).select_from(model)
    item_query = select(model)
    if filters:
        count_query = count_query.where(*filters)
        item_query = item_query.where(*filters)
    if order_by is not None:
        item_query = item_query.order_by(*order_by)
    total = (await session.execute(count_query)).scalar_one()
    items = list((await session.execute(item_query.offset((page - 1) * page_size).limit(page_size))).scalars().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def _lookup_basic(
    session: AsyncSession,
    *,
    model,
    keyword: Optional[str] = None,
    is_active: bool = True,
    limit: int = 20,
    extra_filters: Optional[list] = None,
    order_by=None,
) -> list:
    filters = list(extra_filters or [])
    filters.append(model.is_active == is_active)
    query = select(model).where(*filters)
    if keyword:
        normalized = _normalize(keyword)
        query = query.where(
            or_(
                model.normalized_name.contains(normalized),
                model.code.ilike(f"%{keyword.strip()}%"),
            )
        )
    if order_by is not None:
        query = query.order_by(*order_by)
    query = query.limit(limit)
    return list((await session.execute(query)).scalars().all())


async def get_contract_category_by_id(session: AsyncSession, row_id: int) -> ContractCategory:
    row = await session.get(ContractCategory, row_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy loại hợp đồng")
    return row


async def list_contract_categories_page(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    document_kind: Optional[str] = None,
    legal_contract_type: Optional[str] = None,
    business_group: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = []
    if document_kind:
        filters.append(ContractCategory.document_kind == document_kind)
    if legal_contract_type:
        filters.append(ContractCategory.legal_contract_type == legal_contract_type)
    if business_group:
        filters.append(ContractCategory.business_group == business_group)
    return await _list_basic_page(
        session,
        model=ContractCategory,
        keyword=keyword,
        is_active=is_active,
        page=page,
        page_size=page_size,
        extra_filters=filters,
        order_by=[ContractCategory.sort_order, ContractCategory.name],
    )


async def create_contract_category(session: AsyncSession, data) -> ContractCategory:
    normalized_name = _normalize(data.name)
    await _assert_unique_code_name(
        session,
        model=ContractCategory,
        code=data.code,
        normalized_name=normalized_name,
        code_label="Mã loại hợp đồng",
        name_label="Tên loại hợp đồng",
    )
    row = ContractCategory(
        code=data.code,
        name=data.name,
        normalized_name=normalized_name,
        document_kind=data.document_kind,
        legal_contract_type=data.legal_contract_type,
        business_group=data.business_group,
        default_term_months=data.default_term_months,
        sort_order=data.sort_order,
        is_active=data.is_active,
        description=data.description,
    )
    session.add(row)
    await session.flush()
    return row


async def update_contract_category(session: AsyncSession, row_id: int, data) -> ContractCategory:
    row = await get_contract_category_by_id(session, row_id)
    provided = data.model_fields_set
    new_name = data.name if "name" in provided and data.name is not None else row.name
    normalized_name = _normalize(new_name)
    await _assert_unique_code_name(
        session,
        model=ContractCategory,
        code=row.code,
        normalized_name=normalized_name,
        code_label="Mã loại hợp đồng",
        name_label="Tên loại hợp đồng",
        exclude_id=row.id,
    )
    if "name" in provided and data.name is not None:
        row.name = data.name
        row.normalized_name = normalized_name
    for field in ("document_kind", "legal_contract_type", "business_group", "default_term_months", "sort_order", "description"):
        if field in provided:
            setattr(row, field, getattr(data, field))
    if "is_active" in provided and data.is_active is not None:
        row.is_active = data.is_active
    row.updated_at = _utcnow()
    await session.flush()
    return row


async def soft_delete_contract_category(session: AsyncSession, row_id: int) -> dict:
    row = await get_contract_category_by_id(session, row_id)
    row.is_active = False
    row.updated_at = _utcnow()
    await session.flush()
    return {"message": f"Đã khóa loại hợp đồng '{row.name}'"}


async def lookup_contract_categories(session: AsyncSession, *, keyword: Optional[str] = None, document_kind: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[ContractCategory]:
    filters = []
    if document_kind:
        filters.append(ContractCategory.document_kind == document_kind)
    return await _lookup_basic(
        session,
        model=ContractCategory,
        keyword=keyword,
        is_active=is_active,
        limit=limit,
        extra_filters=filters,
        order_by=[ContractCategory.sort_order, ContractCategory.name],
    )


async def _get_row_by_id(session: AsyncSession, model, row_id: int, not_found: str):
    row = await session.get(model, row_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=not_found)
    return row


async def _create_basic_row(session: AsyncSession, *, model, data, code_label: str, name_label: str):
    normalized_name = _normalize(data.name)
    await _assert_unique_code_name(
        session,
        model=model,
        code=data.code,
        normalized_name=normalized_name,
        code_label=code_label,
        name_label=name_label,
    )
    values = data.model_dump()
    values["normalized_name"] = normalized_name
    row = model(**values)
    session.add(row)
    await session.flush()
    return row


async def _update_basic_row(session: AsyncSession, *, model, row_id: int, data, code_label: str, name_label: str, not_found: str):
    row = await _get_row_by_id(session, model, row_id, not_found)
    provided = data.model_fields_set
    new_name = data.name if "name" in provided and data.name is not None else row.name
    normalized_name = _normalize(new_name)
    await _assert_unique_code_name(
        session,
        model=model,
        code=row.code,
        normalized_name=normalized_name,
        code_label=code_label,
        name_label=name_label,
        exclude_id=row.id,
    )
    if "name" in provided and data.name is not None:
        row.name = data.name
        row.normalized_name = normalized_name
    for field in provided:
        if field not in {"name"}:
            setattr(row, field, getattr(data, field))
    row.updated_at = _utcnow()
    await session.flush()
    return row


async def _soft_delete_basic_row(session: AsyncSession, *, model, row_id: int, not_found: str, label: str) -> dict:
    row = await _get_row_by_id(session, model, row_id, not_found)
    row.is_active = False
    row.updated_at = _utcnow()
    await session.flush()
    return {"message": f"Đã khóa {label} '{row.name}'"}


async def get_nationality_by_id(session: AsyncSession, row_id: int) -> Nationality:
    return await _get_row_by_id(session, Nationality, row_id, "Không tìm thấy quốc tịch")


async def list_nationalities_page(session: AsyncSession, *, keyword: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    return await _list_basic_page(session, model=Nationality, keyword=keyword, is_active=is_active, page=page, page_size=page_size, order_by=[Nationality.name])


async def create_nationality(session: AsyncSession, data) -> Nationality:
    return await _create_basic_row(session, model=Nationality, data=data, code_label="Mã quốc tịch", name_label="Tên quốc tịch")


async def update_nationality(session: AsyncSession, row_id: int, data) -> Nationality:
    return await _update_basic_row(session, model=Nationality, row_id=row_id, data=data, code_label="Mã quốc tịch", name_label="Tên quốc tịch", not_found="Không tìm thấy quốc tịch")


async def soft_delete_nationality(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=Nationality, row_id=row_id, not_found="Không tìm thấy quốc tịch", label="quốc tịch")


async def lookup_nationalities(session: AsyncSession, *, keyword: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[Nationality]:
    return await _lookup_basic(session, model=Nationality, keyword=keyword, is_active=is_active, limit=limit, order_by=[Nationality.name])


async def get_ethnicity_by_id(session: AsyncSession, row_id: int) -> Ethnicity:
    return await _get_row_by_id(session, Ethnicity, row_id, "Không tìm thấy dân tộc")


async def list_ethnicities_page(session: AsyncSession, *, keyword: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    return await _list_basic_page(session, model=Ethnicity, keyword=keyword, is_active=is_active, page=page, page_size=page_size, order_by=[Ethnicity.name])


async def create_ethnicity(session: AsyncSession, data) -> Ethnicity:
    return await _create_basic_row(session, model=Ethnicity, data=data, code_label="Mã dân tộc", name_label="Tên dân tộc")


async def update_ethnicity(session: AsyncSession, row_id: int, data) -> Ethnicity:
    return await _update_basic_row(session, model=Ethnicity, row_id=row_id, data=data, code_label="Mã dân tộc", name_label="Tên dân tộc", not_found="Không tìm thấy dân tộc")


async def soft_delete_ethnicity(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=Ethnicity, row_id=row_id, not_found="Không tìm thấy dân tộc", label="dân tộc")


async def lookup_ethnicities(session: AsyncSession, *, keyword: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[Ethnicity]:
    return await _lookup_basic(session, model=Ethnicity, keyword=keyword, is_active=is_active, limit=limit, order_by=[Ethnicity.name])


async def get_religion_by_id(session: AsyncSession, row_id: int) -> Religion:
    return await _get_row_by_id(session, Religion, row_id, "Không tìm thấy tôn giáo")


async def list_religions_page(session: AsyncSession, *, keyword: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    return await _list_basic_page(session, model=Religion, keyword=keyword, is_active=is_active, page=page, page_size=page_size, order_by=[Religion.name])


async def create_religion(session: AsyncSession, data) -> Religion:
    return await _create_basic_row(session, model=Religion, data=data, code_label="Mã tôn giáo", name_label="Tên tôn giáo")


async def update_religion(session: AsyncSession, row_id: int, data) -> Religion:
    return await _update_basic_row(session, model=Religion, row_id=row_id, data=data, code_label="Mã tôn giáo", name_label="Tên tôn giáo", not_found="Không tìm thấy tôn giáo")


async def soft_delete_religion(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=Religion, row_id=row_id, not_found="Không tìm thấy tôn giáo", label="tôn giáo")


async def lookup_religions(session: AsyncSession, *, keyword: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[Religion]:
    return await _lookup_basic(session, model=Religion, keyword=keyword, is_active=is_active, limit=limit, order_by=[Religion.name])


async def get_bank_by_id(session: AsyncSession, row_id: int) -> Bank:
    return await _get_row_by_id(session, Bank, row_id, "Không tìm thấy ngân hàng")


async def list_banks_page(session: AsyncSession, *, keyword: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    filters = []
    if keyword:
        normalized = _normalize(keyword)
        filters.append(
            or_(
                Bank.normalized_name.contains(normalized),
                Bank.code.ilike(f"%{keyword.strip()}%"),
                Bank.short_name.ilike(f"%{keyword.strip()}%"),
                Bank.bin_code.ilike(f"%{keyword.strip()}%"),
            )
        )
    count_query = select(func.count()).select_from(Bank)
    item_query = select(Bank)
    if is_active is not None:
        filters.append(Bank.is_active == is_active)
    if filters:
        count_query = count_query.where(*filters)
        item_query = item_query.where(*filters)
    item_query = item_query.order_by(Bank.name).offset((page - 1) * page_size).limit(page_size)
    total = (await session.execute(count_query)).scalar_one()
    items = list((await session.execute(item_query)).scalars().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def create_bank(session: AsyncSession, data) -> Bank:
    return await _create_basic_row(session, model=Bank, data=data, code_label="Mã ngân hàng", name_label="Tên ngân hàng")


async def update_bank(session: AsyncSession, row_id: int, data) -> Bank:
    return await _update_basic_row(session, model=Bank, row_id=row_id, data=data, code_label="Mã ngân hàng", name_label="Tên ngân hàng", not_found="Không tìm thấy ngân hàng")


async def soft_delete_bank(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=Bank, row_id=row_id, not_found="Không tìm thấy ngân hàng", label="ngân hàng")


async def lookup_banks(session: AsyncSession, *, keyword: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[Bank]:
    query = select(Bank).where(Bank.is_active == is_active)
    if keyword:
        normalized = _normalize(keyword)
        query = query.where(
            or_(
                Bank.normalized_name.contains(normalized),
                Bank.code.ilike(f"%{keyword.strip()}%"),
                Bank.short_name.ilike(f"%{keyword.strip()}%"),
                Bank.bin_code.ilike(f"%{keyword.strip()}%"),
            )
        )
    query = query.order_by(Bank.name).limit(limit)
    return list((await session.execute(query)).scalars().all())


async def get_skill_by_id(session: AsyncSession, row_id: int) -> Skill:
    return await _get_row_by_id(session, Skill, row_id, "Không tìm thấy kỹ năng")


async def list_skills_page(session: AsyncSession, *, keyword: Optional[str] = None, skill_group: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    filters = []
    if skill_group:
        filters.append(Skill.skill_group == skill_group)
    return await _list_basic_page(session, model=Skill, keyword=keyword, is_active=is_active, page=page, page_size=page_size, extra_filters=filters, order_by=[Skill.name])


async def create_skill(session: AsyncSession, data) -> Skill:
    return await _create_basic_row(session, model=Skill, data=data, code_label="Mã kỹ năng", name_label="Tên kỹ năng")


async def update_skill(session: AsyncSession, row_id: int, data) -> Skill:
    return await _update_basic_row(session, model=Skill, row_id=row_id, data=data, code_label="Mã kỹ năng", name_label="Tên kỹ năng", not_found="Không tìm thấy kỹ năng")


async def soft_delete_skill(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=Skill, row_id=row_id, not_found="Không tìm thấy kỹ năng", label="kỹ năng")


async def lookup_skills(session: AsyncSession, *, keyword: Optional[str] = None, skill_group: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[Skill]:
    filters = []
    if skill_group:
        filters.append(Skill.skill_group == skill_group)
    return await _lookup_basic(session, model=Skill, keyword=keyword, is_active=is_active, limit=limit, extra_filters=filters, order_by=[Skill.name])


async def get_certificate_by_id(session: AsyncSession, row_id: int) -> Certificate:
    return await _get_row_by_id(session, Certificate, row_id, "Không tìm thấy chứng chỉ")


async def list_certificates_page(session: AsyncSession, *, keyword: Optional[str] = None, certificate_group: Optional[str] = None, expiry_policy: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    filters = []
    if certificate_group:
        filters.append(Certificate.certificate_group == certificate_group)
    if expiry_policy:
        filters.append(Certificate.expiry_policy == expiry_policy)
    return await _list_basic_page(session, model=Certificate, keyword=keyword, is_active=is_active, page=page, page_size=page_size, extra_filters=filters, order_by=[Certificate.name])


async def create_certificate(session: AsyncSession, data) -> Certificate:
    return await _create_basic_row(session, model=Certificate, data=data, code_label="Mã chứng chỉ", name_label="Tên chứng chỉ")


async def update_certificate(session: AsyncSession, row_id: int, data) -> Certificate:
    return await _update_basic_row(session, model=Certificate, row_id=row_id, data=data, code_label="Mã chứng chỉ", name_label="Tên chứng chỉ", not_found="Không tìm thấy chứng chỉ")


async def soft_delete_certificate(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=Certificate, row_id=row_id, not_found="Không tìm thấy chứng chỉ", label="chứng chỉ")


async def lookup_certificates(session: AsyncSession, *, keyword: Optional[str] = None, certificate_group: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[Certificate]:
    filters = []
    if certificate_group:
        filters.append(Certificate.certificate_group == certificate_group)
    return await _lookup_basic(session, model=Certificate, keyword=keyword, is_active=is_active, limit=limit, extra_filters=filters, order_by=[Certificate.name])


async def get_leave_type_by_id(session: AsyncSession, row_id: int) -> LeaveType:
    return await _get_row_by_id(session, LeaveType, row_id, "Không tìm thấy loại nghỉ phép")


async def list_leave_types_page(session: AsyncSession, *, keyword: Optional[str] = None, is_active: Optional[bool] = None, page: int = 1, page_size: int = 20) -> dict:
    return await _list_basic_page(session, model=LeaveType, keyword=keyword, is_active=is_active, page=page, page_size=page_size, order_by=[LeaveType.name])


async def create_leave_type(session: AsyncSession, data) -> LeaveType:
    return await _create_basic_row(session, model=LeaveType, data=data, code_label="Mã loại nghỉ phép", name_label="Tên loại nghỉ phép")


async def update_leave_type(session: AsyncSession, row_id: int, data) -> LeaveType:
    return await _update_basic_row(session, model=LeaveType, row_id=row_id, data=data, code_label="Mã loại nghỉ phép", name_label="Tên loại nghỉ phép", not_found="Không tìm thấy loại nghỉ phép")


async def soft_delete_leave_type(session: AsyncSession, row_id: int) -> dict:
    return await _soft_delete_basic_row(session, model=LeaveType, row_id=row_id, not_found="Không tìm thấy loại nghỉ phép", label="loại nghỉ phép")


async def lookup_leave_types(session: AsyncSession, *, keyword: Optional[str] = None, is_active: bool = True, limit: int = 20) -> list[LeaveType]:
    return await _lookup_basic(session, model=LeaveType, keyword=keyword, is_active=is_active, limit=limit, order_by=[LeaveType.name])


async def get_contract_template_by_id(session: AsyncSession, row_id: int) -> ContractTemplate:
    row = await session.get(ContractTemplate, row_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mẫu hợp đồng")
    return row


async def _assert_contract_template_unique(session: AsyncSession, *, code: str, version_no: int, exclude_id: Optional[int] = None) -> None:
    query = select(ContractTemplate).where(ContractTemplate.code == code, ContractTemplate.version_no == version_no)
    if exclude_id is not None:
        query = query.where(ContractTemplate.id != exclude_id)
    if (await session.execute(query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mẫu '{code}' phiên bản {version_no} đã tồn tại")


async def list_contract_templates_page(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    contract_category_id: Optional[int] = None,
    document_kind: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = []
    if contract_category_id is not None:
        filters.append(ContractTemplate.contract_category_id == contract_category_id)
    if document_kind:
        filters.append(ContractTemplate.document_kind == document_kind)
    return await _list_basic_page(
        session,
        model=ContractTemplate,
        keyword=keyword,
        is_active=is_active,
        page=page,
        page_size=page_size,
        extra_filters=filters,
        order_by=[ContractTemplate.code, ContractTemplate.version_no.desc()],
    )


async def create_contract_template(session: AsyncSession, data) -> ContractTemplate:
    await get_contract_category_by_id(session, data.contract_category_id)
    await _assert_contract_template_unique(session, code=data.code, version_no=data.version_no)
    row = ContractTemplate(
        code=data.code,
        name=data.name,
        normalized_name=_normalize(data.name),
        contract_category_id=data.contract_category_id,
        document_kind=data.document_kind,
        template_engine=data.template_engine,
        file_name=data.file_name,
        storage_path=data.storage_path,
        mime_type=data.mime_type,
        file_size=data.file_size,
        file_checksum=data.file_checksum,
        version_no=data.version_no,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        is_active=data.is_active,
        note=data.note,
    )
    session.add(row)
    await session.flush()
    return row


async def update_contract_template(session: AsyncSession, row_id: int, data) -> ContractTemplate:
    row = await get_contract_template_by_id(session, row_id)
    provided = data.model_fields_set
    if "contract_category_id" in provided and data.contract_category_id is not None:
        await get_contract_category_by_id(session, data.contract_category_id)
        row.contract_category_id = data.contract_category_id
    if "name" in provided and data.name is not None:
        row.name = data.name
        row.normalized_name = _normalize(data.name)
    for field in ("document_kind", "template_engine", "file_name", "storage_path", "mime_type", "file_size", "file_checksum", "effective_from", "effective_to", "note"):
        if field in provided:
            setattr(row, field, getattr(data, field))
    if "is_active" in provided and data.is_active is not None:
        row.is_active = data.is_active
    row.updated_at = _utcnow()
    await session.flush()
    return row


async def soft_delete_contract_template(session: AsyncSession, row_id: int) -> dict:
    row = await get_contract_template_by_id(session, row_id)
    row.is_active = False
    row.updated_at = _utcnow()
    await session.flush()
    return {"message": f"Đã khóa mẫu hợp đồng '{row.name}'"}


async def list_template_placeholders(session: AsyncSession, template_id: int) -> list[ContractTemplatePlaceholder]:
    await get_contract_template_by_id(session, template_id)
    query = select(ContractTemplatePlaceholder).where(ContractTemplatePlaceholder.template_id == template_id).order_by(ContractTemplatePlaceholder.sort_order, ContractTemplatePlaceholder.id)
    return list((await session.execute(query)).scalars().all())


async def replace_template_placeholders(session: AsyncSession, template_id: int, rows: list) -> list[ContractTemplatePlaceholder]:
    await get_contract_template_by_id(session, template_id)
    seen: set[str] = set()
    for row in rows:
        if row.placeholder_key in seen:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Placeholder '{row.placeholder_key}' bị trùng trong request")
        seen.add(row.placeholder_key)
    await session.execute(
        select(ContractTemplatePlaceholder).where(ContractTemplatePlaceholder.template_id == template_id)
    )
    await session.execute(
        ContractTemplatePlaceholder.__table__.delete().where(ContractTemplatePlaceholder.template_id == template_id)
    )
    for item in rows:
        session.add(
            ContractTemplatePlaceholder(
                template_id=template_id,
                placeholder_key=item.placeholder_key,
                label=item.label,
                source_scope=item.source_scope,
                source_path=item.source_path,
                data_type=item.data_type,
                formatter=item.formatter,
                is_required=item.is_required,
                default_value=item.default_value,
                sort_order=item.sort_order,
            )
        )
    await session.flush()
    return await list_template_placeholders(session, template_id)


async def get_contract_template_field_registry() -> list[dict]:
    return [
        {
            "token": item.token,
            "label": item.label,
            "source_scope": item.source_scope,
            "source_path": item.source_path,
            "data_type": item.data_type,
            "formatter": item.formatter,
            "is_required": item.is_required,
            "recommended_token": item.recommended_token,
        }
        for item in sorted(SUPPORTED_TEMPLATE_FIELDS.values(), key=lambda row: row.token.lower())
    ]


async def inspect_contract_template_docx(session: AsyncSession, template_id: int) -> dict:
    template = await get_contract_template_by_id(session, template_id)
    if not template.storage_path:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mẫu chưa có storage_path để quét DOCX")
    if template.mime_type != DOCX_MIME:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Chỉ hỗ trợ quét file .docx trong bước này")
    docx_path = resolve_template_storage_path(template.storage_path)
    if not docx_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy file mẫu tại '{template.storage_path}'")
    summary = extract_docx_placeholder_summary(docx_path)
    return {
        "template_id": template.id,
        "template_code": template.code,
        "template_name": template.name,
        "storage_path": template.storage_path,
        "file_name": template.file_name,
        **summary,
    }
