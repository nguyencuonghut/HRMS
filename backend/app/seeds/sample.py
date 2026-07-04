"""
Dữ liệu mẫu — chỉ dùng trên môi trường dev/test.
KHÔNG chạy trên production.

Nội dung:
  - Catalog học vấn mẫu
  - Kỹ năng / chứng chỉ / mẫu hợp đồng mẫu
  - Nhân viên mẫu và dữ liệu demo liên quan

Seeder này idempotent: chạy nhiều lần không sinh dữ liệu trùng.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.seeds import (
    control_branch_sample,
    education_catalog,
    employee_education as education_seed,
    employee_job_records as job_records_seed,
    employee_relatives as relatives_seed,
    employees as employees_seed,
    other_business_catalog,
    employee_assets as assets_seed,
)
from app.services.employee_insurance_service import (
    ensure_employee_insurance_profile,
    get_employee_insurance_profile,
)


async def _seed_sample_employee_insurance_profiles(session: AsyncSession) -> int:
    employees = (await session.execute(select(Employee))).scalars().all()
    added = 0
    for employee in employees:
        existed = await get_employee_insurance_profile(session, employee.id) is not None
        await ensure_employee_insurance_profile(session, employee)
        if not existed:
            added += 1
    return added


async def run(session: AsyncSession) -> None:
    # 1. Clean up orphaned records to avoid FK constraint errors on dirty dev database
    await session.execute(text("DELETE FROM bhxh_salary_adjustments WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM insurance_change_events WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_insurance_profiles WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_contracts WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_job_records WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_bank_accounts WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_addresses WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_assets WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_relatives WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_rewards WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_disciplines WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_training_records WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_training_certificates WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_kpi_monthly WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM employee_yearly_reviews WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM leave_records WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.execute(text("DELETE FROM leave_entitlements WHERE employee_id NOT IN (SELECT id FROM employees)"))
    await session.flush()

    # 2. Reset Postgres sequences to avoid sequence out of sync issues (primary key collision)
    for seq_name, table_name in [
        ("employees_id_seq", "employees"),
        ("employee_insurance_profiles_id_seq", "employee_insurance_profiles"),
        ("employee_contracts_id_seq", "employee_contracts"),
        ("employee_job_records_id_seq", "employee_job_records"),
        ("insurance_change_events_id_seq", "insurance_change_events"),
        ("bhxh_salary_adjustments_id_seq", "bhxh_salary_adjustments"),
        ("employee_bank_accounts_id_seq", "employee_bank_accounts"),
        ("employee_addresses_id_seq", "employee_addresses"),
        ("employee_assets_id_seq", "employee_assets"),
        ("employee_relatives_id_seq", "employee_relatives"),
        ("employee_rewards_id_seq", "employee_rewards"),
        ("employee_disciplines_id_seq", "employee_disciplines"),
        ("employee_training_records_id_seq", "employee_training_records"),
        ("employee_training_certificates_id_seq", "employee_training_certificates"),
        ("employee_kpi_monthly_id_seq", "employee_kpi_monthly"),
        ("employee_yearly_reviews_id_seq", "employee_yearly_reviews"),
        ("leave_records_id_seq", "leave_records"),
        ("leave_entitlements_id_seq", "leave_entitlements"),
    ]:
        await session.execute(
            text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)")
        )
    await session.flush()

    institutions_added, majors_added = await education_catalog.seed_sample_education_catalog(session)
    (
        skills_added,
        certificates_added,
        templates_added,
        placeholders_added,
    ) = await other_business_catalog.seed_sample_other_business_catalog(session)
    emps_added = await employees_seed.seed_sample_employees(session)
    await session.flush()
    insurance_profiles_added = await _seed_sample_employee_insurance_profiles(session)
    await session.flush()
    job_records_added = await job_records_seed.seed_sample_job_records(session)
    await session.flush()
    control_branch_counts = await control_branch_sample.seed_control_branch_employee_domain_data(session)
    await session.flush()
    relatives_added = await relatives_seed.seed_sample_relatives(session)
    print(f"  [sample] Người thân mẫu:    +{relatives_added} dòng")
    assets_added = await assets_seed.seed_sample_assets(session)
    print(f"  [sample] Tài sản cấp phát:  +{assets_added} dòng")
    edu_counts = await education_seed.seed_sample_education(session)
    await session.commit()


    print(f"  [sample] Trường học:        +{institutions_added} upsert")
    print(f"  [sample] Chuyên ngành:      +{majors_added} upsert")
    print(f"  [sample] Kỹ năng:           +{skills_added} upsert")
    print(f"  [sample] Chứng chỉ:         +{certificates_added} upsert")
    print(f"  [sample] Mẫu hợp đồng:      +{templates_added} upsert")
    print(f"  [sample] Placeholder mẫu:   +{placeholders_added} upsert")
    print(f"  [sample] Nhân viên mẫu:     +{emps_added} dòng")
    print(f"  [sample] Hồ sơ BHXH:        +{insurance_profiles_added} dòng")
    print(f"  [sample] Tài sản cấp phát:  +{assets_added} dòng")
    print(f"  [sample] Bản ghi công việc: +{job_records_added} dòng")
    print(f"  [sample] Địa chỉ KS/KSNB/IT: +{control_branch_counts['employee_addresses']} dòng")
    print(f"  [sample] HĐ KS/KSNB/IT:     +{control_branch_counts['contracts']} dòng")
    print(f"  [sample] BHXH KS/KSNB/IT:   +{control_branch_counts['insurance_change_events']} biến động")
    print(f"  [sample] Nghỉ phép KS/..:   +{control_branch_counts['leave_records']} dòng")
    print(f"  [sample] KT/KL KS/..:       +{control_branch_counts['rewards'] + control_branch_counts['disciplines']} dòng")
    print(f"  [sample] Đào tạo KS/..:     +{control_branch_counts['training_records']} dòng")
    print(f"  [sample] KPI/Review KS/..:  +{control_branch_counts['kpi_monthly'] + control_branch_counts['yearly_reviews']} dòng")
    print(f"  [sample] Tuyển dụng KS/..:  +{control_branch_counts['hiring_decisions']} quyết định")
    print(f"  [sample] Học vấn:           +{edu_counts['education_histories']} dòng")
    print(f"  [sample] Kinh nghiệm:       +{edu_counts['work_experiences']} dòng")
    print(f"  [sample] Kỹ năng NV:        +{edu_counts['skills']} dòng")
    print(f"  [sample] Chứng chỉ NV:      +{edu_counts['certificates']} dòng")
    print(f"  [sample] Ngoại ngữ:         +{edu_counts['languages']} dòng")
