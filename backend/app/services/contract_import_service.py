"""Import hợp đồng hàng loạt từ file Excel (12.1 — Slice 1)."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ContractCategory
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.schemas.employee_import import ImportResult, ImportRowError

IMPORT_MAX_ROWS = 1000

COLUMNS = [
    "Mã nhân viên",
    "Số hợp đồng",
    "Loại văn bản",
    "Mã loại hợp đồng",
    "Ngày ký",
    "Ngày hiệu lực",
    "Ngày hết hạn",
    "Mức lương BHXH",
]
REQUIRED_COLUMNS = {
    "Mã nhân viên", "Số hợp đồng", "Loại văn bản",
    "Mã loại hợp đồng", "Ngày ký", "Ngày hiệu lực",
}

VALID_DOCUMENT_KINDS = {"labor_contract", "contract_appendix"}


# ── Template generation ───────────────────────────────────────────────────────

def generate_template() -> bytes:
    wb = Workbook()

    ws = wb.active
    ws.title = "Hợp đồng"
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    opt_fill = PatternFill("solid", fgColor="D6E4F0")

    for col_idx, col_name in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill if col_name in REQUIRED_COLUMNS else opt_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Sample row
    sample = [
        "1", "HDLD/01/2026-001", "labor_contract", "labor_indefinite",
        "01/01/2026", "01/01/2026", "", "5000000",
    ]
    for col_idx, val in enumerate(sample, start=1):
        ws.cell(row=2, column=col_idx, value=val)

    widths = [16, 22, 20, 22, 14, 14, 14, 18]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    ws.row_dimensions[1].height = 36

    # Sheet Hướng dẫn
    guide = wb.create_sheet("Hướng dẫn")
    guide_rows = [
        ["Cột", "Bắt buộc", "Mô tả", "Giá trị hợp lệ / Ví dụ"],
        ["Mã nhân viên", "✅", "Mã số thứ tự nhân viên trong hệ thống", "1 / 001 / NV001"],
        ["Số hợp đồng", "✅", "Số hợp đồng duy nhất trong hệ thống", "HDLD/01/2026-001"],
        ["Loại văn bản", "✅", "Phân loại tài liệu hợp đồng", "labor_contract / contract_appendix"],
        ["Mã loại hợp đồng", "✅", "Mã danh mục loại hợp đồng", "labor_indefinite / labor_definite / probation_agreement"],
        ["Ngày ký", "✅", "Ngày ký kết hợp đồng (dd/mm/yyyy)", "01/01/2026"],
        ["Ngày hiệu lực", "✅", "Ngày bắt đầu có hiệu lực (dd/mm/yyyy)", "01/01/2026"],
        ["Ngày hết hạn", "", "Để trống = vô thời hạn (dd/mm/yyyy)", "31/12/2026"],
        ["Mức lương BHXH", "", "Mức đóng BHXH (VNĐ, số nguyên)", "5000000"],
        [],
        ["LƯU Ý:", "", "Cột header màu xanh đậm = bắt buộc.", ""],
        ["", "", f"Tối đa {IMPORT_MAX_ROWS} dòng mỗi lần import.", ""],
        ["", "", "Dòng trống sẽ bị bỏ qua.", ""],
    ]
    for row in guide_rows:
        guide.append(row)
    guide.column_dimensions["A"].width = 22
    guide.column_dimensions["C"].width = 42
    guide.column_dimensions["D"].width = 38
    for cell in guide["1"]:
        cell.font = Font(bold=True)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(val: object, col: str, row: int, errors: list[ImportRowError]) -> Optional[date]:
    raw = str(val).strip() if val is not None else ""
    if not raw:
        return None
    from datetime import datetime
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    errors.append(ImportRowError(row=row, column=col, message=f"Định dạng ngày không hợp lệ: '{raw}' (cần dd/mm/yyyy)"))
    return None


def _cell(row_vals: tuple, col_name: str, col_map: dict[str, int]) -> str:
    idx = col_map.get(col_name)
    if idx is None:
        return ""
    v = row_vals[idx] if idx < len(row_vals) else None
    return str(v).strip() if v is not None else ""


async def _find_employee_by_code(session: AsyncSession, code_raw: str) -> Optional[Employee]:
    """Tra cứu employee theo employee_seq (parse số từ mã NV)."""
    digits = re.sub(r"\D", "", code_raw.strip())
    if not digits:
        return None
    try:
        seq = int(digits)
    except ValueError:
        return None
    result = await session.execute(select(Employee).where(Employee.employee_seq == seq))
    return result.scalar_one_or_none()


async def _find_contract_category(session: AsyncSession, code: str) -> Optional[ContractCategory]:
    result = await session.execute(
        select(ContractCategory).where(ContractCategory.code == code.strip())
    )
    return result.scalar_one_or_none()


# ── Main import ───────────────────────────────────────────────────────────────

async def process_import(session: AsyncSession, file_bytes: bytes) -> ImportResult:
    try:
        wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception:
        raise ValueError("Không đọc được file Excel. Hãy dùng file .xlsx hợp lệ.")

    ws = wb.worksheets[0]
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        return ImportResult(total=0, success=0, failed=0, errors=[], created_ids=[])

    header_row = [str(c).strip() if c else "" for c in all_rows[0]]
    col_map: dict[str, int] = {h: i for i, h in enumerate(header_row)}

    data_rows = all_rows[1:]
    if len(data_rows) > IMPORT_MAX_ROWS:
        raise ValueError(f"File có quá nhiều dòng. Tối đa {IMPORT_MAX_ROWS} dòng mỗi lần import.")

    total = success = failed = 0
    errors: list[ImportRowError] = []
    created_ids: list[int] = []

    for rel_idx, row_vals in enumerate(data_rows):
        excel_row = rel_idx + 2
        if all(v is None or str(v).strip() == "" for v in row_vals):
            continue
        total += 1
        row_errors: list[ImportRowError] = []

        def get(col_name: str) -> str:
            return _cell(row_vals, col_name, col_map)

        # ── Required string fields ────────────────────────────────────
        emp_code      = get("Mã nhân viên")
        contract_num  = get("Số hợp đồng")
        doc_kind      = get("Loại văn bản")
        category_code = get("Mã loại hợp đồng")

        for field, val in [
            ("Mã nhân viên", emp_code),
            ("Số hợp đồng", contract_num),
            ("Loại văn bản", doc_kind),
            ("Mã loại hợp đồng", category_code),
        ]:
            if not val:
                row_errors.append(ImportRowError(row=excel_row, column=field, message="Trường bắt buộc không được để trống"))

        if doc_kind and doc_kind not in VALID_DOCUMENT_KINDS:
            row_errors.append(ImportRowError(
                row=excel_row, column="Loại văn bản",
                message=f"Giá trị phải là labor_contract hoặc contract_appendix, nhận được: '{doc_kind}'"
            ))

        # ── Dates ────────────────────────────────────────────────────
        signed_date   = _parse_date(get("Ngày ký"),         "Ngày ký",        excel_row, row_errors)
        effective_from = _parse_date(get("Ngày hiệu lực"),  "Ngày hiệu lực",  excel_row, row_errors)
        effective_to   = _parse_date(get("Ngày hết hạn"),   "Ngày hết hạn",   excel_row, row_errors)

        if not signed_date and "Ngày ký" not in {e.column for e in row_errors}:
            row_errors.append(ImportRowError(row=excel_row, column="Ngày ký", message="Trường bắt buộc không được để trống"))
        if not effective_from and "Ngày hiệu lực" not in {e.column for e in row_errors}:
            row_errors.append(ImportRowError(row=excel_row, column="Ngày hiệu lực", message="Trường bắt buộc không được để trống"))

        if effective_from and effective_to and effective_to < effective_from:
            row_errors.append(ImportRowError(
                row=excel_row, column="Ngày hết hạn",
                message="Ngày hết hạn phải sau hoặc bằng ngày hiệu lực"
            ))

        # ── Optional: insurance_salary ────────────────────────────────
        insurance_salary: Optional[Decimal] = None
        salary_raw = get("Mức lương BHXH")
        if salary_raw:
            try:
                insurance_salary = Decimal(salary_raw.replace(",", "").replace(".", ""))
                if insurance_salary <= 0:
                    row_errors.append(ImportRowError(row=excel_row, column="Mức lương BHXH", message="Mức lương BHXH phải > 0"))
                    insurance_salary = None
            except InvalidOperation:
                row_errors.append(ImportRowError(row=excel_row, column="Mức lương BHXH", message=f"Giá trị không hợp lệ: '{salary_raw}'"))

        if row_errors:
            errors.extend(row_errors)
            failed += 1
            continue

        # ── DB lookups ────────────────────────────────────────────────
        employee = await _find_employee_by_code(session, emp_code)
        if not employee:
            errors.append(ImportRowError(row=excel_row, column="Mã nhân viên", message=f"Không tìm thấy nhân viên với mã '{emp_code}'"))
            failed += 1
            continue

        category = await _find_contract_category(session, category_code)
        if not category:
            errors.append(ImportRowError(row=excel_row, column="Mã loại hợp đồng", message=f"Không tìm thấy loại hợp đồng với mã '{category_code}'"))
            failed += 1
            continue

        # Validate document_kind matches category
        if category.document_kind != doc_kind:
            errors.append(ImportRowError(
                row=excel_row, column="Loại văn bản",
                message=f"Loại văn bản '{doc_kind}' không khớp với loại HĐ '{category_code}' (phải là '{category.document_kind}')"
            ))
            failed += 1
            continue

        # Check contract_number unique
        existing = await session.execute(
            select(EmployeeContract).where(EmployeeContract.contract_number == contract_num)
        )
        if existing.scalar_one_or_none():
            errors.append(ImportRowError(row=excel_row, column="Số hợp đồng", message=f"Số hợp đồng '{contract_num}' đã tồn tại"))
            failed += 1
            continue

        # ── Create ────────────────────────────────────────────────────
        try:
            contract = EmployeeContract(
                employee_id=employee.id,
                contract_category_id=category.id,
                document_kind=category.document_kind,
                contract_number=contract_num,
                signed_date=signed_date,
                effective_from=effective_from,
                effective_to=effective_to,
                insurance_salary=insurance_salary,
                status="active",
            )
            session.add(contract)
            await session.flush()
            created_ids.append(contract.id)
            success += 1
        except IntegrityError:
            await session.rollback()
            errors.append(ImportRowError(row=excel_row, column="Số hợp đồng", message=f"Số hợp đồng '{contract_num}' bị trùng (race condition)"))
            failed += 1
        except Exception as exc:
            await session.rollback()
            errors.append(ImportRowError(row=excel_row, column="—", message=f"Lỗi hệ thống: {exc}"))
            failed += 1

    await session.commit()
    return ImportResult(total=total, success=success, failed=failed, errors=errors, created_ids=created_ids)
