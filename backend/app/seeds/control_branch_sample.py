"""Seed dữ liệu domain mẫu cho 5 nhân sự nhánh Kiểm soát.

Mục tiêu:
  - Có 5 nhân sự thật ở KS / KSNB / IT
  - Mỗi người đều có dữ liệu chéo module:
    hợp đồng, nghỉ phép, BHXH, lương BHXH, khen thưởng/kỷ luật,
    đào tạo, KPI, đánh giá cuối năm, tuyển dụng

Seeder idempotent theo khóa nghiệp vụ riêng của từng bảng.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salary import BhxhPositionGroup
from app.schemas.employee_contract import ContractCreate
from app.services.employee_contract_service import create_contract


@dataclass(frozen=True)
class ControlEmployeeSeed:
    id_number: str
    employee_seq: int
    full_name: str
    department_code: str
    job_title_code: str
    job_position_code: str
    join_date: date
    contract_category_code: str
    insurance_mode: str
    bhxh_group_code: str | None
    insurance_grade_no: int | None
    insurance_fixed_amount: Decimal | None
    probation_salary: Decimal
    official_salary: Decimal
    reward_type_code: str
    reward_title: str
    reward_value: Decimal | None
    discipline_title: str
    training_course_code: str
    recruitment_channel_code: str


CONTROL_EMPLOYEES: list[ControlEmployeeSeed] = [
    ControlEmployeeSeed(
        id_number="079086444444",
        employee_seq=14,
        full_name="Tạ Quốc Minh",
        department_code="KS",
        job_title_code="TP",
        job_position_code="TP_KSNB",
        join_date=date(2022, 1, 10),
        contract_category_code="labor_indefinite",
        insurance_mode="computed_by_position_group",
        bhxh_group_code="PROD_MANAGER",
        insurance_grade_no=4,
        insurance_fixed_amount=None,
        probation_salary=Decimal("13500000"),
        official_salary=Decimal("16800000"),
        reward_type_code="SAMPLE_KS_MONETARY",
        reward_title="Thưởng hoàn thành dự án kiểm soát nội bộ",
        reward_value=Decimal("3000000"),
        discipline_title="Nhắc nhở quy trình phê duyệt chứng từ",
        training_course_code="SAMPLE_KS_AUDIT",
        recruitment_channel_code="SAMPLE_KS_REFERRAL",
    ),
    ControlEmployeeSeed(
        id_number="079091555555",
        employee_seq=15,
        full_name="Nguyễn Thị Lan",
        department_code="KSNB",
        job_title_code="TBP",
        job_position_code="TN_KSNB",
        join_date=date(2022, 3, 1),
        contract_category_code="labor_indefinite",
        insurance_mode="computed_by_position_group",
        bhxh_group_code="SUPERVISOR",
        insurance_grade_no=3,
        insurance_fixed_amount=None,
        probation_salary=Decimal("10200000"),
        official_salary=Decimal("12800000"),
        reward_type_code="SAMPLE_KS_NON_MONEY",
        reward_title="Biểu dương kiểm soát tuân thủ định kỳ",
        reward_value=None,
        discipline_title="Nhắc nhở chậm cập nhật checklist kiểm soát",
        training_course_code="SAMPLE_KS_COMPLIANCE",
        recruitment_channel_code="SAMPLE_KS_TOPCV",
    ),
    ControlEmployeeSeed(
        id_number="079093666666",
        employee_seq=16,
        full_name="Phạm Đức Hòa",
        department_code="KSNB",
        job_title_code="NV",
        job_position_code="NV_KSNB",
        join_date=date(2022, 6, 15),
        contract_category_code="labor_definite",
        insurance_mode="fixed_manual",
        bhxh_group_code=None,
        insurance_grade_no=None,
        insurance_fixed_amount=Decimal("9200000"),
        probation_salary=Decimal("8200000"),
        official_salary=Decimal("9400000"),
        reward_type_code="SAMPLE_KS_NON_MONEY",
        reward_title="Biểu dương hoàn tất kiểm tra kho đột xuất",
        reward_value=None,
        discipline_title="Nhắc nhở lưu hồ sơ kiểm tra chưa đúng mẫu",
        training_course_code="SAMPLE_KS_COMPLIANCE",
        recruitment_channel_code="SAMPLE_KS_TOPCV",
    ),
    ControlEmployeeSeed(
        id_number="079094777777",
        employee_seq=17,
        full_name="Lê Minh Trang",
        department_code="IT",
        job_title_code="NVKT",
        job_position_code="CV_IT",
        join_date=date(2023, 2, 6),
        contract_category_code="labor_indefinite",
        insurance_mode="computed_by_position_group",
        bhxh_group_code="TECH_SPECIALIST",
        insurance_grade_no=2,
        insurance_fixed_amount=None,
        probation_salary=Decimal("11800000"),
        official_salary=Decimal("14500000"),
        reward_type_code="SAMPLE_KS_MONETARY",
        reward_title="Thưởng xử lý sự cố hệ thống kiểm soát",
        reward_value=Decimal("2500000"),
        discipline_title="Nhắc nhở chậm đóng ticket bảo trì",
        training_course_code="SAMPLE_KS_ITSEC",
        recruitment_channel_code="SAMPLE_KS_REFERRAL",
    ),
    ControlEmployeeSeed(
        id_number="079096888888",
        employee_seq=18,
        full_name="Vũ Hoàng Sơn",
        department_code="IT",
        job_title_code="NV",
        job_position_code="NV_IT",
        join_date=date(2023, 5, 8),
        contract_category_code="labor_definite",
        insurance_mode="fixed_manual",
        bhxh_group_code=None,
        insurance_grade_no=None,
        insurance_fixed_amount=Decimal("7600000"),
        probation_salary=Decimal("7200000"),
        official_salary=Decimal("8300000"),
        reward_type_code="SAMPLE_KS_NON_MONEY",
        reward_title="Biểu dương hỗ trợ vận hành mạng nội bộ",
        reward_value=None,
        discipline_title="Nhắc nhở bàn giao ca trực chưa đầy đủ",
        training_course_code="SAMPLE_KS_ITSEC",
        recruitment_channel_code="SAMPLE_KS_INTERNAL",
    ),
]


async def _scalar(session: AsyncSession, sql: str, **params):
    return (await session.execute(text(sql), params)).scalar()


async def _fetchone(session: AsyncSession, sql: str, **params):
    return (await session.execute(text(sql), params)).fetchone()


async def _get_employee_id_by_seq(session: AsyncSession, employee_seq: int) -> int:
    row = await _fetchone(
        session,
        "SELECT id FROM employees WHERE employee_seq = :employee_seq",
        employee_seq=employee_seq,
    )
    if not row:
        raise RuntimeError(f"Không tìm thấy employee seed seq={employee_seq}")
    return row[0]


async def _get_user_id_by_email(session: AsyncSession, email: str) -> int:
    row = await _fetchone(session, "SELECT id FROM users WHERE email = :email", email=email)
    if not row:
        raise RuntimeError(f"Không tìm thấy user '{email}' để seed created_by_id")
    return row[0]


async def _get_department_id(session: AsyncSession, code: str) -> int:
    row = await _fetchone(session, "SELECT id FROM departments WHERE code = :code", code=code)
    if not row:
        raise RuntimeError(f"Không tìm thấy phòng ban '{code}'")
    return row[0]


async def _get_job_position_id(session: AsyncSession, code: str) -> int:
    row = await _fetchone(session, "SELECT id FROM job_positions WHERE code = :code", code=code)
    if not row:
        raise RuntimeError(f"Không tìm thấy vị trí '{code}'")
    return row[0]


async def _get_job_title_id(session: AsyncSession, code: str) -> int:
    row = await _fetchone(session, "SELECT id FROM job_titles WHERE code = :code", code=code)
    if not row:
        raise RuntimeError(f"Không tìm thấy chức danh '{code}'")
    return row[0]


async def _get_contract_category_id(session: AsyncSession, code: str) -> int:
    row = await _fetchone(session, "SELECT id FROM contract_categories WHERE code = :code", code=code)
    if not row:
        raise RuntimeError(f"Không tìm thấy loại hợp đồng '{code}'")
    return row[0]


async def _get_bhxh_group_id(session: AsyncSession, code: str) -> int:
    row = await _fetchone(session, "SELECT id FROM bhxh_position_groups WHERE code = :code", code=code)
    if not row:
        raise RuntimeError(f"Không tìm thấy nhóm vị trí BHXH '{code}'")
    return row[0]


async def _get_leave_type_id(session: AsyncSession, code: str) -> int:
    row = await _fetchone(session, "SELECT id FROM leave_types WHERE code = :code", code=code)
    if not row:
        raise RuntimeError(f"Không tìm thấy loại phép '{code}'")
    return row[0]


async def _get_active_policy_snapshot(session: AsyncSession) -> tuple[int | None, str | None, Decimal, Decimal]:
    policy_row = await _fetchone(
        session,
        """
        SELECT id, code
        FROM insurance_policy_versions
        WHERE is_active = TRUE
        ORDER BY effective_from DESC, id DESC
        LIMIT 1
        """,
    )
    if not policy_row:
        return None, None, Decimal("0"), Decimal("0")
    policy_id = policy_row[0]
    policy_code = policy_row[1]
    rates_row = await _fetchone(
        session,
        """
        SELECT
            COALESCE(SUM(employee_rate_percent), 0),
            COALESCE(SUM(employer_rate_percent), 0)
        FROM insurance_policy_component_rates
        WHERE policy_version_id = :policy_id
          AND is_active = TRUE
        """,
        policy_id=policy_id,
    )
    return (
        policy_id,
        policy_code,
        Decimal(str(rates_row[0])),
        Decimal(str(rates_row[1])),
    )


async def _ensure_reward_types(session: AsyncSession) -> int:
    rows = [
        ("SAMPLE_KS_MONETARY", "Thưởng mẫu nhánh Kiểm soát", True, 901),
        ("SAMPLE_KS_NON_MONEY", "Ghi nhận mẫu nhánh Kiểm soát", False, 902),
    ]
    added = 0
    for code, name, is_monetary, sort_order in rows:
        result = await session.execute(
            text(
                """
                INSERT INTO reward_types (code, name, is_monetary, sort_order, is_active, created_at)
                VALUES (:code, :name, :is_monetary, :sort_order, TRUE, NOW())
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "code": code,
                "name": name,
                "is_monetary": is_monetary,
                "sort_order": sort_order,
            },
        )
        added += result.rowcount
    return added


