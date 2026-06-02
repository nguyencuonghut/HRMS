from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Union
from xml.etree import ElementTree
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass(frozen=True)
class SupportedTemplateField:
    token: str
    label: str
    source_scope: str
    source_path: str
    data_type: str
    source_origin: Optional[str] = None
    formatter: Optional[str] = None
    is_required: bool = False
    recommended_token: Optional[str] = None


SUPPORTED_TEMPLATE_FIELDS: dict[str, SupportedTemplateField] = {
    "contract_number": SupportedTemplateField(
        token="contract_number",
        label="Số hợp đồng",
        source_scope="contract_draft",
        source_path="contract.contract_number",
        source_origin="employee_contracts.contract_number",
        data_type="text",
        is_required=True,
    ),
    "contract_start_date": SupportedTemplateField(
        token="contract_start_date",
        label="Ngày bắt đầu hợp đồng",
        source_scope="contract_draft",
        source_path="contract.start_date",
        source_origin="employee_contracts.effective_from",
        data_type="date",
        formatter="vn_date",
        is_required=True,
    ),
    "contract_end_date": SupportedTemplateField(
        token="contract_end_date",
        label="Ngày kết thúc hợp đồng",
        source_scope="contract_draft",
        source_path="contract.end_date",
        source_origin="employee_contracts.effective_to",
        data_type="date",
        formatter="vn_date",
        is_required=False,
    ),
    "department_name": SupportedTemplateField(
        token="department_name",
        label="Phòng ban",
        source_scope="employee",
        source_path="employee.department_name",
        source_origin="employee_job_records.department_id -> departments.name",
        data_type="text",
        is_required=True,
    ),
    "employee_full_name": SupportedTemplateField(
        token="employee_full_name",
        label="Họ và tên",
        source_scope="employee",
        source_path="employee.full_name",
        source_origin="employees.full_name",
        data_type="text",
        is_required=True,
    ),
    "employee_birthday": SupportedTemplateField(
        token="employee_birthday",
        label="Ngày sinh",
        source_scope="employee",
        source_path="employee.date_of_birth",
        source_origin="employees.date_of_birth",
        data_type="date",
        formatter="vn_date",
        is_required=True,
    ),
    "employee_gender": SupportedTemplateField(
        token="employee_gender",
        label="Giới tính",
        source_scope="employee",
        source_path="employee.gender_label",
        source_origin="employees.gender -> gender_label()",
        data_type="text",
    ),
    "employee_cccd": SupportedTemplateField(
        token="employee_cccd",
        label="Số CCCD",
        source_scope="employee",
        source_path="employee.identity_number",
        source_origin="employees.id_number",
        data_type="text",
        is_required=True,
    ),
    "employee_cccd_issued_on": SupportedTemplateField(
        token="employee_cccd_issued_on",
        label="Ngày cấp CCCD",
        source_scope="employee",
        source_path="employee.identity_issued_on",
        source_origin="employees.id_issued_on",
        data_type="date",
        formatter="vn_date",
    ),
    "employee_cccd_issued_by": SupportedTemplateField(
        token="employee_cccd_issued_by",
        label="Nơi cấp CCCD",
        source_scope="employee",
        source_path="employee.identity_issued_by",
        source_origin="employees.id_issued_by",
        data_type="text",
    ),
    "employee_address": SupportedTemplateField(
        token="employee_address",
        label="Địa chỉ thường trú",
        source_scope="employee",
        source_path="employee.permanent_address_full",
        source_origin="employee_addresses.full_address_text (address_type=permanent)",
        data_type="text",
    ),
    "employee_temp_address": SupportedTemplateField(
        token="employee_temp_address",
        label="Địa chỉ hiện tại",
        source_scope="employee",
        source_path="employee.current_address_full",
        source_origin="employee_addresses.full_address_text (address_type=contact)",
        data_type="text",
    ),
    "employee_phone": SupportedTemplateField(
        token="employee_phone",
        label="Số điện thoại",
        source_scope="employee",
        source_path="employee.phone_number",
        source_origin="employees.phone_number",
        data_type="text",
    ),
    "employee_personal_email": SupportedTemplateField(
        token="employee_personal_email",
        label="Email cá nhân",
        source_scope="employee",
        source_path="employee.personal_email",
        source_origin="employees.personal_email",
        data_type="text",
    ),
    "position_title": SupportedTemplateField(
        token="position_title",
        label="Chức danh công việc",
        source_scope="employee",
        source_path="employee.position_name",
        source_origin="employee_job_records.job_title_id -> job_titles.name",
        data_type="text",
    ),
    "insurance_salary": SupportedTemplateField(
        token="insurance_salary",
        label="Lương BHXH",
        source_scope="contract_draft",
        source_path="contract.insurance_salary",
        source_origin="employee_contracts.insurance_salary",
        data_type="currency",
        formatter="currency_vnd",
    ),
    "insurance_salary_words": SupportedTemplateField(
        token="insurance_salary_words",
        label="Lương BHXH bằng chữ",
        source_scope="contract_draft",
        source_path="contract.insurance_salary_words",
        source_origin="employee_contracts.insurance_salary -> number_to_words_vn()",
        data_type="text",
    ),
    "Ngày": SupportedTemplateField(
        token="Ngày",
        label="Ngày ký (ngày)",
        source_scope="system",
        source_path="system.render_date.day",
        source_origin="employee_contracts.signed_date.day",
        data_type="number",
        recommended_token="contract_signing_day",
    ),
    "Tháng": SupportedTemplateField(
        token="Tháng",
        label="Ngày ký (tháng)",
        source_scope="system",
        source_path="system.render_date.month",
        source_origin="employee_contracts.signed_date.month",
        data_type="number",
        recommended_token="contract_signing_month",
    ),
    "Năm": SupportedTemplateField(
        token="Năm",
        label="Ngày ký (năm)",
        source_scope="system",
        source_path="system.render_date.year",
        source_origin="employee_contracts.signed_date.year",
        data_type="number",
        recommended_token="contract_signing_year",
    ),
    "SĐT": SupportedTemplateField(
        token="SĐT",
        label="Số điện thoại",
        source_scope="employee",
        source_path="employee.phone_number",
        source_origin="employees.phone_number",
        data_type="text",
        recommended_token="employee_phone",
    ),
    "Loại_HĐLĐ__": SupportedTemplateField(
        token="Loại_HĐLĐ__",
        label="Loại hợp đồng",
        source_scope="contract_draft",
        source_path="contract.contract_type_label",
        source_origin="employee_contracts.contract_category_id -> contract_categories.name",
        data_type="text",
        recommended_token="contract_type_label",
    ),
    "Thời_hạn_trả_lương": SupportedTemplateField(
        token="Thời_hạn_trả_lương",
        label="Kỳ hạn trả lương",
        source_scope="contract_draft",
        source_path="contract.pay_cycle_label",
        source_origin="Chưa nối nguồn dữ liệu; build_contract_context hiện trả chuỗi rỗng",
        data_type="text",
        recommended_token="salary_payment_cycle",
    ),
}


