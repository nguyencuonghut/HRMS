"""Service liên kết kết quả đánh giá KPI với khen thưởng và đào tạo (10.3)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.employee import Employee
from app.models.performance import EmployeeKpiMonthly, EmployeeYearlyReview
from app.models.reward import EmployeeReward, RewardType
from app.models.training import EmployeeTrainingRecord, TrainingCourse, TrainingPlan, TrainingPlanCourse
from app.schemas.performance import RewardFromReviewRequest, TrainingFromReviewRequest
from app.schemas.performance import KpiMonthlyRead
from app.schemas.performance import YearlyReviewRead
from app.schemas.reward import RewardRead
from app.schemas.training import TrainingRecordRead
from app.services import reward_service as _reward_svc
from app.services import training_record_service as _training_svc
from app.services import yearly_review_service as _review_svc


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_emp_or_404(session: AsyncSession, employee_id: int) -> Employee:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    return emp


# ── Lịch sử KPI / đánh giá của một nhân viên ─────────────────────────────────

async def get_employee_kpi_history(
    session: AsyncSession,
    employee_id: int,
    year: Optional[int] = None,
) -> List[KpiMonthlyRead]:
    await _get_emp_or_404(session, employee_id)

    stmt = select(EmployeeKpiMonthly).where(EmployeeKpiMonthly.employee_id == employee_id)
    if year is not None:
        stmt = stmt.where(EmployeeKpiMonthly.year == year)
    stmt = stmt.order_by(EmployeeKpiMonthly.year.desc(), EmployeeKpiMonthly.month.desc())

    rows = (await session.execute(stmt)).scalars().all()

    # Resolve employee info once
    emp = await session.get(Employee, employee_id)
    from app.services import employee_code_service
    emp_code = await employee_code_service.build_employee_display_code(session, emp) if emp else ""

    dept_name = await _review_svc._get_dept_name(session, employee_id)

    from app.models.auth import User
    result = []
    for row in rows:
        creator = await session.get(User, row.created_by_id) if row.created_by_id else None
        result.append(KpiMonthlyRead(
            id=row.id,
            employee_id=row.employee_id,
            employee_code=emp_code,
            employee_name=emp.full_name if emp else "",
            department_name=dept_name,
            year=row.year,
            month=row.month,
            score=row.score,
            note=row.note,
            created_by_name=getattr(creator, "full_name", None) or (creator.email if creator else None),
            created_at=row.created_at,
            updated_at=row.updated_at,
        ))
    return result


async def get_employee_review_history(
    session: AsyncSession,
    employee_id: int,
) -> List[YearlyReviewRead]:
    await _get_emp_or_404(session, employee_id)

    stmt = (
        select(EmployeeYearlyReview)
        .where(EmployeeYearlyReview.employee_id == employee_id)
        .order_by(EmployeeYearlyReview.year.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()

    result = []
    for row in rows:
        result.append(await _review_svc._build_review_read(session, row))
    return result


# ── Tạo khen thưởng từ đánh giá ──────────────────────────────────────────────

async def create_reward_from_review(
    session: AsyncSession,
    review_id: int,
    data: RewardFromReviewRequest,
    created_by_id: int,
) -> RewardRead:
    review = await session.get(EmployeeYearlyReview, review_id)
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi đánh giá")

    rt = await session.get(RewardType, data.reward_type_id)
    if not rt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy loại khen thưởng")
    if not rt.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Loại khen thưởng không còn hoạt động")
    if rt.is_monetary and data.amount is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Loại khen thưởng tiền mặt phải nhập giá trị",
        )

    emp = await session.get(Employee, review.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    if emp.status == "resigned":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Không thể thêm khen thưởng cho nhân viên đã nghỉ việc",
        )

    from app.services.yearly_review_service import RATING_LABELS
    rating_label = RATING_LABELS.get(review.rating, review.rating)
    title = f"Khen thưởng theo kết quả đánh giá năm {review.year} — {rating_label}"

    reward = EmployeeReward(
        employee_id=review.employee_id,
        reward_type_id=data.reward_type_id,
        title=title,
        reward_date=data.decision_date,
        value=data.amount if rt.is_monetary else None,
        note=data.note,
        source_review_id=review_id,
        created_by_id=created_by_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(reward)
    await session.flush()
    return await _reward_svc._build_reward_read(session, reward)


# ── Tạo đào tạo từ đánh giá ──────────────────────────────────────────────────

async def create_training_from_review(
    session: AsyncSession,
    review_id: int,
    data: TrainingFromReviewRequest,
    created_by_id: int,
) -> TrainingRecordRead:
    review = await session.get(EmployeeYearlyReview, review_id)
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi đánh giá")

    course = await session.get(TrainingCourse, data.course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khóa học")
    if not course.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Khóa học đã ngừng hoạt động")

    if data.plan_id is not None:
        plan = await session.get(TrainingPlan, data.plan_id)
        if not plan:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch đào tạo")
        pc_exists = (
            await session.execute(
                select(TrainingPlanCourse).where(
                    TrainingPlanCourse.plan_id == data.plan_id,
                    TrainingPlanCourse.course_id == data.course_id,
                )
            )
        ).scalar_one_or_none()
        if not pc_exists:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Khóa học không thuộc kế hoạch đào tạo này",
            )

    note = data.note or f"Cải thiện điểm yếu từ đánh giá năm {review.year}"

    record = EmployeeTrainingRecord(
        employee_id=review.employee_id,
        course_id=data.course_id,
        plan_id=data.plan_id,
        status="chua_bat_dau",
        note=note,
        source_review_id=review_id,
        created_by_id=created_by_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(record)
    await session.flush()
    return await _training_svc._build_read(session, record)