async def _ensure_training_catalog(session: AsyncSession, admin_user_id: int) -> tuple[int, int, int]:
    course_rows = [
        ("SAMPLE_KS_AUDIT", "Kiểm soát nội bộ nâng cao", "noi_bo", 16, "Khối Nhân sự"),
        ("SAMPLE_KS_COMPLIANCE", "Tuân thủ hồ sơ và bằng chứng kiểm soát", "online", 8, "Khối Nhân sự"),
        ("SAMPLE_KS_ITSEC", "An toàn hệ thống phục vụ kiểm soát", "ben_ngoai", 12, "Phòng IT"),
    ]
    course_added = 0
    for code, name, course_type, duration_hours, organizer in course_rows:
        result = await session.execute(
            text(
                """
                INSERT INTO training_courses (
                    code, name, course_type, duration_hours, organizer,
                    description, is_mandatory, is_active, created_at, updated_at
                )
                VALUES (
                    :code, :name, :course_type, :duration_hours, :organizer,
                    :description, TRUE, TRUE, NOW(), NOW()
                )
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "code": code,
                "name": name,
                "course_type": course_type,
                "duration_hours": duration_hours,
                "organizer": organizer,
                "description": f"Khóa học mẫu seed cho {name}",
            },
        )
        course_added += result.rowcount

    plan_added = 0
    result = await session.execute(
        text(
            """
            INSERT INTO training_plans (
                title, year, quarter, department_id, description, status,
                created_by_id, created_at, updated_at
            )
            SELECT
                :insert_title, 2026, 2,
                d.id,
                :description,
                'approved',
                :created_by_id,
                NOW(),
                NOW()
            FROM departments d
            WHERE d.code = 'KS'
              AND NOT EXISTS (
                  SELECT 1
                  FROM training_plans tp
                  WHERE tp.title = :exists_title
              )
            """
        ),
        {
            "insert_title": "Kế hoạch đào tạo mẫu nhánh Kiểm soát 2026",
            "exists_title": "Kế hoạch đào tạo mẫu nhánh Kiểm soát 2026",
            "description": "Kế hoạch đào tạo mẫu phục vụ demo dữ liệu nhiều module",
            "created_by_id": admin_user_id,
        },
    )
    plan_added += result.rowcount

    plan_course_added = 0
    for code in [row[0] for row in course_rows]:
        result = await session.execute(
            text(
                """
                INSERT INTO training_plan_courses (
                    plan_id, course_id, target_count, scheduled_date, note, created_at
                )
                SELECT
                    tp.id,
                    tc.id,
                    5,
                    :scheduled_date,
                    :note,
                    NOW()
                FROM training_plans tp
                JOIN training_courses tc ON tc.code = :course_code
                WHERE tp.title = :plan_title
                  AND NOT EXISTS (
                      SELECT 1
                      FROM training_plan_courses tpc
                      WHERE tpc.plan_id = tp.id
                        AND tpc.course_id = tc.id
                  )
                """
            ),
            {
                "course_code": code,
                "plan_title": "Kế hoạch đào tạo mẫu nhánh Kiểm soát 2026",
                "scheduled_date": date(2026, 7, 15),
                "note": "Dòng kế hoạch đào tạo mẫu",
            },
        )
        plan_course_added += result.rowcount

    return course_added, plan_added, plan_course_added


async def _ensure_recruitment_channels(session: AsyncSession) -> int:
    rows = [
        ("SAMPLE_KS_REFERRAL", "Giới thiệu nội bộ - Nhánh Kiểm soát", 901),
        ("SAMPLE_KS_TOPCV", "TopCV - Nhánh Kiểm soát", 902),
        ("SAMPLE_KS_INTERNAL", "Nguồn nội bộ - Nhánh Kiểm soát", 903),
    ]
    added = 0
    for code, name, sort_order in rows:
        result = await session.execute(
            text(
                """
                INSERT INTO recruitment_channels (code, name, is_active, sort_order)
                VALUES (:code, :name, TRUE, :sort_order)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"code": code, "name": name, "sort_order": sort_order},
        )
        added += result.rowcount
    return added