_DOLLAR_PATTERN = re.compile(r"\$\{\s*([^}]+?)\s*\}")
_DOUBLE_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
_MERGEFIELD_PATTERN = re.compile(r"MERGEFIELD\s+(.+?)(?:\s+\\\*|\s+\\@|\s*$)")


def resolve_template_storage_path(storage_path: str) -> Path:
    raw = Path(storage_path)
    if raw.is_absolute():
        return raw
    return PROJECT_ROOT / raw


def _read_docx_xml_parts(source: Union[Path, bytes]) -> dict[str, str]:
    """Đọc các XML part cần thiết từ DOCX (Path hoặc bytes từ MinIO)."""
    parts: dict[str, str] = {}
    zip_source: Union[Path, BytesIO] = BytesIO(source) if isinstance(source, bytes) else source
    with ZipFile(zip_source) as archive:
        for name in archive.namelist():
            if not name.startswith("word/"):
                continue
            if not name.endswith(".xml"):
                continue
            if not (
                name == "word/document.xml"
                or name.startswith("word/header")
                or name.startswith("word/footer")
            ):
                continue
            parts[name] = archive.read(name).decode("utf-8", "ignore")
    return parts


def _extract_text_and_mergefields(xml_text: str) -> tuple[str, list[str]]:
    root = ElementTree.fromstring(xml_text)
    text_fragments = [node.text or "" for node in root.findall(".//w:t", WORD_NS)]
    instr_fragments = [node.text or "" for node in root.findall(".//w:instrText", WORD_NS)]
    joined_text = "".join(text_fragments)
    mergefields: list[str] = []
    for fragment in instr_fragments:
        for match in _MERGEFIELD_PATTERN.findall(fragment):
            token = match.strip().strip('"')
            if token:
                mergefields.append(token)
    return joined_text, mergefields


