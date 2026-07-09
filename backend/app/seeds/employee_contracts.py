"""Seeder hợp đồng cho các nhân viên mẫu để đảm bảo dữ liệu đầy đủ."""

import datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.employee_contract_service import _sync_employee_insurance_profile_from_contracts


def _d(s: str | None) -> datetime.date | None:
    if not s:
        return None
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


def add_months(sourcedate: datetime.date, months: int) -> datetime.date:
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(
        sourcedate.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return datetime.date(year, month, day)


# (employee_seq, contract_category_code, term_months, status, insurance_salary)
CONTRACTS_DATA = [
    (1, "labor_indefinite", None, "active", Decimal("15000000")),
    (2, "labor_indefinite", None, "active", Decimal("12000000")),
    (3, "labor_definite", 12, "active", Decimal("18000000")),
    (4, "labor_definite", 12, "active", Decimal("14000000")),
    (5, "labor_indefinite", None, "active", Decimal("20000000")),
    (6, "labor_definite", 24, "active", Decimal("13000000")),
    (7, "probation_agreement", 2, "active", Decimal("8000000")),
    (8, "probation_agreement", 2, "active", Decimal("7500000")),
    (9, "probation_agreement", 2, "active", Decimal("9000000")),
    (10, "labor_definite", 24, "expired", Decimal("11000000")),
    (11, "labor_indefinite", None, "active", Decimal("16500000")),
    (12, "labor_definite", 12, "active", Decimal("12500000")),
    (13, "labor_indefinite", None, "active", Decimal("17000000")),
    (19, "labor_indefinite", None, "active", Decimal("11800000")),
    (20, "labor_indefinite", None, "active", Decimal("12600000")),
    (21, "labor_indefinite", None, "active", Decimal("13400000")),
    (22, "labor_indefinite", None, "active", Decimal("12800000")),
    (23, "labor_indefinite", None, "active", Decimal("13600000")),
    (24, "labor_indefinite", None, "active", Decimal("12400000")),
    (25, "labor_definite", 24, "expired", Decimal("11900000")),
    (26, "labor_definite", 36, "expired", Decimal("13100000")),
    (27, "labor_definite", 24, "expired", Decimal("12200000")),
    (28, "labor_definite", 48, "expired", Decimal("12900000")),
    (29, "labor_indefinite", None, "active", Decimal("14100000")),
    (30, "labor_definite", 36, "expired", Decimal("12700000")),
]


async def seed_sample_contracts(session: AsyncSession) -> int:
    added = 0
    # Lấy admin user làm người tạo
    admin_row = await session.execute(
        text("SELECT id FROM users WHERE email = 'admin@hrms.local'")
    )
    admin_id = admin_row.scalar() or 1

    for seq, cat_code, term_months, status, salary in CONTRACTS_DATA:
        # Lấy employee info
        emp_row = await session.execute(
            text("SELECT id, start_date FROM employees WHERE employee_seq = :seq"),
            {"seq": seq},
        )
        emp = emp_row.fetchone()
        if not emp:
            continue
        emp_id, start_date = emp

        # Lấy contract category info
        cat_row = await session.execute(
            text("SELECT id, document_kind FROM contract_categories WHERE code = :code"),
            {"code": cat_code},
        )
        cat = cat_row.fetchone()
        if not cat:
            continue
        cat_id, doc_kind = cat

        contract_number = f"HD-SAMPLE-{seq:03d}"

        # Tính toán ngày
        effective_from = start_date
        signed_date = start_date - datetime.timedelta(days=5)
        effective_to = add_months(effective_from, term_months) if term_months else None

        # Kiểm tra sự tồn tại của hợp đồng
        existing = await session.execute(
            text("SELECT id FROM employee_contracts WHERE contract_number = :contract_number"),
            {"contract_number": contract_number},
        )
        if existing.scalar():
            # Cập nhật nếu đã có
            await session.execute(
                text(
                    """
                    UPDATE employee_contracts
                    SET employee_id = :employee_id,
                        contract_category_id = :contract_category_id,
                        document_kind = :document_kind,
                        signed_date = :signed_date,
                        effective_from = :effective_from,
                        effective_to = :effective_to,
                        insurance_salary = :insurance_salary,
                        status = :status,
                        updated_at = NOW()
                    WHERE contract_number = :contract_number
                    """
                ),
                {
                    "employee_id": emp_id,
                    "contract_category_id": cat_id,
                    "document_kind": doc_kind,
                    "signed_date": signed_date,
                    "effective_from": effective_from,
                    "effective_to": effective_to,
                    "insurance_salary": salary,
                    "status": status,
                    "contract_number": contract_number,
                },
            )
        else:
            # Thêm mới
            await session.execute(
                text(
                    """
                    INSERT INTO employee_contracts (
                        employee_id, contract_category_id, document_kind, contract_number,
                        signed_date, effective_from, effective_to, insurance_salary,
                        insurance_salary_mode, status, created_by, created_at
                    ) VALUES (
                        :employee_id, :contract_category_id, :document_kind, :contract_number,
                        :signed_date, :effective_from, :effective_to, :insurance_salary,
                        'fixed_manual', :status, :created_by, NOW()
                    )
                    """
                ),
                {
                    "employee_id": emp_id,
                    "contract_category_id": cat_id,
                    "document_kind": doc_kind,
                    "contract_number": contract_number,
                    "signed_date": signed_date,
                    "effective_from": effective_from,
                    "effective_to": effective_to,
                    "insurance_salary": salary,
                    "status": status,
                    "created_by": admin_id,
                },
            )
            added += 1

        # Đồng bộ hóa bảo hiểm cho nhân sự này
        await _sync_employee_insurance_profile_from_contracts(session, emp_id)

    return added
