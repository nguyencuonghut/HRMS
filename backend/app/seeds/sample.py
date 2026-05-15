"""
Dữ liệu mẫu — chỉ dùng trên môi trường dev/test.
KHÔNG chạy trên production.

Nội dung:
  - Chức danh (job_titles) và hệ số bậc lương (salary_scale_entries)
  - Cơ cấu phòng ban thực tế của công ty (departments)

Seeder này idempotent: chạy nhiều lần không sinh dữ liệu trùng.
"""

import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.seeds import education_catalog, other_business_catalog, employees as employees_seed, employee_job_records as job_records_seed, employee_relatives as relatives_seed

# ─── Chức danh ───────────────────────────────────────────────────────────────

JOB_TITLES = [
    {"code": "CTHD",   "name": "Chủ tịch Hội đồng quản trị", "level": 1},
    {"code": "GD",     "name": "Giám đốc",                    "level": 2},
    {"code": "PDG",    "name": "Phó Giám đốc",                "level": 3},
    {"code": "TP",     "name": "Trưởng phòng",                 "level": 4},
    {"code": "PP",     "name": "Phó phòng",                    "level": 5},
    {"code": "TBP",    "name": "Trưởng bộ phận",               "level": 6},
    {"code": "NVKD",   "name": "Nhân viên kinh doanh",         "level": 7},
    {"code": "NVKT_T", "name": "Nhân viên kỹ thuật trại",      "level": 7},
    {"code": "NVKT",   "name": "Nhân viên kỹ thuật",           "level": 7},
    {"code": "NV",     "name": "Nhân viên",                    "level": 8},
]

# ─── Hệ số bậc lương (7 bậc / chức danh) ────────────────────────────────────
# Lương bậc N = LTTV_vùng × hệ_số
# Ví dụ Vùng III: 4.140.000 × 2.68 = 11.095.200 ₫ (Chủ tịch HĐQT bậc 1)

SCALE_ENTRIES = {
    # code: [bậc1, bậc2, bậc3, bậc4, bậc5, bậc6, bậc7]
    "CTHD":   [2.68, 3.08, 3.54, 4.08, 4.98, 6.07, 7.41],
    "GD":     [2.34, 2.69, 3.09, 3.56, 4.09, 4.71, 5.42],
    "PDG":    [2.10, 2.41, 2.77, 3.19, 3.67, 4.22, 4.86],
    "TP":     [1.78, 2.05, 2.35, 2.71, 3.11, 3.58, 4.12],
    "PP":     [1.56, 1.79, 2.06, 2.37, 2.73, 3.14, 3.61],
    "TBP":    [1.35, 1.55, 1.78, 2.05, 2.36, 2.71, 3.12],
    "NVKD":   [1.10, 1.16, 1.21, 1.31, 1.41, 1.53, 1.67],
    "NVKT_T": [1.10, 1.16, 1.21, 1.31, 1.41, 1.53, 1.67],
    "NVKT":   [1.10, 1.16, 1.21, 1.31, 1.41, 1.53, 1.67],
    "NV":     [1.00, 1.08, 1.15, 1.23, 1.31, 1.40, 1.50],
}

# ─── Cơ cấu phòng ban ────────────────────────────────────────────────────────
# Tuple: (code, name, dept_type, parent_code)
# dept_type: BAN | PHONG | BO_PHAN | NHOM | TO
# parent_code = None → đơn vị cấp gốc

