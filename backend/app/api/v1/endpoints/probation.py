"""API endpoints cho Quản lý thử việc (Plan 14.2)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_employee_access, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.employee_contract import ContractRead
from app.schemas.probation import (
    ProbationApproveRequest,
    ProbationDetailRead,
    ProbationEvaluationCreate,
    ProbationEvaluationRead,
    ProbationEvaluationUpdate,
    ProbationLegalCheck,
)
import app.services.probation_service as svc
from app.services import access_scope_service

_TAG = "Quản lý thử việc"

router = APIRouter()


# ── Slice 1 ───────────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/probation/legal-check",
    response_model=ProbationLegalCheck,
    tags=[_TAG],
    summary="Kiểm tra tính hợp lệ pháp lý thử việc",
)
async def legal_check(
    employee_id: int,
    _: User = require_employee_access("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await svc.validate_probation_legal(session, employee_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{employee_id}/probation",
    response_model=ProbationDetailRead,
    tags=[_TAG],
    summary="Xem chi tiết thử việc của nhân viên",
)
async def get_probation_detail(
    employee_id: int,
    _: User = require_employee_access("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await svc.get_probation_detail(session, employee_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Slice 2 ───────────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/probation/contract",
    response_model=List[ContractRead],
    tags=[_TAG],
    summary="Danh sách hợp đồng thử việc",
)
async def get_probation_contracts(
    employee_id: int,
    _: User = require_employee_access("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    return await svc.get_probation_contracts(session, employee_id)


@router.post(
    "/{employee_id}/probation/contract/generate",
    response_model=ContractRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo hợp đồng thử việc từ template",
)
async def generate_probation_contract(
    employee_id: int,
    current_user: User = require_permission("employees:edit"),
    _: set[int] | None = require_department_scope("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=("employees:edit", "employees:view"),
        employee_id=employee_id,
    )
    try:
        contract = await svc.generate_probation_contract(session, employee_id, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy template hợp đồng thử việc (document_kind='probation_agreement') đang active",
        )
    await session.commit()

    # Build read schema
    from app.models.catalog import ContractCategory
    from app.schemas.employee_contract import _status_display, _days_until
    cat = await session.get(ContractCategory, contract.contract_category_id)
    return ContractRead(
        id=contract.id,
        employee_id=contract.employee_id,
        parent_contract_id=contract.parent_contract_id,
        contract_category_id=contract.contract_category_id,
        document_kind=contract.document_kind,
        contract_number=contract.contract_number,
        signed_date=contract.signed_date,
        effective_from=contract.effective_from,
        effective_to=contract.effective_to,
        insurance_salary=contract.insurance_salary,
        status=contract.status,
        status_display=_status_display(contract.status, contract.effective_to),
        days_until_expiry=_days_until(contract.status, contract.effective_to),
        has_file=bool(contract.file_path),
        file_name=contract.file_name,
        file_size=contract.file_size,
        mime_type=contract.mime_type,
        category_name=cat.name if cat else f"Category #{contract.contract_category_id}",
        notes=contract.notes,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


# ── Slice 3 ───────────────────────────────────────────────────────────────────

@router.post(
    "/{employee_id}/probation/evaluate",
    response_model=ProbationEvaluationRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo phiếu đánh giá thử việc",
)
async def create_evaluation(
    employee_id: int,
    data: ProbationEvaluationCreate,
    current_user: User = require_permission("employees:edit"),
    _: set[int] | None = require_department_scope("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=("employees:edit", "employees:view"),
        employee_id=employee_id,
    )
    try:
        result = await svc.create_evaluation(session, employee_id, data, current_user.id)
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch(
    "/{employee_id}/probation/evaluate/{eval_id}",
    response_model=ProbationEvaluationRead,
    tags=[_TAG],
    summary="Cập nhật phiếu đánh giá thử việc",
)
async def update_evaluation(
    employee_id: int,
    eval_id: int,
    data: ProbationEvaluationUpdate,
    current_user: User = require_permission("employees:edit"),
    _: set[int] | None = require_department_scope("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=("employees:edit", "employees:view"),
        employee_id=employee_id,
    )
    try:
        result = await svc.update_evaluation(session, eval_id, data)
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/{employee_id}/probation/submit",
    response_model=ProbationEvaluationRead,
    tags=[_TAG],
    summary="Nộp phiếu đánh giá thử việc",
)
async def submit_evaluation(
    employee_id: int,
    current_user: User = require_permission("employees:edit"),
    _: set[int] | None = require_department_scope("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=("employees:edit", "employees:view"),
        employee_id=employee_id,
    )
    # Find evaluation for this employee
    from sqlmodel import select
    from app.models.probation import ProbationEvaluation
    from app.models.employee_job import EmployeeJobRecord

    job_record = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not job_record:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi công việc hiện tại")

    ev = (
        await session.execute(
            select(ProbationEvaluation).where(
                ProbationEvaluation.employee_id == employee_id,
                ProbationEvaluation.job_record_id == job_record.id,
            )
        )
    ).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu đánh giá")

    try:
        result = await svc.submit_evaluation(session, ev.id, current_user.id)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/{employee_id}/probation/recall",
    response_model=ProbationEvaluationRead,
    tags=[_TAG],
    summary="Rút lại phiếu đánh giá về nháp để chỉnh sửa",
)
async def recall_evaluation(
    employee_id: int,
    current_user: User = require_permission("employees:edit"),
    _: set[int] | None = require_department_scope("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=("employees:edit", "employees:view"),
        employee_id=employee_id,
    )
    from sqlmodel import select
    from app.models.probation import ProbationEvaluation
    from app.models.employee_job import EmployeeJobRecord

    job_record = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not job_record:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi công việc hiện tại")

    ev = (
        await session.execute(
            select(ProbationEvaluation).where(
                ProbationEvaluation.employee_id == employee_id,
                ProbationEvaluation.job_record_id == job_record.id,
            )
        )
    ).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu đánh giá")

    try:
        result = await svc.recall_evaluation(session, ev.id)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Slice 4 ───────────────────────────────────────────────────────────────────

@router.post(
    "/{employee_id}/probation/approve",
    response_model=ProbationEvaluationRead,
    tags=[_TAG],
    summary="Phê duyệt phiếu đánh giá thử việc",
)
async def approve_evaluation(
    employee_id: int,
    data: ProbationApproveRequest,
    current_user: User = require_permission("employees:edit"),
    _: set[int] | None = require_department_scope("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    await access_scope_service.ensure_employee_access(
        session,
        current_user,
        permission_codes=("employees:edit", "employees:view"),
        employee_id=employee_id,
    )
    # Find submitted evaluation for this employee
    from sqlmodel import select
    from app.models.probation import ProbationEvaluation
    from app.models.employee_job import EmployeeJobRecord

    job_record = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not job_record:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi công việc hiện tại")

    ev = (
        await session.execute(
            select(ProbationEvaluation).where(
                ProbationEvaluation.employee_id == employee_id,
                ProbationEvaluation.job_record_id == job_record.id,
            )
        )
    ).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu đánh giá")

    try:
        result = await svc.approve_evaluation(session, ev.id, data, current_user.id)
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