def extract_docx_placeholder_summary(docx_path: Union[Path, bytes]) -> dict:
    xml_parts = _read_docx_xml_parts(docx_path)
    text_blob_parts: list[str] = []
    mergefields: list[str] = []
    for xml_text in xml_parts.values():
        joined_text, part_mergefields = _extract_text_and_mergefields(xml_text)
        text_blob_parts.append(joined_text)
        mergefields.extend(part_mergefields)
    text_blob = "\n".join(text_blob_parts)
    dollar = sorted(set(token.strip() for token in _DOLLAR_PATTERN.findall(text_blob) if token.strip()))
    double = sorted(set(token.strip() for token in _DOUBLE_PATTERN.findall(text_blob) if token.strip()))
    merge = sorted(set(token.strip() for token in mergefields if token.strip()))
    styles = []
    if dollar:
        styles.append("dollar_braces")
    if double:
        styles.append("double_braces")
    if merge:
        styles.append("mergefield")
    warnings: list[str] = []
    if len(styles) > 1:
        warnings.append("Mẫu đang trộn nhiều kiểu placeholder. Nên chuẩn hóa về {{snake_case}} duy nhất.")
    if dollar:
        warnings.append("Mẫu đang dùng placeholder dạng ${...} (legacy). Nên chuyển sang {{snake_case}}.")
    if merge:
        warnings.append("Mẫu đang dùng MERGEFIELD (legacy). Nên chuyển sang {{recommended_token}} tương ứng.")
    detected = []
    for syntax, tokens in (
        ("dollar_braces", dollar),
        ("double_braces", double),
        ("mergefield", merge),
    ):
        for token in tokens:
            supported = SUPPORTED_TEMPLATE_FIELDS.get(token)
            detected.append(
                {
                    "placeholder_key": token,
                    "syntax": syntax,
                    "is_supported": supported is not None,
                    "recommended_token": supported.recommended_token if supported else None,
                    "label": supported.label if supported else None,
                    "source_scope": supported.source_scope if supported else None,
                    "source_path": supported.source_path if supported else None,
                    "source_origin": supported.source_origin if supported else None,
                    "data_type": supported.data_type if supported else None,
                    "formatter": supported.formatter if supported else None,
                    "is_required": supported.is_required if supported else False,
                }
            )
    suggested_rows = []
    sort_order = 10
    for item in detected:
        if not item["is_supported"]:
            continue
        suggested_rows.append(
            {
                "placeholder_key": item["placeholder_key"],
                "label": item["label"],
                "source_scope": item["source_scope"],
                "source_path": item["source_path"],
                "data_type": item["data_type"],
                "formatter": item["formatter"],
                "is_required": item["is_required"],
                "default_value": None,
                "sort_order": sort_order,
            }
        )
        sort_order += 10
    return {
        "styles": styles,
        "warnings": warnings,
        "detected_placeholders": detected,
        "supported_count": len([item for item in detected if item["is_supported"]]),
        "unsupported_count": len([item for item in detected if not item["is_supported"]]),
        "suggested_rows": suggested_rows,
    }
