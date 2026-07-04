"""
Dữ liệu bootstrap vận hành.

Phân lớp:
  - Không phải baseline hệ thống bắt buộc cho mọi tenant
  - Không phải sample/test data
  - Dùng để khởi tạo nhanh môi trường có thể vận hành ngay sau deploy

Hiện bao gồm:
  - job_titles
  - salary_scales / salary_scale_entries / bhxh_position_groups
  - departments
"""

import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


JOB_TITLES = [
    {"code": "CTHD",   "name": "Chủ tịch Hội đồng quản trị", "level": 1},
    {"code": "GD",     "name": "Giám đốc",                    "level": 2},
    {"code": "PDG",    "name": "Phó Giám đốc",                "level": 3},
    {"code": "TP",     "name": "Trưởng phòng",                "level": 4},
    {"code": "PP",     "name": "Phó phòng",                   "level": 5},
    {"code": "TBP",    "name": "Trưởng bộ phận",              "level": 6},
    {"code": "NVKD",   "name": "Nhân viên kinh doanh",        "level": 7},
    {"code": "NVKT_T", "name": "Nhân viên kỹ thuật trại",     "level": 7},
    {"code": "NVKT",   "name": "Nhân viên kỹ thuật",          "level": 7},
    {"code": "NV",     "name": "Nhân viên",                   "level": 8},
]

BHXH_POSITION_GROUPS = [
    {
        "code": "EXEC_COMPANY",
        "name": "Giám đốc Công ty và các vị trí tương đương",
        "description": "Nhóm điều hành cấp công ty cao nhất.",
        "coefficients": [2.68, 3.08, 3.54, 4.08, 4.98, 6.07, 7.41],
    },
    {
        "code": "EXEC_DEPUTY",
        "name": "Phó Giám đốc Công ty, Kế toán trưởng công ty, và các vị trí tương đương",
        "description": "Nhóm điều hành/phụ trách cấp công ty tương đương Phó Giám đốc.",
        "coefficients": [2.00, 2.42, 2.95, 3.60, 4.39, 5.36, 6.54],
    },
    {
        "code": "PROD_MANAGER",
        "name": "Giám đốc sản xuất, Trưởng phòng chuyên trách, Trưởng ban và các vị trí tương đương",
        "description": "Nhóm quản lý chuyên trách cấp phòng/ban hoặc tương đương.",
        "coefficients": [1.84, 2.02, 2.23, 2.45, 2.69, 2.96, 3.26],
    },
    {
        "code": "PROD_DEPUTY",
        "name": "Phó Giám đốc sản xuất, Phó trưởng phòng, Giám đốc vùng, phó ban, và các vị trí tương đương",
        "description": "Nhóm quản lý/phó quản lý khối sản xuất và vùng.",
        "coefficients": [1.70, 1.82, 1.95, 2.10, 2.29, 2.50, 2.72],
    },
    {
        "code": "SUPERVISOR",
        "name": "Trưởng ca sản xuất, Trưởng vùng, giám sát, quản lý trại, và các vị trí tương đương",
        "description": "Nhóm giám sát, trưởng ca, quản lý tuyến đầu.",
        "coefficients": [1.50, 1.61, 1.72, 1.84, 1.97, 2.10, 2.27],
    },
    {
        "code": "TECH_MAINTENANCE",
        "name": "Nhân viên vận hành máy Sản xuất, cơ điện, bảo trì, và các vị trí tương đương",
        "description": "Nhóm kỹ thuật vận hành, cơ điện, bảo trì.",
        "coefficients": [1.14, 1.25, 1.38, 1.52, 1.67, 1.84, 2.02],
    },
    {
        "code": "TECH_SPECIALIST",
        "name": "Nhân viên Kỹ thuật, dinh dưỡng, phân tích, KCS và các vị trí tương đương",
        "description": "Nhóm kỹ thuật chuyên môn, phân tích, KCS.",
        "coefficients": [1.14, 1.20, 1.27, 1.36, 1.47, 1.58, 1.71],
    },
    {
        "code": "OFFICE_STAFF",
        "name": "Nhân viên Kế toán, Hành chính, Thu mua, Kinh doanh, Thủ kho, kỹ thuật thị trường, kỹ thuật trại, đại diện bán hàng, và các vị trí tương đương",
        "description": "Nhóm nhân viên nghiệp vụ văn phòng/thị trường.",
        "coefficients": [1.10, 1.16, 1.22, 1.31, 1.41, 1.53, 1.67],
    },
    {
        "code": "DRIVER",
        "name": "Lái xe con, lái xe nâng <3,5 tấn",
        "description": "Nhóm lái xe con và lái xe nâng nhẹ.",
        "coefficients": [1.14, 1.20, 1.27, 1.34, 1.44, 1.54, 1.69],
    },
    {
        "code": "WORKER_SERVICE",
        "name": "Công nhân sản xuất, Nhân viên Bảo vệ, Phục vụ bếp ăn, và các vị trí tương đương",
        "description": "Nhóm công nhân sản xuất và phục vụ hỗ trợ.",
        "coefficients": [1.08, 1.14, 1.20, 1.27, 1.35, 1.43, 1.52],
    },
    {
        "code": "JANITOR",
        "name": "Nhân viên tạp vụ, và các vị trí tương đương",
        "description": "Nhóm tạp vụ và vị trí tương đương.",
        "coefficients": [1.00, 1.05, 1.10, 1.16, 1.22, 1.29, 1.37],
    },
]

