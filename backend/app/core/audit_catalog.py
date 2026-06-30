from __future__ import annotations

AUDIT_ACTION_DEFS: list[tuple[str, str, str]] = [
    ("LOGIN", "Đăng nhập", "info"),
    ("CREATE", "Tạo mới", "success"),
    ("UPDATE", "Cập nhật", "warn"),
    ("DELETE", "Xóa", "danger"),
    ("EXPORT", "Xuất dữ liệu", "secondary"),
    ("RESET_PASSWORD", "Đặt lại mật khẩu", "warn"),
    ("CREATE_CONTRACT", "Tạo hợp đồng", "success"),
]

AUDIT_ENTITY_DEFS: list[tuple[str, str, str]] = [
    ("user", "Người dùng", "warn"),
    ("user_role", "Phân quyền người dùng", "warn"),
    ("role", "Vai trò", "danger"),
    ("role_permissions", "Quyền vai trò", "danger"),
    ("department", "Phòng/Ban", "info"),
    ("department_head", "Người đứng đầu đơn vị", "info"),
    ("job_title", "Chức danh", "secondary"),
    ("job_position", "Vị trí", "secondary"),
    ("employee", "Nhân viên", "info"),
    ("employee_address", "Địa chỉ nhân viên", "info"),
    ("employee_bank_account", "Tài khoản ngân hàng", "info"),
    ("employee_job_record", "Hồ sơ công việc", "info"),
    ("employee_relative", "Người thân", "info"),
    ("employee_education", "Học vấn", "info"),
    ("employee_work_experience", "Kinh nghiệm làm việc", "info"),
    ("employee_skill", "Kỹ năng", "info"),
    ("employee_certificate", "Chứng chỉ nhân viên", "info"),
    ("employee_language", "Ngoại ngữ", "info"),
    ("employee_attachment", "Tệp đính kèm nhân viên", "info"),
    ("employee_contract", "Hợp đồng nhân viên", "success"),
    ("contract", "Hợp đồng", "success"),
    ("contract_category", "Loại hợp đồng", "secondary"),
    ("contract_template", "Mẫu hợp đồng", "secondary"),
    ("leave_record", "Đơn nghỉ phép", "secondary"),
    ("leave_entitlement", "Phép năm", "secondary"),
    ("reward_type", "Loại khen thưởng", "secondary"),
    ("employee_reward", "Khen thưởng nhân viên", "secondary"),
    ("employee_discipline", "Kỷ luật nhân viên", "danger"),
    ("training_course", "Khóa đào tạo", "secondary"),
    ("training_plan", "Kế hoạch đào tạo", "secondary"),
    ("training_plan_course", "Khóa học trong kế hoạch", "secondary"),
    ("education_level", "Trình độ học vấn", "secondary"),
    ("educational_institution", "Cơ sở đào tạo", "secondary"),
    ("education_major", "Chuyên ngành", "secondary"),
    ("administrative_unit", "Đơn vị hành chính", "secondary"),
    ("administrative_import_batch", "Lô import địa chỉ", "secondary"),
    ("headcount_plan", "Kế hoạch nhân sự", "secondary"),
    ("job_requisition", "Yêu cầu tuyển dụng", "secondary"),
    ("job_posting", "Tin tuyển dụng", "secondary"),
    ("candidate", "Ứng viên", "secondary"),
    ("candidate_application", "Hồ sơ ứng tuyển", "secondary"),
    ("insurance_period_report", "Kỳ báo cáo BHXH", "secondary"),
    ("nationality", "Quốc tịch", "secondary"),
    ("ethnicity", "Dân tộc", "secondary"),
    ("religion", "Tôn giáo", "secondary"),
    ("bank", "Ngân hàng", "secondary"),
    ("skill", "Danh mục kỹ năng", "secondary"),
    ("certificate", "Danh mục chứng chỉ", "secondary"),
    ("leave_type", "Loại nghỉ phép", "secondary"),
]

AUDIT_ACTION_LABELS = {code: label for code, label, _ in AUDIT_ACTION_DEFS}
AUDIT_ACTION_SEVERITIES = {code: severity for code, _, severity in AUDIT_ACTION_DEFS}
AUDIT_ACTION_ORDER = {
    code: index for index, (code, _, _) in enumerate(AUDIT_ACTION_DEFS, start=1)
}

AUDIT_ENTITY_LABELS = {code: label for code, label, _ in AUDIT_ENTITY_DEFS}
AUDIT_ENTITY_SEVERITIES = {code: severity for code, _, severity in AUDIT_ENTITY_DEFS}
AUDIT_ENTITY_ORDER = {
    code: index for index, (code, _, _) in enumerate(AUDIT_ENTITY_DEFS, start=1)
}
