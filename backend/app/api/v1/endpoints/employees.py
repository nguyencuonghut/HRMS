"""Quản lý nhân viên — CRUD hồ sơ cá nhân (3.1) + thông tin công việc (3.2) + người thân (3.3) + học vấn (3.4) + hồ sơ đính kèm (3.5)."""

from datetime import timedelta

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.core.security import create_signed_token, decode_token
from app.models.auth import User
from app.schemas.employee import (
    EmployeeAddressRead,
    EmployeeAddressWrite,
    EmployeeBankAccountRead,
    EmployeeBankAccountWrite,
    EmployeeCreate,
    EmployeeListPage,
    EmployeeRead,
    EmployeeUpdate,
    EmployeeLookupItem,
    JobRecordCreate,
    JobRecordRead,
    JobRecordTransfer,
    JobRecordUpdate,
    EmployeeRelativeRead,
    RelativeCreate,
    RelativeUpdate,
    EducationHistoryRead,
    EducationHistoryCreate,
    EducationHistoryUpdate,
    WorkExperienceRead,
    WorkExperienceCreate,
    WorkExperienceUpdate,
    EmployeeSkillRead,
    EmployeeSkillCreate,
    EmployeeSkillUpdate,
    EmployeeCertificateRead,
    EmployeeCertificateCreate,
    EmployeeCertificateUpdate,
    EmployeeLanguageRead,
    EmployeeLanguageCreate,
    EmployeeLanguageUpdate,
)
from app.schemas.employee_attachment import (
    EmployeeAttachmentRead,
    MAX_FILE_SIZE,
    VALID_DOCUMENT_TYPES,
)
from app.services import (
    auth_service,
    employee_attachment_service,
    employee_code_service,
    employee_education_service,
    employee_job_service,
    employee_relative_service,
    employee_service,
)
from app.core.storage import delete_attachment, get_object_stream, save_employee_attachment

router = APIRouter()

_PREVIEW_TOKEN_TTL_SECONDS = 300


class PreviewLinkRead(BaseModel):
    url: str
    expires_in_seconds: int


def _build_preview_token(*, employee_id: int, resource_id: int, resource_kind: str) -> str:
    return create_signed_token(
        "employee-file-preview",
        token_type="preview",
        expires=timedelta(seconds=_PREVIEW_TOKEN_TTL_SECONDS),
        extra_claims={
            "scope": "employee-file-preview",
            "employee_id": employee_id,
            "resource_id": resource_id,
            "resource_kind": resource_kind,
        },
    )


def _validate_preview_token(
    token: str,
    *,
    employee_id: int,
    resource_id: int,
    resource_kind: str,
) -> None:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Link preview không hợp lệ hoặc đã hết hạn",
    )
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise exc from e
    if payload.get("type") != "preview" or payload.get("scope") != "employee-file-preview":
        raise exc
    if payload.get("employee_id") != employee_id:
        raise exc
    if payload.get("resource_id") != resource_id:
        raise exc
    if payload.get("resource_kind") != resource_kind:
        raise exc


def _build_list_item_data(emp, display_code: str) -> dict:
    return {
        "id": emp.id,
        "employee_seq": emp.employee_seq,
        "display_code": display_code,
        "full_name": emp.full_name,
        "date_of_birth": emp.date_of_birth,
        "gender": emp.gender,
        "nationality_id": emp.nationality_id,
        "ethnicity_id": emp.ethnicity_id,
        "id_number": emp.id_number,
        "phone_number": emp.phone_number,
        "personal_email": emp.personal_email,
        "status": emp.status,
        "start_date": emp.start_date,
        "resigned_date": emp.resigned_date,
        "is_active": emp.is_active,
        "created_at": emp.created_at,
        "updated_at": emp.updated_at,
        "id_expires_on": emp.id_expires_on,
        "passport_expires_on": emp.passport_expires_on,
        "work_permit_expires_on": emp.work_permit_expires_on,
    }


# ── Lookup (phải trước /{employee_id}) ────────────────────────────────────────