async def _ensure_contract_for_employee(
    session: AsyncSession,
    employee_id: int,
    employee: ControlEmployeeSeed,
    created_by_id: int,
) -> int:
    contract_number = f"KS-SAMPLE-{employee.employee_seq:03d}"
    exists = await _scalar(
        session,
        "SELECT COUNT(*) FROM employee_contracts WHERE contract_number = :contract_number",
        contract_number=contract_number,
    )
    if exists:
        return 0

    payload = ContractCreate(
        contract_category_id=await _get_contract_category_id(session, employee.contract_category_code),
        contract_number=contract_number,
        signed_date=employee.join_date,
        effective_from=employee.join_date,
        effective_to=None if employee.contract_category_code == "labor_indefinite" else employee.join_date.replace(year=employee.join_date.year + 3),
        insurance_salary_mode=employee.insurance_mode,
        bhxh_position_group_id=(
            await _get_bhxh_group_id(session, employee.bhxh_group_code)
            if employee.bhxh_group_code
            else None
        ),
        insurance_salary_grade_no=employee.insurance_grade_no,
        bhxh_seniority_start_date=employee.join_date,
        insurance_salary_fixed_amount=employee.insurance_fixed_amount,
        insurance_salary=employee.insurance_fixed_amount,
        notes="Hợp đồng mẫu nhánh Kiểm soát",
    )
    await create_contract(session, employee_id, payload, created_by=created_by_id)
    return 1


