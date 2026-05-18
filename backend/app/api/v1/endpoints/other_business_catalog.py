import hashlib
import io
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.catalog import (
    BankCreate,
    BankListPage,
    BankRead,
    BankUpdate,
    CertificateCreate,
    CertificateListPage,
    CertificateRead,
    CertificateUpdate,
    ContractCategoryCreate,
    ContractCategoryListPage,
    ContractCategoryRead,
    ContractCategoryUpdate,
    ContractTemplateCreate,
    ContractTemplateDocxInspectionRead,
    ContractTemplateFieldRegistryRead,
    ContractTemplateHealthRead,
    ContractTemplateListPage,
    ContractTemplatePlaceholderRead,
    ContractTemplatePlaceholderWrite,
    ContractTemplateRead,
    ContractTemplateUpdate,
    EthnicityCreate,
    EthnicityListPage,
    EthnicityRead,
    EthnicityUpdate,
    LeaveTypeCreate,
    LeaveTypeListPage,
    LeaveTypeRead,
    LeaveTypeUpdate,
    NationalityCreate,
    NationalityListPage,
    NationalityRead,
    NationalityUpdate,
    ReligionCreate,
    ReligionListPage,
    ReligionRead,
    ReligionUpdate,
    SkillCreate,
    SkillListPage,
    SkillRead,
    SkillUpdate,
)
from app.core.storage import delete_attachment, get_object_stream, save_template_file
from app.services import auth_service, other_business_catalog_service

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_TEMPLATE_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


contract_category_router = APIRouter()
nationality_router = APIRouter()
ethnicity_router = APIRouter()
religion_router = APIRouter()
bank_router = APIRouter()
skill_router = APIRouter()
certificate_router = APIRouter()
leave_type_router = APIRouter()
contract_template_router = APIRouter()
lookup_router = APIRouter()


