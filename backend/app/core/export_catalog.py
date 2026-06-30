from __future__ import annotations

REPORT_DEFS: list[tuple[str, str]] = [
    ("dashboard", "Dashboard tổng quan"),
    ("hr-employee-list", "Nhân sự: Danh sách nhân viên"),
    ("hr-movement", "Nhân sự: Biến động nhân sự"),
    ("hr-tenure", "Nhân sự: Thâm niên nhân sự"),
    ("hr-org-structure", "Nhân sự: Cơ cấu tổ chức"),
    ("leaves", "Nghỉ phép: Phân tích nghỉ phép"),
    ("insurance", "Bảo hiểm: Phân tích bảo hiểm"),
    ("contracts", "Hợp đồng: Báo cáo hợp đồng"),
    ("recruitment", "Tuyển dụng: Báo cáo tuyển dụng"),
    ("probation", "Thử việc: Báo cáo thử việc"),
]

EXPORT_FORMAT_DEFS: list[tuple[str, str]] = [
    ("xlsx", "Excel (.xlsx)"),
    ("pdf", "PDF (.pdf)"),
]

EXPORT_STATUS_DEFS: list[tuple[str, str, str]] = [
    ("pending", "Chờ xử lý", "warn"),
    ("processing", "Đang xử lý", "info"),
    ("done", "Hoàn tất", "success"),
    ("failed", "Thất bại", "danger"),
]

REPORT_TYPE_LABELS = {code: label for code, label in REPORT_DEFS}
REPORT_TYPE_ORDER = {code: index for index, (code, _) in enumerate(REPORT_DEFS, start=1)}

EXPORT_FORMAT_LABELS = {code: label for code, label in EXPORT_FORMAT_DEFS}
EXPORT_FORMAT_ORDER = {
    code: index for index, (code, _) in enumerate(EXPORT_FORMAT_DEFS, start=1)
}

EXPORT_STATUS_LABELS = {code: label for code, label, _ in EXPORT_STATUS_DEFS}
EXPORT_STATUS_SEVERITIES = {code: severity for code, _, severity in EXPORT_STATUS_DEFS}
EXPORT_STATUS_ORDER = {
    code: index for index, (code, _, _) in enumerate(EXPORT_STATUS_DEFS, start=1)
}
