"""Seed dữ liệu nhân viên mẫu — chỉ dùng trên môi trường dev/test.

Idempotent: dùng ON CONFLICT (employee_seq) DO NOTHING.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.administrative_import_service import normalize_text


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _n(v: str) -> str:
    return normalize_text(v)


# 10 nhân viên mẫu — đa dạng trạng thái, giới tính
SAMPLE_EMPLOYEES = [
    {
        "employee_seq": 1,
        "full_name": "Nguyễn Văn An",
        "last_name": "Nguyễn",
        "first_name": "Văn An",
        "date_of_birth": "1988-03-15",
        "gender": "male",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "001088123456",
        "id_issued_on": "2021-06-15",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234001",
        "personal_email": "nguyenvanan@gmail.com",
        "personal_tax_code": "8801234001",
        "start_date": "2024-01-15",
        "status": "official",
        "bank_account_number": "0001234001234",
        "bank_code": "VCB",
        "account_name": "NGUYEN VAN AN",
    },
    {
        "employee_seq": 2,
        "full_name": "Trần Thị Bình",
        "last_name": "Trần",
        "first_name": "Thị Bình",
        "date_of_birth": "1992-07-22",
        "gender": "female",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "038092456789",
        "id_issued_on": "2022-01-10",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234002",
        "personal_email": "tranthibinh@gmail.com",
        "personal_tax_code": "8801234002",
        "start_date": "2024-03-01",
        "status": "official",
        "bank_account_number": "0002234001234",
        "bank_code": "BIDV",
        "account_name": "TRAN THI BINH",
    },
    {
        "employee_seq": 3,
        "full_name": "Lê Văn Cường",
        "last_name": "Lê",
        "first_name": "Văn Cường",
        "date_of_birth": "1985-11-08",
        "gender": "male",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "001085654321",
        "id_issued_on": "2021-03-20",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234003",
        "personal_email": "levancuong@gmail.com",
        "personal_tax_code": "8801234003",
        "start_date": "2024-06-15",
        "status": "official",
        "bank_account_number": "0003234001234",
        "bank_code": "AGRIBANK",
        "account_name": "LE VAN CUONG",
    },
    {
        "employee_seq": 4,
        "full_name": "Phạm Thị Dung",
        "last_name": "Phạm",
        "first_name": "Thị Dung",
        "date_of_birth": "1995-02-28",
        "gender": "female",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "086095789012",
        "id_issued_on": "2023-05-15",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234004",
        "personal_email": "phamthidung@gmail.com",
        "personal_tax_code": "8801234004",
        "start_date": "2024-09-01",
        "status": "official",
        "bank_account_number": "0004234001234",
        "bank_code": "TECHCOMBANK",
        "account_name": "PHAM THI DUNG",
    },
    {
        "employee_seq": 5,
        "full_name": "Hoàng Văn Em",
        "last_name": "Hoàng",
        "first_name": "Văn Em",
        "date_of_birth": "1990-09-12",
        "gender": "male",
        "nationality_code": "VN",
        "ethnicity_code": "TAY",
        "id_number": "020090345678",
        "id_issued_on": "2021-09-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234005",
        "personal_email": "hoangvanem@gmail.com",
        "personal_tax_code": "8801234005",
        "start_date": "2025-01-01",
        "status": "official",
        "bank_account_number": "0005234001234",
        "bank_code": "VIETINBANK",
        "account_name": "HOANG VAN EM",
    },
    {
        "employee_seq": 6,
        "full_name": "Ngô Thị Phương",
        "last_name": "Ngô",
        "first_name": "Thị Phương",
        "date_of_birth": "1994-05-18",
        "gender": "female",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "079094567890",
        "id_issued_on": "2022-06-20",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234006",
        "personal_email": "ngothiphuong@gmail.com",
        "personal_tax_code": "8801234006",
        "start_date": "2025-04-01",
        "status": "official",
        "bank_account_number": "0006234001234",
        "bank_code": "VCB",
        "account_name": "NGO THI PHUONG",
    },
    {
        "employee_seq": 7,
        "full_name": "Đỗ Văn Giang",
        "last_name": "Đỗ",
        "first_name": "Văn Giang",
        "date_of_birth": "1999-12-03",
        "gender": "male",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "036099678901",
        "id_issued_on": "2023-12-10",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234007",
        "personal_email": "dovangiang@gmail.com",
        "personal_tax_code": None,
        "start_date": "2025-11-01",
        "status": "probation",
        "bank_account_number": "0007234001234",
        "bank_code": "BIDV",
        "account_name": "DO VAN GIANG",
    },
    {
        "employee_seq": 8,
        "full_name": "Vũ Thị Hoa",
        "last_name": "Vũ",
        "first_name": "Thị Hoa",
        "date_of_birth": "2001-04-25",
        "gender": "female",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "001201789012",
        "id_issued_on": "2023-04-30",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234008",
        "personal_email": "vuthihoa@gmail.com",
        "personal_tax_code": None,
        "start_date": "2026-03-01",
        "status": "probation",
        "bank_account_number": "0008234001234",
        "bank_code": "AGRIBANK",
        "account_name": "VU THI HOA",
    },
    {
        "employee_seq": 9,
        "full_name": "Bùi Văn Ích",
        "last_name": "Bùi",
        "first_name": "Văn Ích",
        "date_of_birth": "1998-08-10",
        "gender": "male",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "051098890123",
        "id_issued_on": "2022-08-15",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234009",
        "personal_email": "buivanych@gmail.com",
        "personal_tax_code": None,
        "start_date": "2026-04-15",
        "status": "probation",
        "bank_account_number": "0009234001234",
        "bank_code": "TECHCOMBANK",
        "account_name": "BUI VAN ICH",
    },
    {
        "employee_seq": 10,
        "full_name": "Trịnh Thị Kim",
        "last_name": "Trịnh",
        "first_name": "Thị Kim",
        "date_of_birth": "1987-06-30",
        "gender": "female",
        "nationality_code": "VN",
        "ethnicity_code": "KINH",
        "id_number": "025087901234",
        "id_issued_on": "2021-07-05",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ và DLQGVDC",
        "phone_number": "0901234010",
        "personal_email": "trinhthikim@gmail.com",
        "personal_tax_code": "8801234010",
        "start_date": "2023-06-01",
        "status": "resigned",
        "resigned_date": "2025-12-31",
        "bank_account_number": "0010234001234",
        "bank_code": "VCB",
        "account_name": "TRINH THI KIM",
    },
]


async def seed_sample_employees(session: AsyncSession) -> int:
    """Seed 10 nhân viên mẫu. Idempotent — bỏ qua nếu employee_seq đã tồn tại."""
    added = 0
    for emp in SAMPLE_EMPLOYEES:
        result = await session.execute(
            text("""
                INSERT INTO employees (
                    employee_seq, full_name, normalized_name, last_name, first_name,
                    date_of_birth, gender, nationality_id, ethnicity_id,
                    id_number, id_issued_on, id_issued_by,
                    phone_number, personal_email, personal_tax_code,
                    status, start_date, resigned_date,
                    is_active, created_at
                )
                SELECT
                    :employee_seq, :full_name, :normalized_name, :last_name, :first_name,
                    :date_of_birth, :gender,
                    (SELECT id FROM nationalities WHERE code = :nationality_code),
                    (SELECT id FROM ethnicities WHERE code = :ethnicity_code),
                    :id_number, :id_issued_on, :id_issued_by,
                    :phone_number, :personal_email, :personal_tax_code,
                    :status, :start_date, :resigned_date,
                    true, now()
                ON CONFLICT (employee_seq) DO NOTHING
            """),
            {
                "employee_seq": emp["employee_seq"],
                "full_name": emp["full_name"],
                "normalized_name": _n(emp["full_name"]),
                "last_name": emp["last_name"],
                "first_name": emp["first_name"],
                "date_of_birth": _d(emp["date_of_birth"]),
                "gender": emp["gender"],
                "nationality_code": emp["nationality_code"],
                "ethnicity_code": emp["ethnicity_code"],
                "id_number": emp["id_number"],
                "id_issued_on": _d(emp["id_issued_on"]),
                "id_issued_by": emp["id_issued_by"],
                "phone_number": emp.get("phone_number"),
                "personal_email": emp.get("personal_email"),
                "personal_tax_code": emp.get("personal_tax_code"),
                "status": emp["status"],
                "start_date": _d(emp["start_date"]),
                "resigned_date": _d(emp.get("resigned_date")),
            },
        )
        added += result.rowcount

        # Thêm tài khoản ngân hàng nếu employee vừa được insert
        if result.rowcount > 0:
            await session.execute(
                text("""
                    INSERT INTO employee_bank_accounts (
                        employee_id, bank_id, account_number, account_name, is_primary, is_active, created_at
                    )
                    SELECT
                        e.id,
                        (SELECT id FROM banks WHERE code = :bank_code),
                        :account_number, :account_name, true, true, now()
                    FROM employees e WHERE e.employee_seq = :employee_seq
                    ON CONFLICT DO NOTHING
                """),
                {
                    "employee_seq": emp["employee_seq"],
                    "bank_code": emp["bank_code"],
                    "account_number": emp["bank_account_number"],
                    "account_name": emp["account_name"],
                },
            )

    return added