DEPARTMENTS = [
    # ── Cấp gốc ────────────────────────────────────────────────────────────
    ("LD",   "Ban lãnh đạo",          "BAN",     None),
    ("KS",   "Phòng kiểm soát",       "PHONG",   None),
    ("HC",   "Phòng hành chính",      "PHONG",   None),
    ("KD",   "Phòng kinh doanh",      "PHONG",   None),
    ("DA",   "Ban dự án",             "BAN",     None),
    ("PK",   "Phòng kế toán",         "PHONG",   None),
    ("TM",   "Phòng thu mua",         "PHONG",   None),
    ("KH",   "Bộ phận kho",           "BO_PHAN", None),
    ("BT",   "Phòng bảo trì",         "PHONG",   None),
    ("SX",   "Phòng sản xuất",        "PHONG",   None),
    ("MKT",  "Phòng marketing",       "PHONG",   None),
    ("PC",   "Bộ phận pháp chế",      "BO_PHAN", None),
    ("CL",   "Phòng chất lượng",      "PHONG",   None),
    ("KT",   "Phòng kỹ thuật",        "PHONG",   None),
    ("PT",   "Phòng trại",            "PHONG",   None),
    # ── Con của KS ─────────────────────────────────────────────────────────
    ("IT",   "Bộ phận IT",                    "BO_PHAN", "KS"),
    ("KSNB", "Bộ phận kiểm soát nội bộ",      "BO_PHAN", "KS"),
    # ── Con của HC ─────────────────────────────────────────────────────────
    ("BV",   "Ban bảo vệ",                    "BAN",     "HC"),
    ("LXNM", "Tổ lái xe nhà máy",             "TO",      "HC"),
    ("TV",   "Tổ tạp vụ",                     "TO",      "HC"),
    ("NB",   "Tổ nhà bếp",                    "TO",      "HC"),
    ("TR",   "Tổ trồng rau",                  "TO",      "HC"),
    # ── Con của KD ─────────────────────────────────────────────────────────
    ("KTT",  "Bộ phận kỹ thuật trại",         "BO_PHAN", "KD"),
    ("KTTT", "Bộ phận kỹ thuật thị trường",   "BO_PHAN", "KD"),
    ("AKD",  "Bộ phận Admin kinh doanh",       "BO_PHAN", "KD"),
    # ── Con của PK ─────────────────────────────────────────────────────────
    ("BH",   "Bộ phận bán hàng",              "BO_PHAN", "PK"),
    ("CAN",  "Bộ phận cân",                   "BO_PHAN", "PK"),
    # ── Con của TM ─────────────────────────────────────────────────────────
    ("ATM",  "Bộ phận Admin thu mua",          "BO_PHAN", "TM"),
    # ── Con của KH ─────────────────────────────────────────────────────────
    ("KTK",  "Tổ kế toán kho",                "TO",      "KH"),
    ("KNL",  "Tổ kho nguyên liệu",            "TO",      "KH"),
    ("KTP",  "Tổ kho thành phẩm",             "TO",      "KH"),
    ("KTTY", "Tổ kho thuốc thú y",            "TO",      "KH"),
    # ── Con của BT ─────────────────────────────────────────────────────────
    ("BTC",  "Tổ bảo trì cơ",                 "TO",      "BT"),
    ("BTD",  "Tổ bảo trì điện",               "TO",      "BT"),
    # ── Con của SX ─────────────────────────────────────────────────────────
    ("GSGC", "Bộ phận sản xuất gia súc gia cầm", "BO_PHAN", "SX"),
    ("TS",   "Bộ phận sản xuất thủy sản",     "BO_PHAN", "SX"),
    # ── Con của CL ─────────────────────────────────────────────────────────
    ("CNL",  "Nhóm chất lượng nguyên liệu",   "NHOM",    "CL"),
    ("MIX",  "Tổ trộn mix",                   "TO",      "CL"),
    ("CLGS", "Nhóm chất lượng thành phẩm gia súc",   "NHOM", "CL"),
    ("CLTS", "Nhóm chất lượng thành phẩm thủy sản",  "NHOM", "CL"),
    ("PTN",  "Phòng thí nghiệm",              "PHONG",   "CL"),
    # ── Con của PT ─────────────────────────────────────────────────────────
    ("BTT",  "Bộ phận bảo trì trại",          "BO_PHAN", "PT"),
    ("APT",  "Bộ phận Admin trại",            "BO_PHAN", "PT"),
    ("GSB",  "Bộ phận giám sát bán",          "BO_PHAN", "PT"),
    ("LXT",  "Tổ lái xe trại",                "TO",      "PT"),
    ("DTT",  "Bộ phận dịch tễ trại",          "BO_PHAN", "PT"),
]


async def _get_title_id(session: AsyncSession, code: str) -> int | None:
    result = await session.execute(
        text("SELECT id FROM job_titles WHERE code = :code"), {"code": code}
    )
    row = result.fetchone()
    return row[0] if row else None


async def seed_job_titles(session: AsyncSession) -> int:
    inserted = 0
    for t in JOB_TITLES:
        result = await session.execute(
            text("""
                INSERT INTO job_titles (code, name, level, is_active)
                VALUES (:code, :name, :level, true)
                ON CONFLICT (code) DO NOTHING
            """),
            t,
        )
        inserted += result.rowcount
    return inserted


