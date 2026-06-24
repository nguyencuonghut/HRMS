"""
Dữ liệu bắt buộc — chạy trên mọi môi trường (dev/staging/prod).

Nội dung:
  - Mức lương tối thiểu vùng theo Nghị định 293/2025/NĐ-CP (hiệu lực 01/01/2026)
  - Vùng BHXH mặc định của công ty (Vùng III — có thể sửa trong DB sau)
  - Danh mục thành phần đóng BHXH/BHYT/BHTN (5 component chuẩn)
  - Policy version mặc định theo Luật BHXH 2024 (41/2024/QH15), hiệu lực 01/07/2025
  - Danh mục hành chính hệ cũ: tỉnh/thành + quận/huyện + xã/phường từ JSON chuyển đổi từ Excel
  - Danh mục hành chính hệ mới: 34 tỉnh/thành + xã/phường từ JSON chính thức

Seeder này idempotent: chạy nhiều lần không sinh dữ liệu trùng.
"""

import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.seeds import (
    administrative_units,
    bhyt_clinics as bhyt_clinics_seed,
    document_checklist_types as document_checklist_seed,
    education_catalog,
    notification_templates as notification_templates_seed,
    old_administrative_units,
    other_business_catalog,
)


async def seed_minimum_wages(session: AsyncSession) -> int:
    """Seed mức lương tối thiểu vùng theo NĐ 293/2025/NĐ-CP.

    Returns số dòng được thêm mới (0 nếu đã tồn tại).
    """
    wages = [
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 1,
            "amount": 5_310_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng I — HN (quận/huyện nội thành), TP.HCM, Đồng Nai, Bình Dương, Vũng Tàu...",
        },
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 2,
            "amount": 4_730_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng II — các tỉnh/TP loại II còn lại",
        },
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 3,
            "amount": 4_140_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng III — phần còn lại của các tỉnh có Vùng I/II và các tỉnh khác",
        },
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 4,
            "amount": 3_700_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng IV — vùng sâu, vùng xa, miền núi, hải đảo",
        },
    ]

    inserted = 0
    for w in wages:
        result = await session.execute(
            text("""
                INSERT INTO regional_minimum_wages
                    (decree_number, region, amount, effective_from, effective_to, note)
                VALUES
                    (:decree_number, :region, :amount, :effective_from, :effective_to, :note)
                ON CONFLICT DO NOTHING
            """),
            w,
        )
        inserted += result.rowcount

    return inserted


async def seed_company_region(session: AsyncSession, region: int = 3) -> int:
    """Seed vùng BHXH của công ty. Mặc định Vùng III.

    Returns 1 nếu thêm mới, 0 nếu đã có dữ liệu.
    """
    existing = await session.execute(
        text("SELECT COUNT(*) FROM company_bhxh_region WHERE effective_to IS NULL")
    )
    if existing.scalar() > 0:
        return 0

    region_names = {1: "Vùng I", 2: "Vùng II", 3: "Vùng III", 4: "Vùng IV"}
    await session.execute(
        text("""
            INSERT INTO company_bhxh_region (region, effective_from, effective_to, note)
            VALUES (:region, :effective_from, NULL, :note)
        """),
        {
            "region": region,
            "effective_from": datetime.date(2026, 1, 1),
            "note": f"{region_names[region]} — vùng BHXH mặc định, cập nhật nếu công ty chuyển địa điểm",
        },
    )
    return 1


async def seed_bhxh_seniority_settings(session: AsyncSession) -> int:
    """Seed rule thâm niên mặc định của công ty.

    Rule mặc định hiện tại:
      - xét nâng bậc vào 01/01 hàng năm
      - 3 năm tăng 1 bậc
      - cutoff tính tròn năm đầu: 30/04
    """
    existing = await session.execute(
        text("SELECT COUNT(*) FROM bhxh_seniority_settings WHERE effective_to IS NULL")
    )
    if existing.scalar() > 0:
        return 0

    await session.execute(
        text("""
            INSERT INTO bhxh_seniority_settings
                (raise_month, raise_day, years_per_grade,
                 first_year_cutoff_month, first_year_cutoff_day,
                 effective_from, effective_to, note)
            VALUES
                (:raise_month, :raise_day, :years_per_grade,
                 :first_year_cutoff_month, :first_year_cutoff_day,
                 :effective_from, NULL, :note)
        """),
        {
            "raise_month": 1,
            "raise_day": 1,
            "years_per_grade": 3,
            "first_year_cutoff_month": 4,
            "first_year_cutoff_day": 30,
            "effective_from": datetime.date(2026, 1, 1),
            "note": "Rule mặc định: xét tăng bậc ngày 01/01, 3 năm/1 bậc, cutoff năm đầu 30/04.",
        },
    )
    return 1


