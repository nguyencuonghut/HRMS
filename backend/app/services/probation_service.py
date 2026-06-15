"""Service layer cho Quản lý thử việc (Plan 14.2)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.auth import AuditLog, User
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobTitle
from app.models.probation import ProbationEvaluation
from app.schemas.probation import (
    ProbationApproveRequest,
    ProbationDetailRead,
    ProbationEvaluationCreate,
    ProbationEvaluationRead,
    ProbationEvaluationUpdate,
    ProbationLegalCheck,
)
from app.services.offer_service import (
    PROBATION_LIMITS,
    _LEVEL_TO_GROUP,
    _probation_limit_for_level,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _job_record_has_probation_data(job_record: EmployeeJobRecord | None) -> bool:
    if not job_record:
        return False
    return any(
        value is not None
        for value in (
            job_record.probation_start_date,
            job_record.probation_end_date,
            job_record.official_date,
        )
    )


def _resolve_probation_mode(
    employee_status: str,
    job_record: EmployeeJobRecord | None,
) -> str:
    if employee_status == "probation":
        return "active"
    if _job_record_has_probation_data(job_record):
        return "historical"
    return "none"


# ── Helper: build read schema ─────────────────────────────────────────────────

async def _build_eval_read(session: AsyncSession, ev: ProbationEvaluation) -> ProbationEvaluationRead:
    emp = await session.get(Employee, ev.employee_id)
    evaluator = await session.get(User, ev.evaluator_id)
    approved_by = await session.get(User, ev.approved_by_id) if ev.approved_by_id else None
    return ProbationEvaluationRead(
        id=ev.id,
        employee_id=ev.employee_id,
        employee_name=emp.full_name if emp else None,
        job_record_id=ev.job_record_id,
        evaluation_date=ev.evaluation_date,
        evaluator_id=ev.evaluator_id,
        evaluator_name=evaluator.full_name if evaluator else None,
        hr_reviewer_id=ev.hr_reviewer_id,
        attitude_score=ev.attitude_score,
        competence_score=ev.competence_score,
        culture_score=ev.culture_score,
        kpi_score=ev.kpi_score,
        overall_score=ev.overall_score,
        manager_comment=ev.manager_comment,
        hr_comment=ev.hr_comment,
        result=ev.result,
        extension_days=ev.extension_days,
        status=ev.status,
        approved_by_id=ev.approved_by_id,
        approved_by_name=approved_by.full_name if approved_by else None,
        approved_at=ev.approved_at,
        created_at=ev.created_at,
        updated_at=ev.updated_at,
    )


def _compute_overall_score(
    attitude: Optional[Decimal],
    competence: Optional[Decimal],
    culture: Optional[Decimal],
    kpi: Optional[Decimal],
) -> Optional[Decimal]:
    scores = [s for s in [attitude, competence, culture, kpi] if s is not None]
    if not scores:
        return None
    return sum(scores) / Decimal(len(scores))


# ── Slice 1: Legal check ──────────────────────────────────────────────────────

async def validate_probation_legal(
    session: AsyncSession,
    employee_id: int,
    job_record_id: Optional[int] = None,
) -> ProbationLegalCheck:
    """Kiểm tra tính hợp lệ pháp lý của thời gian thử việc."""
    violations: List[str] = []
    warnings: List[str] = []
    employee = await session.get(Employee, employee_id)

    # Lấy job record
    if job_record_id:
        job_record = (
            await session.execute(
                select(EmployeeJobRecord).where(
                    EmployeeJobRecord.id == job_record_id,
                    EmployeeJobRecord.employee_id == employee_id,
                )
            )
        ).scalar_one_or_none()
    else:
        job_record = (
            await session.execute(
                select(EmployeeJobRecord).where(
                    EmployeeJobRecord.employee_id == employee_id,
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                )
            )
        ).scalar_one_or_none()

    probation_days = 0
    probation_limit = 30
    job_level: Optional[int] = None
    job_level_group = "worker"

    if job_record:
        # Tính số ngày thử việc
        if job_record.probation_start_date and job_record.probation_end_date:
            delta = job_record.probation_end_date - job_record.probation_start_date
            probation_days = delta.days

        # Lấy job_title.level để tính giới hạn
        if job_record.job_title_id:
            jt = await session.get(JobTitle, job_record.job_title_id)
            if jt:
                job_level = getattr(jt, "level", None)

        job_level_group = _LEVEL_TO_GROUP.get(job_level or 99, "worker")
        probation_limit = _probation_limit_for_level(job_level)

        # Kiểm tra vi phạm: thời gian thử việc vượt giới hạn pháp lý
        if probation_days > probation_limit:
            probation_mode = _resolve_probation_mode(
                employee.status if employee else "none",
                job_record,
            )
            message = (
                f"Thời gian thử việc {probation_days} ngày vượt quá giới hạn pháp lý "
                f"{probation_limit} ngày cho nhóm '{job_level_group}'"
            )
            if probation_mode == "historical":
                warnings.append(
                    f"Dữ liệu thử việc lịch sử: {message}. Hệ thống chỉ cảnh báo để đối soát hồ sơ."
                )
            else:
                violations.append(message)

        # Kiểm tra lương thử việc (WARNING)
        from app.models.recruitment import HiringDecision
        hiring = (
            await session.execute(
                select(HiringDecision).where(
                    HiringDecision.employee_id == employee_id
                )
            )
        ).scalar_one_or_none()
        if hiring and hiring.official_salary and hiring.official_salary > 0:
            threshold = hiring.official_salary * Decimal("0.85")
            if hiring.probation_salary < threshold:
                warnings.append(
                    f"Lương thử việc ({hiring.probation_salary:,.0f}) "
                    f"thấp hơn 85% lương chính thức ({hiring.official_salary:,.0f})"
                )

    return ProbationLegalCheck(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
        probation_days=probation_days,
        probation_limit=probation_limit,
        job_level=job_level,
        job_level_group=job_level_group,
    )


async def get_probation_detail(
    session: AsyncSession,
    employee_id: int,
) -> ProbationDetailRead:
    """Lấy chi tiết thử việc của nhân viên."""
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise LookupError(f"Không tìm thấy nhân viên #{employee_id}")

    # Lấy employee code
    from app.services import employee_code_service
    employee_code = await employee_code_service.build_employee_display_code(session, emp)

    # Lấy job record hiện tại
    job_record = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()

    department_name: Optional[str] = None
    job_title_name: Optional[str] = None
    job_title_level: Optional[int] = None
    days_remaining: Optional[int] = None

    if job_record:
        if job_record.department_id:
            dept = await session.get(Department, job_record.department_id)
            department_name = dept.name if dept else None

        if job_record.job_title_id:
            jt = await session.get(JobTitle, job_record.job_title_id)
            if jt:
                job_title_name = jt.name
                job_title_level = getattr(jt, "level", None)

        if job_record.probation_end_date:
            today = _today()
            days_remaining = (job_record.probation_end_date - today).days

    probation_mode = _resolve_probation_mode(emp.status, job_record)
    can_edit_evaluation = probation_mode in {"active", "historical"}
    can_generate_contract = probation_mode == "active"
    approval_triggers_workflow = probation_mode == "active"

    # Legal check
    legal_check = await validate_probation_legal(session, employee_id)

    # Evaluation hiện tại
    evaluation: Optional[ProbationEvaluationRead] = None
    if job_record:
        ev = (
            await session.execute(
                select(ProbationEvaluation).where(
                    ProbationEvaluation.employee_id == employee_id,
                    ProbationEvaluation.job_record_id == job_record.id,
                )
            )
        ).scalar_one_or_none()
        if ev:
            evaluation = await _build_eval_read(session, ev)

    # Hợp đồng thử việc
    from app.models.employee_contract import EmployeeContract
    contracts_raw = (
        await session.execute(
            select(EmployeeContract).where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.document_kind == "probation_agreement",
            ).order_by(EmployeeContract.created_at.desc())
        )
    ).scalars().all()

    from app.schemas.employee_contract import ContractRead
    contracts = []
    for c in contracts_raw:
        from app.models.catalog import ContractCategory
        cat = await session.get(ContractCategory, c.contract_category_id)
        from app.schemas.employee_contract import _status_display, _days_until
        contracts.append(ContractRead(
            id=c.id,
            employee_id=c.employee_id,
            parent_contract_id=c.parent_contract_id,
            contract_category_id=c.contract_category_id,
            document_kind=c.document_kind,
            contract_number=c.contract_number,
            signed_date=c.signed_date,
            effective_from=c.effective_from,
            effective_to=c.effective_to,
            insurance_salary=c.insurance_salary,
            status=c.status,
            status_display=_status_display(c.status, c.effective_to),
            days_until_expiry=_days_until(c.status, c.effective_to),
            has_file=bool(c.file_path),
            file_name=c.file_name,
            file_size=c.file_size,
            mime_type=c.mime_type,
            category_name=cat.name if cat else f"Category #{c.contract_category_id}",
            notes=c.notes,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))

    return ProbationDetailRead(
        employee_id=emp.id,
        employee_name=emp.full_name,
        employee_code=employee_code,
        department_name=department_name,
        job_title_name=job_title_name,
        job_title_level=job_title_level,
        status=emp.status,
        probation_mode=probation_mode,
        can_edit_evaluation=can_edit_evaluation,
        can_generate_contract=can_generate_contract,
        approval_triggers_workflow=approval_triggers_workflow,
        probation_start_date=job_record.probation_start_date if job_record else None,
        probation_end_date=job_record.probation_end_date if job_record else None,
        official_date=job_record.official_date if job_record else None,
        days_remaining=days_remaining,
        legal_check=legal_check,
        evaluation=evaluation,
        contracts=contracts,
    )


# ── Slice 2: Probation Contract ───────────────────────────────────────────────

async def generate_probation_contract(
    session: AsyncSession,
    employee_id: int,
    created_by_id: int,
) -> Optional[object]:
    """Tạo hợp đồng thử việc từ template nếu có."""
    from app.models.catalog import ContractCategory, ContractTemplate
    from app.models.employee_contract import EmployeeContract

    emp = await session.get(Employee, employee_id)
    if not emp:
        raise LookupError(f"Không tìm thấy nhân viên #{employee_id}")

    job_record = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if _resolve_probation_mode(emp.status, job_record) != "active":
        raise ValueError("Chỉ có thể tạo hợp đồng thử việc cho nhân viên đang ở probation mode active")

    # Lấy template probation_agreement mới nhất còn active
    template = (
        await session.execute(
            select(ContractTemplate)
            .where(
                ContractTemplate.document_kind == "probation_agreement",
                ContractTemplate.is_active == True,  # noqa: E712
            )
            .order_by(ContractTemplate.id.desc())
        )
    ).scalars().first()

    if not template:
        logger.warning(
            "Không tìm thấy ContractTemplate document_kind='probation_agreement' đang active "
            "cho nhân viên %s",
            employee_id,
        )
        return None

    today = _today()
    effective_from = job_record.probation_start_date if job_record and job_record.probation_start_date else today
    effective_to = job_record.probation_end_date if job_record and job_record.probation_end_date else None

    import time as _time
    contract_number = f"HDTV-{employee_id}-{int(_time.time())}"

    contract = EmployeeContract(
        employee_id=employee_id,
        contract_category_id=template.contract_category_id,
        document_kind="probation_agreement",
        contract_number=contract_number,
        signed_date=today,
        effective_from=effective_from,
        effective_to=effective_to,
        status="draft",
        created_by=created_by_id,
    )
    session.add(contract)
    await session.flush()
    await session.refresh(contract)
    return contract


async def get_probation_contracts(
    session: AsyncSession,
    employee_id: int,
) -> list:
    from app.models.employee_contract import EmployeeContract
    from app.models.catalog import ContractCategory
    from app.schemas.employee_contract import ContractRead, _status_display, _days_until

    rows = (
        await session.execute(
            select(EmployeeContract).where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.document_kind == "probation_agreement",
            ).order_by(EmployeeContract.created_at.desc())
        )
    ).scalars().all()

    result = []
    for c in rows:
        cat = await session.get(ContractCategory, c.contract_category_id)
        result.append(ContractRead(
            id=c.id,
            employee_id=c.employee_id,
            parent_contract_id=c.parent_contract_id,
            contract_category_id=c.contract_category_id,
            document_kind=c.document_kind,
            contract_number=c.contract_number,
            signed_date=c.signed_date,
            effective_from=c.effective_from,
            effective_to=c.effective_to,
            insurance_salary=c.insurance_salary,
            status=c.status,
            status_display=_status_display(c.status, c.effective_to),
            days_until_expiry=_days_until(c.status, c.effective_to),
            has_file=bool(c.file_path),
            file_name=c.file_name,
            file_size=c.file_size,
            mime_type=c.mime_type,
            category_name=cat.name if cat else f"Category #{c.contract_category_id}",
            notes=c.notes,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return result


# ── Slice 3: Evaluation CRUD ──────────────────────────────────────────────────

async def create_evaluation(
    session: AsyncSession,
    employee_id: int,
    data: ProbationEvaluationCreate,
    created_by_id: int,
) -> ProbationEvaluationRead:
    """Tạo phiếu đánh giá thử việc mới."""
    # 1. Kiểm tra nhân viên tồn tại và có dữ liệu thử việc khả dụng
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise LookupError(f"Không tìm thấy nhân viên #{employee_id}")

    # 2. Lấy job_record hiện tại
    job_record = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not job_record:
        raise LookupError("Không tìm thấy bản ghi công việc hiện tại")

    probation_mode = _resolve_probation_mode(emp.status, job_record)
    if probation_mode == "none":
        raise ValueError(
            "Nhân viên không có dữ liệu thử việc trên bản ghi công việc hiện tại"
        )

    # 3. Kiểm tra unique (employee_id, job_record_id)
    existing = (
        await session.execute(
            select(ProbationEvaluation).where(
                ProbationEvaluation.employee_id == employee_id,
                ProbationEvaluation.job_record_id == job_record.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Đã tồn tại phiếu đánh giá cho lần thử việc này")

    # 4. Tính overall_score
    overall = _compute_overall_score(
        data.attitude_score,
        data.competence_score,
        data.culture_score,
        data.kpi_score,
    )

    # 5. Tạo evaluation
    ev = ProbationEvaluation(
        employee_id=employee_id,
        job_record_id=job_record.id,
        evaluation_date=data.evaluation_date,
        evaluator_id=data.evaluator_id,
        attitude_score=data.attitude_score,
        competence_score=data.competence_score,
        culture_score=data.culture_score,
        kpi_score=data.kpi_score,
        overall_score=overall,
        result=data.result,
        extension_days=data.extension_days,
        manager_comment=data.manager_comment,
        status="draft",
    )
    session.add(ev)
    await session.flush()
    await session.refresh(ev)
    return await _build_eval_read(session, ev)


async def get_evaluation(session: AsyncSession, eval_id: int) -> ProbationEvaluation:
    ev = await session.get(ProbationEvaluation, eval_id)
    if not ev:
        raise LookupError(f"Không tìm thấy phiếu đánh giá #{eval_id}")
    return ev


async def update_evaluation(
    session: AsyncSession,
    eval_id: int,
    data: ProbationEvaluationUpdate,
) -> ProbationEvaluationRead:
    ev = await get_evaluation(session, eval_id)
    if ev.status != "draft":
        raise ValueError("Chỉ có thể cập nhật phiếu đánh giá ở trạng thái draft")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ev, field, value)

    # Recompute overall
    ev.overall_score = _compute_overall_score(
        ev.attitude_score, ev.competence_score, ev.culture_score, ev.kpi_score
    )
    ev.updated_at = _utcnow()
    session.add(ev)
    await session.flush()
    await session.refresh(ev)
    return await _build_eval_read(session, ev)


async def submit_evaluation(
    session: AsyncSession,
    eval_id: int,
    user_id: int,
) -> ProbationEvaluationRead:
    ev = await get_evaluation(session, eval_id)
    if ev.status != "draft":
        raise ValueError("Chỉ có thể nộp phiếu đánh giá ở trạng thái draft")

    # Validate: ít nhất 2 điểm số hoặc có manager_comment
    scores = [s for s in [ev.attitude_score, ev.competence_score, ev.culture_score, ev.kpi_score]
              if s is not None]
    if len(scores) < 2 and not ev.manager_comment:
        raise ValueError(
            "Phiếu đánh giá cần có ít nhất 2 điểm số hoặc nhận xét của quản lý"
        )

    ev.status = "submitted"
    ev.updated_at = _utcnow()
    session.add(ev)
    await session.flush()
    await session.refresh(ev)
    return await _build_eval_read(session, ev)


async def recall_evaluation(
    session: AsyncSession,
    eval_id: int,
) -> ProbationEvaluationRead:
    """Rút lại phiếu đánh giá từ trạng thái submitted → draft để chỉnh sửa."""
    ev = await get_evaluation(session, eval_id)
    if ev.status != "submitted":
        raise ValueError(
            f"Chỉ có thể rút lại phiếu đánh giá ở trạng thái 'submitted' (hiện tại: '{ev.status}')"
        )
    ev.status = "draft"
    ev.updated_at = _utcnow()
    session.add(ev)
    await session.flush()
    await session.refresh(ev)
    return await _build_eval_read(session, ev)


# ── Slice 4: Approve + Workflow ───────────────────────────────────────────────

async def approve_evaluation(
    session: AsyncSession,
    eval_id: int,
    data: ProbationApproveRequest,
    user_id: int,
) -> ProbationEvaluationRead:
    """Phê duyệt phiếu đánh giá và kích hoạt workflow tương ứng."""
    # SELECT FOR UPDATE
    ev = (
        await session.execute(
            select(ProbationEvaluation)
            .where(ProbationEvaluation.id == eval_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not ev:
        raise LookupError(f"Không tìm thấy phiếu đánh giá #{eval_id}")

    if ev.status != "submitted":
        raise ValueError(
            f"Chỉ có thể phê duyệt phiếu đánh giá ở trạng thái 'submitted' (hiện tại: '{ev.status}')"
        )

    # Kết quả không được là 'pending'
    if data.result == "pending":
        raise ValueError("Kết quả phê duyệt không được là 'pending'")

    # Nếu extended: cần extension_days > 0
    if data.result == "extended":
        ext_days = data.extension_days or ev.extension_days
        if not ext_days or ext_days <= 0:
            raise ValueError("Khi gia hạn thử việc, cần chỉ định số ngày gia hạn (extension_days > 0)")

    # Cập nhật evaluation
    ev.result = data.result
    ev.hr_comment = data.hr_comment or ev.hr_comment
    if data.extension_days:
        ev.extension_days = data.extension_days
    ev.status = "approved"
    ev.approved_by_id = user_id
    ev.approved_at = _utcnow()
    ev.updated_at = _utcnow()
    session.add(ev)
    await session.flush()

    # Kích hoạt workflow
    emp = await session.get(Employee, ev.employee_id)
    job_record = await session.get(EmployeeJobRecord, ev.job_record_id)
    probation_mode = _resolve_probation_mode(emp.status, job_record) if emp else "none"

    if probation_mode == "active":
        if data.result == "passed":
            await _execute_passed_workflow(session, ev, user_id)
        elif data.result == "failed":
            await _execute_failed_workflow(session, ev, user_id)
        elif data.result == "extended":
            await _execute_extended_workflow(session, ev, user_id)
    else:
        session.add(
            AuditLog(
                user_id=user_id,
                action="probation_evaluation_approved_historical",
                entity_type="employee",
                entity_id=ev.employee_id,
                entity_name=emp.full_name if emp else None,
                old_data={"status": emp.status if emp else None, "probation_mode": probation_mode},
                new_data={"evaluation_status": "approved", "result": data.result},
            )
        )

    await session.refresh(ev)
    return await _build_eval_read(session, ev)


async def _execute_passed_workflow(
    session: AsyncSession,
    ev: ProbationEvaluation,
    user_id: int,
) -> None:
    """Workflow khi nhân viên vượt qua thử việc: chuyển sang chính thức."""
    emp = await session.get(Employee, ev.employee_id)
    if not emp:
        return

    old_status = emp.status
    emp.status = "official"
    session.add(emp)

    # Cập nhật official_date trên job_record
    job_record = await session.get(EmployeeJobRecord, ev.job_record_id)
    if job_record:
        job_record.official_date = ev.evaluation_date
        job_record.updated_at = _utcnow()
        session.add(job_record)

    # Tạo hợp đồng lao động chính thức (no-fail)
    try:
        from app.models.catalog import ContractTemplate
        labor_template = (
            await session.execute(
                select(ContractTemplate)
                .where(
                    ContractTemplate.document_kind == "labor_contract",
                    ContractTemplate.is_active == True,  # noqa: E712
                )
                .order_by(ContractTemplate.id.desc())
            )
        ).scalars().first()
        if labor_template:
            from app.models.employee_contract import EmployeeContract
            import time as _time
            contract = EmployeeContract(
                employee_id=emp.id,
                contract_category_id=labor_template.contract_category_id,
                document_kind="labor_contract",
                contract_number=f"HDLD-{emp.id}-{int(_time.time())}",
                signed_date=ev.evaluation_date,
                effective_from=ev.evaluation_date,
                status="draft",
                created_by=user_id,
            )
            session.add(contract)
    except Exception as e:
        logger.warning("generate_labor_contract failed for emp %s: %s", emp.id, e)

    # AuditLog
    session.add(AuditLog(
        user_id=user_id,
        action="probation_passed",
        entity_type="employee",
        entity_id=emp.id,
        entity_name=emp.full_name,
        old_data={"status": old_status},
        new_data={"status": "official", "official_date": str(ev.evaluation_date)},
    ))
    await session.flush()


async def _execute_failed_workflow(
    session: AsyncSession,
    ev: ProbationEvaluation,
    user_id: int,
) -> None:
    """Workflow khi nhân viên không vượt qua thử việc: chuyển sang nghỉ việc."""
    emp = await session.get(Employee, ev.employee_id)
    if not emp:
        return

    old_status = emp.status
    emp.status = "resigned"
    # Gán resigned_date nếu có field (kiểm tra gracefully)
    if hasattr(emp, "resigned_date"):
        emp.resigned_date = ev.evaluation_date
    session.add(emp)

    session.add(AuditLog(
        user_id=user_id,
        action="probation_failed",
        entity_type="employee",
        entity_id=emp.id,
        entity_name=emp.full_name,
        old_data={"status": old_status},
        new_data={"status": "resigned", "resigned_date": str(ev.evaluation_date)},
    ))
    await session.flush()


async def _execute_extended_workflow(
    session: AsyncSession,
    ev: ProbationEvaluation,
    user_id: int,
) -> None:
    """Workflow khi gia hạn thử việc: cập nhật probation_end_date."""
    job_record = await session.get(EmployeeJobRecord, ev.job_record_id)
    if not job_record:
        return

    from datetime import timedelta
    extension = ev.extension_days or 0
    new_end = job_record.probation_end_date + timedelta(days=extension)

    # Validate: tổng ngày thử việc không vượt giới hạn pháp lý
    if job_record.probation_start_date:
        total_days = (new_end - job_record.probation_start_date).days
        jt = await session.get(JobTitle, job_record.job_title_id) if job_record.job_title_id else None
        level = getattr(jt, "level", None) if jt else None
        limit = _probation_limit_for_level(level)
        if total_days > limit:
            raise ValueError(
                f"Sau gia hạn, tổng thời gian thử việc ({total_days} ngày) "
                f"vượt quá giới hạn pháp lý ({limit} ngày)"
            )

    old_end = job_record.probation_end_date
    job_record.probation_end_date = new_end
    job_record.updated_at = _utcnow()
    session.add(job_record)

    emp = await session.get(Employee, ev.employee_id)
    session.add(AuditLog(
        user_id=user_id,
        action="probation_extended",
        entity_type="employee",
        entity_id=ev.employee_id,
        entity_name=emp.full_name if emp else f"Employee #{ev.employee_id}",
        old_data={"probation_end_date": str(old_end)},
        new_data={
            "probation_end_date": str(new_end),
            "extension_days": extension,
        },
    ))
    await session.flush()