DEPARTMENTS = [
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
    ("IT",   "Bộ phận IT",                    "BO_PHAN", "KS"),
    ("KSNB", "Bộ phận kiểm soát nội bộ",      "BO_PHAN", "KS"),
    ("BV",   "Ban bảo vệ",                    "BAN",     "HC"),
    ("LXNM", "Tổ lái xe nhà máy",             "TO",      "HC"),
    ("TV",   "Tổ tạp vụ",                     "TO",      "HC"),
    ("NB",   "Tổ nhà bếp",                    "TO",      "HC"),
    ("TR",   "Tổ trồng rau",                  "TO",      "HC"),
    ("KTT",  "Bộ phận kỹ thuật trại",         "BO_PHAN", "KD"),
    ("KTTT", "Bộ phận kỹ thuật thị trường",   "BO_PHAN", "KD"),
    ("AKD",  "Bộ phận Admin kinh doanh",      "BO_PHAN", "KD"),
    ("BH",   "Bộ phận bán hàng",              "BO_PHAN", "PK"),
    ("CAN",  "Bộ phận cân",                   "BO_PHAN", "PK"),
    ("ATM",  "Bộ phận Admin thu mua",         "BO_PHAN", "TM"),
    ("KTK",  "Tổ kế toán kho",                "TO",      "KH"),
    ("KNL",  "Tổ kho nguyên liệu",            "TO",      "KH"),
    ("KTP",  "Tổ kho thành phẩm",             "TO",      "KH"),
    ("KTTY", "Tổ kho thuốc thú y",            "TO",      "KH"),
    ("BTC",  "Tổ bảo trì cơ",                 "TO",      "BT"),
    ("BTD",  "Tổ bảo trì điện",               "TO",      "BT"),
    ("GSGC", "Bộ phận sản xuất gia súc gia cầm", "BO_PHAN", "SX"),
    ("TS",   "Bộ phận sản xuất thủy sản",     "BO_PHAN", "SX"),
    ("CNL",  "Nhóm chất lượng nguyên liệu",   "NHOM",    "CL"),
    ("MIX",  "Tổ trộn mix",                   "TO",      "CL"),
    ("CLGS", "Nhóm chất lượng thành phẩm gia súc",   "NHOM", "CL"),
    ("CLTS", "Nhóm chất lượng thành phẩm thủy sản",  "NHOM", "CL"),
    ("PTN",  "Phòng thí nghiệm",              "PHONG",   "CL"),
    ("BTT",  "Bộ phận bảo trì trại",          "BO_PHAN", "PT"),
    ("APT",  "Bộ phận Admin trại",            "BO_PHAN", "PT"),
    ("GSB",  "Bộ phận giám sát bán",          "BO_PHAN", "PT"),
    ("LXT",  "Tổ lái xe trại",                "TO",      "PT"),
    ("DTT",  "Bộ phận dịch tễ trại",          "BO_PHAN", "PT"),
]