def _retirement_threshold_rows() -> list[dict]:
    rows: list[dict] = []
    for year in range(2021, 2029):
        extra_months = (year - 2021) * 3
        total_months = 60 * 12 + 3 + extra_months
        rows.append(
            {
                "gender": "male",
                "applicable_year": year,
                "age_years": total_months // 12,
                "age_months": total_months % 12,
            }
        )
    for year in range(2021, 2036):
        extra_months = (year - 2021) * 4
        total_months = 55 * 12 + 4 + extra_months
        rows.append(
            {
                "gender": "female",
                "applicable_year": year,
                "age_years": total_months // 12,
                "age_months": total_months % 12,
            }
        )
    return rows


async def seed_retirement_age_policy(session: AsyncSession) -> int:
    existing = await session.execute(
        text("SELECT COUNT(*) FROM retirement_age_policies WHERE effective_to IS NULL")
    )
    if existing.scalar() > 0:
        return 0

    policy_id = (
        await session.execute(
            text("""
                INSERT INTO retirement_age_policies
                    (name, legal_basis_summary, effective_from, effective_to, note)
                VALUES
                    (:name, :legal_basis_summary, :effective_from, NULL, :note)
                RETURNING id
            """),
            {
                "name": "Lộ trình tuổi nghỉ hưu NLĐ điều kiện bình thường",
                "legal_basis_summary": (
                    "Khoản 2 Điều 169 Bộ luật Lao động 2019; "
                    "Nghị định 135/2020/NĐ-CP."
                ),
                "effective_from": datetime.date(2021, 1, 1),
                "note": (
                    "Seed mặc định cho báo cáo người lao động cao tuổi. "
                    "Ngưỡng được khai báo theo năm áp dụng cho nam và nữ."
                ),
            },
        )
    ).scalar_one()

    inserted = 1
    for row in _retirement_threshold_rows():
        result = await session.execute(
            text("""
                INSERT INTO retirement_age_policy_thresholds
                    (policy_id, gender, applicable_year, age_years, age_months)
                VALUES
                    (:policy_id, :gender, :applicable_year, :age_years, :age_months)
                ON CONFLICT (policy_id, gender, applicable_year) DO NOTHING
            """),
            {"policy_id": policy_id, **row},
        )
        inserted += result.rowcount
    return inserted


async def seed_insurance_components(session: AsyncSession) -> int:
    """Seed danh mục 5 thành phần đóng BHXH/BHYT/BHTN chuẩn.

    Migration 0018 đã seed các component này khi chạy lần đầu.
    Hàm này là belt-and-suspenders cho môi trường migration seed bị bỏ qua.
    Format phải khớp với migration: insurance_kind lowercase, sort_order bội số 10.

    Căn cứ: Luật BHXH 2024 (41/2024/QH15), Luật BHYT sửa đổi, Luật Việc làm 2025.
    Returns số dòng được thêm mới (0 nếu đã tồn tại).
    """
    components = [
        # ── BHXH ──────────────────────────────────────────────────────────────
        {"code": "RETIREMENT_SURVIVOR",  "name_vi": "BHXH - Hưu trí và Tử tuất",                              "insurance_kind": "bhxh", "sort_order": 10},
        {"code": "SICKNESS_MATERNITY",   "name_vi": "BHXH - Ốm đau và Thai sản",                              "insurance_kind": "bhxh", "sort_order": 20},
        {"code": "OCC_ACCIDENT_DISEASE", "name_vi": "BHTNLĐ-BNN - Tai nạn lao động và Bệnh nghề nghiệp",      "insurance_kind": "bhxh", "sort_order": 30},
        # ── BHYT ──────────────────────────────────────────────────────────────
        {"code": "HEALTH",               "name_vi": "BHYT - Y tế",                                             "insurance_kind": "bhyt", "sort_order": 40},
        # ── BHTN ──────────────────────────────────────────────────────────────
        {"code": "UNEMPLOYMENT",         "name_vi": "BHTN - Thất nghiệp",                                      "insurance_kind": "bhtn", "sort_order": 50},
    ]

    inserted = 0
    for c in components:
        result = await session.execute(
            text("""
                INSERT INTO insurance_contribution_components
                    (code, name_vi, insurance_kind, sort_order, is_active)
                VALUES
                    (:code, :name_vi, :insurance_kind, :sort_order, TRUE)
                ON CONFLICT (code) DO NOTHING
            """),
            c,
        )
        inserted += result.rowcount

    return inserted


