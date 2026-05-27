"""Service layer cho Onboarding Checklist (Plan 14.1)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.auth import User
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.onboarding import (
    OnboardingChecklist,
    OnboardingChecklistItem,
    OnboardingTask,
)
from app.models.org import Department
from app.schemas.onboarding import (
    OnboardingChecklistCreate,
    OnboardingChecklistItemRead,
    OnboardingChecklistItemUpdate,
    OnboardingChecklistListItem,
    OnboardingChecklistPage,
    OnboardingChecklistRead,
    OnboardingChecklistUpdate,
    OnboardingTaskCreate,
    OnboardingTaskRead,
    OnboardingTaskUpdate,
)

logger = logging.getLogger(__name__)

_VALID_GROUPS = {"admin", "it", "training", "specialty"}
_VALID_ITEM_STATUSES = {"pending", "in_progress", "done", "skipped"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today() -> date:
    return datetime.now(timezone.utc).date()


# ── Task templates ─────────────────────────────────────────────────────────────


async def list_tasks(
    session: AsyncSession,
    is_active: Optional[bool] = None,
    group: Optional[str] = None,
) -> List[OnboardingTaskRead]:
    q = select(OnboardingTask).order_by(OnboardingTask.group, OnboardingTask.sort_order)
    if is_active is not None:
        q = q.where(OnboardingTask.is_active == is_active)
    if group:
        q = q.where(OnboardingTask.group == group)
    rows = (await session.execute(q)).scalars().all()
    return [OnboardingTaskRead.model_validate(r) for r in rows]


async def create_task(
    session: AsyncSession,
    data: OnboardingTaskCreate,
    created_by_id: Optional[int] = None,
) -> OnboardingTaskRead:
    if data.group not in _VALID_GROUPS:
        raise ValueError(f"group phải là một trong: {', '.join(sorted(_VALID_GROUPS))}")
    # check duplicate code
    existing = (
        await session.execute(select(OnboardingTask).where(OnboardingTask.code == data.code))
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Code '{data.code}' đã tồn tại")
    task = OnboardingTask(
        code=data.code,
        name=data.name,
        description=data.description,
        group=data.group,
        default_assignee_role=data.default_assignee_role,
        due_offset_days=data.due_offset_days,
        sort_order=data.sort_order,
        created_by_id=created_by_id,
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)
    return OnboardingTaskRead.model_validate(task)


async def update_task(
    session: AsyncSession, task_id: int, data: OnboardingTaskUpdate
) -> OnboardingTaskRead:
    task = (
        await session.execute(select(OnboardingTask).where(OnboardingTask.id == task_id))
    ).scalar_one_or_none()
    if not task:
        raise LookupError(f"OnboardingTask id={task_id} không tồn tại")
    if data.group is not None and data.group not in _VALID_GROUPS:
        raise ValueError(f"group phải là một trong: {', '.join(sorted(_VALID_GROUPS))}")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    task.updated_at = _utcnow()
    await session.flush()
    await session.refresh(task)
    return OnboardingTaskRead.model_validate(task)


async def delete_task(session: AsyncSession, task_id: int) -> None:
    task = (
        await session.execute(select(OnboardingTask).where(OnboardingTask.id == task_id))
    ).scalar_one_or_none()
    if not task:
        raise LookupError(f"OnboardingTask id={task_id} không tồn tại")
    # kiểm tra xem có item nào dùng task này không
    has_items = (
        await session.execute(
            select(OnboardingChecklistItem).where(
                OnboardingChecklistItem.task_id == task_id
            ).limit(1)
        )
    ).scalar_one_or_none()
    if has_items:
        # soft delete
        task.is_active = False
        task.updated_at = _utcnow()
        await session.flush()
    else:
        await session.delete(task)
        await session.flush()


# ── Checklist CRUD ─────────────────────────────────────────────────────────────


async def _build_checklist_read(
    session: AsyncSession, checklist: OnboardingChecklist
) -> OnboardingChecklistRead:
    """Build đầy đủ OnboardingChecklistRead kèm items."""
    # Employee
    emp = (
        await session.execute(select(Employee).where(Employee.id == checklist.employee_id))
    ).scalar_one()

    # Employee code (from employee_code_sequences logic — stored as formatted code)
    # We build employee_code inline from seq
    emp_code = f"NV{emp.employee_seq:05d}"

    # Department từ job record hiện tại
    dept_name: Optional[str] = None
    job_rec = (
        await session.execute(
            select(EmployeeJobRecord)
            .where(
                EmployeeJobRecord.employee_id == emp.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if job_rec and job_rec.department_id:
        dept = (
            await session.execute(
                select(Department).where(Department.id == job_rec.department_id)
            )
        ).scalar_one_or_none()
        if dept:
            dept_name = dept.name

    # Buddy
    buddy_name: Optional[str] = None
    if checklist.buddy_user_id:
        buddy = (
            await session.execute(
                select(User).where(User.id == checklist.buddy_user_id)
            )
        ).scalar_one_or_none()
        if buddy:
            buddy_name = buddy.full_name

    # Items + join task + assignee
    items_result = (
        await session.execute(
            select(OnboardingChecklistItem, OnboardingTask)
            .join(OnboardingTask, OnboardingChecklistItem.task_id == OnboardingTask.id)
            .where(OnboardingChecklistItem.checklist_id == checklist.id)
            .order_by(OnboardingTask.sort_order)
        )
    ).all()

    today = _today()
    item_reads: List[OnboardingChecklistItemRead] = []
    for item, task in items_result:
        assignee_name: Optional[str] = None
        if item.assignee_user_id:
            assignee = (
                await session.execute(
                    select(User).where(User.id == item.assignee_user_id)
                )
            ).scalar_one_or_none()
            if assignee:
                assignee_name = assignee.full_name

        is_overdue = (
            item.due_date < today and item.status not in ("done", "skipped")
        )
        item_reads.append(
            OnboardingChecklistItemRead(
                id=item.id,
                checklist_id=item.checklist_id,
                task_id=item.task_id,
                task_code=task.code,
                task_name=task.name,
                task_group=task.group,
                assignee_user_id=item.assignee_user_id,
                assignee_name=assignee_name,
                due_date=item.due_date,
                completed_at=item.completed_at,
                status=item.status,
                note=item.note,
                is_overdue=is_overdue,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )

    return OnboardingChecklistRead(
        id=checklist.id,
        employee_id=checklist.employee_id,
        employee_name=emp.full_name,
        employee_code=emp_code,
        department_name=dept_name,
        start_date=emp.start_date,
        hiring_decision_id=checklist.hiring_decision_id,
        buddy_user_id=checklist.buddy_user_id,
        buddy_name=buddy_name,
        status=checklist.status,
        completion_pct=float(checklist.completion_pct),
        items=item_reads,
        created_by_id=checklist.created_by_id,
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
    )


async def create_checklist(
    session: AsyncSession,
    employee_id: int,
    hiring_decision_id: Optional[int] = None,
    buddy_user_id: Optional[int] = None,
    created_by_id: Optional[int] = None,
) -> OnboardingChecklistRead:
    # 1. Employee tồn tại?
    emp = (
        await session.execute(select(Employee).where(Employee.id == employee_id))
    ).scalar_one_or_none()
    if not emp:
        raise LookupError(f"Employee id={employee_id} không tồn tại")

    # 2. Đã có checklist?
    existing = (
        await session.execute(
            select(OnboardingChecklist).where(
                OnboardingChecklist.employee_id == employee_id
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Nhân viên đã có checklist onboarding")

    # 3. Tạo checklist
    checklist = OnboardingChecklist(
        employee_id=employee_id,
        hiring_decision_id=hiring_decision_id,
        buddy_user_id=buddy_user_id,
        status="in_progress",
        completion_pct=0.0,
        created_by_id=created_by_id,
    )
    session.add(checklist)
    await session.flush()  # lấy checklist.id

    # 4. Lấy tất cả active tasks
    tasks = (
        await session.execute(
            select(OnboardingTask)
            .where(OnboardingTask.is_active == True)  # noqa: E712
            .order_by(OnboardingTask.sort_order)
        )
    ).scalars().all()

    # 5. Tạo items
    for task in tasks:
        item = OnboardingChecklistItem(
            checklist_id=checklist.id,
            task_id=task.id,
            due_date=emp.start_date + timedelta(days=task.due_offset_days),
            status="pending",
        )
        session.add(item)

    await session.flush()
    await session.refresh(checklist)
    return await _build_checklist_read(session, checklist)


async def get_checklist_detail(
    session: AsyncSession, checklist_id: int
) -> OnboardingChecklistRead:
    checklist = (
        await session.execute(
            select(OnboardingChecklist).where(OnboardingChecklist.id == checklist_id)
        )
    ).scalar_one_or_none()
    if not checklist:
        raise LookupError(f"OnboardingChecklist id={checklist_id} không tồn tại")
    return await _build_checklist_read(session, checklist)


async def get_checklist_by_employee(
    session: AsyncSession, employee_id: int
) -> OnboardingChecklistRead:
    checklist = (
        await session.execute(
            select(OnboardingChecklist).where(
                OnboardingChecklist.employee_id == employee_id
            )
        )
    ).scalar_one_or_none()
    if not checklist:
        raise LookupError(f"Nhân viên id={employee_id} chưa có checklist onboarding")
    return await _build_checklist_read(session, checklist)


async def update_checklist(
    session: AsyncSession, checklist_id: int, data: OnboardingChecklistUpdate
) -> OnboardingChecklistRead:
    checklist = (
        await session.execute(
            select(OnboardingChecklist).where(OnboardingChecklist.id == checklist_id)
        )
    ).scalar_one_or_none()
    if not checklist:
        raise LookupError(f"OnboardingChecklist id={checklist_id} không tồn tại")
    if data.buddy_user_id is not None:
        checklist.buddy_user_id = data.buddy_user_id
    if data.status is not None:
        if data.status not in ("in_progress", "completed", "cancelled"):
            raise ValueError("status phải là in_progress | completed | cancelled")
        checklist.status = data.status
    checklist.updated_at = _utcnow()
    await session.flush()
    await session.refresh(checklist)
    return await _build_checklist_read(session, checklist)


async def _recompute_completion(session: AsyncSession, checklist: OnboardingChecklist) -> None:
    """Tính lại completion_pct và auto-complete nếu cần."""
    rows = (
        await session.execute(
            select(OnboardingChecklistItem).where(
                OnboardingChecklistItem.checklist_id == checklist.id
            )
        )
    ).scalars().all()

    if not rows:
        checklist.completion_pct = 0.0
    else:
        non_skipped = [r for r in rows if r.status != "skipped"]
        done = [r for r in non_skipped if r.status == "done"]
        total = len(non_skipped)
        checklist.completion_pct = round(len(done) / total * 100, 2) if total > 0 else 0.0

        # auto-complete nếu tất cả done hoặc skipped
        all_terminal = all(r.status in ("done", "skipped") for r in rows)
        if all_terminal and checklist.status == "in_progress":
            checklist.status = "completed"

    checklist.updated_at = _utcnow()


async def update_item_status(
    session: AsyncSession,
    item_id: int,
    data: OnboardingChecklistItemUpdate,
) -> OnboardingChecklistItemRead:
    item = (
        await session.execute(
            select(OnboardingChecklistItem).where(OnboardingChecklistItem.id == item_id)
        )
    ).scalar_one_or_none()
    if not item:
        raise LookupError(f"OnboardingChecklistItem id={item_id} không tồn tại")

    if data.status not in _VALID_ITEM_STATUSES:
        raise ValueError(f"status phải là một trong: {', '.join(sorted(_VALID_ITEM_STATUSES))}")

    item.status = data.status
    if data.status == "done":
        item.completed_at = _utcnow()
    else:
        item.completed_at = None
    if data.assignee_user_id is not None:
        item.assignee_user_id = data.assignee_user_id
    if data.note is not None:
        item.note = data.note
    item.updated_at = _utcnow()

    # recompute checklist completion
    checklist = (
        await session.execute(
            select(OnboardingChecklist).where(OnboardingChecklist.id == item.checklist_id)
        )
    ).scalar_one()
    await _recompute_completion(session, checklist)
    await session.flush()

    # Fetch task for response
    task = (
        await session.execute(select(OnboardingTask).where(OnboardingTask.id == item.task_id))
    ).scalar_one()
    assignee_name: Optional[str] = None
    if item.assignee_user_id:
        assignee = (
            await session.execute(select(User).where(User.id == item.assignee_user_id))
        ).scalar_one_or_none()
        if assignee:
            assignee_name = assignee.full_name

    today = _today()
    is_overdue = item.due_date < today and item.status not in ("done", "skipped")

    return OnboardingChecklistItemRead(
        id=item.id,
        checklist_id=item.checklist_id,
        task_id=item.task_id,
        task_code=task.code,
        task_name=task.name,
        task_group=task.group,
        assignee_user_id=item.assignee_user_id,
        assignee_name=assignee_name,
        due_date=item.due_date,
        completed_at=item.completed_at,
        status=item.status,
        note=item.note,
        is_overdue=is_overdue,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def list_checklists(
    session: AsyncSession,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    days_until_completion: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> OnboardingChecklistPage:
    today = _today()

    # Build join query
    q = (
        select(
            OnboardingChecklist,
            Employee,
            EmployeeJobRecord,
        )
        .join(Employee, OnboardingChecklist.employee_id == Employee.id)
        .outerjoin(
            EmployeeJobRecord,
            sa.and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
    )

    if status:
        q = q.where(OnboardingChecklist.status == status)
    if department_id:
        q = q.where(EmployeeJobRecord.department_id == department_id)
    if days_until_completion is not None:
        # filter: probation_end_date <= today + N days
        cutoff = today + timedelta(days=days_until_completion)
        q = q.where(EmployeeJobRecord.probation_end_date <= cutoff)

    q = q.order_by(OnboardingChecklist.created_at.desc())

    total_result = await session.execute(
        select(sa.func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).all()

    # Subquery: item counts per checklist
    checklist_ids = [r[0].id for r in rows]
    item_counts: dict[int, dict] = {cid: {"total": 0, "done": 0, "overdue": 0} for cid in checklist_ids}
    if checklist_ids:
        items_q = await session.execute(
            select(
                OnboardingChecklistItem.checklist_id,
                OnboardingChecklistItem.status,
                OnboardingChecklistItem.due_date,
            ).where(OnboardingChecklistItem.checklist_id.in_(checklist_ids))
        )
        for row in items_q.all():
            cid, st, dd = row.checklist_id, row.status, row.due_date
            item_counts[cid]["total"] += 1
            if st == "done":
                item_counts[cid]["done"] += 1
            if dd < today and st not in ("done", "skipped"):
                item_counts[cid]["overdue"] += 1

    # Buddy names
    buddy_ids = list({r[0].buddy_user_id for r in rows if r[0].buddy_user_id})
    buddy_map: dict[int, str] = {}
    if buddy_ids:
        buddy_rows = (
            await session.execute(select(User).where(User.id.in_(buddy_ids)))
        ).scalars().all()
        buddy_map = {u.id: u.full_name for u in buddy_rows}

    # Department names
    dept_ids = list({r[2].department_id for r in rows if r[2] and r[2].department_id})
    dept_map: dict[int, str] = {}
    if dept_ids:
        dept_rows = (
            await session.execute(select(Department).where(Department.id.in_(dept_ids)))
        ).scalars().all()
        dept_map = {d.id: d.name for d in dept_rows}

    result: List[OnboardingChecklistListItem] = []
    for checklist, emp, job_rec in rows:
        counts = item_counts.get(checklist.id, {"total": 0, "done": 0, "overdue": 0})
        dept_name: Optional[str] = None
        if job_rec and job_rec.department_id:
            dept_name = dept_map.get(job_rec.department_id)

        result.append(
            OnboardingChecklistListItem(
                id=checklist.id,
                employee_id=emp.id,
                employee_name=emp.full_name,
                employee_code=f"NV{emp.employee_seq:05d}",
                department_name=dept_name,
                start_date=emp.start_date,
                buddy_name=buddy_map.get(checklist.buddy_user_id) if checklist.buddy_user_id else None,
                status=checklist.status,
                completion_pct=float(checklist.completion_pct),
                total_items=counts["total"],
                done_items=counts["done"],
                overdue_items=counts["overdue"],
                days_since_start=(today - emp.start_date).days,
            )
        )

    return OnboardingChecklistPage(items=result, total=total, page=page, page_size=page_size)


async def get_overdue_items(session: AsyncSession) -> list[dict]:
    """Dùng bởi reminder_service: lấy các item quá hạn chưa done."""
    today = _today()
    rows = (
        await session.execute(
            select(OnboardingChecklistItem, OnboardingChecklist, Employee)
            .join(OnboardingChecklist, OnboardingChecklistItem.checklist_id == OnboardingChecklist.id)
            .join(Employee, OnboardingChecklist.employee_id == Employee.id)
            .where(
                OnboardingChecklistItem.due_date < today,
                OnboardingChecklistItem.status.notin_(["done", "skipped"]),
                OnboardingChecklist.status == "in_progress",
            )
            .order_by(OnboardingChecklistItem.due_date)
        )
    ).all()
    result = []
    for item, checklist, emp in rows:
        result.append(
            {
                "item_id": item.id,
                "checklist_id": checklist.id,
                "employee_id": emp.id,
                "employee_name": emp.full_name,
                "task_id": item.task_id,
                "due_date": item.due_date,
                "status": item.status,
                "assignee_user_id": item.assignee_user_id,
            }
        )
    return result
