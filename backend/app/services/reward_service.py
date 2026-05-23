"""Service khen thưởng nhân viên (8.1)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import String, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.auth import User
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.reward import EmployeeReward, RewardType
from app.schemas.reward import (
    RewardCreate,
    RewardListPage,
    RewardRead,
    RewardTypeCreate,
    RewardTypeRead,
    RewardTypeUpdate,
    RewardUpdate,
)
from app.services import employee_code_service

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_reward_type_or_404(session: AsyncSession, type_id: int) -> RewardType:
    rt = await session.get(RewardType, type_id)
    if not rt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy loại khen thưởng")
    return rt


async def _get_reward_or_404(session: AsyncSession, reward_id: int) -> EmployeeReward:
    r = await session.get(EmployeeReward, reward_id)
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quyết định khen thưởng")
    return r


async def _build_reward_read(
    session: AsyncSession,
    record: EmployeeReward,
) -> RewardRead:
    emp = await session.get(Employee, record.employee_id)
    rt = await session.get(RewardType, record.reward_type_id)
    creator = await session.get(User, record.created_by_id) if record.created_by_id else None

    emp_code = ""
    dept_name: Optional[str] = None
    if emp:
        emp_code = await employee_code_service.build_employee_display_code(session, emp)
        # Lấy phòng ban từ job record mới nhất
        jr_stmt = (
            select(EmployeeJobRecord)
            .where(EmployeeJobRecord.employee_id == emp.id)
            .order_by(EmployeeJobRecord.effective_from.desc())
            .limit(1)
        )
        jr_result = await session.execute(jr_stmt)
        jr = jr_result.scalar_one_or_none()
        if jr and jr.department_id:
            dept = await session.get(Department, jr.department_id)
            dept_name = dept.name if dept else None

    return RewardRead(
        id=record.id,
        employee_id=record.employee_id,
        employee_code=emp_code,
        employee_name=emp.full_name if emp else "",
        department_name=dept_name,
        reward_type_id=record.reward_type_id,
        reward_type_name=rt.name if rt else "",
        reward_type_is_monetary=rt.is_monetary if rt else False,
        title=record.title,
        description=record.description,
        reward_date=record.reward_date,
        decision_number=record.decision_number,
        issued_by=record.issued_by,
        value=record.value,
        note=record.note,
        has_file=record.file_path is not None,
        file_name=record.file_name,
        file_size=record.file_size,
        created_by_id=record.created_by_id,
        created_by_name=creator.full_name if creator else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ── RewardType CRUD ───────────────────────────────────────────────────────────


async def list_reward_types(
    session: AsyncSession,
    *,
    include_inactive: bool = False,
) -> list[RewardTypeRead]:
    stmt = select(RewardType).order_by(RewardType.sort_order, RewardType.name)
    if not include_inactive:
        stmt = stmt.where(RewardType.is_active.is_(True))
    result = await session.execute(stmt)
    return [RewardTypeRead.model_validate(rt) for rt in result.scalars().all()]


async def create_reward_type(
    session: AsyncSession,
    data: RewardTypeCreate,
) -> RewardTypeRead:
    # Kiểm tra code unique
    existing = await session.execute(
        select(RewardType).where(RewardType.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã loại khen thưởng '{data.code}' đã tồn tại")

    rt = RewardType(**data.model_dump())
    session.add(rt)
    await session.flush()
    return RewardTypeRead.model_validate(rt)


async def update_reward_type(
    session: AsyncSession,
    type_id: int,
    data: RewardTypeUpdate,
) -> RewardTypeRead:
    rt = await _get_reward_type_or_404(session, type_id)
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(rt, field, val)
    session.add(rt)
    await session.flush()
    return RewardTypeRead.model_validate(rt)


async def delete_reward_type(session: AsyncSession, type_id: int) -> None:
    rt = await _get_reward_type_or_404(session, type_id)

    # Chặn nếu đã có records dùng type này
    count_stmt = select(func.count()).where(EmployeeReward.reward_type_id == type_id)
    count_result = await session.execute(count_stmt)
    if count_result.scalar_one() > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Không thể xóa loại khen thưởng đang được sử dụng. Hãy vô hiệu hóa thay vì xóa.",
        )
    await session.delete(rt)


# ── EmployeeReward CRUD ───────────────────────────────────────────────────────


async def list_rewards(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    reward_type_id: Optional[int] = None,
    department_id: Optional[int] = None,
    from_date=None,
    to_date=None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> RewardListPage:
    # Base query — join EmployeeCodeSequence để có thể search theo mã NV
    stmt = (
        select(EmployeeReward)
        .join(Employee, Employee.id == EmployeeReward.employee_id)
        .join(EmployeeCodeSequence, EmployeeCodeSequence.id == Employee.employee_code_sequence_id)
    )

    if employee_id is not None:
        stmt = stmt.where(EmployeeReward.employee_id == employee_id)
    if reward_type_id is not None:
        stmt = stmt.where(EmployeeReward.reward_type_id == reward_type_id)
    if department_id is not None:
        dept_sub = (
            select(EmployeeJobRecord.employee_id)
            .where(EmployeeJobRecord.department_id == department_id)
            .distinct()
        )
        stmt = stmt.where(EmployeeReward.employee_id.in_(dept_sub))
    if from_date is not None:
        stmt = stmt.where(EmployeeReward.reward_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(EmployeeReward.reward_date <= to_date)
    if search:
        from app.services.administrative_import_service import normalize_text
        kw = f"%{search.strip()}%"
        norm_kw = f"%{normalize_text(search.strip())}%"
        generated_code = EmployeeCodeSequence.code + func.lpad(
            sa_cast(Employee.employee_seq, String),
            EmployeeCodeSequence.min_digits,
            "0",
        )
        stmt = stmt.where(
            or_(
                Employee.full_name.ilike(kw),
                Employee.normalized_name.ilike(norm_kw),
                generated_code.ilike(kw),
                EmployeeReward.decision_number.ilike(kw),
            )
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(total_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(EmployeeReward.reward_date.desc(), EmployeeReward.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    records = result.scalars().all()

    items = [await _build_reward_read(session, r) for r in records]
    return RewardListPage(items=items, total=total, page=page, page_size=page_size)


async def get_reward(session: AsyncSession, reward_id: int) -> RewardRead:
    record = await _get_reward_or_404(session, reward_id)
    return await _build_reward_read(session, record)


async def create_reward(
    session: AsyncSession,
    data: RewardCreate,
    file: Optional[UploadFile],
    created_by_id: int,
) -> RewardRead:
    from pathlib import Path as _Path

    # Validate reward_type
    rt = await _get_reward_type_or_404(session, data.reward_type_id)

    # Validate value logic
    if rt.is_monetary and data.value is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Loại khen thưởng tiền mặt phải nhập giá trị",
        )
    value = data.value if rt.is_monetary else None

    # Validate employee tồn tại
    emp = await session.get(Employee, data.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    if emp.status == "resigned":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Không thể thêm khen thưởng cho nhân viên đã nghỉ việc",
        )

    # Upload file nếu có
    file_path = file_name = mime_type = None
    file_size_val = None
    if file and file.filename:
        from app.schemas.reward import ALLOWED_FILE_EXTS, MAX_FILE_SIZE
        ext = _Path(file.filename).suffix.lower()
        if ext not in ALLOWED_FILE_EXTS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Chỉ chấp nhận: {', '.join(sorted(ALLOWED_FILE_EXTS))}",
            )
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File vượt quá 10 MB")
        import io as _io
        file.file = _io.BytesIO(content)  # type: ignore[assignment]
        file.size = len(content)

        # Upload sau khi flush để có reward_id
        # Tạo record trước với file_path=None, rồi upload sau khi có id
        record = EmployeeReward(
            employee_id=data.employee_id,
            reward_type_id=data.reward_type_id,
            title=data.title,
            description=data.description,
            reward_date=data.reward_date,
            decision_number=data.decision_number,
            issued_by=data.issued_by,
            value=value,
            note=data.note,
            created_by_id=created_by_id,
        )
        session.add(record)
        await session.flush()  # get record.id

        file_path, file_size_val = await storage.save_reward_file(record.id, file)
        file_name = file.filename
        mime_type = file.content_type
        record.file_path = file_path
        record.file_name = file_name
        record.file_size = file_size_val
        record.mime_type = mime_type
        session.add(record)
        await session.flush()
    else:
        record = EmployeeReward(
            employee_id=data.employee_id,
            reward_type_id=data.reward_type_id,
            title=data.title,
            description=data.description,
            reward_date=data.reward_date,
            decision_number=data.decision_number,
            issued_by=data.issued_by,
            value=value,
            note=data.note,
            created_by_id=created_by_id,
        )
        session.add(record)
        await session.flush()

    return await _build_reward_read(session, record)


async def update_reward(
    session: AsyncSession,
    reward_id: int,
    data: RewardUpdate,
    file: Optional[UploadFile],
) -> RewardRead:
    from pathlib import Path as _Path

    record = await _get_reward_or_404(session, reward_id)

    # Nếu đổi reward_type → re-validate monetary
    if data.reward_type_id is not None:
        rt = await _get_reward_type_or_404(session, data.reward_type_id)
        record.reward_type_id = data.reward_type_id
        new_value = data.value if data.value is not None else record.value
        if rt.is_monetary and new_value is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Loại khen thưởng tiền mặt phải nhập giá trị",
            )
        if not rt.is_monetary:
            record.value = None
        else:
            record.value = new_value
    else:
        if data.value is not None:
            record.value = data.value

    for field in ("title", "description", "reward_date", "decision_number", "issued_by", "note"):
        val = getattr(data, field)
        if val is not None:
            setattr(record, field, val)

    # Xử lý file mới
    if file and file.filename:
        from app.schemas.reward import ALLOWED_FILE_EXTS, MAX_FILE_SIZE
        ext = _Path(file.filename).suffix.lower()
        if ext not in ALLOWED_FILE_EXTS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Chỉ chấp nhận: {', '.join(sorted(ALLOWED_FILE_EXTS))}",
            )
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File vượt quá 10 MB")
        import io as _io
        file.file = _io.BytesIO(content)  # type: ignore[assignment]
        file.size = len(content)

        # Xóa file cũ
        if record.file_path:
            try:
                storage.delete_attachment(record.file_path)
            except Exception:
                logger.warning("Không thể xóa file MinIO cũ: %s", record.file_path)

        file_path, file_size_val = await storage.save_reward_file(record.id, file)
        record.file_path = file_path
        record.file_name = file.filename
        record.file_size = file_size_val
        record.mime_type = file.content_type

    record.updated_at = _utcnow()
    session.add(record)
    await session.flush()
    return await _build_reward_read(session, record)


async def delete_reward(session: AsyncSession, reward_id: int) -> None:
    record = await _get_reward_or_404(session, reward_id)
    if record.file_path:
        try:
            storage.delete_attachment(record.file_path)
        except Exception:
            logger.warning("Không thể xóa file MinIO: %s", record.file_path)
    await session.delete(record)


async def get_employee_reward_history(
    session: AsyncSession,
    employee_id: int,
) -> list[RewardRead]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    stmt = (
        select(EmployeeReward)
        .where(EmployeeReward.employee_id == employee_id)
        .order_by(EmployeeReward.reward_date.desc(), EmployeeReward.id.desc())
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [await _build_reward_read(session, r) for r in records]
