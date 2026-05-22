from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.insurance import (
    InsuranceChangeEvent,
    InsurancePeriodReport,
    InsuranceReportLineItem,
)
from app.schemas.insurance_report import (
    ApproveBody,
    InsurancePeriodReportCreate,
    InsurancePeriodReportUpdate,
    InsuranceReportLineItemCreate,
    InsuranceReportLineItemUpdate,
    RejectBody,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_report_dict(
    report: InsurancePeriodReport,
    total: int,
    adjusted: int,
    missing: int,
) -> dict:
    return {
        "id": report.id,
        "period_year": report.period_year,
        "period_month": report.period_month,
        "submission_type": report.submission_type,
        "status": report.status,
        "prepared_by_id": report.prepared_by_id,
        "prepared_at": report.prepared_at,
        "reviewed_by_id": report.reviewed_by_id,
        "reviewed_at": report.reviewed_at,
        "review_note": report.review_note,
        "note": report.note,
        "line_item_count": total,
        "adjusted_count": adjusted,
        "missing_clinic_code_count": missing,
        "created_at": report.created_at,
    }


def _to_line_item_dict(
    item: InsuranceReportLineItem,
    event: InsuranceChangeEvent,
    employee_code: str,
) -> dict:
    return {
        "id": item.id,
        "report_id": item.report_id,
        "event_id": item.event_id,
        "employee_name": event.employee_name_snapshot,
        "employee_code": employee_code,
        "bhxh_code": event.bhxh_code_snapshot,
        "change_type": event.change_type,
        "change_reason": event.change_reason,
        "effective_date": event.effective_date,
        "basis_amount": event.basis_amount,
        "bhyt_clinic_code": event.bhyt_clinic_code_snapshot,
        "suggested_year": item.suggested_year,
        "suggested_month": item.suggested_month,
        "declared_year": item.declared_year,
        "declared_month": item.declared_month,
        "is_adjusted": item.is_adjusted,
        "adjustment_note": item.adjustment_note,
        "sort_order": item.sort_order,
    }


async def _single_counts(session: AsyncSession, report_id: int) -> tuple[int, int, int]:
    """Returns (line_item_count, adjusted_count, missing_clinic_code_count)."""
    row = (
        await session.execute(
            select(
                func.count(InsuranceReportLineItem.id).label("total"),
                func.count(InsuranceReportLineItem.id)
                .filter(InsuranceReportLineItem.is_adjusted.is_(True))
                .label("adjusted"),
                func.count(InsuranceReportLineItem.id)
                .filter(
                    InsuranceChangeEvent.change_type == "increase",
                    InsuranceChangeEvent.bhyt_clinic_code_snapshot.is_(None),
                )
                .label("missing"),
            )
            .outerjoin(
                InsuranceChangeEvent,
                InsuranceChangeEvent.id == InsuranceReportLineItem.event_id,
            )
            .where(InsuranceReportLineItem.report_id == report_id)
        )
    ).one()
    return row.total, row.adjusted, row.missing


async def _batch_counts(
    session: AsyncSession,
    report_ids: list[int],
) -> dict[int, tuple[int, int, int]]:
    """Bulk-load counts for a list of report IDs — avoids N+1 in list views."""
    if not report_ids:
        return {}
    rows = (
        await session.execute(
            select(
                InsuranceReportLineItem.report_id,
                func.count(InsuranceReportLineItem.id).label("total"),
                func.count(InsuranceReportLineItem.id)
                .filter(InsuranceReportLineItem.is_adjusted.is_(True))
                .label("adjusted"),
                func.count(InsuranceReportLineItem.id)
                .filter(
                    InsuranceChangeEvent.change_type == "increase",
                    InsuranceChangeEvent.bhyt_clinic_code_snapshot.is_(None),
                )
                .label("missing"),
            )
            .outerjoin(
                InsuranceChangeEvent,
                InsuranceChangeEvent.id == InsuranceReportLineItem.event_id,
            )
            .where(InsuranceReportLineItem.report_id.in_(report_ids))
            .group_by(InsuranceReportLineItem.report_id)
        )
    ).all()
    return {row.report_id: (row.total, row.adjusted, row.missing) for row in rows}


async def _get_report_or_404(
    session: AsyncSession, report_id: int
) -> InsurancePeriodReport:
    report = await session.get(InsurancePeriodReport, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo cáo")
    return report


def _require_editable(report: InsurancePeriodReport) -> None:
    if report.status not in ("draft", "rejected"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể chỉnh sửa báo cáo ở trạng thái '{report.status}'",
        )


async def _emp_code_map(session: AsyncSession, employee_ids: set[int]) -> dict[int, str]:
    if not employee_ids:
        return {}
    rows = (
        await session.execute(
            select(Employee.id, Employee.employee_seq).where(
                Employee.id.in_(employee_ids)
            )
        )
    ).all()
    return {row.id: str(row.employee_seq) for row in rows}


# ── Public API ────────────────────────────────────────────────────────────────

async def create_report(
    session: AsyncSession,
    payload: InsurancePeriodReportCreate,
    created_by_id: int,
) -> dict:
    # supplement requires initial to exist
    if payload.submission_type == "supplement":
        initial = (
            await session.execute(
                select(InsurancePeriodReport).where(
                    InsurancePeriodReport.period_year == payload.period_year,
                    InsurancePeriodReport.period_month == payload.period_month,
                    InsurancePeriodReport.submission_type == "initial",
                )
            )
        ).scalar_one_or_none()
        if not initial:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Cần có báo cáo lần đầu (initial) trước khi tạo báo cáo bổ sung"
                ),
            )

    # prevent duplicate
    existing = (
        await session.execute(
            select(InsurancePeriodReport).where(
                InsurancePeriodReport.period_year == payload.period_year,
                InsurancePeriodReport.period_month == payload.period_month,
                InsurancePeriodReport.submission_type == payload.submission_type,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Đã tồn tại báo cáo {payload.submission_type} "
                f"cho kỳ {payload.period_month:02d}/{payload.period_year}"
            ),
        )

    report = InsurancePeriodReport(
        period_year=payload.period_year,
        period_month=payload.period_month,
        submission_type=payload.submission_type,
        status="draft",
        note=payload.note,
        created_by_id=created_by_id,
    )
    session.add(report)
    await session.flush()

    # auto-populate: events with suggested = requested period, not yet in any approved report
    already_approved_subq = select(InsuranceReportLineItem.event_id).join(
        InsurancePeriodReport,
        InsurancePeriodReport.id == InsuranceReportLineItem.report_id,
    ).where(InsurancePeriodReport.status == "approved")

    events = (
        await session.execute(
            select(InsuranceChangeEvent)
            .where(
                InsuranceChangeEvent.suggested_declaration_year == payload.period_year,
                InsuranceChangeEvent.suggested_declaration_month == payload.period_month,
                InsuranceChangeEvent.id.not_in(already_approved_subq),
            )
            .order_by(
                InsuranceChangeEvent.change_type.desc(),
                InsuranceChangeEvent.id.asc(),
            )
        )
    ).scalars().all()

    for idx, event in enumerate(events):
        session.add(
            InsuranceReportLineItem(
                report_id=report.id,
                event_id=event.id,
                suggested_year=event.suggested_declaration_year,
                suggested_month=event.suggested_declaration_month,
                declared_year=event.suggested_declaration_year,
                declared_month=event.suggested_declaration_month,
                sort_order=idx,
            )
        )

    await session.commit()
    await session.refresh(report)
    total, adjusted, missing = await _single_counts(session, report.id)
    return _to_report_dict(report, total, adjusted, missing)


async def list_reports(
    session: AsyncSession,
    *,
    year: Optional[int],
    status_filter: Optional[str],
    page: int,
    page_size: int,
) -> dict:
    stmt = select(InsurancePeriodReport)
    if year:
        stmt = stmt.where(InsurancePeriodReport.period_year == year)
    if status_filter:
        stmt = stmt.where(InsurancePeriodReport.status == status_filter)
    stmt = stmt.order_by(
        InsurancePeriodReport.period_year.desc(),
        InsurancePeriodReport.period_month.desc(),
    )

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    counts_map = await _batch_counts(session, [r.id for r in rows])
    items = [
        _to_report_dict(r, *counts_map.get(r.id, (0, 0, 0))) for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_report_detail(session: AsyncSession, report_id: int) -> dict:
    report = await _get_report_or_404(session, report_id)

    rows = (
        await session.execute(
            select(InsuranceReportLineItem, InsuranceChangeEvent)
            .join(
                InsuranceChangeEvent,
                InsuranceChangeEvent.id == InsuranceReportLineItem.event_id,
            )
            .where(InsuranceReportLineItem.report_id == report_id)
            .order_by(
                InsuranceReportLineItem.sort_order.asc(),
                InsuranceReportLineItem.id.asc(),
            )
        )
    ).all()

    emp_ids = {event.employee_id for _, event in rows}
    emp_map = await _emp_code_map(session, emp_ids)

    line_items = [
        _to_line_item_dict(item, event, emp_map.get(event.employee_id, str(event.employee_id)))
        for item, event in rows
    ]

    total, adjusted, missing = await _single_counts(session, report_id)
    base = _to_report_dict(report, total, adjusted, missing)
    return {**base, "line_items": line_items}


async def update_report(
    session: AsyncSession,
    report_id: int,
    payload: InsurancePeriodReportUpdate,
) -> dict:
    report = await _get_report_or_404(session, report_id)
    _require_editable(report)
    report.note = payload.note
    await session.commit()
    await session.refresh(report)
    total, adjusted, missing = await _single_counts(session, report_id)
    return _to_report_dict(report, total, adjusted, missing)


async def delete_report(session: AsyncSession, report_id: int) -> None:
    report = await _get_report_or_404(session, report_id)
    if report.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể xóa báo cáo ở trạng thái 'draft'",
        )
    await session.delete(report)
    await session.commit()


async def add_line_item(
    session: AsyncSession,
    report_id: int,
    payload: InsuranceReportLineItemCreate,
) -> dict:
    report = await _get_report_or_404(session, report_id)
    _require_editable(report)

    event = await session.get(InsuranceChangeEvent, payload.event_id)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy biến động")

    dup = (
        await session.execute(
            select(InsuranceReportLineItem).where(
                InsuranceReportLineItem.report_id == report_id,
                InsuranceReportLineItem.event_id == payload.event_id,
            )
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Biến động đã có trong báo cáo này",
        )

    max_sort = (
        await session.execute(
            select(func.coalesce(func.max(InsuranceReportLineItem.sort_order), -1)).where(
                InsuranceReportLineItem.report_id == report_id
            )
        )
    ).scalar_one()

    declared_year = payload.declared_year or event.suggested_declaration_year
    declared_month = payload.declared_month or event.suggested_declaration_month
    is_adj = (
        declared_year != event.suggested_declaration_year
        or declared_month != event.suggested_declaration_month
    )

    item = InsuranceReportLineItem(
        report_id=report_id,
        event_id=event.id,
        suggested_year=event.suggested_declaration_year,
        suggested_month=event.suggested_declaration_month,
        declared_year=declared_year,
        declared_month=declared_month,
        is_adjusted=is_adj,
        sort_order=max_sort + 1,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    emp_map = await _emp_code_map(session, {event.employee_id})
    return _to_line_item_dict(item, event, emp_map.get(event.employee_id, str(event.employee_id)))


async def update_line_item(
    session: AsyncSession,
    report_id: int,
    line_item_id: int,
    payload: InsuranceReportLineItemUpdate,
    adjusted_by_id: int,
) -> dict:
    report = await _get_report_or_404(session, report_id)
    _require_editable(report)

    item = await session.get(InsuranceReportLineItem, line_item_id)
    if not item or item.report_id != report_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dòng báo cáo")

    item.declared_year = payload.declared_year
    item.declared_month = payload.declared_month
    item.is_adjusted = (
        payload.declared_year != item.suggested_year
        or payload.declared_month != item.suggested_month
    )
    item.adjustment_note = payload.adjustment_note
    item.adjusted_by_id = adjusted_by_id
    item.adjusted_at = _utcnow()
    await session.commit()
    await session.refresh(item)

    event = await session.get(InsuranceChangeEvent, item.event_id)
    emp_map = await _emp_code_map(session, {event.employee_id})
    return _to_line_item_dict(item, event, emp_map.get(event.employee_id, str(event.employee_id)))


async def remove_line_item(
    session: AsyncSession,
    report_id: int,
    line_item_id: int,
) -> None:
    report = await _get_report_or_404(session, report_id)
    _require_editable(report)

    item = await session.get(InsuranceReportLineItem, line_item_id)
    if not item or item.report_id != report_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dòng báo cáo")

    await session.delete(item)
    await session.commit()


async def list_line_items(session: AsyncSession, report_id: int) -> list[dict]:
    await _get_report_or_404(session, report_id)

    rows = (
        await session.execute(
            select(InsuranceReportLineItem, InsuranceChangeEvent)
            .join(
                InsuranceChangeEvent,
                InsuranceChangeEvent.id == InsuranceReportLineItem.event_id,
            )
            .where(InsuranceReportLineItem.report_id == report_id)
            .order_by(
                InsuranceReportLineItem.sort_order.asc(),
                InsuranceReportLineItem.id.asc(),
            )
        )
    ).all()

    emp_ids = {event.employee_id for _, event in rows}
    emp_map = await _emp_code_map(session, emp_ids)
    return [
        _to_line_item_dict(item, event, emp_map.get(event.employee_id, str(event.employee_id)))
        for item, event in rows
    ]


async def submit_for_review(
    session: AsyncSession,
    report_id: int,
    prepared_by_id: int,
) -> dict:
    report = await _get_report_or_404(session, report_id)
    if report.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Chỉ có thể nộp duyệt báo cáo ở trạng thái 'draft', "
                f"hiện tại: '{report.status}'"
            ),
        )

    count = (
        await session.execute(
            select(func.count(InsuranceReportLineItem.id)).where(
                InsuranceReportLineItem.report_id == report_id
            )
        )
    ).scalar_one()
    if count == 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Báo cáo phải có ít nhất 1 dòng biến động trước khi nộp duyệt",
        )

    report.status = "pending_review"
    report.prepared_by_id = prepared_by_id
    report.prepared_at = _utcnow()
    await session.commit()
    await session.refresh(report)
    total, adjusted, missing = await _single_counts(session, report_id)
    return _to_report_dict(report, total, adjusted, missing)


