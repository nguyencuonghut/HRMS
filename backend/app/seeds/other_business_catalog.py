"""
Seed dữ liệu danh mục nghiệp vụ khác.

Phân lớp:
  - Required: loại hợp đồng, quốc tịch, dân tộc, tôn giáo, ngân hàng, loại nghỉ phép
  - Sample: kỹ năng, chứng chỉ, metadata mẫu hợp đồng/phụ lục và placeholder mẫu
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.administrative_import_service import normalize_text


CONTRACT_CATEGORIES = [
    {
        "code": "labor_indefinite",
        "name": "HĐLĐ không xác định thời hạn",
        "document_kind": "labor_contract",
        "legal_contract_type": "indefinite_term",
        "business_group": "standard",
        "default_term_months": None,
        "sort_order": 10,
        "description": "Mẫu dùng cho hợp đồng lao động không xác định thời hạn.",
    },
    {
        "code": "labor_definite",
        "name": "HĐLĐ xác định thời hạn",
        "document_kind": "labor_contract",
        "legal_contract_type": "definite_term",
        "business_group": "standard",
        "default_term_months": 12,
        "sort_order": 20,
        "description": "Mẫu dùng cho hợp đồng lao động xác định thời hạn.",
    },
    {
        "code": "appendix_salary_change",
        "name": "Phụ lục điều chỉnh lương",
        "document_kind": "contract_appendix",
        "legal_contract_type": None,
        "business_group": "salary_change",
        "default_term_months": None,
        "sort_order": 30,
        "description": "Phụ lục ghi nhận thay đổi mức lương và phụ cấp trong hợp đồng.",
    },
    {
        "code": "appendix_job_change",
        "name": "Phụ lục điều chỉnh chức danh/công việc",
        "document_kind": "contract_appendix",
        "legal_contract_type": None,
        "business_group": "job_change",
        "default_term_months": None,
        "sort_order": 40,
        "description": "Phụ lục thay đổi chức danh, công việc hoặc nơi làm việc.",
    },
]


NATIONALITIES = [
    {"code": "VN", "name": "Việt Nam", "iso2_code": "VN", "iso3_code": "VNM"},
    {"code": "CN", "name": "Trung Quốc", "iso2_code": "CN", "iso3_code": "CHN"},
    {"code": "KR", "name": "Hàn Quốc", "iso2_code": "KR", "iso3_code": "KOR"},
    {"code": "JP", "name": "Nhật Bản", "iso2_code": "JP", "iso3_code": "JPN"},
    {"code": "TH", "name": "Thái Lan", "iso2_code": "TH", "iso3_code": "THA"},
    {"code": "PH", "name": "Philippines", "iso2_code": "PH", "iso3_code": "PHL"},
    {"code": "ID", "name": "Indonesia", "iso2_code": "ID", "iso3_code": "IDN"},
    {"code": "IN", "name": "Ấn Độ", "iso2_code": "IN", "iso3_code": "IND"},
]


ETHNICITIES = [
    {"code": "KINH", "name": "Kinh"},
    {"code": "TAY", "name": "Tày"},
    {"code": "THAI", "name": "Thái"},
    {"code": "MUONG", "name": "Mường"},
    {"code": "NUNG", "name": "Nùng"},
    {"code": "HMONG", "name": "H'Mông"},
    {"code": "HOA", "name": "Hoa"},
    {"code": "KHMER", "name": "Khmer"},
]


RELIGIONS = [
    {"code": "NONE", "name": "Không"},
    {"code": "PHAT_GIAO", "name": "Phật giáo"},
    {"code": "CONG_GIAO", "name": "Công giáo"},
    {"code": "TINH_LANH", "name": "Tin Lành"},
    {"code": "CAO_DAI", "name": "Cao Đài"},
    {"code": "HOA_HAO", "name": "Phật giáo Hòa Hảo"},
]


BANKS = [
    {"code": "AGRIBANK", "name": "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", "short_name": "Agribank", "bin_code": "970405", "swift_code": "VBAAVNVX"},
    {"code": "VCB", "name": "Ngân hàng TMCP Ngoại thương Việt Nam", "short_name": "Vietcombank", "bin_code": "970436", "swift_code": "BFTVVNVX"},
    {"code": "BIDV", "name": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "short_name": "BIDV", "bin_code": "970418", "swift_code": "BIDVVNVX"},
    {"code": "VIETINBANK", "name": "Ngân hàng TMCP Công thương Việt Nam", "short_name": "VietinBank", "bin_code": "970415", "swift_code": "ICBVVNVX"},
    {"code": "TECHCOMBANK", "name": "Ngân hàng TMCP Kỹ thương Việt Nam", "short_name": "Techcombank", "bin_code": "970407", "swift_code": "VTCBVNVX"},
    {"code": "MB", "name": "Ngân hàng TMCP Quân đội", "short_name": "MB Bank", "bin_code": "970422", "swift_code": "MSCBVNVX"},
    {"code": "ACB", "name": "Ngân hàng TMCP Á Châu", "short_name": "ACB", "bin_code": "970416", "swift_code": None},
    {"code": "SACOMBANK", "name": "Ngân hàng TMCP Sài Gòn Thương Tín", "short_name": "Sacombank", "bin_code": "970403", "swift_code": "SGTTVNVX"},
]


LEAVE_TYPES = [
    {
        "code": "annual_leave",
        "name": "Phép năm",
        "is_paid_leave": True,
        "affects_annual_leave": True,
        "allow_half_day": True,
        "requires_attachment": False,
        "color_tag": "green",
        "description": "Nghỉ phép năm theo số dư phép của nhân viên.",
    },
    {
        "code": "sick_leave",
        "name": "Nghỉ bệnh",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": True,
        "requires_attachment": True,
        "color_tag": "orange",
        "description": "Nghỉ bệnh có thể cần giấy tờ y tế đính kèm.",
    },
    {
        "code": "maternity_leave",
        "name": "Nghỉ thai sản",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": True,
        "color_tag": "pink",
        "description": "Nghỉ thai sản theo chế độ BHXH.",
    },
    {
        "code": "bereavement_leave",
        "name": "Nghỉ tang",
        "is_paid_leave": True,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": False,
        "color_tag": "slate",
        "description": "Nghỉ tang theo quy định nội bộ và pháp luật.",
    },
    {
        "code": "marriage_leave",
        "name": "Nghỉ cưới",
        "is_paid_leave": True,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": False,
        "color_tag": "violet",
        "description": "Nghỉ cưới theo quy định nội bộ và pháp luật.",
    },
    {
        "code": "unpaid_leave",
        "name": "Nghỉ không lương",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": True,
        "requires_attachment": False,
        "color_tag": "gray",
        "description": "Nghỉ không hưởng lương theo thỏa thuận.",
    },
]


SKILLS = [
    {"code": "production_operation", "name": "Vận hành sản xuất", "skill_group": "production"},
    {"code": "feed_formulation", "name": "Xây dựng công thức thức ăn chăn nuôi", "skill_group": "production"},
    {"code": "raw_material_testing", "name": "Kiểm nghiệm nguyên liệu", "skill_group": "quality"},
    {"code": "qa_qc", "name": "QA/QC", "skill_group": "quality"},
    {"code": "farm_management", "name": "Quản lý trang trại", "skill_group": "farm"},
    {"code": "biosecurity", "name": "An toàn sinh học", "skill_group": "farm"},
    {"code": "veterinary_practice", "name": "Nghiệp vụ thú y", "skill_group": "farm"},
    {"code": "import_export_ops", "name": "Nghiệp vụ xuất nhập khẩu", "skill_group": "supply_chain"},
    {"code": "customs_declaration", "name": "Khai báo hải quan", "skill_group": "supply_chain"},
    {"code": "logistics_planning", "name": "Điều phối logistics", "skill_group": "supply_chain"},
]


CERTIFICATES = [
    {
        "code": "OSH",
        "name": "Chứng nhận An toàn vệ sinh lao động",
        "certificate_group": "safety",
        "issuer_name": "Đơn vị đào tạo được cấp phép",
        "expiry_policy": "months_after_issue",
        "default_valid_months": 24,
    },
    {
        "code": "HACCP",
        "name": "Chứng nhận HACCP",
        "certificate_group": "quality",
        "issuer_name": "Tổ chức chứng nhận phù hợp",
        "expiry_policy": "fixed_date",
        "default_valid_months": 36,
    },
    {
        "code": "ISO_22000",
        "name": "Chứng nhận ISO 22000",
        "certificate_group": "quality",
        "issuer_name": "Tổ chức chứng nhận phù hợp",
        "expiry_policy": "fixed_date",
        "default_valid_months": 36,
    },
    {
        "code": "VETERINARY_PRACTICE",
        "name": "Chứng chỉ hành nghề thú y",
        "certificate_group": "farm",
        "issuer_name": "Cơ quan có thẩm quyền",
        "expiry_policy": "fixed_date",
        "default_valid_months": 60,
    },
    {
        "code": "CUSTOMS_DECLARATION",
        "name": "Chứng chỉ nghiệp vụ khai báo hải quan",
        "certificate_group": "supply_chain",
        "issuer_name": "Cơ sở đào tạo được công nhận",
        "expiry_policy": "none",
        "default_valid_months": None,
    },
]


CONTRACT_TEMPLATES = [
    {
        "code": "ld_indefinite",
        "name": "Mẫu HĐLĐ không xác định thời hạn",
        "contract_category_code": "labor_indefinite",
        "document_kind": "labor_contract",
        "template_engine": "docx_placeholders",
        "file_name": "hdld_khong_xac_dinh_thoi_han_v1.docx",
        "storage_path": None,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Metadata seed ban đầu, chờ upload file mẫu Word thật.",
    },
    {
        "code": "ld_definite_12m",
        "name": "Mẫu HĐLĐ xác định thời hạn 12 tháng",
        "contract_category_code": "labor_definite",
        "document_kind": "labor_contract",
        "template_engine": "docx_placeholders",
        "file_name": "hdld_xac_dinh_thoi_han_12_thang_v1.docx",
        "storage_path": None,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Metadata seed ban đầu, chờ upload file mẫu Word thật.",
    },
    {
        "code": "appendix_salary_change",
        "name": "Mẫu phụ lục điều chỉnh lương",
        "contract_category_code": "appendix_salary_change",
        "document_kind": "contract_appendix",
        "template_engine": "docx_placeholders",
        "file_name": "phu_luc_dieu_chinh_luong_v1.docx",
        "storage_path": None,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Metadata seed ban đầu, chờ upload file mẫu Word thật.",
    },
]


CONTRACT_TEMPLATE_PLACEHOLDERS = {
    "ld_indefinite": [
        ("employee.full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 10),
        ("employee.date_of_birth", "Ngày sinh", "employee", "employee.date_of_birth", "date", "vn_date", True, None, 20),
        ("employee.nationality", "Quốc tịch", "employee", "employee.nationality_name", "text", None, True, None, 30),
        ("employee.cccd_number", "Số CCCD", "employee", "employee.identity_number", "text", None, True, None, 40),
        ("employee.department_name", "Phòng ban", "employee", "employee.department_name", "text", None, True, None, 50),
        ("employee.position_name", "Vị trí công việc", "employee", "employee.position_name", "text", None, True, None, 60),
        ("contract.contract_number", "Số hợp đồng", "contract_draft", "contract.contract_number", "text", None, True, None, 70),
        ("contract.effective_date", "Ngày hiệu lực", "contract_draft", "contract.effective_date", "date", "vn_date", True, None, 80),
        ("contract.bhxh_salary", "Lương BHXH", "contract_draft", "contract.bhxh_salary", "currency", "currency_vnd", True, None, 90),
    ],
    "ld_definite_12m": [
        ("employee.full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 10),
        ("employee.department_name", "Phòng ban", "employee", "employee.department_name", "text", None, True, None, 20),
        ("contract.contract_number", "Số hợp đồng", "contract_draft", "contract.contract_number", "text", None, True, None, 30),
        ("contract.effective_date", "Ngày hiệu lực", "contract_draft", "contract.effective_date", "date", "vn_date", True, None, 40),
        ("contract.expired_at", "Ngày hết hạn", "contract_draft", "contract.expired_at", "date", "vn_date", True, None, 50),
    ],
    "appendix_salary_change": [
        ("employee.full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 10),
        ("contract.contract_number", "Số HĐ gốc", "contract_draft", "contract.contract_number", "text", None, True, None, 20),
        ("appendix.effective_date", "Ngày áp dụng", "contract_draft", "appendix.effective_date", "date", "vn_date", True, None, 30),
        ("appendix.old_salary", "Lương cũ", "contract_draft", "appendix.old_salary", "currency", "currency_vnd", True, None, 40),
        ("appendix.new_salary", "Lương mới", "contract_draft", "appendix.new_salary", "currency", "currency_vnd", True, None, 50),
    ],
}


def _normalize(value: str) -> str:
    return normalize_text(value)


async def seed_required_other_business_catalog(session: AsyncSession) -> tuple[int, int, int, int, int, int]:
    contract_categories_added = 0
    nationalities_added = 0
    ethnicities_added = 0
    religions_added = 0
    banks_added = 0
    leave_types_added = 0

    for item in CONTRACT_CATEGORIES:
        result = await session.execute(
            text(
                """
                INSERT INTO contract_categories
                    (code, name, normalized_name, document_kind, legal_contract_type, business_group,
                     default_term_months, sort_order, is_active, description)
                VALUES
                    (:code, :name, :normalized_name, :document_kind, :legal_contract_type, :business_group,
                     :default_term_months, :sort_order, true, :description)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    document_kind = EXCLUDED.document_kind,
                    legal_contract_type = EXCLUDED.legal_contract_type,
                    business_group = EXCLUDED.business_group,
                    default_term_months = EXCLUDED.default_term_months,
                    sort_order = EXCLUDED.sort_order,
                    is_active = true,
                    description = EXCLUDED.description
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        contract_categories_added += result.rowcount

    for item in NATIONALITIES:
        result = await session.execute(
            text(
                """
                INSERT INTO nationalities (code, name, normalized_name, iso2_code, iso3_code, is_active)
                VALUES (:code, :name, :normalized_name, :iso2_code, :iso3_code, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    iso2_code = EXCLUDED.iso2_code,
                    iso3_code = EXCLUDED.iso3_code,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        nationalities_added += result.rowcount

    for item in ETHNICITIES:
        result = await session.execute(
            text(
                """
                INSERT INTO ethnicities (code, name, normalized_name, is_active)
                VALUES (:code, :name, :normalized_name, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        ethnicities_added += result.rowcount

    for item in RELIGIONS:
        result = await session.execute(
            text(
                """
                INSERT INTO religions (code, name, normalized_name, is_active)
                VALUES (:code, :name, :normalized_name, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        religions_added += result.rowcount

    for item in BANKS:
        result = await session.execute(
            text(
                """
                INSERT INTO banks (code, name, normalized_name, short_name, bin_code, swift_code, is_active)
                VALUES (:code, :name, :normalized_name, :short_name, :bin_code, :swift_code, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    short_name = EXCLUDED.short_name,
                    bin_code = EXCLUDED.bin_code,
                    swift_code = EXCLUDED.swift_code,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        banks_added += result.rowcount

    for item in LEAVE_TYPES:
        result = await session.execute(
            text(
                """
                INSERT INTO leave_types
                    (code, name, normalized_name, is_paid_leave, affects_annual_leave, allow_half_day,
                     requires_attachment, color_tag, is_active, description)
                VALUES
                    (:code, :name, :normalized_name, :is_paid_leave, :affects_annual_leave, :allow_half_day,
                     :requires_attachment, :color_tag, true, :description)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    is_paid_leave = EXCLUDED.is_paid_leave,
                    affects_annual_leave = EXCLUDED.affects_annual_leave,
                    allow_half_day = EXCLUDED.allow_half_day,
                    requires_attachment = EXCLUDED.requires_attachment,
                    color_tag = EXCLUDED.color_tag,
                    is_active = true,
                    description = EXCLUDED.description
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        leave_types_added += result.rowcount

    return (
        contract_categories_added,
        nationalities_added,
        ethnicities_added,
        religions_added,
        banks_added,
        leave_types_added,
    )


async def seed_sample_other_business_catalog(session: AsyncSession) -> tuple[int, int, int, int]:
    skills_added = 0
    certificates_added = 0
    templates_added = 0
    placeholders_added = 0

    for item in SKILLS:
        result = await session.execute(
            text(
                """
                INSERT INTO skills (code, name, normalized_name, skill_group, is_active)
                VALUES (:code, :name, :normalized_name, :skill_group, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    skill_group = EXCLUDED.skill_group,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        skills_added += result.rowcount

    for item in CERTIFICATES:
        result = await session.execute(
            text(
                """
                INSERT INTO certificates
                    (code, name, normalized_name, certificate_group, issuer_name, expiry_policy,
                     default_valid_months, is_active)
                VALUES
                    (:code, :name, :normalized_name, :certificate_group, :issuer_name, :expiry_policy,
                     :default_valid_months, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    certificate_group = EXCLUDED.certificate_group,
                    issuer_name = EXCLUDED.issuer_name,
                    expiry_policy = EXCLUDED.expiry_policy,
                    default_valid_months = EXCLUDED.default_valid_months,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        certificates_added += result.rowcount

    for item in CONTRACT_TEMPLATES:
        result = await session.execute(
            text(
                """
                INSERT INTO contract_templates
                    (code, name, normalized_name, contract_category_id, document_kind, template_engine,
                     file_name, storage_path, mime_type, file_size, file_checksum, version_no,
                     effective_from, effective_to, is_active, note)
                SELECT
                    :code, :name, :normalized_name, cc.id, :document_kind, :template_engine,
                    :file_name, :storage_path, :mime_type, :file_size, :file_checksum, :version_no,
                    NULL, NULL, true, :note
                FROM contract_categories cc
                WHERE cc.code = :contract_category_code
                ON CONFLICT (code, version_no) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    contract_category_id = EXCLUDED.contract_category_id,
                    document_kind = EXCLUDED.document_kind,
                    template_engine = EXCLUDED.template_engine,
                    file_name = EXCLUDED.file_name,
                    storage_path = EXCLUDED.storage_path,
                    mime_type = EXCLUDED.mime_type,
                    file_size = EXCLUDED.file_size,
                    file_checksum = EXCLUDED.file_checksum,
                    is_active = true,
                    note = EXCLUDED.note
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        templates_added += result.rowcount

    for template_code, rows in CONTRACT_TEMPLATE_PLACEHOLDERS.items():
        template_id = (
            await session.execute(
                text("SELECT id FROM contract_templates WHERE code = :code AND version_no = 1"),
                {"code": template_code},
            )
        ).scalar()
        if not template_id:
            continue

        for row in rows:
            result = await session.execute(
                text(
                    """
                    INSERT INTO contract_template_placeholders
                        (template_id, placeholder_key, label, source_scope, source_path, data_type,
                         formatter, is_required, default_value, sort_order)
                    VALUES
                        (:template_id, :placeholder_key, :label, :source_scope, :source_path, :data_type,
                         :formatter, :is_required, :default_value, :sort_order)
                    ON CONFLICT (template_id, placeholder_key) DO UPDATE SET
                        label = EXCLUDED.label,
                        source_scope = EXCLUDED.source_scope,
                        source_path = EXCLUDED.source_path,
                        data_type = EXCLUDED.data_type,
                        formatter = EXCLUDED.formatter,
                        is_required = EXCLUDED.is_required,
                        default_value = EXCLUDED.default_value,
                        sort_order = EXCLUDED.sort_order
                    """
                ),
                {
                    "template_id": template_id,
                    "placeholder_key": row[0],
                    "label": row[1],
                    "source_scope": row[2],
                    "source_path": row[3],
                    "data_type": row[4],
                    "formatter": row[5],
                    "is_required": row[6],
                    "default_value": row[7],
                    "sort_order": row[8],
                },
            )
            placeholders_added += result.rowcount

    return skills_added, certificates_added, templates_added, placeholders_added
