"""RBAC metadata shared by seeders and APIs."""

from __future__ import annotations

MODULE_DEFS: list[tuple[str, str]] = [
    ("org", "Cơ cấu tổ chức"),
    ("catalog", "Danh mục"),
    ("settings", "Cài đặt"),
    ("employees", "Nhân sự"),
    ("contracts", "Hợp đồng"),
    ("leaves", "Nghỉ phép"),
    ("insurance", "Bảo hiểm BHXH"),
    ("salary", "Lương BHXH"),
    ("rewards", "Khen thưởng"),
    ("disciplines", "Kỷ luật"),
    ("training", "Đào tạo"),
    ("recruitment", "Tuyển dụng"),
    ("performance", "Đánh giá KPI"),
    ("data_import", "Nhập dữ liệu"),
    ("reports", "Báo cáo"),
    ("users", "Tài khoản người dùng"),
    ("roles", "Vai trò & Quyền"),
    ("audit_logs", "Nhật ký hệ thống"),
]

ACTION_DEFS: list[tuple[str, str]] = [
    ("view", "Xem"),
    ("create", "Thêm mới"),
    ("edit", "Chỉnh sửa"),
    ("delete", "Xóa"),
    ("export", "Xuất dữ liệu"),
]

MODULE_LABELS = {code: label for code, label in MODULE_DEFS}
ACTION_LABELS = {code: label for code, label in ACTION_DEFS}
MODULE_ORDER = {code: index for index, (code, _) in enumerate(MODULE_DEFS, start=1)}
ACTION_ORDER = {code: index for index, (code, _) in enumerate(ACTION_DEFS, start=1)}