async def _ensure_insurance_profile_and_change(
    session: AsyncSession,
    employee_id: int,
    employee: ControlEmployeeSeed,
    created_by_id: int,
) -> tuple[int, int]:
    policy_id, policy_code, employee_rate_total, employer_rate_total = await _get_active_policy_snapshot(session)
    contract_row = await _fetchone(
        session,
        """
        SELECT ec.contract_number, ec.insurance_salary, ec.effective_from, ec.effective_to,
               ec.document_kind AS contract_type_code
        FROM employee_contracts ec
        WHERE ec.employee_id = :employee_id
        ORDER BY ec.effective_from DESC, ec.id DESC
        LIMIT 1
        """,
        employee_id=employee_id,
    )
    if not contract_row:
        raise RuntimeError(f"Employee {employee.full_name} chưa có hợp đồng để seed BHXH")

    profile_updated = await session.execute(
        text(
            """
            UPDATE employee_insurance_profiles
            SET bhxh_code = :bhxh_code,
                bhyt_initial_clinic_name = :clinic_name,
                bhyt_initial_clinic_code = :clinic_code,
                company_bhxh_joined_date = :joined_date,
                participation_status = 'active',
                status_effective_from = :joined_date,
                status_note = :status_note,
                insurance_policy_version_id = :policy_id,
                updated_at = NOW()
            WHERE employee_id = :employee_id
              AND (
                  bhxh_code IS DISTINCT FROM :bhxh_code OR
                  bhyt_initial_clinic_name IS DISTINCT FROM :clinic_name OR
                  bhyt_initial_clinic_code IS DISTINCT FROM :clinic_code OR
                  company_bhxh_joined_date IS DISTINCT FROM :joined_date OR
                  participation_status IS DISTINCT FROM 'active' OR
                  status_effective_from IS DISTINCT FROM :joined_date OR
                  status_note IS DISTINCT FROM :status_note OR
                  insurance_policy_version_id IS DISTINCT FROM :policy_id
              )
            """
        ),
        {
            "employee_id": employee_id,
            "bhxh_code": f"BHXH{employee.employee_seq:06d}",
            "clinic_name": "BVĐK Tỉnh Đắk Lắk",
            "clinic_code": f"DKL{employee.employee_seq:03d}",
            "joined_date": employee.join_date,
            "status_note": "Hồ sơ BHXH mẫu nhánh Kiểm soát",
            "policy_id": policy_id,
        },
    )

    event_added = 0
    event_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM insurance_change_events
        WHERE employee_id = :employee_id
          AND contract_number_snapshot = :contract_number
          AND change_reason = 'new_hire'
        """,
        employee_id=employee_id,
        contract_number=contract_row[0],
    )
    if not event_exists:
        employee_row = await _fetchone(
            session,
            """
            SELECT full_name, date_of_birth, gender
            FROM employees
            WHERE id = :employee_id
            """,
            employee_id=employee_id,
        )
        await session.execute(
            text(
                """
                INSERT INTO insurance_change_events (
                    employee_id, change_type, change_reason, ibhxh_reason_code,
                    effective_date, period_year, period_month,
                    employee_name_snapshot, date_of_birth_snapshot, gender_snapshot,
                    nationality_code_snapshot, identity_number_snapshot,
                    contract_number_snapshot, contract_type_code_snapshot,
                    contract_signed_date_snapshot, contract_from_snapshot, contract_to_snapshot,
                    bhxh_code_snapshot, basis_amount, allowances_amount,
                    bhyt_clinic_name_snapshot, bhyt_clinic_code_snapshot,
                    policy_version_code_snapshot,
                    employee_rate_total_snapshot, employer_rate_total_snapshot,
                    old_status, new_status,
                    suggested_declaration_year, suggested_declaration_month,
                    is_manual, note, created_by_id, created_at
                )
                VALUES (
                    :employee_id, 'increase', 'new_hire', 'T-01',
                    :effective_date, :period_year, :period_month,
                    :employee_name_snapshot, :date_of_birth_snapshot, :gender_snapshot,
                    'VN', :identity_number_snapshot,
                    :contract_number_snapshot, :contract_type_code_snapshot,
                    :contract_signed_date_snapshot, :contract_from_snapshot, :contract_to_snapshot,
                    :bhxh_code_snapshot, :basis_amount, 0,
                    :clinic_name, :clinic_code,
                    :policy_code,
                    :employee_rate_total, :employer_rate_total,
                    NULL, 'active',
                    :period_year, :period_month,
                    FALSE, :note, :created_by_id, NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "effective_date": employee.join_date,
                "period_year": employee.join_date.year,
                "period_month": employee.join_date.month,
                "employee_name_snapshot": employee_row[0],
                "date_of_birth_snapshot": employee_row[1],
                "gender_snapshot": employee_row[2],
                "identity_number_snapshot": employee.id_number,
                "contract_number_snapshot": contract_row[0],
                "contract_type_code_snapshot": contract_row[4][:5] if contract_row[4] else None,
                "contract_signed_date_snapshot": employee.join_date,
                "contract_from_snapshot": contract_row[2],
                "contract_to_snapshot": contract_row[3],
                "bhxh_code_snapshot": f"BHXH{employee.employee_seq:06d}",
                "basis_amount": contract_row[1],
                "clinic_name": "BVĐK Tỉnh Đắk Lắk",
                "clinic_code": f"DKL{employee.employee_seq:03d}",
                "policy_code": policy_code,
                "employee_rate_total": employee_rate_total,
                "employer_rate_total": employer_rate_total,
                "note": "Biến động tăng BHXH mẫu khi tuyển mới",
                "created_by_id": created_by_id,
            },
        )
        event_added = 1

    return profile_updated.rowcount, event_added


