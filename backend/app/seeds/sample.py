"""
Dữ liệu mẫu — chỉ dùng trên môi trường dev/test.
KHÔNG chạy trên production.

Nội dung:
  - Catalog học vấn mẫu
  - Kỹ năng / chứng chỉ / mẫu hợp đồng mẫu
  - Nhân viên mẫu và dữ liệu demo liên quan

Seeder này idempotent: chạy nhiều lần không sinh dữ liệu trùng.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.seeds import education_catalog, other_business_catalog, employees as employees_seed, employee_job_records as job_records_seed, employee_relatives as relatives_seed, employee_education as education_seed
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
    relatives_added = await relatives_seed.seed_sample_relatives(session)
    print(f"  [sample] Người thân mẫu:    +{relatives_added} dòng")
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
    print(f"  [sample] Bản ghi công việc: +{job_records_added} dòng")
    print(f"  [sample] Học vấn:           +{edu_counts['education_histories']} dòng")
    print(f"  [sample] Kinh nghiệm:       +{edu_counts['work_experiences']} dòng")
    print(f"  [sample] Kỹ năng NV:        +{edu_counts['skills']} dòng")
    print(f"  [sample] Chứng chỉ NV:      +{edu_counts['certificates']} dòng")
    print(f"  [sample] Ngoại ngữ:         +{edu_counts['languages']} dòng")
