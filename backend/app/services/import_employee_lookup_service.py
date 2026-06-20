from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.services import employee_code_service


@dataclass(slots=True)
class EmployeeLookupResult:
    employee: Employee | None
    error: str | None = None


def _extract_seq(code_raw: str) -> int | None:
    digits = re.sub(r"\D", "", code_raw.strip())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


class EmployeeImportLookup:
    def __init__(
        self,
        *,
        by_display_code: dict[str, list[Employee]],
        by_sequence_pair: dict[tuple[str, int], Employee],
        by_global_seq: dict[int, list[Employee]],
    ) -> None:
        self._by_display_code = by_display_code
        self._by_sequence_pair = by_sequence_pair
        self._by_global_seq = by_global_seq

    @classmethod
    async def build(cls, session: AsyncSession) -> EmployeeImportLookup:
        employees = (await session.execute(select(Employee))).scalars().all()
        display_codes = await employee_code_service.batch_build_employee_display_codes(session, employees)
        sequence_rows = (
            await session.execute(select(EmployeeCodeSequence.id, EmployeeCodeSequence.code))
        ).all()
        sequence_code_by_id = {row.id: row.code for row in sequence_rows}

        by_display_code: dict[str, list[Employee]] = {}
        by_sequence_pair: dict[tuple[str, int], Employee] = {}
        by_global_seq: dict[int, list[Employee]] = {}

        for employee in employees:
            display_code = display_codes.get(employee.id, str(employee.employee_seq))
            by_display_code.setdefault(display_code, []).append(employee)
            if employee.employee_code_sequence_id is not None:
                sequence_code = sequence_code_by_id.get(employee.employee_code_sequence_id)
                if sequence_code:
                    by_sequence_pair[(sequence_code.upper(), employee.employee_seq)] = employee
            by_global_seq.setdefault(employee.employee_seq, []).append(employee)

        return cls(
            by_display_code=by_display_code,
            by_sequence_pair=by_sequence_pair,
            by_global_seq=by_global_seq,
        )

    def resolve(
        self,
        *,
        employee_code_raw: str,
        sequence_code_raw: str | None = None,
    ) -> EmployeeLookupResult:
        code = employee_code_raw.strip()
        sequence_code = (sequence_code_raw or "").strip().upper()

        if not code:
            return EmployeeLookupResult(None, "Mã nhân viên trống")

        if sequence_code:
            seq = _extract_seq(code)
            if seq is None:
                return EmployeeLookupResult(
                    None,
                    f"Mã nhân viên '{code}' không chứa phần số để đối chiếu với hệ mã '{sequence_code}'",
                )
            employee = self._by_sequence_pair.get((sequence_code, seq))
            if employee:
                return EmployeeLookupResult(employee)
            return EmployeeLookupResult(
                None,
                f"Không tìm thấy nhân viên với hệ mã '{sequence_code}' và số '{seq}'",
            )

        seq = _extract_seq(code)
        seq_matches = self._by_global_seq.get(seq, []) if seq is not None else []
        # Bare numeric input like "9901" is ambiguous if that sequence exists in
        # multiple code systems, even when one display code happens to equal it.
        if seq is not None and code.isdigit() and code == str(seq) and len(seq_matches) > 1:
            return EmployeeLookupResult(
                None,
                f"Số nhân viên '{seq}' tồn tại ở nhiều hệ mã. Hãy điền thêm cột 'Hệ mã nhân viên'",
            )

        exact_matches = self._by_display_code.get(code, [])
        if len(exact_matches) == 1:
            return EmployeeLookupResult(exact_matches[0])
        if len(exact_matches) > 1:
            return EmployeeLookupResult(
                None,
                f"Mã nhân viên '{code}' đang bị trùng giữa nhiều hệ mã. Hãy điền thêm cột 'Hệ mã nhân viên'",
            )

        if seq is None:
            return EmployeeLookupResult(None, f"Không tìm thấy nhân viên với mã '{code}'")

        if len(seq_matches) == 1:
            return EmployeeLookupResult(seq_matches[0])
        if len(seq_matches) > 1:
            return EmployeeLookupResult(
                None,
                f"Số nhân viên '{seq}' tồn tại ở nhiều hệ mã. Hãy điền thêm cột 'Hệ mã nhân viên'",
            )
        return EmployeeLookupResult(None, f"Không tìm thấy nhân viên với mã '{code}'")
