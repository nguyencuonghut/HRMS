"""Quản lý nhân viên — CRUD hồ sơ cá nhân (3.1) + thông tin công việc (3.2)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
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
)
from app.services import auth_service, employee_job_service, employee_service

router = APIRouter()


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
    limit: int = Query(20, ge=1, le=100),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    items = await employee_service.lookup_employees(session, keyword=keyword, limit=limit)
    return [
        EmployeeLookupItem(
            id=e.id,
            employee_seq=e.employee_seq,
            display_code=employee_service.compute_display_code(e.employee_seq),
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
    emp_ids = [emp.id for emp in result["items"]]
    prefixes = await employee_job_service.batch_get_display_code_prefixes(session, emp_ids)
    items = [
        EmployeeListItem(**_build_list_item_data(
            emp,
            employee_service.compute_display_code(emp.employee_seq, prefixes.get(emp.id)),
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
        session, current_user.id, "CREATE",
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
        session, current_user.id, "UPDATE",
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
