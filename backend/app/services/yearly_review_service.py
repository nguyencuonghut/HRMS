"""Service đánh giá cuối năm nhân viên (10.2)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.discipline import EmployeeDiscipline
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.performance import EmployeeKpiMonthly, EmployeeYearlyReview
from app.schemas.performance import (
    MonthlyScore,
    YearlyKpiSummary,
    YearlyReviewCreate,
    YearlyReviewListPage,
    YearlyReviewRead,
    YearlyReviewUpdate,
)
from app.services import employee_code_service
from app.utils.employee_code_sql import sql_padded_employee_seq_expr

log = logging.getLogger(__name__)

# ── Rating constants ──────────────────────────────────────────────────────────

RATING_LABELS: dict[str, str] = {
    "xuat_sac":      "Xuất sắc",
    "tot":           "Tốt",
    "dat":           "Đạt",
    "can_cai_thien": "Cần cải thiện",
}

VALID_RATINGS = set(RATING_LABELS.keys())


def compute_rating(avg_score: Optional[Decimal], has_discipline: bool = False) -> Optional[str]:
    """Tính xếp loại gợi ý từ điểm trung bình và tình trạng kỷ luật.

    Ngưỡng:
      > 100 → Xuất sắc  (không thể đạt tự động vì max score = 100, chỉ gán tay)
      ≥ 95  → Tốt       (và không có vi phạm kỷ luật trong năm)
      > 85  → Đạt       (và không có vi phạm kỷ luật trong năm)
      còn lại hoặc có vi phạm → Cần cải thiện
    """
    if avg_score is None:
        return None
    if has_discipline:
        return "can_cai_thien"
    if avg_score > Decimal("100"):
        return "xuat_sac"
    if avg_score >= Decimal("95"):
        return "tot"
    if avg_score > Decimal("85"):
        return "dat"
    return "can_cai_thien"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_or_404(session: AsyncSession, review_id: int) -> EmployeeYearlyReview:
    review = await session.get(EmployeeYearlyReview, review_id)
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi đánh giá")
    return review


async def _get_emp_code(session: AsyncSession, emp: Employee) -> str:
    return await employee_code_service.build_employee_display_code(session, emp)


async def _get_dept_name(session: AsyncSession, emp_id: int) -> Optional[str]:
    jr = (
        await session.execute(
            select(EmployeeJobRecord)
            .where(
                EmployeeJobRecord.employee_id == emp_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if jr and jr.department_id:
        dept = await session.get(Department, jr.department_id)
        return dept.name if dept else None
    return None


async def _has_discipline_in_year(session: AsyncSession, employee_id: int, year: int) -> bool:
    """Kiểm tra nhân viên có vi phạm kỷ luật nào trong năm (theo violation_date) không."""
    from sqlalchemy import extract
    result = (
        await session.execute(
            select(EmployeeDiscipline.id).where(
                EmployeeDiscipline.employee_id == employee_id,
                extract("year", EmployeeDiscipline.violation_date) == year,
            ).limit(1)
        )
    ).scalar_one_or_none()
    return result is not None


async def _get_avg_and_months(session: AsyncSession, employee_id: int, year: int):
    """Returns (avg_score, months_count, monthly_scores)."""
    rows = (
        await session.execute(
            select(EmployeeKpiMonthly.month, EmployeeKpiMonthly.score)
            .where(
                EmployeeKpiMonthly.employee_id == employee_id,
                EmployeeKpiMonthly.year == year,
            )
            .order_by(EmployeeKpiMonthly.month)
        )
    ).all()

    if not rows:
        return None, 0, []

    monthly_scores = [MonthlyScore(month=r.month, score=r.score) for r in rows]
    total = sum(r.score for r in rows)
    avg_score = total / len(rows)
    return avg_score, len(rows), monthly_scores


async def _build_review_read(session: AsyncSession, review: EmployeeYearlyReview) -> YearlyReviewRead:
    emp = await session.get(Employee, review.employee_id)
    creator: Optional[User] = await session.get(User, review.created_by_id) if review.created_by_id else None

    emp_code = ""
    dept_name: Optional[str] = None
    if emp:
        emp_code = await _get_emp_code(session, emp)
        dept_name = await _get_dept_name(session, emp.id)

    avg_score, months_count, _ = await _get_avg_and_months(session, review.employee_id, review.year)

    return YearlyReviewRead(
        id=review.id,
        employee_id=review.employee_id,
        employee_code=emp_code,
        employee_name=emp.full_name if emp else "",
        department_name=dept_name,
        year=review.year,
        months_count=months_count,
        avg_score=avg_score,
        rating=review.rating,
        rating_label=RATING_LABELS.get(review.rating, review.rating),
        review_note=review.review_note,
        created_by_name=getattr(creator, "full_name", None) or (creator.email if creator else None),
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def get_yearly_kpi_summary(
    session: AsyncSession,
    employee_id: int,
    year: int,
) -> YearlyKpiSummary:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    emp_code = await _get_emp_code(session, emp)
    dept_name = await _get_dept_name(session, emp.id)

    avg_score, months_count, monthly_scores = await _get_avg_and_months(session, employee_id, year)
    has_discipline = await _has_discipline_in_year(session, employee_id, year)
    suggested_rating = compute_rating(avg_score, has_discipline)

    existing = (
        await session.execute(
            select(EmployeeYearlyReview.id).where(
                EmployeeYearlyReview.employee_id == employee_id,
                EmployeeYearlyReview.year == year,
            )
        )
    ).scalar_one_or_none()

    return YearlyKpiSummary(
        employee_id=employee_id,
        employee_code=emp_code,
        employee_name=emp.full_name,
        department_name=dept_name,
        year=year,
        monthly_scores=monthly_scores,
        months_count=months_count,
        avg_score=avg_score,
        has_discipline=has_discipline,
        suggested_rating=suggested_rating,
        has_review=existing is not None,
        review_id=existing,
    )


async def get_yearly_review(session: AsyncSession, review_id: int) -> YearlyReviewRead:
    review = await _get_or_404(session, review_id)
    return await _build_review_read(session, review)


async def get_yearly_reviews(
    session: AsyncSession,
    *,
    year: Optional[int] = None,
    department_id: Optional[int] = None,
    rating: Optional[str] = None,
    search: Optional[str] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
    page: int = 1,
    page_size: int = 20,
) -> YearlyReviewListPage:
    stmt = (
        select(EmployeeYearlyReview)
        .join(Employee, Employee.id == EmployeeYearlyReview.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
    )

    if year is not None:
        stmt = stmt.where(EmployeeYearlyReview.year == year)
    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)
    if rating is not None:
        stmt = stmt.where(EmployeeYearlyReview.rating == rating)
    if allowed_department_ids is not None:
        if not allowed_department_ids:
            stmt = stmt.where(false())
        else:
            stmt = stmt.where(EmployeeJobRecord.department_id.in_(allowed_department_ids))

    if search:
        from app.services.administrative_import_service import normalize_text
        kw = f"%{search.strip()}%"
        norm_kw = f"%{normalize_text(search.strip())}%"
        dept_prefix = func.coalesce(
            func.nullif(func.btrim(Department.display_prefix), ""),
            Department.code,
        )
        generated_code = dept_prefix + sql_padded_employee_seq_expr(
            Employee.employee_seq,
            min_digits=4,
        )
        stmt = stmt.where(
            or_(
                Employee.full_name.ilike(kw),
                Employee.normalized_name.ilike(norm_kw),
                generated_code.ilike(kw),
            )
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(
        EmployeeYearlyReview.year.desc(),
        EmployeeYearlyReview.id.desc(),
    )
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    items: List[YearlyReviewRead] = []
    for row in rows:
        items.append(await _build_review_read(session, row))

    return YearlyReviewListPage(items=items, total=total, page=page, page_size=page_size)


async def create_review(
    session: AsyncSession,
    data: YearlyReviewCreate,
    created_by_id: int,
) -> YearlyReviewRead:
    if data.rating not in VALID_RATINGS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Xếp loại không hợp lệ: {data.rating}",
        )

    emp = await session.get(Employee, data.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    existing = (
        await session.execute(
            select(EmployeeYearlyReview).where(
                EmployeeYearlyReview.employee_id == data.employee_id,
                EmployeeYearlyReview.year == data.year,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Đã tồn tại đánh giá cuối năm {data.year} của nhân viên này",
        )

    review = EmployeeYearlyReview(
        employee_id=data.employee_id,
        year=data.year,
        rating=data.rating,
        review_note=data.review_note,
        created_by_id=created_by_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(review)
    await session.flush()
    return await _build_review_read(session, review)


async def update_review(
    session: AsyncSession,
    review_id: int,
    data: YearlyReviewUpdate,
) -> YearlyReviewRead:
    review = await _get_or_404(session, review_id)

    if data.rating is not None:
        if data.rating not in VALID_RATINGS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Xếp loại không hợp lệ: {data.rating}",
            )
        review.rating = data.rating
    if data.review_note is not None:
        review.review_note = data.review_note

    review.updated_at = _utcnow()
    session.add(review)
    await session.flush()
    return await _build_review_read(session, review)


async def delete_review(session: AsyncSession, review_id: int) -> None:
    review = await _get_or_404(session, review_id)
    await session.delete(review)