async def seed_insurance_policy_version_baseline(session: AsyncSession) -> bool:
    """Seed policy version tỷ lệ đóng mặc định theo pháp luật hiện hành.

    Migration 0018 đã seed VN_STANDARD_2026_01_01 khi chạy lần đầu.
    Hàm này chỉ seed khi không có bất kỳ policy nào tồn tại (fresh env không migration).

    Căn cứ pháp lý (tỷ lệ verify từ văn bản trước khi deploy prod):
      - Luật BHXH 2024 (41/2024/QH15), hiệu lực 01/07/2025 — Điều 85, 86, 87
        · Hưu trí - Tử tuất: NLĐ 8%, NSDLĐ 14%
        · Ốm đau - Thai sản: NLĐ 0%, NSDLĐ 3%
        · TNLĐ-BNN: NLĐ 0%, NSDLĐ 0.5%
          (NQ 28/2023/NQ-CP giảm xuống 0.3% đến hết 2025; từ 2026 về 0.5% nếu không gia hạn)
      - Nghị định 188/2025/NĐ-CP: BHYT NLĐ 1.5%, NSDLĐ 3%
      - Luật Việc làm 2025: BHTN NLĐ 1%, NSDLĐ 1% (HĐ ≥ 3 tháng)
      Tổng: NLĐ 10.5%, NSDLĐ 21.5%

    Returns True nếu đã seed, False nếu bỏ qua (đã có policy).
    """
    existing = await session.execute(
        text("SELECT COUNT(*) FROM insurance_policy_versions")
    )
    if existing.scalar() > 0:
        return False

    result = await session.execute(
        text("""
            INSERT INTO insurance_policy_versions
                (code, name, legal_basis_summary, effective_from, effective_to,
                 is_active, company_region, note)
            VALUES
                (:code, :name, :legal_basis_summary, :effective_from, NULL,
                 TRUE, :company_region, :note)
            RETURNING id
        """),
        {
            "code": "VN_STANDARD_BASELINE",
            "name": "Tỷ lệ đóng BHXH/BHYT/BHTN — mặc định hệ thống",
            "legal_basis_summary": (
                "Luật BHXH 2024 (41/2024/QH15) Điều 85–87; "
                "NĐ 188/2025/NĐ-CP (BHYT); "
                "Luật Việc làm 2025 (BHTN). "
                "Seed tự động khi không có migration data."
            ),
            "effective_from": datetime.date(2026, 1, 1),
            "company_region": 3,
            "note": "Seed tự động. Verify lại tỷ lệ TNLĐ-BNN (0.5%) trước deploy prod.",
        },
    )
    policy_id = result.scalar_one()

    component_rates = [
        ("RETIREMENT_SURVIVOR",  "8.0000", "14.0000", False),
        ("SICKNESS_MATERNITY",   "0.0000",  "3.0000", False),
        ("OCC_ACCIDENT_DISEASE", "0.0000",  "0.5000", False),
        ("HEALTH",               "1.5000",  "3.0000", False),
        ("UNEMPLOYMENT",         "1.0000",  "1.0000", False),
    ]

    for code, emp_rate, er_rate, advances in component_rates:
        await session.execute(
            text("""
                INSERT INTO insurance_policy_component_rates
                    (policy_version_id, component_code,
                     employee_rate_percent, employer_rate_percent,
                     employer_advances_employee_part, is_active)
                VALUES
                    (:policy_version_id, :component_code,
                     :employee_rate_percent, :employer_rate_percent,
                     :employer_advances_employee_part, TRUE)
                ON CONFLICT (policy_version_id, component_code) DO NOTHING
            """),
            {
                "policy_version_id": policy_id,
                "component_code": code,
                "employee_rate_percent": emp_rate,
                "employer_rate_percent": er_rate,
                "employer_advances_employee_part": advances,
            },
        )

    return True