def _request_meta(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@contract_category_router.get("", response_model=ContractCategoryListPage, summary="Danh sách loại hợp đồng")
async def list_contract_categories(
    keyword: Optional[str] = Query(None),
    document_kind: Optional[str] = Query(None),
    legal_contract_type: Optional[str] = Query(None),
    business_group: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.list_contract_categories_page(
        session,
        keyword=keyword,
        document_kind=document_kind,
        legal_contract_type=legal_contract_type,
        business_group=business_group,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@contract_category_router.post("", response_model=ContractCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_contract_category(
    body: ContractCategoryCreate,
    request: Request,
    current_user: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    row = await other_business_catalog_service.create_contract_category(session, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="contract_category", entity_id=row.id, entity_name=row.name,
        new_data={"code": row.code, "document_kind": row.document_kind, "legal_contract_type": row.legal_contract_type, "business_group": row.business_group, "is_active": row.is_active},
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
    await session.refresh(row)
    return row


@contract_category_router.get("/{row_id}", response_model=ContractCategoryRead)
async def get_contract_category(row_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_contract_category_by_id(session, row_id)


@contract_category_router.put("/{row_id}", response_model=ContractCategoryRead)
async def update_contract_category(
    row_id: int,
    body: ContractCategoryUpdate,
    request: Request,
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    existing = await other_business_catalog_service.get_contract_category_by_id(session, row_id)
    old_data = {"name": existing.name, "document_kind": existing.document_kind, "legal_contract_type": existing.legal_contract_type, "business_group": existing.business_group, "is_active": existing.is_active}
    row = await other_business_catalog_service.update_contract_category(session, row_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="contract_category", entity_id=row.id, entity_name=row.name,
        old_data=old_data,
        new_data={"name": row.name, "document_kind": row.document_kind, "legal_contract_type": row.legal_contract_type, "business_group": row.business_group, "is_active": row.is_active},
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
    await session.refresh(row)
    return row


@contract_category_router.delete("/{row_id}")
async def delete_contract_category(
    row_id: int,
    request: Request,
    current_user: User = require_permission("catalog:delete"),
    session: AsyncSession = Depends(get_session),
):
    row = await other_business_catalog_service.get_contract_category_by_id(session, row_id)
    result = await other_business_catalog_service.soft_delete_contract_category(session, row_id)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "DELETE", entity_type="contract_category", entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
    await session.commit()
    return result


def _register_basic_catalog_routes(router: APIRouter, *, list_fn_name: str, create_fn_name: str, get_fn_name: str, update_fn_name: str, delete_fn_name: str, read_model, page_model, create_model, update_model, entity_type: str, label: str):
    @router.get("", response_model=page_model)
    async def _list(
        keyword: Optional[str] = Query(None),
        is_active: Optional[bool] = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=200),
        _: User = require_permission("catalog:view"),
        session: AsyncSession = Depends(get_session),
    ):
        fn = getattr(other_business_catalog_service, list_fn_name)
        return await fn(session, keyword=keyword, is_active=is_active, page=page, page_size=page_size)

    @router.post("", response_model=read_model, status_code=status.HTTP_201_CREATED)
    async def _create(
        body: create_model,
        request: Request,
        current_user: User = require_permission("catalog:create"),
        session: AsyncSession = Depends(get_session),
    ):
        fn = getattr(other_business_catalog_service, create_fn_name)
        row = await fn(session, body)
        ip, ua = _request_meta(request)
        await auth_service.log_audit(session, current_user.id, "CREATE", entity_type=entity_type, entity_id=row.id, entity_name=row.name, new_data={"code": row.code, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
        await session.commit()
        await session.refresh(row)
        return row

    @router.get("/{row_id}", response_model=read_model)
    async def _get(
        row_id: int,
        _: User = require_permission("catalog:view"),
        session: AsyncSession = Depends(get_session),
    ):
        fn = getattr(other_business_catalog_service, get_fn_name)
        return await fn(session, row_id)

    @router.put("/{row_id}", response_model=read_model)
    async def _update(
        row_id: int,
        body: update_model,
        request: Request,
        current_user: User = require_permission("catalog:edit"),
        session: AsyncSession = Depends(get_session),
    ):
        get_fn = getattr(other_business_catalog_service, get_fn_name)
        update_fn = getattr(other_business_catalog_service, update_fn_name)
        existing = await get_fn(session, row_id)
        old_data = {"name": existing.name, "is_active": existing.is_active}
        row = await update_fn(session, row_id, body)
        ip, ua = _request_meta(request)
        await auth_service.log_audit(session, current_user.id, "UPDATE", entity_type=entity_type, entity_id=row.id, entity_name=row.name, old_data=old_data, new_data={"name": row.name, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
        await session.commit()
        await session.refresh(row)
        return row

    @router.delete("/{row_id}")
    async def _delete(
        row_id: int,
        request: Request,
        current_user: User = require_permission("catalog:delete"),
        session: AsyncSession = Depends(get_session),
    ):
        get_fn = getattr(other_business_catalog_service, get_fn_name)
        delete_fn = getattr(other_business_catalog_service, delete_fn_name)
        row = await get_fn(session, row_id)
        result = await delete_fn(session, row_id)
        ip, ua = _request_meta(request)
        await auth_service.log_audit(session, current_user.id, "DELETE", entity_type=entity_type, entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
        await session.commit()
        return result


_register_basic_catalog_routes(
    nationality_router,
    list_fn_name="list_nationalities_page", create_fn_name="create_nationality", get_fn_name="get_nationality_by_id", update_fn_name="update_nationality", delete_fn_name="soft_delete_nationality",
    read_model=NationalityRead, page_model=NationalityListPage, create_model=NationalityCreate, update_model=NationalityUpdate,
    entity_type="nationality", label="quốc tịch",
)
_register_basic_catalog_routes(
    ethnicity_router,
    list_fn_name="list_ethnicities_page", create_fn_name="create_ethnicity", get_fn_name="get_ethnicity_by_id", update_fn_name="update_ethnicity", delete_fn_name="soft_delete_ethnicity",
    read_model=EthnicityRead, page_model=EthnicityListPage, create_model=EthnicityCreate, update_model=EthnicityUpdate,
    entity_type="ethnicity", label="dân tộc",
)
_register_basic_catalog_routes(
    religion_router,
    list_fn_name="list_religions_page", create_fn_name="create_religion", get_fn_name="get_religion_by_id", update_fn_name="update_religion", delete_fn_name="soft_delete_religion",
    read_model=ReligionRead, page_model=ReligionListPage, create_model=ReligionCreate, update_model=ReligionUpdate,
    entity_type="religion", label="tôn giáo",
)


@bank_router.get("", response_model=BankListPage)
async def list_banks(
    keyword: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.list_banks_page(session, keyword=keyword, is_active=is_active, page=page, page_size=page_size)


@bank_router.post("", response_model=BankRead, status_code=status.HTTP_201_CREATED)
async def create_bank(
    body: BankCreate,
    request: Request,
    current_user: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    row = await other_business_catalog_service.create_bank(session, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "CREATE", entity_type="bank", entity_id=row.id, entity_name=row.name, new_data={"code": row.code, "short_name": row.short_name, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@bank_router.get("/{row_id}", response_model=BankRead)
async def get_bank(row_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_bank_by_id(session, row_id)


@bank_router.put("/{row_id}", response_model=BankRead)
async def update_bank(
    row_id: int, body: BankUpdate, request: Request, current_user: User = require_permission("catalog:edit"), session: AsyncSession = Depends(get_session)
):
    existing = await other_business_catalog_service.get_bank_by_id(session, row_id)
    old_data = {"name": existing.name, "short_name": existing.short_name, "bin_code": existing.bin_code, "swift_code": existing.swift_code, "is_active": existing.is_active}
    row = await other_business_catalog_service.update_bank(session, row_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "UPDATE", entity_type="bank", entity_id=row.id, entity_name=row.name, old_data=old_data, new_data={"name": row.name, "short_name": row.short_name, "bin_code": row.bin_code, "swift_code": row.swift_code, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@bank_router.delete("/{row_id}")
async def delete_bank(row_id: int, request: Request, current_user: User = require_permission("catalog:delete"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.get_bank_by_id(session, row_id)
    result = await other_business_catalog_service.soft_delete_bank(session, row_id)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "DELETE", entity_type="bank", entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
    await session.commit()
    return result


@skill_router.get("", response_model=SkillListPage)
async def list_skills(
    keyword: Optional[str] = Query(None),
    skill_group: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.list_skills_page(session, keyword=keyword, skill_group=skill_group, is_active=is_active, page=page, page_size=page_size)


@skill_router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(body: SkillCreate, request: Request, current_user: User = require_permission("catalog:create"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.create_skill(session, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "CREATE", entity_type="skill", entity_id=row.id, entity_name=row.name, new_data={"code": row.code, "skill_group": row.skill_group, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@skill_router.get("/{row_id}", response_model=SkillRead)
async def get_skill(row_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_skill_by_id(session, row_id)


@skill_router.put("/{row_id}", response_model=SkillRead)
async def update_skill(row_id: int, body: SkillUpdate, request: Request, current_user: User = require_permission("catalog:edit"), session: AsyncSession = Depends(get_session)):
    existing = await other_business_catalog_service.get_skill_by_id(session, row_id)
    old_data = {"name": existing.name, "skill_group": existing.skill_group, "is_active": existing.is_active}
    row = await other_business_catalog_service.update_skill(session, row_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "UPDATE", entity_type="skill", entity_id=row.id, entity_name=row.name, old_data=old_data, new_data={"name": row.name, "skill_group": row.skill_group, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@skill_router.delete("/{row_id}")
async def delete_skill(row_id: int, request: Request, current_user: User = require_permission("catalog:delete"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.get_skill_by_id(session, row_id)
    result = await other_business_catalog_service.soft_delete_skill(session, row_id)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "DELETE", entity_type="skill", entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
    await session.commit()
    return result


@certificate_router.get("", response_model=CertificateListPage)
async def list_certificates(
    keyword: Optional[str] = Query(None),
    certificate_group: Optional[str] = Query(None),
    expiry_policy: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.list_certificates_page(session, keyword=keyword, certificate_group=certificate_group, expiry_policy=expiry_policy, is_active=is_active, page=page, page_size=page_size)


@certificate_router.post("", response_model=CertificateRead, status_code=status.HTTP_201_CREATED)
async def create_certificate(body: CertificateCreate, request: Request, current_user: User = require_permission("catalog:create"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.create_certificate(session, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "CREATE", entity_type="certificate", entity_id=row.id, entity_name=row.name, new_data={"code": row.code, "certificate_group": row.certificate_group, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@certificate_router.get("/{row_id}", response_model=CertificateRead)
async def get_certificate(row_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_certificate_by_id(session, row_id)


@certificate_router.put("/{row_id}", response_model=CertificateRead)
async def update_certificate(row_id: int, body: CertificateUpdate, request: Request, current_user: User = require_permission("catalog:edit"), session: AsyncSession = Depends(get_session)):
    existing = await other_business_catalog_service.get_certificate_by_id(session, row_id)
    old_data = {"name": existing.name, "certificate_group": existing.certificate_group, "expiry_policy": existing.expiry_policy, "is_active": existing.is_active}
    row = await other_business_catalog_service.update_certificate(session, row_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "UPDATE", entity_type="certificate", entity_id=row.id, entity_name=row.name, old_data=old_data, new_data={"name": row.name, "certificate_group": row.certificate_group, "expiry_policy": row.expiry_policy, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@certificate_router.delete("/{row_id}")
async def delete_certificate(row_id: int, request: Request, current_user: User = require_permission("catalog:delete"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.get_certificate_by_id(session, row_id)
    result = await other_business_catalog_service.soft_delete_certificate(session, row_id)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "DELETE", entity_type="certificate", entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
    await session.commit()
    return result


@leave_type_router.get("", response_model=LeaveTypeListPage)
async def list_leave_types(
    keyword: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.list_leave_types_page(session, keyword=keyword, is_active=is_active, page=page, page_size=page_size)


@leave_type_router.post("", response_model=LeaveTypeRead, status_code=status.HTTP_201_CREATED)
async def create_leave_type(body: LeaveTypeCreate, request: Request, current_user: User = require_permission("catalog:create"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.create_leave_type(session, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "CREATE", entity_type="leave_type", entity_id=row.id, entity_name=row.name, new_data={"code": row.code, "is_paid_leave": row.is_paid_leave, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@leave_type_router.get("/{row_id}", response_model=LeaveTypeRead)
async def get_leave_type(row_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_leave_type_by_id(session, row_id)


@leave_type_router.put("/{row_id}", response_model=LeaveTypeRead)
async def update_leave_type(row_id: int, body: LeaveTypeUpdate, request: Request, current_user: User = require_permission("catalog:edit"), session: AsyncSession = Depends(get_session)):
    existing = await other_business_catalog_service.get_leave_type_by_id(session, row_id)
    old_data = {"name": existing.name, "is_paid_leave": existing.is_paid_leave, "affects_annual_leave": existing.affects_annual_leave, "allow_half_day": existing.allow_half_day, "requires_attachment": existing.requires_attachment, "is_active": existing.is_active}
    row = await other_business_catalog_service.update_leave_type(session, row_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "UPDATE", entity_type="leave_type", entity_id=row.id, entity_name=row.name, old_data=old_data, new_data={"name": row.name, "is_paid_leave": row.is_paid_leave, "affects_annual_leave": row.affects_annual_leave, "allow_half_day": row.allow_half_day, "requires_attachment": row.requires_attachment, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@leave_type_router.delete("/{row_id}")
async def delete_leave_type(row_id: int, request: Request, current_user: User = require_permission("catalog:delete"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.get_leave_type_by_id(session, row_id)
    result = await other_business_catalog_service.soft_delete_leave_type(session, row_id)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "DELETE", entity_type="leave_type", entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
    await session.commit()
    return result


@contract_template_router.get("", response_model=ContractTemplateListPage)
async def list_contract_templates(
    keyword: Optional[str] = Query(None),
    contract_category_id: Optional[int] = Query(None),
    document_kind: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.list_contract_templates_page(session, keyword=keyword, contract_category_id=contract_category_id, document_kind=document_kind, is_active=is_active, page=page, page_size=page_size)


@contract_template_router.post("", response_model=ContractTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_contract_template(body: ContractTemplateCreate, request: Request, current_user: User = require_permission("catalog:create"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.create_contract_template(session, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "CREATE", entity_type="contract_template", entity_id=row.id, entity_name=row.name, new_data={"code": row.code, "version_no": row.version_no, "document_kind": row.document_kind, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@contract_template_router.get("/health-summary", response_model=list[ContractTemplateHealthRead])
async def get_contract_template_health_summary(_: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_contract_template_health_summary(session)


@contract_template_router.get("/{row_id}", response_model=ContractTemplateRead)
async def get_contract_template(row_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.get_contract_template_by_id(session, row_id)


@contract_template_router.put("/{row_id}", response_model=ContractTemplateRead)
async def update_contract_template(row_id: int, body: ContractTemplateUpdate, request: Request, current_user: User = require_permission("catalog:edit"), session: AsyncSession = Depends(get_session)):
    existing = await other_business_catalog_service.get_contract_template_by_id(session, row_id)
    old_data = {"name": existing.name, "file_name": existing.file_name, "document_kind": existing.document_kind, "is_active": existing.is_active}
    row = await other_business_catalog_service.update_contract_template(session, row_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "UPDATE", entity_type="contract_template", entity_id=row.id, entity_name=row.name, old_data=old_data, new_data={"name": row.name, "file_name": row.file_name, "document_kind": row.document_kind, "is_active": row.is_active}, ip_address=ip, user_agent=ua)
    await session.commit()
    await session.refresh(row)
    return row


@contract_template_router.delete("/{row_id}")
async def delete_contract_template(row_id: int, request: Request, current_user: User = require_permission("catalog:delete"), session: AsyncSession = Depends(get_session)):
    row = await other_business_catalog_service.get_contract_template_by_id(session, row_id)
    result = await other_business_catalog_service.soft_delete_contract_template(session, row_id)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(session, current_user.id, "DELETE", entity_type="contract_template", entity_id=row.id, entity_name=row.name, old_data={"is_active": True}, new_data={"is_active": False}, ip_address=ip, user_agent=ua)
    await session.commit()
    return result


@contract_template_router.get("/{template_id}/placeholders", response_model=list[ContractTemplatePlaceholderRead])
async def get_contract_template_placeholders(template_id: int, _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.list_template_placeholders(session, template_id)


@contract_template_router.put("/{template_id}/placeholders", response_model=list[ContractTemplatePlaceholderRead])
async def put_contract_template_placeholders(
    template_id: int,
    body: list[ContractTemplatePlaceholderWrite],
    request: Request,
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    template = await other_business_catalog_service.get_contract_template_by_id(session, template_id)
    old_rows = await other_business_catalog_service.list_template_placeholders(session, template_id)
    rows = await other_business_catalog_service.replace_template_placeholders(session, template_id, body)
    ip, ua = _request_meta(request)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="contract_template", entity_id=template.id, entity_name=template.name,
        old_data={"placeholder_count": len(old_rows)},
        new_data={"placeholder_count": len(rows)},
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
    return rows


@contract_template_router.post("/{template_id}/inspect-docx", response_model=ContractTemplateDocxInspectionRead)
async def inspect_contract_template_docx(
    template_id: int,
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.inspect_contract_template_docx(session, template_id)


@contract_template_router.post("/{template_id}/upload", response_model=ContractTemplateRead, tags=["Danh mục nghiệp vụ khác"])
async def upload_contract_template_file(
    template_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    if Path(file.filename or "").suffix.lower() != ".docx":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Chỉ chấp nhận file .docx")

    content = await file.read()
    if len(content) > _TEMPLATE_MAX_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File vượt quá giới hạn 5 MB")

    checksum = hashlib.md5(content).hexdigest()

    # Lấy template, xóa file cũ trên MinIO nếu có
    template = await other_business_catalog_service.get_contract_template_by_id(session, template_id)
    old_path = template.storage_path

    # Reset buffer để save_template_file có thể đọc
    file.file = io.BytesIO(content)  # type: ignore[assignment]
    file.size = len(content)

    object_name, file_size = await save_template_file(template_id, file)
    row = await other_business_catalog_service.update_template_file_meta(
        session, template_id,
        object_name=object_name,
        file_name=file.filename or "template.docx",
        file_size=file_size,
        file_checksum=checksum,
    )

    if old_path:
        delete_attachment(old_path)

    ip, ua = _request_meta(request)
    await auth_service.log_audit(
        session, current_user.id, "UPLOAD_TEMPLATE_FILE",
        entity_type="contract_template", entity_id=template_id,
        entity_name=row.name,
        new_data={"file_name": row.file_name, "file_size": row.file_size},
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
    await session.refresh(row)
    return row


@contract_template_router.get("/{template_id}/download", tags=["Danh mục nghiệp vụ khác"])
async def download_contract_template_file(
    template_id: int,
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    template = await other_business_catalog_service.get_contract_template_by_id(session, template_id)
    if not template.storage_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mẫu hợp đồng chưa có file đính kèm")

    filename = template.file_name or "template.docx"
    return StreamingResponse(
        get_object_stream(template.storage_path),
        media_type=template.mime_type or _DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@lookup_router.get("/lookups/contract-categories", response_model=list[ContractCategoryRead])
async def lookup_contract_categories(
    keyword: Optional[str] = Query(None),
    document_kind: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await other_business_catalog_service.lookup_contract_categories(session, keyword=keyword, document_kind=document_kind, limit=limit)


@lookup_router.get("/lookups/nationalities", response_model=list[NationalityRead])
async def lookup_nationalities(keyword: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_nationalities(session, keyword=keyword, limit=limit)


@lookup_router.get("/lookups/ethnicities", response_model=list[EthnicityRead])
async def lookup_ethnicities(keyword: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_ethnicities(session, keyword=keyword, limit=limit)


@lookup_router.get("/lookups/religions", response_model=list[ReligionRead])
async def lookup_religions(keyword: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_religions(session, keyword=keyword, limit=limit)


@lookup_router.get("/lookups/banks", response_model=list[BankRead])
async def lookup_banks(keyword: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_banks(session, keyword=keyword, limit=limit)


@lookup_router.get("/lookups/skills", response_model=list[SkillRead])
async def lookup_skills(keyword: Optional[str] = Query(None), skill_group: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_skills(session, keyword=keyword, skill_group=skill_group, limit=limit)


@lookup_router.get("/lookups/certificates", response_model=list[CertificateRead])
async def lookup_certificates(keyword: Optional[str] = Query(None), certificate_group: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_certificates(session, keyword=keyword, certificate_group=certificate_group, limit=limit)


@lookup_router.get("/lookups/leave-types", response_model=list[LeaveTypeRead])
async def lookup_leave_types(keyword: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100), _: User = require_permission("catalog:view"), session: AsyncSession = Depends(get_session)):
    return await other_business_catalog_service.lookup_leave_types(session, keyword=keyword, limit=limit)


@lookup_router.get("/lookups/contract-template-fields", response_model=list[ContractTemplateFieldRegistryRead])
async def lookup_contract_template_fields(
    _: User = require_permission("catalog:view"),
):
    return await other_business_catalog_service.get_contract_template_field_registry()