async def approve_report(
    session: AsyncSession,
    report_id: int,
    reviewed_by_id: int,
    payload: ApproveBody,
) -> dict:
    report = await _get_report_or_404(session, report_id)
    if report.status != "pending_review":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Chỉ có thể duyệt báo cáo ở trạng thái 'pending_review', "
                f"hiện tại: '{report.status}'"
            ),
        )
    if report.prepared_by_id == reviewed_by_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Người duyệt không được là người đã nộp báo cáo",
        )

    report.status = "approved"
    report.reviewed_by_id = reviewed_by_id
    report.reviewed_at = _utcnow()
    report.review_note = payload.note
    await session.commit()
    await session.refresh(report)
    total, adjusted, missing = await _single_counts(session, report_id)
    return _to_report_dict(report, total, adjusted, missing)


async def reject_report(
    session: AsyncSession,
    report_id: int,
    reviewed_by_id: int,
    payload: RejectBody,
) -> dict:
    report = await _get_report_or_404(session, report_id)
    if report.status != "pending_review":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Chỉ có thể trả lại báo cáo ở trạng thái 'pending_review', "
                f"hiện tại: '{report.status}'"
            ),
        )

    report.status = "rejected"
    report.reviewed_by_id = reviewed_by_id
    report.reviewed_at = _utcnow()
    report.review_note = payload.review_note
    await session.commit()
    await session.refresh(report)
    total, adjusted, missing = await _single_counts(session, report_id)
    return _to_report_dict(report, total, adjusted, missing)
