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
    employee_contracts as contracts_seed,
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


async def _backfill_all_employees_to_completion(session: AsyncSession) -> None:
    from datetime import date
    from app.models.employee import EmployeeAddress, EmployeeBankAccount
    from app.models.employee_insurance import EmployeeInsuranceProfile
    from app.models.employee_relative import EmployeeRelative
    from app.models.employee_education import EmployeeEducationHistory
    from app.models.employee_contract import EmployeeContract
    from app.models.reward import EmployeeReward, RewardType
    from app.models.discipline import EmployeeDiscipline
    from app.models.employee_asset import EmployeeAsset
    from app.models.recruitment import EmployeeDocumentChecklist, DocumentChecklistType
    from app.models.catalog import AdministrativeUnit, ContractCategory, EducationLevel, Bank
    from app.models.org import Department, JobTitle, JobPosition
    from app.models.employee_job import EmployeeJobRecord
    from app.core.encryption import encrypt
    from app.services.administrative_import_service import normalize_text
    from datetime import date
    from decimal import Decimal

    # Fetch default catalog records
    dept = (await session.execute(select(Department))).scalars().first()
    jt = (await session.execute(select(JobTitle))).scalars().first()
    jp = (await session.execute(select(JobPosition))).scalars().first()
    cc = (await session.execute(select(ContractCategory))).scalars().first()
    # Fetch 'dai_hoc' specifically to match university institutions
    el = (await session.execute(select(EducationLevel).where(EducationLevel.code == "dai_hoc"))).scalars().first()
    if not el:
        el = (await session.execute(select(EducationLevel).where(EducationLevel.name.like("%Đại học%")))).scalars().first()
    if not el:
        el = (await session.execute(select(EducationLevel))).scalars().first()
    bank = (await session.execute(select(Bank))).scalars().first()
    rt = (await session.execute(select(RewardType))).scalars().first()

    province = (await session.execute(select(AdministrativeUnit).where(AdministrativeUnit.unit_type == "province"))).scalars().first()
    district = (await session.execute(select(AdministrativeUnit).where(AdministrativeUnit.unit_type == "district"))).scalars().first()
    ward = (await session.execute(select(AdministrativeUnit).where(AdministrativeUnit.unit_type == "ward"))).scalars().first()

    employees = (await session.execute(select(Employee))).scalars().all()

    for emp in employees:
        # 1. Address
        addr = (await session.execute(select(EmployeeAddress).where(EmployeeAddress.employee_id == emp.id))).scalars().first()
        if not addr:
            addr = EmployeeAddress(
                employee_id=emp.id,
                address_type="permanent",
                new_province_unit_id=province.id if province else None,
                new_district_unit_id=district.id if district else None,
                new_ward_unit_id=ward.id if ward else None,
                new_address_line="Số 123 Đường Láng",
                full_address_text="Số 123 Đường Láng, phường Láng Thượng, quận Đống Đa, Hà Nội",
                created_at=emp.created_at
            )
            session.add(addr)

        # 2. Bank Account
        bk_acc = (await session.execute(select(EmployeeBankAccount).where(EmployeeBankAccount.employee_id == emp.id))).scalars().first()
        if not bk_acc:
            bk_acc = EmployeeBankAccount(
                employee_id=emp.id,
                bank_id=bank.id if bank else 1,
                account_number=encrypt("123456789"),
                account_name=normalize_text(emp.full_name).upper(),
                is_primary=True,
                is_active=True,
                created_at=emp.created_at
            )
            session.add(bk_acc)

        # 3. Contract
        contract = (await session.execute(select(EmployeeContract).where(EmployeeContract.employee_id == emp.id))).scalars().first()
        if not contract:
            contract = EmployeeContract(
                employee_id=emp.id,
                contract_number=f"HD-AUTO-{emp.id:03d}",
                contract_category_id=cc.id if cc else 1,
                signed_date=emp.start_date,
                effective_from=emp.start_date,
                effective_to=None,
                status="expired" if emp.status == "resigned" else "active",
                insurance_salary=Decimal("10000000"),
                insurance_salary_grade_no=2,
                created_at=emp.created_at
            )
            session.add(contract)

        # 4. Job Record
        job = (await session.execute(select(EmployeeJobRecord).where(EmployeeJobRecord.employee_id == emp.id))).scalars().first()
        if not job:
            job = EmployeeJobRecord(
                employee_id=emp.id,
                department_id=dept.id if dept else 1,
                job_title_id=jt.id if jt else 1,
                job_position_id=jp.id if jp else 1,
                is_current=True,
                effective_from=emp.start_date,
                created_at=emp.created_at
            )
            session.add(job)

        # 5. Relative
        relatives = (await session.execute(select(EmployeeRelative).where(EmployeeRelative.employee_id == emp.id))).scalars().all()
        if not relatives:
            gender = emp.gender or "male"
            spouse_type = "vo" if gender == "male" else "chong"
            spouse_name = "Nguyễn Thị Mai" if gender == "male" else "Trần Văn Hùng"
            
            # 1. Spouse
            spouse = EmployeeRelative(
                employee_id=emp.id,
                full_name=spouse_name,
                relationship_type=spouse_type,
                date_of_birth=date(1990, 6, 20),
                phone_number="0987654321",
                is_emergency_contact=True,
                participates_in_health_care_insurance=False,
                created_at=emp.created_at
            )
            session.add(spouse)
            
            # 2. Child under 18
            child_under = EmployeeRelative(
                employee_id=emp.id,
                full_name="Nguyễn Hoàng Nam",
                relationship_type="con",
                date_of_birth=date(2016, 5, 20),
                participates_in_health_care_insurance=False,
                created_at=emp.created_at
            )
            session.add(child_under)

            # 3. Child over 18
            child_over = EmployeeRelative(
                employee_id=emp.id,
                full_name="Nguyễn Hoàng Long",
                relationship_type="con",
                date_of_birth=date(2005, 3, 15),
                participates_in_health_care_insurance=False,
                created_at=emp.created_at
            )
            session.add(child_over)

        # 6. Asset
        asset = (await session.execute(select(EmployeeAsset).where(EmployeeAsset.employee_id == emp.id))).scalars().first()
        if not asset:
            asset = EmployeeAsset(
                employee_id=emp.id,
                asset_name="Laptop Dell Latitude",
                asset_type="laptop",
                handover_date=emp.start_date,
                status="allocated",
                created_at=emp.created_at
            )
            session.add(asset)

        # 7. Education History
        edu = (await session.execute(select(EmployeeEducationHistory).where(EmployeeEducationHistory.employee_id == emp.id))).scalars().first()
        if not edu:
            edu = EmployeeEducationHistory(
                employee_id=emp.id,
                institution_name="Đại học Bách Khoa Hà Nội",
                major_name="Công nghệ thông tin",
                education_level_id=el.id if el else 1,
                graduation_year=2018,
                diploma_type="Chính quy",
                is_main_education=True,
                created_at=emp.created_at
            )
            session.add(edu)

        # 8. Reward
        reward = (await session.execute(select(EmployeeReward).where(EmployeeReward.employee_id == emp.id))).scalars().first()
        if not reward:
            reward = EmployeeReward(
                employee_id=emp.id,
                reward_type_id=rt.id if rt else 1,
                title="Hoàn thành xuất sắc nhiệm vụ",
                reward_date=emp.start_date,
                decision_number=f"QD-KT-{emp.id:03d}",
                issued_by="Tổng Giám Đốc",
                value=Decimal("1000000"),
                created_at=emp.created_at
            )
            session.add(reward)

        # 9. Discipline
        discipline = (await session.execute(select(EmployeeDiscipline).where(EmployeeDiscipline.employee_id == emp.id))).scalars().first()
        if not discipline:
            discipline = EmployeeDiscipline(
                employee_id=emp.id,
                discipline_form="khien_trach",
                violation_date=emp.start_date,
                effective_date=emp.start_date,
                title="Đi muộn không lý do",
                decision_number=f"QD-KL-{emp.id:03d}",
                issued_by="Trưởng phòng HCNS",
                created_at=emp.created_at
            )
            session.add(discipline)

        # 10. Insurance Profile Updates
        profile = (await session.execute(select(EmployeeInsuranceProfile).where(EmployeeInsuranceProfile.employee_id == emp.id))).scalars().first()
        if profile:
            if not profile.company_bhxh_joined_date:
                profile.company_bhxh_joined_date = emp.start_date
            
            # Apply the 30% Health Care / 70% Accident rule for sample employees (employee_seq <= 13)
            # Control branch employees keep their pre-seeded codes from control_branch_sample.py
            if emp.employee_seq <= 13:
                # 30% are CSSK (employee_seq: 3, 6, 9, 12)
                if emp.employee_seq % 3 == 0:
                    profile.health_care_insurance_code = f"CSSK-AUTO-{emp.employee_seq:03d}"
                    profile.accident_insurance_code = None
                    # 50% of CSSK have family participation (employee_seq: 6, 12)
                    if (emp.employee_seq // 3) % 2 == 0:
                        profile.health_care_family_participation = True
                    else:
                        profile.health_care_family_participation = False
                else:
                    # Remaining 70% are Accident (accident_insurance_code)
                    profile.accident_insurance_code = f"TNLD-AUTO-{emp.employee_seq:03d}"
                    profile.health_care_insurance_code = None
                    profile.health_care_family_participation = None
            else:
                # For control branch or other employees, ensure they have at least one type of insurance
                if not profile.health_care_insurance_code and not profile.accident_insurance_code:
                    if emp.employee_seq % 2 == 0:
                        profile.accident_insurance_code = f"TNLD-AUTO-{emp.employee_seq:03d}"
                        profile.health_care_insurance_code = None
                        profile.health_care_family_participation = None
                    else:
                        profile.health_care_insurance_code = f"CSSK-AUTO-{emp.employee_seq:03d}"
                        profile.accident_insurance_code = None
                        profile.health_care_family_participation = False

            if not profile.bhxh_code:
                profile.bhxh_code = f"BHXH-{emp.id:09d}"
            session.add(profile)
            
            # Sync relative participates_in_health_care_insurance with the employee's family participation status
            emp_relatives = (await session.execute(select(EmployeeRelative).where(EmployeeRelative.employee_id == emp.id))).scalars().all()
            has_health_care_family = bool(profile.health_care_insurance_code) and (profile.health_care_family_participation is True)
            
            for rel in emp_relatives:
                if has_health_care_family:
                    if rel.relationship_type in {"vo", "chong"}:
                        rel.participates_in_health_care_insurance = True
                    elif rel.relationship_type == "con":
                        age = 0
                        if rel.date_of_birth:
                            today = date.today()
                            age = today.year - rel.date_of_birth.year - ((today.month, today.day) < (rel.date_of_birth.month, rel.date_of_birth.day))
                        if age < 18:
                            rel.participates_in_health_care_insurance = True
                        else:
                            rel.participates_in_health_care_insurance = False
                    else:
                        rel.participates_in_health_care_insurance = False
                else:
                    rel.participates_in_health_care_insurance = False
                session.add(rel)

        # 11. NDA checklist items status set to submitted
        chk_items = (await session.execute(
            select(EmployeeDocumentChecklist, DocumentChecklistType)
            .join(DocumentChecklistType, EmployeeDocumentChecklist.document_type_id == DocumentChecklistType.id)
            .where(EmployeeDocumentChecklist.employee_id == emp.id)
        )).all()
        for item, dtype in chk_items:
            if dtype.code == "cam_ket_bao_mat_thong_tin":
                item.status = "submitted"
                session.add(item)

    await session.flush()


async def run(session: AsyncSession) -> None:
    # 0. Xóa cohort demo dashboard cũ để sample seed chỉ còn dữ liệu nhân sự mẫu tổng quát
    dashboard_demo_filter = "dashboard.demo.%@hrms.local"
    await session.execute(
        text(
            """
            DELETE FROM employee_yearly_reviews
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_kpi_monthly
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_training_certificates
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_training_records
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_disciplines
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_rewards
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_education_histories
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_assets
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_relatives
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_addresses
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_bank_accounts
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM bhxh_salary_adjustments
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM insurance_change_events
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_insurance_profiles
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_contracts
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employee_job_records
            WHERE employee_id IN (
                SELECT id FROM employees WHERE personal_email LIKE :dashboard_demo_filter
            )
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )
    await session.execute(
        text(
            """
            DELETE FROM employees
            WHERE personal_email LIKE :dashboard_demo_filter
            """
        ),
        {"dashboard_demo_filter": dashboard_demo_filter},
    )

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
    contracts_added = await contracts_seed.seed_sample_contracts(session)
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
    await _backfill_all_employees_to_completion(session)
    await session.commit()


    print(f"  [sample] Trường học:        +{institutions_added} upsert")
    print(f"  [sample] Chuyên ngành:      +{majors_added} upsert")
    print(f"  [sample] Kỹ năng:           +{skills_added} upsert")
    print(f"  [sample] Chứng chỉ:         +{certificates_added} upsert")
    print(f"  [sample] Mẫu hợp đồng:      +{templates_added} upsert")
    print(f"  [sample] Placeholder mẫu:   +{placeholders_added} upsert")
    print(f"  [sample] Nhân viên mẫu:     +{emps_added} dòng")
    print(f"  [sample] Hồ sơ BHXH:        +{insurance_profiles_added} dòng")
    print(f"  [sample] Hợp đồng mẫu:      +{contracts_added} dòng")
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