async def seed_salary_scale(session: AsyncSession) -> int:
    result = await session.execute(
        text("""
            INSERT INTO salary_scales (name, effective_from, effective_to, note)
            VALUES (:name, :effective_from, NULL, :note)
            ON CONFLICT DO NOTHING
            RETURNING id
        """),
        {
            "name": "Thang bảng lương 2026",
            "effective_from": datetime.date(2026, 1, 1),
            "note": "Xây dựng theo NĐ 293/2025/NĐ-CP — LTTV Vùng III: 4.140.000 ₫",
        },
    )
    row = result.fetchone()
    if not row:
        existing = await session.execute(
            text("SELECT id FROM salary_scales WHERE name = 'Thang bảng lương 2026'")
        )
        scale_id = existing.fetchone()[0]
        return 0

    scale_id = row[0]
    entries_inserted = 0

    for title_code, coefficients in SCALE_ENTRIES.items():
        title_id = await _get_title_id(session, title_code)
        if not title_id:
            continue
        for grade_no, coefficient in enumerate(coefficients, start=1):
            r = await session.execute(
                text("""
                    INSERT INTO salary_scale_entries
                        (salary_scale_id, job_title_id, grade_no, coefficient,
                         promotion_months, criteria)
                    VALUES
                        (:scale_id, :title_id, :grade_no, :coefficient,
                         :promo_months, :criteria)
                    ON CONFLICT (salary_scale_id, job_title_id, grade_no) DO NOTHING
                """),
                {
                    "scale_id": scale_id,
                    "title_id": title_id,
                    "grade_no": grade_no,
                    "coefficient": coefficient,
                    "promo_months": 12,
                    "criteria": (
                        f"Bậc {grade_no}: hoàn thành tốt nhiệm vụ được giao, "
                        "không vi phạm nội quy trong 12 tháng liên tiếp"
                    ),
                },
            )
            entries_inserted += r.rowcount

    return entries_inserted


async def seed_departments(session: AsyncSession) -> int:
    inserted = 0
    code_to_id: dict[str, int] = {}

    # Lần 1: chèn cấp gốc (parent = None)
    for order_no, (code, name, dept_type, parent_code) in enumerate(DEPARTMENTS, start=1):
        if parent_code is not None:
            continue
        result = await session.execute(
            text("""
                INSERT INTO departments
                    (code, name, short_name, parent_id, dept_type, order_no, is_active)
                VALUES (:code, :name, NULL, NULL, :dept_type, :order_no, true)
                ON CONFLICT (code) DO NOTHING
                RETURNING id, code
            """),
            {"code": code, "name": name, "dept_type": dept_type, "order_no": order_no},
        )
        row = result.fetchone()
        if row:
            code_to_id[row[1]] = row[0]
            inserted += 1

    # Nạp lại id những dòng đã tồn tại trước đó (để làm parent_id cho cấp con)
    for code, *_ in DEPARTMENTS:
        if code not in code_to_id:
            r = await session.execute(
                text("SELECT id FROM departments WHERE code = :code"), {"code": code}
            )
            row = r.fetchone()
            if row:
                code_to_id[code] = row[0]

    # Lần 2: chèn cấp con (có parent)
    for order_no, (code, name, dept_type, parent_code) in enumerate(DEPARTMENTS, start=1):
        if parent_code is None:
            continue
        parent_id = code_to_id.get(parent_code)
        if not parent_id:
            print(f"    ⚠ Bỏ qua '{code}': không tìm thấy parent '{parent_code}'")
            continue
        result = await session.execute(
            text("""
                INSERT INTO departments
                    (code, name, short_name, parent_id, dept_type, order_no, is_active)
                VALUES (:code, :name, NULL, :parent_id, :dept_type, :order_no, true)
                ON CONFLICT (code) DO NOTHING
                RETURNING id, code
            """),
            {
                "code": code, "name": name, "dept_type": dept_type,
                "parent_id": parent_id, "order_no": order_no,
            },
        )
        row = result.fetchone()
        if row:
            code_to_id[row[1]] = row[0]
            inserted += 1

    return inserted


async def run(session: AsyncSession) -> None:
    titles = await seed_job_titles(session)
    await session.flush()

    scale_entries = await seed_salary_scale(session)
    await session.flush()

    depts = await seed_departments(session)
    institutions_added, majors_added = await education_catalog.seed_sample_education_catalog(session)
    (
        skills_added,
        certificates_added,
        templates_added,
        placeholders_added,
    ) = await other_business_catalog.seed_sample_other_business_catalog(session)
    emps_added = await employees_seed.seed_sample_employees(session)
    await session.flush()
    job_records_added = await job_records_seed.seed_sample_job_records(session)
    await session.flush()
    relatives_added = await relatives_seed.seed_sample_relatives(session)
    print(f"  [sample] Người thân mẫu:    +{relatives_added} dòng")
    await session.commit()

    print(f"  [sample] Chức danh:        +{titles} dòng")
    print(f"  [sample] Hệ số bậc lương:  +{scale_entries} dòng")
    print(f"  [sample] Phòng/ban:         +{depts} dòng")
    print(f"  [sample] Trường học:        +{institutions_added} upsert")
    print(f"  [sample] Chuyên ngành:      +{majors_added} upsert")
    print(f"  [sample] Kỹ năng:           +{skills_added} upsert")
    print(f"  [sample] Chứng chỉ:         +{certificates_added} upsert")
    print(f"  [sample] Mẫu hợp đồng:      +{templates_added} upsert")
    print(f"  [sample] Placeholder mẫu:   +{placeholders_added} upsert")
    print(f"  [sample] Nhân viên mẫu:     +{emps_added} dòng")
    print(f"  [sample] Bản ghi công việc: +{job_records_added} dòng")