@router.get(
    "/lookup",
    response_model=list[EmployeeLookupItem],
    summary="Tìm kiếm nhanh nhân viên (cho dropdown)",
)
async def lookup_employees(
    keyword: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=500),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    items = await employee_service.lookup_employees(session, keyword=keyword, limit=limit)
    display_codes = await employee_code_service.batch_build_employee_display_codes(session, items)
    return [
        EmployeeLookupItem(
            id=e.id,
            employee_seq=e.employee_seq,
            display_code=display_codes[e.id],
            full_name=e.full_name,
            status=e.status,
        )
        for e in items
    ]


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=EmployeeListPage, summary="Danh sách nhân viên (phân trang)")
async def list_employees(
    keyword: Optional[str] = Query(None, description="Tìm theo tên, số CCCD, SĐT"),
    status: Optional[str] = Query(None, description="probation | official | long_leave | resigned"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    result = await employee_service.list_employees_page(
        session,
        keyword=keyword,
        status=status,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    from app.schemas.employee import EmployeeListItem
    display_codes = await employee_code_service.batch_build_employee_display_codes(session, result["items"])
    items = [
        EmployeeListItem(**_build_list_item_data(
            emp,
            display_codes[emp.id],
        ))
        for emp in result["items"]
    ]
    return EmployeeListPage(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED, summary="Tạo nhân viên mới")
async def create_employee(
    payload: EmployeeCreate,
    current_user: User = require_permission("employees:create"),
    session: AsyncSession = Depends(get_session),
):
    emp = await employee_service.create_employee(session, payload)
    await session.flush()
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="employee", entity_id=emp.id, entity_name=emp.full_name,
        new_data={"employee_seq": emp.employee_seq, "full_name": emp.full_name, "status": emp.status},
    )
    await session.commit()
    await session.refresh(emp)
    extra = await employee_service.build_employee_read_data(session, emp)
    return EmployeeRead(**emp.model_dump(), **extra)


# ── Get by ID ──────────────────────────────────────────────────────────────────

@router.get("/{employee_id}", response_model=EmployeeRead, summary="Chi tiết nhân viên")
async def get_employee(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    emp = await employee_service.get_employee_by_id(session, employee_id)
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    extra = await employee_service.build_employee_read_data(session, emp)
    return EmployeeRead(**emp.model_dump(), **extra)


# ── Update ─────────────────────────────────────────────────────────────────────

@router.put("/{employee_id}", response_model=EmployeeRead, summary="Cập nhật thông tin nhân viên")
async def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    emp_before = await employee_service.get_employee_by_id(session, employee_id)
    if not emp_before:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    old_data = {"full_name": emp_before.full_name, "status": emp_before.status, "is_active": emp_before.is_active}
    emp = await employee_service.update_employee(session, employee_id, payload)
    new_data = {"full_name": emp.full_name, "status": emp.status, "is_active": emp.is_active}

    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="employee", entity_id=emp.id, entity_name=emp.full_name,
        old_data=old_data, new_data=new_data,
    )
    await session.commit()
    await session.refresh(emp)
    extra = await employee_service.build_employee_read_data(session, emp)
    return EmployeeRead(**emp.model_dump(), **extra)


# ── Soft delete ────────────────────────────────────────────────────────────────

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Vô hiệu hóa nhân viên")
async def deactivate_employee(
    employee_id: int,
    current_user: User = require_permission("employees:delete"),
    session: AsyncSession = Depends(get_session),
):
    emp = await employee_service.soft_delete_employee(session, employee_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="employee", entity_id=emp.id, entity_name=emp.full_name,
    )
    await session.commit()


# ── Addresses ──────────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/addresses",
    response_model=list[EmployeeAddressRead],
    summary="Danh sách địa chỉ nhân viên",
)
async def get_addresses(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    addresses = await employee_service.get_employee_addresses(session, employee_id)
    return await employee_service.enrich_addresses(session, addresses)


@router.put(
    "/{employee_id}/addresses",
    response_model=EmployeeAddressRead,
    summary="Tạo hoặc cập nhật địa chỉ nhân viên",
)
async def upsert_address(
    employee_id: int,
    payload: EmployeeAddressWrite,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    addr = await employee_service.upsert_employee_address(session, employee_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="employee_address", entity_id=employee_id,
        new_data={"address_type": payload.address_type},
    )
    await session.commit()
    await session.refresh(addr)
    return await employee_service.build_address_read(session, addr)


# ── Bank Accounts ──────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/bank-accounts",
    response_model=list[EmployeeBankAccountRead],
    summary="Danh sách tài khoản ngân hàng",
)
async def get_bank_accounts(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    return await employee_service.get_employee_bank_accounts(session, employee_id)


@router.post(
    "/{employee_id}/bank-accounts",
    response_model=EmployeeBankAccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm tài khoản ngân hàng",
)
async def add_bank_account(
    employee_id: int,
    payload: EmployeeBankAccountWrite,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    acc = await employee_service.create_bank_account(session, employee_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="employee_bank_account", entity_id=employee_id,
        new_data={"account_number": payload.account_number, "bank_id": payload.bank_id},
    )
    await session.commit()
    await session.refresh(acc)
    return acc


@router.put(
    "/{employee_id}/bank-accounts/{account_id}",
    response_model=EmployeeBankAccountRead,
    summary="Cập nhật tài khoản ngân hàng",
)
async def update_bank_account(
    employee_id: int,
    account_id: int,
    payload: EmployeeBankAccountWrite,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    acc = await employee_service.update_bank_account(session, employee_id, account_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="employee_bank_account", entity_id=employee_id,
        new_data={"account_id": account_id, "account_number": payload.account_number},
    )
    await session.commit()
    await session.refresh(acc)
    return acc


@router.delete(
    "/{employee_id}/bank-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa tài khoản ngân hàng",
)
async def delete_bank_account(
    employee_id: int,
    account_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service.delete_bank_account(session, employee_id, account_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="employee_bank_account", entity_id=employee_id,
        new_data={"account_id": account_id},
    )
    await session.commit()


# ── Job Records (3.2) ──────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/job-records",
    response_model=list[JobRecordRead],
    summary="Lịch sử công việc (mới nhất trước)",
)
async def get_job_records(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    records = await employee_job_service.get_job_records(session, employee_id)
    return [await employee_job_service.build_job_record_read(session, r) for r in records]


@router.post(
    "/{employee_id}/job-records",
    response_model=JobRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Gán phòng ban lần đầu",
)
async def create_job_record(
    employee_id: int,
    payload: JobRecordCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    result = await employee_job_service.create_job_record(session, employee_id, payload, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE_JOB_RECORD",
        entity_type="employee_job_record", entity_id=employee_id,
        new_data={"department_id": payload.department_id, "effective_from": str(payload.effective_from)},
    )
    await session.commit()
    return result


@router.put(
    "/{employee_id}/job-records/current",
    response_model=JobRecordRead,
    summary="Sửa bản ghi công việc hiện tại (chỉnh ghi nhầm, không tạo lịch sử)",
)
async def update_current_job_record(
    employee_id: int,
    payload: JobRecordUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    result = await employee_job_service.update_current_record(session, employee_id, payload, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_JOB_RECORD",
        entity_type="employee_job_record", entity_id=employee_id,
        new_data=payload.model_dump(exclude_none=True),
    )
    await session.commit()
    return result


@router.post(
    "/{employee_id}/job-records/transfer",
    response_model=JobRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Chuyển công tác / thăng chức (tạo bản ghi mới, giữ lịch sử)",
)
async def transfer_job_record(
    employee_id: int,
    payload: JobRecordTransfer,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    result = await employee_job_service.transfer_job_record(session, employee_id, payload, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "TRANSFER_JOB_RECORD",
        entity_type="employee_job_record", entity_id=employee_id,
        new_data={"department_id": payload.department_id, "effective_from": str(payload.effective_from)},
    )
    await session.commit()
    return result


# ── Relatives (3.3) ────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/relatives",
    response_model=list[EmployeeRelativeRead],
    summary="Danh sách người thân",
)
async def get_relatives(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_relative_service.get_relatives(session, employee_id)


@router.post(
    "/{employee_id}/relatives",
    response_model=EmployeeRelativeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm người thân",
)
async def create_relative(
    employee_id: int,
    payload: RelativeCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    rel = await employee_relative_service.create_relative(session, employee_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE_RELATIVE",
        entity_type="employee_relative", entity_id=employee_id,
        new_data={"full_name": payload.full_name, "relationship_type": payload.relationship_type},
    )
    await session.commit()
    await session.refresh(rel)
    return rel


@router.put(
    "/{employee_id}/relatives/{relative_id}",
    response_model=EmployeeRelativeRead,
    summary="Cập nhật thông tin người thân",
)
async def update_relative(
    employee_id: int,
    relative_id: int,
    payload: RelativeUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    rel = await employee_relative_service.update_relative(session, employee_id, relative_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_RELATIVE",
        entity_type="employee_relative", entity_id=employee_id,
        new_data={"relative_id": relative_id, **payload.model_dump(exclude_unset=True)},
    )
    await session.commit()
    await session.refresh(rel)
    return rel


@router.delete(
    "/{employee_id}/relatives/{relative_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa người thân",
)
async def delete_relative(
    employee_id: int,
    relative_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    await employee_relative_service.delete_relative(session, employee_id, relative_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_RELATIVE",
        entity_type="employee_relative", entity_id=employee_id,
        new_data={"relative_id": relative_id},
    )
    await session.commit()


# ── Education Histories (3.4) ─────────────────────────────────────────────────

@router.get(
    "/{employee_id}/education-histories",
    response_model=list[EducationHistoryRead],
    summary="Danh sách học vấn",
)
async def list_education_histories(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_education_service.get_education_histories(session, employee_id)


@router.post(
    "/{employee_id}/education-histories",
    response_model=EducationHistoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm học vấn",
)
async def create_education_history(
    employee_id: int,
    payload: EducationHistoryCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    edu = await employee_education_service.create_education_history(session, employee_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE_EDUCATION_HISTORY",
        entity_type="employee_education", entity_id=employee_id,
        new_data={"edu_id": edu.id, "institution_name": edu.institution_name or edu.institution_id},
    )
    await session.commit()
    return edu


@router.put(
    "/{employee_id}/education-histories/{edu_id}",
    response_model=EducationHistoryRead,
    summary="Cập nhật học vấn",
)
async def update_education_history(
    employee_id: int,
    edu_id: int,
    payload: EducationHistoryUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    edu = await employee_education_service.update_education_history(session, employee_id, edu_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_EDUCATION_HISTORY",
        entity_type="employee_education", entity_id=employee_id,
        new_data={"edu_id": edu_id, **payload.model_dump(exclude_unset=True)},
    )
    await session.commit()
    return edu


@router.delete(
    "/{employee_id}/education-histories/{edu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa học vấn",
)
async def delete_education_history(
    employee_id: int,
    edu_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    await employee_education_service.delete_education_history(session, employee_id, edu_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_EDUCATION_HISTORY",
        entity_type="employee_education", entity_id=employee_id,
        new_data={"edu_id": edu_id},
    )
    await session.commit()


# ── Work Experiences (3.4) ────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/work-experiences",
    response_model=list[WorkExperienceRead],
    summary="Danh sách kinh nghiệm làm việc",
)
async def list_work_experiences(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_education_service.get_work_experiences(session, employee_id)


@router.post(
    "/{employee_id}/work-experiences",
    response_model=WorkExperienceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm kinh nghiệm làm việc",
)
async def create_work_experience(
    employee_id: int,
    payload: WorkExperienceCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    exp = await employee_education_service.create_work_experience(session, employee_id, payload)
    await session.flush()
    await auth_service.log_audit(
        session, current_user.id, "CREATE_WORK_EXPERIENCE",
        entity_type="employee_work_experience", entity_id=employee_id,
        new_data={"exp_id": exp.id, "company_name": exp.company_name},
    )
    await session.commit()
    await session.refresh(exp)
    return exp


@router.put(
    "/{employee_id}/work-experiences/{exp_id}",
    response_model=WorkExperienceRead,
    summary="Cập nhật kinh nghiệm làm việc",
)
async def update_work_experience(
    employee_id: int,
    exp_id: int,
    payload: WorkExperienceUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    exp = await employee_education_service.update_work_experience(session, employee_id, exp_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_WORK_EXPERIENCE",
        entity_type="employee_work_experience", entity_id=employee_id,
        new_data={"exp_id": exp_id, **payload.model_dump(exclude_unset=True)},
    )
    await session.commit()
    await session.refresh(exp)
    return exp


@router.delete(
    "/{employee_id}/work-experiences/{exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa kinh nghiệm làm việc",
)
async def delete_work_experience(
    employee_id: int,
    exp_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    await employee_education_service.delete_work_experience(session, employee_id, exp_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_WORK_EXPERIENCE",
        entity_type="employee_work_experience", entity_id=employee_id,
        new_data={"exp_id": exp_id},
    )
    await session.commit()


# ── Skills (3.4) ──────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/skills",
    response_model=list[EmployeeSkillRead],
    summary="Danh sách kỹ năng",
)
async def list_employee_skills(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_education_service.get_employee_skills(session, employee_id)


@router.post(
    "/{employee_id}/skills",
    response_model=EmployeeSkillRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm kỹ năng",
)
async def create_employee_skill(
    employee_id: int,
    payload: EmployeeSkillCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    sk = await employee_education_service.create_employee_skill(session, employee_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE_SKILL",
        entity_type="employee_skill", entity_id=employee_id,
        new_data={"skill_id": payload.skill_id, "proficiency_level": payload.proficiency_level},
    )
    await session.commit()
    return sk


@router.put(
    "/{employee_id}/skills/{skill_record_id}",
    response_model=EmployeeSkillRead,
    summary="Cập nhật kỹ năng",
)
async def update_employee_skill(
    employee_id: int,
    skill_record_id: int,
    payload: EmployeeSkillUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    sk = await employee_education_service.update_employee_skill(session, employee_id, skill_record_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_SKILL",
        entity_type="employee_skill", entity_id=employee_id,
        new_data={"skill_record_id": skill_record_id, **payload.model_dump(exclude_unset=True)},
    )
    await session.commit()
    return sk


@router.delete(
    "/{employee_id}/skills/{skill_record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa kỹ năng",
)
async def delete_employee_skill(
    employee_id: int,
    skill_record_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    await employee_education_service.delete_employee_skill(session, employee_id, skill_record_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_SKILL",
        entity_type="employee_skill", entity_id=employee_id,
        new_data={"skill_record_id": skill_record_id},
    )
    await session.commit()


# ── Certificates (3.4) ────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/certificates",
    response_model=list[EmployeeCertificateRead],
    summary="Danh sách chứng chỉ",
)
async def list_employee_certificates(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_education_service.get_employee_certificates(session, employee_id)


@router.post(
    "/{employee_id}/certificates",
    response_model=EmployeeCertificateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm chứng chỉ",
)
async def create_employee_certificate(
    employee_id: int,
    payload: EmployeeCertificateCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    cert = await employee_education_service.create_employee_certificate(session, employee_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE_CERTIFICATE",
        entity_type="employee_certificate", entity_id=employee_id,
        new_data={"certificate_id": payload.certificate_id},
    )
    await session.commit()
    return cert


@router.put(
    "/{employee_id}/certificates/{cert_id}",
    response_model=EmployeeCertificateRead,
    summary="Cập nhật chứng chỉ",
)
async def update_employee_certificate(
    employee_id: int,
    cert_id: int,
    payload: EmployeeCertificateUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    cert = await employee_education_service.update_employee_certificate(session, employee_id, cert_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_CERTIFICATE",
        entity_type="employee_certificate", entity_id=employee_id,
        new_data={"cert_id": cert_id, **payload.model_dump(exclude_unset=True)},
    )
    await session.commit()
    return cert


@router.delete(
    "/{employee_id}/certificates/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa chứng chỉ",
)
async def delete_employee_certificate(
    employee_id: int,
    cert_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    await employee_education_service.delete_employee_certificate(session, employee_id, cert_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_CERTIFICATE",
        entity_type="employee_certificate", entity_id=employee_id,
        new_data={"cert_id": cert_id},
    )
    await session.commit()


# ── Languages (3.4) ───────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/languages",
    response_model=list[EmployeeLanguageRead],
    summary="Danh sách ngoại ngữ",
)
async def list_employee_languages(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_education_service.get_employee_languages(session, employee_id)


@router.post(
    "/{employee_id}/languages",
    response_model=EmployeeLanguageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm ngoại ngữ",
)
async def create_employee_language(
    employee_id: int,
    payload: EmployeeLanguageCreate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    lang = await employee_education_service.create_employee_language(session, employee_id, payload)
    await session.flush()
    await auth_service.log_audit(
        session, current_user.id, "CREATE_LANGUAGE",
        entity_type="employee_language", entity_id=employee_id,
        new_data={"language_name": payload.language_name, "proficiency_level": payload.proficiency_level},
    )
    await session.commit()
    await session.refresh(lang)
    return lang


@router.put(
    "/{employee_id}/languages/{lang_id}",
    response_model=EmployeeLanguageRead,
    summary="Cập nhật ngoại ngữ",
)
async def update_employee_language(
    employee_id: int,
    lang_id: int,
    payload: EmployeeLanguageUpdate,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    lang = await employee_education_service.update_employee_language(session, employee_id, lang_id, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_LANGUAGE",
        entity_type="employee_language", entity_id=employee_id,
        new_data={"lang_id": lang_id, **payload.model_dump(exclude_unset=True)},
    )
    await session.commit()
    await session.refresh(lang)
    return lang


@router.delete(
    "/{employee_id}/languages/{lang_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa ngoại ngữ",
)
async def delete_employee_language(
    employee_id: int,
    lang_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    await employee_education_service.delete_employee_language(session, employee_id, lang_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_LANGUAGE",
        entity_type="employee_language", entity_id=employee_id,
        new_data={"lang_id": lang_id},
    )
    await session.commit()


# ── 3.5 Hồ sơ đính kèm ────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/attachments",
    response_model=list[EmployeeAttachmentRead],
    summary="Danh sách tài liệu đính kèm",
)
async def list_attachments(
    employee_id: int,
    document_type: Optional[str] = Query(None, description="Lọc theo loại tài liệu"),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await employee_attachment_service.get_attachments(session, employee_id, document_type)


@router.post(
    "/{employee_id}/attachments",
    response_model=EmployeeAttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload tài liệu đính kèm",
)
async def upload_attachment(
    employee_id: int,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(422, detail=f"document_type không hợp lệ: {document_type}")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, detail="File vượt quá giới hạn 20 MB")
    await file.seek(0)
    object_name, file_size = await save_employee_attachment(employee_id, file)
    att = await employee_attachment_service.create_attachment(
        session,
        employee_id=employee_id,
        document_type=document_type,
        description=description,
        file_name=file.filename or "file",
        file_path=object_name,
        file_size=file_size,
        mime_type=file.content_type,
    )
    await auth_service.log_audit(
        session, current_user.id, "UPLOAD_ATTACHMENT",
        entity_type="employee_attachment", entity_id=employee_id,
        new_data={"document_type": document_type, "file_name": file.filename},
    )
    await session.commit()
    return att


@router.get(
    "/{employee_id}/attachments/{att_id}/download",
    summary="Tải tài liệu đính kèm",
)
async def download_attachment(
    employee_id: int,
    att_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    att = await employee_attachment_service.get_attachment_or_404(session, employee_id, att_id)
    filename = att.file_name.encode("utf-8").decode("latin-1", errors="replace")
    return StreamingResponse(
        get_object_stream(att.file_path),
        media_type=att.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{employee_id}/attachments/{att_id}/preview-url",
    response_model=PreviewLinkRead,
    summary="Lấy link preview ngắn hạn cho tài liệu đính kèm",
)
async def get_attachment_preview_url(
    employee_id: int,
    att_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    await employee_attachment_service.get_attachment_or_404(session, employee_id, att_id)
    token = _build_preview_token(
        employee_id=employee_id,
        resource_id=att_id,
        resource_kind="attachment",
    )
    return PreviewLinkRead(
        url=f"/api/v1/employees/{employee_id}/attachments/{att_id}/preview?token={token}",
        expires_in_seconds=_PREVIEW_TOKEN_TTL_SECONDS,
    )


@router.get(
    "/{employee_id}/attachments/{att_id}/preview",
    summary="Preview tài liệu đính kèm bằng link ngắn hạn",
)
async def preview_attachment(
    employee_id: int,
    att_id: int,
    token: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
):
    _validate_preview_token(
        token,
        employee_id=employee_id,
        resource_id=att_id,
        resource_kind="attachment",
    )
    att = await employee_attachment_service.get_attachment_or_404(session, employee_id, att_id)
    filename = att.file_name.encode("utf-8").decode("latin-1", errors="replace")
    return StreamingResponse(
        get_object_stream(att.file_path),
        media_type=att.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete(
    "/{employee_id}/attachments/{att_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa tài liệu đính kèm",
)
async def delete_attachment_endpoint(
    employee_id: int,
    att_id: int,
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    att = await employee_attachment_service.get_attachment_or_404(session, employee_id, att_id)
    delete_attachment(att.file_path)
    await session.delete(att)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_ATTACHMENT",
        entity_type="employee_attachment", entity_id=employee_id,
        new_data={"att_id": att_id, "file_name": att.file_name},
    )
    await session.commit()


# ── Document Checklist (13.6) ─────────────────────────────────────────────────
from app.services import document_checklist_service
from app.services.document_checklist_service import ChecklistItemRead, ChecklistItemUpdate
from app.core.storage import get_object_stream as _get_obj_stream

_DOC_PERM_VIEW = "recruitment:view"
_DOC_PERM_MANAGE = "recruitment:manage"

@router.get(
    "/{employee_id}/document-checklist",
    response_model=list[ChecklistItemRead],
    summary="Danh sách hồ sơ pháp lý nhân viên",
)
async def get_document_checklist(
    employee_id: int,
    _: User = require_permission(_DOC_PERM_VIEW),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    return await document_checklist_service.get_employee_checklist(session, employee_id)


@router.put(
    "/{employee_id}/document-checklist/{item_id}",
    response_model=ChecklistItemRead,
    summary="Cập nhật trạng thái giấy tờ",
)
async def update_checklist_item(
    employee_id: int,
    item_id: int,
    data: ChecklistItemUpdate,
    current_user: User = require_permission(_DOC_PERM_MANAGE),
    session: AsyncSession = Depends(get_session),
):
    result = await document_checklist_service.update_checklist_item(
        session, employee_id, item_id, data, current_user.id
    )
    await session.commit()
    return result


@router.post(
    "/{employee_id}/document-checklist/{item_id}/upload",
    response_model=ChecklistItemRead,
    summary="Upload file scan giấy tờ",
)
async def upload_checklist_file(
    employee_id: int,
    item_id: int,
    file: UploadFile = File(...),
    current_user: User = require_permission(_DOC_PERM_MANAGE),
    session: AsyncSession = Depends(get_session),
):
    result = await document_checklist_service.upload_document_file(
        session, employee_id, item_id, file, current_user.id
    )
    await session.commit()
    return result


@router.get(
    "/{employee_id}/document-checklist/{item_id}/download",
    summary="Tải file scan giấy tờ",
)
async def download_checklist_file(
    employee_id: int,
    item_id: int,
    _: User = require_permission(_DOC_PERM_VIEW),
    session: AsyncSession = Depends(get_session),
):
    file_path, file_name, mime_type = await document_checklist_service.get_document_download_stream(
        session, employee_id, item_id
    )
    safe_name = (file_name or "file").encode("utf-8").decode("latin-1", errors="replace")
    return StreamingResponse(
        _get_obj_stream(file_path),
        media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get(
    "/{employee_id}/document-checklist/{item_id}/preview-url",
    response_model=PreviewLinkRead,
    summary="Lấy link preview ngắn hạn cho file checklist",
)
async def get_checklist_preview_url(
    employee_id: int,
    item_id: int,
    _: User = require_permission(_DOC_PERM_VIEW),
    session: AsyncSession = Depends(get_session),
):
    await document_checklist_service.get_document_download_stream(session, employee_id, item_id)
    token = _build_preview_token(
        employee_id=employee_id,
        resource_id=item_id,
        resource_kind="document-checklist",
    )
    return PreviewLinkRead(
        url=f"/api/v1/employees/{employee_id}/document-checklist/{item_id}/preview?token={token}",
        expires_in_seconds=_PREVIEW_TOKEN_TTL_SECONDS,
    )


@router.get(
    "/{employee_id}/document-checklist/{item_id}/preview",
    summary="Preview file checklist bằng link ngắn hạn",
)
async def preview_checklist_file(
    employee_id: int,
    item_id: int,
    token: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
):
    _validate_preview_token(
        token,
        employee_id=employee_id,
        resource_id=item_id,
        resource_kind="document-checklist",
    )
    file_path, file_name, mime_type = await document_checklist_service.get_document_download_stream(
        session, employee_id, item_id
    )
    safe_name = (file_name or "file").encode("utf-8").decode("latin-1", errors="replace")
    return StreamingResponse(
        _get_obj_stream(file_path),
        media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


@router.delete(
    "/{employee_id}/document-checklist/{item_id}/file",
    response_model=ChecklistItemRead,
    summary="Xóa file scan (giữ record)",
)
async def delete_checklist_file(
    employee_id: int,
    item_id: int,
    current_user: User = require_permission(_DOC_PERM_MANAGE),
    session: AsyncSession = Depends(get_session),
):
    result = await document_checklist_service.delete_document_file(
        session, employee_id, item_id, current_user.id
    )
    await session.commit()
    return result


@router.post(
    "/{employee_id}/document-checklist/{item_id}/waive",
    response_model=ChecklistItemRead,
    summary="Miễn giấy tờ",
)
async def waive_checklist_item(
    employee_id: int,
    item_id: int,
    reason: str,
    current_user: User = require_permission(_DOC_PERM_MANAGE),
    session: AsyncSession = Depends(get_session),
):
    result = await document_checklist_service.waive_item(
        session, employee_id, item_id, reason, current_user.id
    )
    await session.commit()
    return result


@router.post(
    "/{employee_id}/document-checklist/init",
    response_model=list[ChecklistItemRead],
    summary="Khởi tạo checklist giấy tờ mặc định cho nhân viên",
)
async def init_document_checklist(
    employee_id: int,
    current_user: User = require_permission(_DOC_PERM_MANAGE),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    result = await document_checklist_service.init_employee_checklist(
        session, employee_id, current_user.id
    )
    await session.commit()
    return result


@router.post(
    "/{employee_id}/document-checklist",
    response_model=ChecklistItemRead,
    status_code=201,
    summary="Thêm một loại giấy tờ vào checklist",
)
async def add_checklist_item(
    employee_id: int,
    document_type_id: int,
    current_user: User = require_permission(_DOC_PERM_MANAGE),
    session: AsyncSession = Depends(get_session),
):
    await employee_service._get_or_404(session, employee_id)
    result = await document_checklist_service.add_checklist_item(
        session, employee_id, document_type_id, current_user.id
    )
    await session.commit()
    return result
