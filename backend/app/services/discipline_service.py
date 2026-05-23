"""Service kỷ luật nhân viên (8.2)."""
from __future__ import annotations

import io as _io
import logging
from datetime import datetime, timezone
from pathlib import Path as _Path
from typing import Optional

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import String, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.auth import User
from app.models.discipline import EmployeeDiscipline
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.schemas.discipline import (
    ALLOWED_FILE_EXTS,
    DISCIPLINE_FORMS,
    MAX_FILE_SIZE,
    DisciplineCreate,
    DisciplineListPage,
    DisciplineRead,
    DisciplineUpdate,
)
from app.services import employee_code_service

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_discipline_or_404(session: AsyncSession, discipline_id: int) -> EmployeeDiscipline:
    d = await session.get(EmployeeDiscipline, discipline_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quyết định kỷ luật")
    return d


async def _build_read(session: AsyncSession, record: EmployeeDiscipline) -> DisciplineRead:
    emp = await session.get(Employee, record.employee_id)
    creator = await session.get(User, record.created_by_id) if record.created_by_id else None

    emp_code = ""
    dept_name: Optional[str] = None
    if emp:
        emp_code = await employee_code_service.build_employee_display_code(session, emp)
        jr_stmt = (
            select(EmployeeJobRecord)
            .where(EmployeeJobRecord.employee_id == emp.id)
            .order_by(EmployeeJobRecord.effective_from.desc())
            .limit(1)
        )
        jr = (await session.execute(jr_stmt)).scalar_one_or_none()
        if jr and jr.department_id:
            dept = await session.get(Department, jr.department_id)
            dept_name = dept.name if dept else None

    return DisciplineRead(
        id=record.id,
        employee_id=record.employee_id,
        employee_code=emp_code,
        employee_name=emp.full_name if emp else "",
        department_name=dept_name,
        discipline_form=record.discipline_form,
        discipline_form_label=DISCIPLINE_FORMS.get(record.discipline_form, record.discipline_form),
        violation_date=record.violation_date,
        effective_date=record.effective_date,
        end_date=record.end_date,
        extended_months=record.extended_months,
        title=record.title,
        description=record.description,
        decision_number=record.decision_number,
        issued_by=record.issued_by,
        note=record.note,
        has_file=record.file_path is not None,
        file_name=record.file_name,
        file_size=record.file_size,
        created_by_id=record.created_by_id,
        created_by_name=creator.full_name if creator else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _validate_and_read_file(file: UploadFile) -> bytes:
    ext = _Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_FILE_EXTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ chấp nhận: {', '.join(sorted(ALLOWED_FILE_EXTS))}",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File vượt quá 10 MB")
    file.file = _io.BytesIO(content)  # type: ignore[assignment]
    file.size = len(content)
    return content


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_disciplines(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    discipline_form: Optional[str] = None,
    department_id: Optional[int] = None,
    from_date=None,
    to_date=None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> DisciplineListPage:
    stmt = (
        select(EmployeeDiscipline)
        .join(Employee, Employee.id == EmployeeDiscipline.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id) & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
    )

    if employee_id is not None:
        stmt = stmt.where(EmployeeDiscipline.employee_id == employee_id)
    if discipline_form is not None:
        stmt = stmt.where(EmployeeDiscipline.discipline_form == discipline_form)
    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)
    if from_date is not None:
        stmt = stmt.where(EmployeeDiscipline.effective_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(EmployeeDiscipline.effective_date <= to_date)
    if search:
        from app.services.administrative_import_service import normalize_text
        kw = f"%{search.strip()}%"
        norm_kw = f"%{normalize_text(search.strip())}%"
        dept_prefix = func.coalesce(
            func.nullif(func.btrim(Department.display_prefix), ""),
            Department.code,
        )
        generated_code = dept_prefix + func.lpad(
            sa_cast(Employee.employee_seq, String),
            4,
            "0",
        )
        stmt = stmt.where(
            or_(
                Employee.full_name.ilike(kw),
                Employee.normalized_name.ilike(norm_kw),
                generated_code.ilike(kw),
                EmployeeDiscipline.decision_number.ilike(kw),
            )
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(EmployeeDiscipline.effective_date.desc(), EmployeeDiscipline.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    records = (await session.execute(stmt)).scalars().all()

    items = [await _build_read(session, r) for r in records]
    return DisciplineListPage(items=items, total=total, page=page, page_size=page_size)


async def get_discipline(session: AsyncSession, discipline_id: int) -> DisciplineRead:
    record = await _get_discipline_or_404(session, discipline_id)
    return await _build_read(session, record)


async def create_discipline(
    session: AsyncSession,
    data: DisciplineCreate,
    file: Optional[UploadFile],
    created_by_id: int,
) -> DisciplineRead:
    emp = await session.get(Employee, data.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    if emp.status == "resigned":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Không thể thêm kỷ luật cho nhân viên đã nghỉ việc",
        )

    end_date = None
    if data.discipline_form == "keo_dai_nang_luong" and data.extended_months:
        end_date = data.effective_date + relativedelta(months=data.extended_months)

    if file and file.filename:
        await _validate_and_read_file(file)

    record = EmployeeDiscipline(
        employee_id=data.employee_id,
        discipline_form=data.discipline_form,
        violation_date=data.violation_date,
        effective_date=data.effective_date,
        end_date=end_date,
        extended_months=data.extended_months,
        title=data.title,
        description=data.description,
        decision_number=data.decision_number,
        issued_by=data.issued_by,
        note=data.note,
        created_by_id=created_by_id,
    )
    session.add(record)
    await session.flush()

    if file and file.filename:
        file_path, file_size = await storage.save_discipline_file(record.id, file)
        record.file_path = file_path
        record.file_name = file.filename
        record.file_size = file_size
        record.mime_type = file.content_type
        session.add(record)
        await session.flush()

    return await _build_read(session, record)


async def update_discipline(
    session: AsyncSession,
    discipline_id: int,
    data: DisciplineUpdate,
    file: Optional[UploadFile],
) -> DisciplineRead:
    record = await _get_discipline_or_404(session, discipline_id)

    new_form = data.discipline_form if data.discipline_form is not None else record.discipline_form
    new_effective = data.effective_date if data.effective_date is not None else record.effective_date
    new_months = data.extended_months if data.extended_months is not None else record.extended_months

    if data.discipline_form is not None:
        record.discipline_form = data.discipline_form
        if data.discipline_form != "keo_dai_nang_luong":
            record.extended_months = None
            record.end_date = None
    if data.violation_date is not None:
        record.violation_date = data.violation_date
    if data.effective_date is not None:
        record.effective_date = data.effective_date
    if data.title is not None:
        record.title = data.title
    for field in ("description", "decision_number", "issued_by", "note"):
        val = getattr(data, field)
        if val is not None:
            setattr(record, field, val)

    if new_form == "keo_dai_nang_luong":
        if data.extended_months is not None:
            record.extended_months = data.extended_months
        record.end_date = new_effective + relativedelta(months=record.extended_months or new_months or 1)
    else:
        record.extended_months = None
        record.end_date = None

    if file and file.filename:
        await _validate_and_read_file(file)
        if record.file_path:
            try:
                storage.delete_attachment(record.file_path)
            except Exception:
                logger.warning("Không thể xóa file MinIO cũ: %s", record.file_path)
        file_path, file_size = await storage.save_discipline_file(record.id, file)
        record.file_path = file_path
        record.file_name = file.filename
        record.file_size = file_size
        record.mime_type = file.content_type

    record.updated_at = _utcnow()
    session.add(record)
    await session.flush()
    return await _build_read(session, record)


async def delete_discipline(session: AsyncSession, discipline_id: int) -> None:
    record = await _get_discipline_or_404(session, discipline_id)
    if record.file_path:
        try:
            storage.delete_attachment(record.file_path)
        except Exception:
            logger.warning("Không thể xóa file MinIO: %s", record.file_path)
    await session.delete(record)


async def get_employee_discipline_history(
    session: AsyncSession,
    employee_id: int,
) -> list[DisciplineRead]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    stmt = (
        select(EmployeeDiscipline)
        .where(EmployeeDiscipline.employee_id == employee_id)
        .order_by(EmployeeDiscipline.effective_date.desc(), EmployeeDiscipline.id.desc())
    )
    records = (await session.execute(stmt)).scalars().all()
    return [await _build_read(session, r) for r in records]