async def seed_job_titles(session: AsyncSession) -> int:
    inserted = 0
    for t in JOB_TITLES:
        result = await session.execute(
            text("""
                INSERT INTO job_titles (code, name, level, is_active)
                VALUES (:code, :name, :level, true)
                ON CONFLICT (code) WHERE deleted_at IS NULL DO NOTHING
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
    if row:
        scale_id = row[0]
    else:
        existing = await session.execute(
            text("SELECT id FROM salary_scales WHERE name = 'Thang bảng lương 2026'")
        )
        scale_id = existing.fetchone()[0]

    group_ids: dict[str, int] = {}
    groups_inserted = 0
    entries_inserted = 0

    for group in BHXH_POSITION_GROUPS:
        insert_group = await session.execute(
            text("""
                INSERT INTO bhxh_position_groups
                    (code, name, description, is_active)
                VALUES
                    (:code, :name, :description, TRUE)
                ON CONFLICT (code) DO NOTHING
                RETURNING id
            """),
            {
                "code": group["code"],
                "name": group["name"],
                "description": group["description"],
            },
        )
        inserted_row = insert_group.fetchone()
        if inserted_row:
            group_ids[group["code"]] = inserted_row[0]
            groups_inserted += 1

    for group in BHXH_POSITION_GROUPS:
        if group["code"] in group_ids:
            continue
        existing_group = await session.execute(
            text("SELECT id FROM bhxh_position_groups WHERE code = :code"),
            {"code": group["code"]},
        )
        row = existing_group.fetchone()
        if row:
            group_ids[group["code"]] = row[0]

    for group in BHXH_POSITION_GROUPS:
        group_id = group_ids.get(group["code"])
        if not group_id:
            continue
        for grade_no, coefficient in enumerate(group["coefficients"], start=1):
            params = {
                "scale_id": scale_id,
                "group_id": group_id,
                "grade_no": grade_no,
                "coefficient": coefficient,
                "promo_months": 12,
                "criteria": (
                    f"Bậc {grade_no}: hoàn thành tốt nhiệm vụ được giao, "
                    "không vi phạm nội quy trong 12 tháng liên tiếp"
                ),
            }
            existing_entry = await session.execute(
                text("""
                    SELECT id
                    FROM salary_scale_entries
                    WHERE salary_scale_id = :scale_id
                      AND bhxh_position_group_id = :group_id
                      AND grade_no = :grade_no
                """),
                params,
            )
            row = existing_entry.fetchone()
            if row:
                r = await session.execute(
                    text("""
                        UPDATE salary_scale_entries
                        SET coefficient = :coefficient,
                            promotion_months = :promo_months,
                            criteria = :criteria
                        WHERE id = :entry_id
                    """),
                    {**params, "entry_id": row[0]},
                )
            else:
                r = await session.execute(
                    text("""
                        INSERT INTO salary_scale_entries
                            (salary_scale_id, job_title_id, bhxh_position_group_id,
                             grade_no, coefficient, promotion_months, criteria)
                        VALUES
                            (:scale_id, NULL, :group_id,
                             :grade_no, :coefficient, :promo_months, :criteria)
                    """),
                    params,
                )
            entries_inserted += r.rowcount

    if groups_inserted:
        print(f"  [bootstrap] Nhóm vị trí BHXH: +{groups_inserted} dòng")
    return entries_inserted


async def seed_departments(session: AsyncSession) -> int:
    inserted = 0
    code_to_id: dict[str, int] = {}

    for order_no, (code, name, dept_type, parent_code) in enumerate(DEPARTMENTS, start=1):
        if parent_code is not None:
            continue
        result = await session.execute(
            text("""
                INSERT INTO departments
                    (code, name, short_name, parent_id, dept_type, order_no, is_active)
                VALUES (:code, :name, NULL, NULL, :dept_type, :order_no, true)
                ON CONFLICT (code) WHERE deleted_at IS NULL DO NOTHING
                RETURNING id, code
            """),
            {"code": code, "name": name, "dept_type": dept_type, "order_no": order_no},
        )
        row = result.fetchone()
        if row:
            code_to_id[row[1]] = row[0]
            inserted += 1

    for code, *_ in DEPARTMENTS:
        if code not in code_to_id:
            r = await session.execute(
                text("SELECT id FROM departments WHERE code = :code"), {"code": code}
            )
            row = r.fetchone()
            if row:
                code_to_id[code] = row[0]

    for order_no, (code, name, dept_type, parent_code) in enumerate(DEPARTMENTS, start=1):
        if parent_code is None:
            continue
        parent_id = code_to_id.get(parent_code)
        if not parent_id:
            continue
        result = await session.execute(
            text("""
                INSERT INTO departments
                    (code, name, short_name, parent_id, dept_type, order_no, is_active)
                VALUES (:code, :name, NULL, :parent_id, :dept_type, :order_no, true)
                ON CONFLICT (code) WHERE deleted_at IS NULL DO NOTHING
                RETURNING id, code
            """),
            {
                "code": code,
                "name": name,
                "dept_type": dept_type,
                "parent_id": parent_id,
                "order_no": order_no,
            },
        )
        row = result.fetchone()
        if row:
            code_to_id[row[1]] = row[0]
            inserted += 1

    return inserted


async def seed_job_positions(session: AsyncSession) -> int:
    # Bootstrap defaults for legal probation grouping.
    # These values are operational presets for the small baseline position set and
    # should be reviewed against real job requirements of each tenant/company.
    positions = [
        {
            "code": "CT_HDQT",
            "name": "Chủ tịch HĐQT",
            "dept_code": "LD",
            "title_code": "CTHD",
            "probation_legal_group": "enterprise_manager",
        },
        {
            "code": "NV_IT",
            "name": "Nhân viên IT",
            "dept_code": "IT",
            "title_code": "NV",
            "probation_legal_group": "college_plus",
        },
        {
            "code": "NV_KSNB",
            "name": "Nhân viên kiểm soát nội bộ",
            "dept_code": "KSNB",
            "title_code": "NV",
            "probation_legal_group": "college_plus",
        },
        {
            "code": "CV_IT",
            "name": "Chuyên viên IT",
            "dept_code": "IT",
            "title_code": "NVKT",
            "probation_legal_group": "college_plus",
        },
        {
            "code": "TN_KSNB",
            "name": "Trưởng nhóm kiểm soát nội bộ",
            "dept_code": "KSNB",
            "title_code": "TBP",
            "probation_legal_group": "college_plus",
        },
        {
            "code": "TP_KSNB",
            "name": "Trưởng phòng kiểm soát nội bộ",
            "dept_code": "KS",
            "title_code": "TP",
            "probation_legal_group": "college_plus",
        },
    ]

    inserted = 0
    for pos in positions:
        # Lấy department_id
        r_dept = await session.execute(
            text("SELECT id FROM departments WHERE code = :code AND deleted_at IS NULL"),
            {"code": pos["dept_code"]}
        )
        dept_id = r_dept.scalar()
        if not dept_id:
            continue

        # Lấy job_title_id
        title_id = None
        if pos["title_code"]:
            r_title = await session.execute(
                text("SELECT id FROM job_titles WHERE code = :code AND deleted_at IS NULL"),
                {"code": pos["title_code"]}
            )
            title_id = r_title.scalar()

        # Check if position code exists
        existing = await session.execute(
            text("SELECT id FROM job_positions WHERE code = :code AND deleted_at IS NULL"),
            {"code": pos["code"]}
        )
        row = existing.fetchone()
        if row:
            r = await session.execute(
                text("""
                    UPDATE job_positions
                    SET name = :name,
                        department_id = :department_id,
                        job_title_id = :job_title_id,
                        probation_legal_group = :probation_legal_group,
                        is_active = true,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {
                    "id": row[0],
                    "name": pos["name"],
                    "department_id": dept_id,
                    "job_title_id": title_id,
                    "probation_legal_group": pos["probation_legal_group"],
                }
            )
        else:
            r = await session.execute(
                text("""
                    INSERT INTO job_positions
                        (code, name, department_id, job_title_id, default_grade,
                         bhxh_allowance, non_bhxh_allowance, probation_legal_group,
                         is_active, created_at)
                    VALUES
                        (:code, :name, :department_id, :job_title_id, 1,
                         0, 0, :probation_legal_group, true, CURRENT_TIMESTAMP)
                """),
                {
                    "code": pos["code"],
                    "name": pos["name"],
                    "department_id": dept_id,
                    "job_title_id": title_id,
                    "probation_legal_group": pos["probation_legal_group"],
                }
            )
        inserted += r.rowcount

        await session.execute(
            text("""
                INSERT INTO department_job_positions
                    (department_id, job_position_id, is_active, created_at, updated_at)
                SELECT
                    :department_id,
                    jp.id,
                    true,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                FROM job_positions jp
                WHERE jp.code = :code
                  AND jp.deleted_at IS NULL
                ON CONFLICT (department_id, job_position_id)
                DO UPDATE SET
                    is_active = true,
                    updated_at = CURRENT_TIMESTAMP
            """),
            {
                "department_id": dept_id,
                "code": pos["code"],
            },
        )

    return inserted


async def run(session: AsyncSession) -> None:
    titles = await seed_job_titles(session)
    await session.flush()

    scale_entries = await seed_salary_scale(session)
    await session.flush()

    departments = await seed_departments(session)
    await session.flush()

    positions = await seed_job_positions(session)
    await session.commit()

    print(f"  [bootstrap] Chức danh:        +{titles} dòng")
    print(f"  [bootstrap] Hệ số bậc lương:  +{scale_entries} dòng")
    print(f"  [bootstrap] Phòng/ban:        +{departments} dòng")
    print(f"  [bootstrap] Vị trí công việc: +{positions} dòng")
