from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_code import EmployeeCodeSequence, EmployeeCodeSequenceRule
from app.schemas.employee_code_rule import EmployeeCodeSequenceRuleUpsert
from app.services import department_service, job_position_service


def _to_read(rule: EmployeeCodeSequenceRule, sequence: EmployeeCodeSequence) -> dict:
    return {
        "id": rule.id,
        "scope_type": rule.scope_type,
        "department_id": rule.department_id,
        "job_position_id": rule.job_position_id,
        "employee_code_sequence_id": rule.employee_code_sequence_id,
        "employee_code_sequence_code": sequence.code,
        "employee_code_sequence_name": sequence.name,
        "apply_to_descendants": rule.apply_to_descendants,
        "note": rule.note,
        "is_active": rule.is_active,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


async def list_sequences(session: AsyncSession) -> list[EmployeeCodeSequence]:
    rows = await session.execute(
        select(EmployeeCodeSequence)
        .where(EmployeeCodeSequence.is_active.is_(True))
        .order_by(EmployeeCodeSequence.code)
    )
    return list(rows.scalars().all())


async def _get_active_sequence_or_422(
    session: AsyncSession,
    sequence_id: int,
) -> EmployeeCodeSequence:
    sequence = await session.get(EmployeeCodeSequence, sequence_id)
    if not sequence or not sequence.is_active:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Hệ mã nhân viên không hợp lệ hoặc đã ngừng áp dụng",
        )
    return sequence


async def _get_rule(
    session: AsyncSession,
    *,
    scope_type: str,
    department_id: int | None = None,
    job_position_id: int | None = None,
) -> tuple[EmployeeCodeSequenceRule, EmployeeCodeSequence] | None:
    stmt = (
        select(EmployeeCodeSequenceRule, EmployeeCodeSequence)
        .join(
            EmployeeCodeSequence,
            EmployeeCodeSequence.id == EmployeeCodeSequenceRule.employee_code_sequence_id,
        )
        .where(
            EmployeeCodeSequenceRule.scope_type == scope_type,
            EmployeeCodeSequenceRule.is_active.is_(True),
        )
    )
    if department_id is not None:
        stmt = stmt.where(EmployeeCodeSequenceRule.department_id == department_id)
    if job_position_id is not None:
        stmt = stmt.where(EmployeeCodeSequenceRule.job_position_id == job_position_id)
    return (await session.execute(stmt)).first()


async def get_department_rule(session: AsyncSession, department_id: int) -> dict | None:
    await department_service.get_by_id(session, department_id)
    row = await _get_rule(session, scope_type="department", department_id=department_id)
    if not row:
        return None
    rule, sequence = row
    return _to_read(rule, sequence)


async def upsert_department_rule(
    session: AsyncSession,
    department_id: int,
    payload: EmployeeCodeSequenceRuleUpsert,
) -> dict:
    await department_service.get_by_id(session, department_id)
    sequence = await _get_active_sequence_or_422(session, payload.employee_code_sequence_id)
    existing = await _get_rule(session, scope_type="department", department_id=department_id)

    if existing:
        rule, _ = existing
        rule.employee_code_sequence_id = sequence.id
        rule.apply_to_descendants = payload.apply_to_descendants
        rule.note = payload.note.strip() if payload.note else None
        await session.flush()
    else:
        rule = EmployeeCodeSequenceRule(
            scope_type="department",
            department_id=department_id,
            employee_code_sequence_id=sequence.id,
            apply_to_descendants=payload.apply_to_descendants,
            note=payload.note.strip() if payload.note else None,
            is_active=True,
        )
        session.add(rule)
        await session.flush()

    await session.commit()
    await session.refresh(rule)
    return _to_read(rule, sequence)


async def delete_department_rule(session: AsyncSession, department_id: int) -> dict:
    await department_service.get_by_id(session, department_id)
    existing = await _get_rule(session, scope_type="department", department_id=department_id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy rule hệ mã cho phòng/ban")
    rule, _ = existing
    await session.delete(rule)
    await session.commit()
    return {"message": "Đã xóa rule hệ mã của phòng/ban"}


async def get_job_position_rule(session: AsyncSession, job_position_id: int) -> dict | None:
    await job_position_service.get_by_id(session, job_position_id)
    row = await _get_rule(session, scope_type="job_position", job_position_id=job_position_id)
    if not row:
        return None
    rule, sequence = row
    return _to_read(rule, sequence)


async def upsert_job_position_rule(
    session: AsyncSession,
    job_position_id: int,
    payload: EmployeeCodeSequenceRuleUpsert,
) -> dict:
    await job_position_service.get_by_id(session, job_position_id)
    sequence = await _get_active_sequence_or_422(session, payload.employee_code_sequence_id)
    existing = await _get_rule(session, scope_type="job_position", job_position_id=job_position_id)

    if existing:
        rule, _ = existing
        rule.employee_code_sequence_id = sequence.id
        rule.apply_to_descendants = False
        rule.note = payload.note.strip() if payload.note else None
        await session.flush()
    else:
        rule = EmployeeCodeSequenceRule(
            scope_type="job_position",
            job_position_id=job_position_id,
            employee_code_sequence_id=sequence.id,
            apply_to_descendants=False,
            note=payload.note.strip() if payload.note else None,
            is_active=True,
        )
        session.add(rule)
        await session.flush()

    await session.commit()
    await session.refresh(rule)
    return _to_read(rule, sequence)


async def delete_job_position_rule(session: AsyncSession, job_position_id: int) -> dict:
    await job_position_service.get_by_id(session, job_position_id)
    existing = await _get_rule(session, scope_type="job_position", job_position_id=job_position_id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy rule hệ mã cho vị trí công việc")
    rule, _ = existing
    await session.delete(rule)
    await session.commit()
    return {"message": "Đã xóa rule hệ mã của vị trí công việc"}