async def run(session: AsyncSession) -> None:
    wages_added = await seed_minimum_wages(session)
    region_added = await seed_company_region(session)
    seniority_added = await seed_bhxh_seniority_settings(session)
    retirement_policy_added = await seed_retirement_age_policy(session)
    ins_components_added = await seed_insurance_components(session)
    ins_policy_seeded = await seed_insurance_policy_version_baseline(session)
    education_levels_added = await education_catalog.seed_required_education_catalog(session)
    (
        contract_categories_added,
        nationalities_added,
        ethnicities_added,
        religions_added,
        banks_added,
        leave_types_added,
    ) = await other_business_catalog.seed_required_other_business_catalog(session)
    old_admin_units_upserted, old_admin_hierarchies_added = await old_administrative_units.seed_old_administrative_system(session)
    admin_units_upserted, admin_hierarchies_added = await administrative_units.seed_new_administrative_system(session)
    clinics_added = await bhyt_clinics_seed.seed_bhyt_clinics(session)
    checklist_seed_stats = await document_checklist_seed.seed_required_document_checklist_types(session)
    await notification_templates_seed.seed_notification_templates(session)
    await session.commit()

    print(f"  [required] Mức lương tối thiểu vùng: +{wages_added} dòng")
    print(f"  [required] Vùng BHXH công ty:         +{region_added} dòng")
    print(f"  [required] Rule thâm niên BHXH:      +{seniority_added} dòng")
    print(f"  [required] Policy tuổi nghỉ hưu:     +{retirement_policy_added} dòng")
    print(f"  [required] Component BHXH/BHYT/BHTN:  +{ins_components_added} dòng")
    print(f"  [required] Policy version baseline:    {'seeded (BHXH_2025_V1)' if ins_policy_seeded else 'bỏ qua (đã có policy active)'}")
    print(f"  [required] Trình độ học vấn:         +{education_levels_added} upsert")
    print(f"  [required] Loại hợp đồng:            +{contract_categories_added} upsert")
    print(f"  [required] Quốc tịch:                +{nationalities_added} upsert")
    print(f"  [required] Dân tộc:                  +{ethnicities_added} upsert")
    print(f"  [required] Tôn giáo:                 +{religions_added} upsert")
    print(f"  [required] Ngân hàng:                +{banks_added} upsert")
    print(f"  [required] Loại nghỉ phép:           +{leave_types_added} upsert")
    print(f"  [required] Đơn vị hành chính cũ:      +{old_admin_units_upserted} upsert")
    print(f"  [required] Quan hệ cũ tỉnh→huyện→xã:  +{old_admin_hierarchies_added} dòng")
    print(f"  [required] Đơn vị hành chính mới:     +{admin_units_upserted} upsert")
    print(f"  [required] Quan hệ tỉnh → xã/phường:  +{admin_hierarchies_added} dòng")
    print(f"  [required] Bệnh viện KCB BHYT:         +{clinics_added} upsert")
    print(
        "  [required] Checklist hồ sơ pháp lý:   "
        f"+{checklist_seed_stats['inserted']} thêm mới, "
        f"+{checklist_seed_stats['updated']} cập nhật, "
        f"+{checklist_seed_stats['deactivated']} vô hiệu hóa, "
        f"+{checklist_seed_stats['backfilled']} backfill"
    )
    print("  [required] Notification templates:    upsert")
