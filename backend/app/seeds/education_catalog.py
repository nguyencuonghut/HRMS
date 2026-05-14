"""
Seed dữ liệu danh mục học vấn.

Phân lớp:
  - Required: trình độ học vấn chuẩn hóa, dùng ở mọi môi trường
  - Sample: trường học + chuyên ngành mẫu phù hợp doanh nghiệp sản xuất thức ăn chăn nuôi,
            trang trại chăn nuôi và xuất nhập khẩu nông nghiệp
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


EDUCATION_LEVELS = [
    {"code": "primary_school", "name": "Tiểu học", "rank_no": 1},
    {"code": "secondary_school", "name": "THCS", "rank_no": 2},
    {"code": "high_school", "name": "THPT", "rank_no": 3},
    {"code": "intermediate", "name": "Trung cấp", "rank_no": 4},
    {"code": "college", "name": "Cao đẳng", "rank_no": 5},
    {"code": "bachelor", "name": "Đại học", "rank_no": 6},
    {"code": "master", "name": "Thạc sĩ", "rank_no": 7},
    {"code": "doctor", "name": "Tiến sĩ", "rank_no": 8},
]


EDUCATIONAL_INSTITUTIONS = [
    {
        "code": "VNUA",
        "name": "Học viện Nông nghiệp Việt Nam",
        "short_name": "HV Nông nghiệp VN",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "NLU_HCMC",
        "name": "Trường Đại học Nông Lâm Thành phố Hồ Chí Minh",
        "short_name": "ĐH Nông Lâm TP.HCM",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "CTU",
        "name": "Trường Đại học Cần Thơ",
        "short_name": "ĐH Cần Thơ",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "HUAF",
        "name": "Trường Đại học Nông Lâm, Đại học Huế",
        "short_name": "ĐH Nông Lâm Huế",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "TNUAF",
        "name": "Trường Đại học Nông Lâm, Đại học Thái Nguyên",
        "short_name": "ĐH Nông Lâm Thái Nguyên",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "VNUF",
        "name": "Trường Đại học Lâm nghiệp",
        "short_name": "ĐH Lâm nghiệp",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "TUAF",
        "name": "Trường Đại học Tây Nguyên",
        "short_name": "ĐH Tây Nguyên",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "NTU",
        "name": "Trường Đại học Nha Trang",
        "short_name": "ĐH Nha Trang",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "FTU",
        "name": "Trường Đại học Ngoại thương",
        "short_name": "ĐH Ngoại thương",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "NEU",
        "name": "Trường Đại học Kinh tế Quốc dân",
        "short_name": "ĐH Kinh tế Quốc dân",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "HCMUT",
        "name": "Trường Đại học Bách khoa, Đại học Quốc gia Thành phố Hồ Chí Minh",
        "short_name": "ĐH Bách khoa TP.HCM",
        "institution_type": "university",
        "country_code": "VN",
        "province_code": None,
    },
    {
        "code": "CAE_NAMBO",
        "name": "Trường Cao đẳng Cơ điện và Nông nghiệp Nam Bộ",
        "short_name": "CĐ Cơ điện NN Nam Bộ",
        "institution_type": "college",
        "country_code": "VN",
        "province_code": None,
    },
]


EDUCATION_MAJORS = [
    {"code": "animal_husbandry", "name": "Chăn nuôi", "major_group": "animal_science"},
    {"code": "veterinary_medicine", "name": "Thú y", "major_group": "veterinary"},
    {"code": "feed_nutrition", "name": "Dinh dưỡng và thức ăn chăn nuôi", "major_group": "animal_science"},
    {"code": "aquaculture", "name": "Nuôi trồng thủy sản", "major_group": "aquaculture"},
    {"code": "aquatic_pathology", "name": "Bệnh học thủy sản", "major_group": "aquaculture"},
    {"code": "biotechnology", "name": "Công nghệ sinh học", "major_group": "science"},
    {"code": "food_technology", "name": "Công nghệ thực phẩm", "major_group": "processing"},
    {"code": "agronomy", "name": "Nông học", "major_group": "agriculture"},
    {"code": "crop_science", "name": "Khoa học cây trồng", "major_group": "agriculture"},
    {"code": "plant_protection", "name": "Bảo vệ thực vật", "major_group": "agriculture"},
    {"code": "agricultural_economics", "name": "Kinh tế nông nghiệp", "major_group": "business"},
    {"code": "international_business", "name": "Kinh doanh quốc tế", "major_group": "business"},
    {"code": "import_export", "name": "Xuất nhập khẩu", "major_group": "supply_chain"},
    {"code": "logistics_supply_chain", "name": "Logistics và quản lý chuỗi cung ứng", "major_group": "supply_chain"},
    {"code": "quality_management", "name": "Quản lý chất lượng", "major_group": "quality"},
    {"code": "analytical_chemistry", "name": "Hóa phân tích", "major_group": "quality"},
    {"code": "mechanical_engineering", "name": "Cơ khí", "major_group": "engineering"},
    {"code": "industrial_electrical", "name": "Điện công nghiệp", "major_group": "engineering"},
    {"code": "automation_engineering", "name": "Tự động hóa", "major_group": "engineering"},
    {"code": "accounting", "name": "Kế toán", "major_group": "business"},
    {"code": "finance_banking", "name": "Tài chính - Ngân hàng", "major_group": "business"},
    {"code": "business_administration", "name": "Quản trị kinh doanh", "major_group": "business"},
]


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


async def seed_required_education_catalog(session: AsyncSession) -> int:
    inserted = 0
    for item in EDUCATION_LEVELS:
        result = await session.execute(
            text(
                """
                INSERT INTO education_levels (code, name, normalized_name, rank_no, is_active)
                VALUES (:code, :name, :normalized_name, :rank_no, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    rank_no = EXCLUDED.rank_no,
                    is_active = true
                """
            ),
            {
                **item,
                "normalized_name": _normalize(item["name"]),
            },
        )
        inserted += result.rowcount
    return inserted


async def seed_sample_education_catalog(session: AsyncSession) -> tuple[int, int]:
    institutions_added = 0
    majors_added = 0

    for item in EDUCATIONAL_INSTITUTIONS:
        result = await session.execute(
            text(
                """
                INSERT INTO educational_institutions
                    (code, name, normalized_name, short_name, institution_type, country_code, province_code, is_active)
                VALUES
                    (:code, :name, :normalized_name, :short_name, :institution_type, :country_code, :province_code, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    short_name = EXCLUDED.short_name,
                    institution_type = EXCLUDED.institution_type,
                    country_code = EXCLUDED.country_code,
                    province_code = EXCLUDED.province_code,
                    is_active = true
                """
            ),
            {
                **item,
                "normalized_name": _normalize(item["name"]),
            },
        )
        institutions_added += result.rowcount

    for item in EDUCATION_MAJORS:
        result = await session.execute(
            text(
                """
                INSERT INTO education_majors
                    (code, name, normalized_name, major_group, is_active)
                VALUES
                    (:code, :name, :normalized_name, :major_group, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    major_group = EXCLUDED.major_group,
                    is_active = true
                """
            ),
            {
                **item,
                "normalized_name": _normalize(item["name"]),
            },
        )
        majors_added += result.rowcount

    return institutions_added, majors_added