async def _ensure_leave_data(session: AsyncSession, employee_id: int, employee: ControlEmployeeSeed, created_by_id: int) -> tuple[int, int]:
    leave_type_id = await _get_leave_type_id(session, "annual_leave")
    entitlement_added = 0
    entitlement_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM leave_entitlements
        WHERE employee_id = :employee_id
          AND leave_type_id = :leave_type_id
          AND year = 2026
        """,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
    )
    if not entitlement_exists:
        await session.execute(
            text(
                """
                INSERT INTO leave_entitlements (
                    employee_id, leave_type_id, year,
                    allocated_days, carryover_days, carryover_expires, used_days,
                    note, created_by_id, created_at, updated_at
                )
                VALUES (
                    :employee_id, :leave_type_id, 2026,
                    12.0, 1.0, DATE '2026-06-30', 2.0,
                    :note, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "leave_type_id": leave_type_id,
                "note": "Cấp phép mẫu cho nhân sự nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        entitlement_added = 1

    record_added = 0
    record_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM leave_records
        WHERE employee_id = :employee_id
          AND leave_type_id = :leave_type_id
          AND start_date = DATE '2026-04-14'
          AND end_date = DATE '2026-04-15'
        """,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
    )
    if not record_exists:
        entitlement_id = await _scalar(
            session,
            """
            SELECT id
            FROM leave_entitlements
            WHERE employee_id = :employee_id
              AND leave_type_id = :leave_type_id
              AND year = 2026
            LIMIT 1
            """,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
        )
        await session.execute(
            text(
                """
                INSERT INTO leave_records (
                    employee_id, leave_type_id, entitlement_id,
                    start_date, end_date, total_days,
                    reason, status, note, created_by_id, created_at, updated_at
                )
                VALUES (
                    :employee_id, :leave_type_id, :entitlement_id,
                    DATE '2026-04-14', DATE '2026-04-15', 2.0,
                    :reason, 'active', :note, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "leave_type_id": leave_type_id,
                "entitlement_id": entitlement_id,
                "reason": "Nghỉ phép năm mẫu để demo báo cáo",
                "note": "Leave record mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        record_added = 1

    return entitlement_added, record_added


async def _ensure_reward_and_discipline(
    session: AsyncSession,
    employee_id: int,
    employee: ControlEmployeeSeed,
    created_by_id: int,
) -> tuple[int, int]:
    reward_type_id = await _scalar(
        session,
        "SELECT id FROM reward_types WHERE code = :code",
        code=employee.reward_type_code,
    )
    reward_added = 0
    reward_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM employee_rewards
        WHERE employee_id = :employee_id
          AND title = :title
        """,
        employee_id=employee_id,
        title=employee.reward_title,
    )
    if not reward_exists:
        await session.execute(
            text(
                """
                INSERT INTO employee_rewards (
                    employee_id, reward_type_id, title, description, reward_date,
                    decision_number, issued_by, value, note, created_by_id, created_at, updated_at
                )
                VALUES (
                    :employee_id, :reward_type_id, :title, :description, DATE '2026-05-10',
                    :decision_number, :issued_by, :value, :note, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "reward_type_id": reward_type_id,
                "title": employee.reward_title,
                "description": "Dữ liệu khen thưởng mẫu để demo báo cáo và lịch sử nhân sự",
                "decision_number": f"KT-KS-{employee.employee_seq:03d}",
                "issued_by": "Ban Tổng giám đốc",
                "value": employee.reward_value,
                "note": "Khen thưởng mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        reward_added = 1

    discipline_added = 0
    discipline_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM employee_disciplines
        WHERE employee_id = :employee_id
          AND title = :title
        """,
        employee_id=employee_id,
        title=employee.discipline_title,
    )
    if not discipline_exists:
        await session.execute(
            text(
                """
                INSERT INTO employee_disciplines (
                    employee_id, discipline_form, violation_date, effective_date,
                    end_date, extended_months, title, description,
                    decision_number, issued_by, note,
                    created_by_id, created_at, updated_at
                )
                VALUES (
                    :employee_id, 'khien_trach', DATE '2026-03-20', DATE '2026-03-25',
                    NULL, NULL, :title, :description,
                    :decision_number, :issued_by, :note,
                    :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "title": employee.discipline_title,
                "description": "Kỷ luật mẫu mức khiển trách để demo lịch sử nhân sự",
                "decision_number": f"KL-KS-{employee.employee_seq:03d}",
                "issued_by": "Giám đốc khối kiểm soát",
                "note": "Kỷ luật mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        discipline_added = 1

    return reward_added, discipline_added


async def _ensure_training_data(
    session: AsyncSession,
    employee_id: int,
    employee: ControlEmployeeSeed,
    created_by_id: int,
) -> tuple[int, int]:
    record_added = 0
    record_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM employee_training_records etr
        JOIN training_courses tc ON tc.id = etr.course_id
        WHERE etr.employee_id = :employee_id
          AND tc.code = :course_code
        """,
        employee_id=employee_id,
        course_code=employee.training_course_code,
    )
    if not record_exists:
        await session.execute(
            text(
                """
                INSERT INTO employee_training_records (
                    employee_id, course_id, plan_id, status, result, score,
                    start_date, end_date, note, created_by_id, created_at, updated_at
                )
                SELECT
                    :employee_id,
                    tc.id,
                    tp.id,
                    'hoan_thanh',
                    'dat',
                    88.50,
                    DATE '2026-06-10',
                    DATE '2026-06-12',
                    :note,
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM training_courses tc
                LEFT JOIN training_plans tp ON tp.title = :plan_title
                WHERE tc.code = :course_code
                """
            ),
            {
                "employee_id": employee_id,
                "course_code": employee.training_course_code,
                "plan_title": "Kế hoạch đào tạo mẫu nhánh Kiểm soát 2026",
                "note": "Training record mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        record_added = 1

    certificate_added = 0
    certificate_name = f"Chứng nhận {employee.training_course_code}"
    certificate_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM employee_training_certificates
        WHERE employee_id = :employee_id
          AND certificate_name = :certificate_name
        """,
        employee_id=employee_id,
        certificate_name=certificate_name,
    )
    if not certificate_exists:
        await session.execute(
            text(
                """
                INSERT INTO employee_training_certificates (
                    employee_id, certificate_name, issuing_organization, issued_date,
                    expiry_date, related_course_id, note,
                    created_by_id, created_at, updated_at
                )
                SELECT
                    :employee_id,
                    :certificate_name,
                    :issuing_organization,
                    DATE '2026-06-12',
                    DATE '2028-06-12',
                    tc.id,
                    :note,
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM training_courses tc
                WHERE tc.code = :course_code
                """
            ),
            {
                "employee_id": employee_id,
                "certificate_name": certificate_name,
                "issuing_organization": "Trung tâm đào tạo nội bộ",
                "note": "Chứng chỉ đào tạo mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
                "course_code": employee.training_course_code,
            },
        )
        certificate_added = 1

    return record_added, certificate_added


async def _ensure_performance_data(session: AsyncSession, employee_id: int, created_by_id: int) -> tuple[int, int]:
    kpi_months = [(2026, 1, Decimal("88")), (2026, 2, Decimal("91")), (2026, 3, Decimal("93"))]
    kpi_added = 0
    for year, month, score in kpi_months:
        exists = await _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM employee_kpi_monthly
            WHERE employee_id = :employee_id
              AND year = :year
              AND month = :month
            """,
            employee_id=employee_id,
            year=year,
            month=month,
        )
        if exists:
            continue
        await session.execute(
            text(
                """
                INSERT INTO employee_kpi_monthly (
                    employee_id, year, month, score, note, created_by_id, created_at, updated_at
                )
                VALUES (
                    :employee_id, :year, :month, :score, :note, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "year": year,
                "month": month,
                "score": score,
                "note": "Điểm KPI mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        kpi_added += 1

    review_added = 0
    review_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM employee_yearly_reviews
        WHERE employee_id = :employee_id
          AND year = 2026
        """,
        employee_id=employee_id,
    )
    if not review_exists:
        await session.execute(
            text(
                """
                INSERT INTO employee_yearly_reviews (
                    employee_id, year, rating, review_note, created_by_id, created_at, updated_at
                )
                VALUES (
                    :employee_id, 2026, 'dat', :review_note, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "employee_id": employee_id,
                "review_note": "Đánh giá cuối năm mẫu cho nhân sự nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        review_added = 1

    return kpi_added, review_added


async def _ensure_recruitment_data(
    session: AsyncSession,
    employee_id: int,
    employee: ControlEmployeeSeed,
    created_by_id: int,
) -> dict[str, int]:
    department_id = await _get_department_id(session, employee.department_code)
    job_position_id = await _get_job_position_id(session, employee.job_position_code)
    job_title_id = await _get_job_title_id(session, employee.job_title_code)
    channel_id = await _scalar(
        session,
        "SELECT id FROM recruitment_channels WHERE code = :code",
        code=employee.recruitment_channel_code,
    )

    counts = {
        "headcount_plans": 0,
        "job_requisitions": 0,
        "job_postings": 0,
        "candidates": 0,
        "applications": 0,
        "pipeline_stages": 0,
        "stage_results": 0,
        "offers": 0,
        "hiring_decisions": 0,
    }

    plan_year = employee.join_date.year
    plan_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM headcount_plans
        WHERE year = :year
          AND department_id = :department_id
          AND job_position_id = :job_position_id
        """,
        year=plan_year,
        department_id=department_id,
        job_position_id=job_position_id,
    )
    if not plan_exists:
        await session.execute(
            text(
                """
                INSERT INTO headcount_plans (
                    year, department_id, job_position_id, current_count, planned_count,
                    reason, created_by_id, created_at, updated_at
                )
                VALUES (
                    :year, :department_id, :job_position_id, 0, 1,
                    :reason, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "year": plan_year,
                "department_id": department_id,
                "job_position_id": job_position_id,
                "reason": f"Kế hoạch tuyển dụng mẫu cho {employee.full_name}",
                "created_by_id": created_by_id,
            },
        )
        counts["headcount_plans"] += 1

    jr_code = f"SAMPLE-KS-JR-{employee.employee_seq:03d}"
    jr_exists = await _scalar(
        session,
        "SELECT COUNT(*) FROM job_requisitions WHERE code = :code",
        code=jr_code,
    )
    if not jr_exists:
        await session.execute(
            text(
                """
                INSERT INTO job_requisitions (
                    code, job_position_id, department_id, headcount_plan_id,
                    quantity, quantity_remaining, reason_type, deadline,
                    salary_min, salary_max, jd_description, jd_requirements,
                    status, submitted_by_id, submitted_at, approved_by_id, approved_at,
                    rejection_note, internal_note, created_by_id, created_at, updated_at
                )
                SELECT
                    :code,
                    :job_position_id,
                    :department_id,
                    hp.id,
                    1,
                    0,
                    'replacement',
                    :deadline,
                    :salary_min,
                    :salary_max,
                    :jd_description,
                    :jd_requirements,
                    'completed',
                    :created_by_id,
                    NOW(),
                    :created_by_id,
                    NOW(),
                    NULL,
                    :internal_note,
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM headcount_plans hp
                WHERE hp.year = :plan_year
                  AND hp.department_id = :department_id
                  AND hp.job_position_id = :job_position_id
                """
            ),
            {
                "code": jr_code,
                "job_position_id": job_position_id,
                "department_id": department_id,
                "deadline": employee.join_date - timedelta(days=10),
                "salary_min": employee.probation_salary,
                "salary_max": employee.official_salary,
                "jd_description": f"JR mẫu cho vị trí {employee.job_position_code}",
                "jd_requirements": "Có kinh nghiệm phù hợp và hoàn tất hồ sơ đúng quy định",
                "internal_note": "JR mẫu để liên kết dữ liệu employee - ATS",
                "created_by_id": created_by_id,
                "plan_year": plan_year,
            },
        )
        counts["job_requisitions"] += 1

    posting_title = f"Tuyển {employee.job_position_code} - mẫu"
    posting_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM job_postings
        WHERE job_requisition_id = (
            SELECT id FROM job_requisitions WHERE code = :jr_code
        )
        """,
        jr_code=jr_code,
    )
    if not posting_exists:
        await session.execute(
            text(
                """
                INSERT INTO job_postings (
                    job_requisition_id, title, description, requirements, benefits,
                    work_location, deadline, salary_display, posting_type, channels,
                    status, opened_at, closed_at, expires_at, note,
                    created_by_id, created_at, updated_at
                )
                SELECT
                    jr.id,
                    :title,
                    :description,
                    :requirements,
                    :benefits,
                    :work_location,
                    :deadline,
                    :salary_display,
                    'external',
                    ARRAY[:channel_id]::integer[],
                    'closed',
                    NOW() - INTERVAL '45 days',
                    NOW() - INTERVAL '15 days',
                    NOW() - INTERVAL '15 days',
                    :note,
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM job_requisitions jr
                WHERE jr.code = :jr_code
                """
            ),
            {
                "jr_code": jr_code,
                "title": posting_title,
                "description": f"Bài đăng tuyển dụng mẫu cho {employee.full_name}",
                "requirements": "Có kỹ năng chuyên môn và kinh nghiệm phù hợp",
                "benefits": "Đóng BHXH đầy đủ, môi trường ổn định",
                "work_location": "Đắk Lắk",
                "deadline": employee.join_date - timedelta(days=25),
                "salary_display": f"{employee.probation_salary:,.0f} - {employee.official_salary:,.0f} VND",
                "channel_id": channel_id,
                "note": "Job posting mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        counts["job_postings"] += 1

    candidate_email = f"candidate.ks.{employee.employee_seq}@example.com"
    candidate_exists = await _scalar(
        session,
        "SELECT COUNT(*) FROM candidates WHERE personal_email = :email",
        email=candidate_email,
    )
    if not candidate_exists:
        await session.execute(
            text(
                """
                INSERT INTO candidates (
                    full_name, last_name, first_name, date_of_birth, gender,
                    personal_email, phone_number, current_company, current_position,
                    expected_salary, source_channel_id, source_note, internal_note,
                    tags, is_active, created_by_id, created_at, updated_at
                )
                VALUES (
                    :full_name, :last_name, :first_name, :date_of_birth, :gender,
                    :personal_email, :phone_number, :current_company, :current_position,
                    :expected_salary, :source_channel_id, :source_note, :internal_note,
                    ARRAY['sample','control-branch']::text[],
                    TRUE, :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "full_name": f"Ứng viên {employee.full_name}",
                "last_name": "Ứng viên",
                "first_name": employee.full_name,
                "date_of_birth": employee.join_date.replace(year=employee.join_date.year - 26),
                "gender": "female" if employee.employee_seq % 2 else "male",
                "personal_email": candidate_email,
                "phone_number": f"09123{employee.employee_seq:05d}",
                "current_company": "Công ty mẫu",
                "current_position": employee.job_position_code,
                "expected_salary": employee.official_salary,
                "source_channel_id": channel_id,
                "source_note": "Ứng viên mẫu để seed ATS",
                "internal_note": "Candidate mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        counts["candidates"] += 1

    application_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM candidate_applications ca
        JOIN candidates c ON c.id = ca.candidate_id
        JOIN job_requisitions jr ON jr.id = ca.job_requisition_id
        WHERE c.personal_email = :email
          AND jr.code = :jr_code
        """,
        email=candidate_email,
        jr_code=jr_code,
    )
    if not application_exists:
        await session.execute(
            text(
                """
                INSERT INTO candidate_applications (
                    candidate_id, job_requisition_id, applied_date, source_channel_id,
                    current_stage, rejection_reason, internal_note,
                    created_by_id, created_at, updated_at
                )
                SELECT
                    c.id,
                    jr.id,
                    :applied_date,
                    :source_channel_id,
                    'hired',
                    NULL,
                    :internal_note,
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM candidates c
                CROSS JOIN job_requisitions jr
                WHERE c.personal_email = :email
                  AND jr.code = :jr_code
                """
            ),
            {
                "email": candidate_email,
                "jr_code": jr_code,
                "applied_date": employee.join_date - timedelta(days=40),
                "source_channel_id": channel_id,
                "internal_note": "Application mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        counts["applications"] += 1

    stage_defs = [
        (1, "Sàng lọc hồ sơ", "screening"),
        (2, "Phỏng vấn", "interview"),
        (3, "Vòng cuối", "final"),
    ]
    for stage_order, stage_name, stage_type in stage_defs:
        exists = await _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM pipeline_stages ps
            JOIN job_requisitions jr ON jr.id = ps.job_requisition_id
            WHERE jr.code = :jr_code
              AND ps.stage_type = :stage_type
            """,
            jr_code=jr_code,
            stage_type=stage_type,
        )
        if exists:
            continue
        await session.execute(
            text(
                """
                INSERT INTO pipeline_stages (
                    job_requisition_id, stage_order, stage_name, stage_type, is_active
                )
                SELECT
                    jr.id, :stage_order, :stage_name, :stage_type, TRUE
                FROM job_requisitions jr
                WHERE jr.code = :jr_code
                """
            ),
            {
                "jr_code": jr_code,
                "stage_order": stage_order,
                "stage_name": stage_name,
                "stage_type": stage_type,
            },
        )
        counts["pipeline_stages"] += 1

    result_defs = [
        ("screening", "pass", Decimal("85")),
        ("interview", "pass", Decimal("88")),
        ("final", "pass", Decimal("92")),
    ]
    for stage_type, result_value, score in result_defs:
        exists = await _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM candidate_stage_results csr
            JOIN pipeline_stages ps ON ps.id = csr.stage_id
            JOIN candidate_applications ca ON ca.id = csr.application_id
            JOIN candidates c ON c.id = ca.candidate_id
            WHERE c.personal_email = :email
              AND ps.stage_type = :stage_type
            """,
            email=candidate_email,
            stage_type=stage_type,
        )
        if exists:
            continue
        await session.execute(
            text(
                """
                INSERT INTO candidate_stage_results (
                    application_id, stage_id, result, score, notes,
                    evaluated_by_id, evaluated_at, created_at, updated_at
                )
                SELECT
                    ca.id,
                    ps.id,
                    :result,
                    :score,
                    :notes,
                    :evaluated_by_id,
                    NOW(),
                    NOW(),
                    NOW()
                FROM candidate_applications ca
                JOIN candidates c ON c.id = ca.candidate_id
                JOIN job_requisitions jr ON jr.id = ca.job_requisition_id
                JOIN pipeline_stages ps ON ps.job_requisition_id = jr.id
                WHERE c.personal_email = :email
                  AND jr.code = :jr_code
                  AND ps.stage_type = :stage_type
                """
            ),
            {
                "email": candidate_email,
                "jr_code": jr_code,
                "stage_type": stage_type,
                "result": result_value,
                "score": score,
                "notes": f"Kết quả mẫu stage {stage_type}",
                "evaluated_by_id": created_by_id,
            },
        )
        counts["stage_results"] += 1

    offer_exists = await _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM offers o
        JOIN candidates c ON c.id = o.candidate_id
        WHERE c.personal_email = :email
          AND o.job_requisition_id = (SELECT id FROM job_requisitions WHERE code = :jr_code)
        """,
        email=candidate_email,
        jr_code=jr_code,
    )
    if not offer_exists:
        await session.execute(
            text(
                """
                INSERT INTO offers (
                    application_id, candidate_id, job_requisition_id, job_position_id, department_id,
                    proposed_start_date, probation_salary, official_salary, probation_days,
                    benefits_note, status, sent_at, responded_at, expires_at,
                    internal_note, created_by_id, created_at, updated_at
                )
                SELECT
                    ca.id,
                    c.id,
                    jr.id,
                    :job_position_id,
                    :department_id,
                    :proposed_start_date,
                    :probation_salary,
                    :official_salary,
                    60,
                    :benefits_note,
                    'accepted',
                    NOW() - INTERVAL '20 days',
                    NOW() - INTERVAL '18 days',
                    :expires_at,
                    :internal_note,
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM candidate_applications ca
                JOIN candidates c ON c.id = ca.candidate_id
                JOIN job_requisitions jr ON jr.id = ca.job_requisition_id
                WHERE c.personal_email = :email
                  AND jr.code = :jr_code
                """
            ),
            {
                "email": candidate_email,
                "jr_code": jr_code,
                "job_position_id": job_position_id,
                "department_id": department_id,
                "proposed_start_date": employee.join_date,
                "probation_salary": employee.probation_salary,
                "official_salary": employee.official_salary,
                "benefits_note": "Offer mẫu bao gồm BHXH đầy đủ và phụ cấp theo quy định",
                "expires_at": employee.join_date - timedelta(days=12),
                "internal_note": "Offer mẫu nhánh Kiểm soát",
                "created_by_id": created_by_id,
            },
        )
        counts["offers"] += 1

    decision_number = f"QDTD-KS-{employee.employee_seq:03d}"
    decision_exists = await _scalar(
        session,
        "SELECT COUNT(*) FROM hiring_decisions WHERE decision_number = :decision_number",
        decision_number=decision_number,
    )
    if not decision_exists:
        await session.execute(
            text(
                """
                INSERT INTO hiring_decisions (
                    offer_id, candidate_id, job_requisition_id, decision_number, signed_date,
                    department_id, job_position_id, job_title_id, start_date,
                    probation_salary, official_salary, probation_days,
                    employee_id, status, created_by_id, created_at, updated_at
                )
                SELECT
                    o.id,
                    o.candidate_id,
                    o.job_requisition_id,
                    :decision_number,
                    :signed_date,
                    :department_id,
                    :job_position_id,
                    :job_title_id,
                    :start_date,
                    :probation_salary,
                    :official_salary,
                    60,
                    :employee_id,
                    'converted',
                    :created_by_id,
                    NOW(),
                    NOW()
                FROM offers o
                JOIN candidates c ON c.id = o.candidate_id
                WHERE c.personal_email = :email
                  AND o.job_requisition_id = (SELECT id FROM job_requisitions WHERE code = :jr_code)
                """
            ),
            {
                "email": candidate_email,
                "jr_code": jr_code,
                "decision_number": decision_number,
                "signed_date": employee.join_date - timedelta(days=5),
                "department_id": department_id,
                "job_position_id": job_position_id,
                "job_title_id": job_title_id,
                "start_date": employee.join_date,
                "probation_salary": employee.probation_salary,
                "official_salary": employee.official_salary,
                "employee_id": employee_id,
                "created_by_id": created_by_id,
            },
        )
        counts["hiring_decisions"] += 1

    return counts


async def seed_control_branch_employee_domain_data(session: AsyncSession) -> dict[str, int]:
    """Seed full cross-module data for 5 control-branch employees."""
    summary = {
        "reward_types": 0,
        "training_courses": 0,
        "training_plans": 0,
        "training_plan_courses": 0,
        "recruitment_channels": 0,
        "contracts": 0,
        "insurance_profiles_updated": 0,
        "insurance_change_events": 0,
        "leave_entitlements": 0,
        "leave_records": 0,
        "rewards": 0,
        "disciplines": 0,
        "training_records": 0,
        "training_certificates": 0,
        "kpi_monthly": 0,
        "yearly_reviews": 0,
        "headcount_plans": 0,
        "job_requisitions": 0,
        "job_postings": 0,
        "candidates": 0,
        "applications": 0,
        "pipeline_stages": 0,
        "stage_results": 0,
        "offers": 0,
        "hiring_decisions": 0,
    }

    admin_user_id = await _get_user_id_by_email(session, "admin@hrms.local")
    reward_types = await _ensure_reward_types(session)
    training_courses, training_plans, training_plan_courses = await _ensure_training_catalog(session, admin_user_id)
    recruitment_channels = await _ensure_recruitment_channels(session)
    summary["reward_types"] += reward_types
    summary["training_courses"] += training_courses
    summary["training_plans"] += training_plans
    summary["training_plan_courses"] += training_plan_courses
    summary["recruitment_channels"] += recruitment_channels

    for employee in CONTROL_EMPLOYEES:
        employee_id = await _get_employee_id_by_seq(session, employee.employee_seq)
        summary["contracts"] += await _ensure_contract_for_employee(session, employee_id, employee, admin_user_id)
        profile_updated, change_added = await _ensure_insurance_profile_and_change(session, employee_id, employee, admin_user_id)
        summary["insurance_profiles_updated"] += profile_updated
        summary["insurance_change_events"] += change_added
        entitlement_added, leave_record_added = await _ensure_leave_data(session, employee_id, employee, admin_user_id)
        summary["leave_entitlements"] += entitlement_added
        summary["leave_records"] += leave_record_added
        reward_added, discipline_added = await _ensure_reward_and_discipline(session, employee_id, employee, admin_user_id)
        summary["rewards"] += reward_added
        summary["disciplines"] += discipline_added
        training_record_added, certificate_added = await _ensure_training_data(session, employee_id, employee, admin_user_id)
        summary["training_records"] += training_record_added
        summary["training_certificates"] += certificate_added
        kpi_added, review_added = await _ensure_performance_data(session, employee_id, admin_user_id)
        summary["kpi_monthly"] += kpi_added
        summary["yearly_reviews"] += review_added
        recruitment_counts = await _ensure_recruitment_data(session, employee_id, employee, admin_user_id)
        for key, value in recruitment_counts.items():
            summary[key] += value

    await session.flush()
    return summary
