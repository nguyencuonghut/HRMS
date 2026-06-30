from __future__ import annotations

NOTIFICATION_EVENT_DEFS: list[tuple[str, str]] = [
    ("contract_expiry", "Hợp đồng sắp hết hạn"),
    ("probation_end", "Thử việc sắp kết thúc"),
    ("birthday", "Sinh nhật nhân viên"),
    ("carryover_expiry", "Tồn phép sắp hết hạn"),
]

NOTIFICATION_STATUS_DEFS: list[tuple[str, str, str]] = [
    ("sent", "Đã gửi", "success"),
    ("failed", "Thất bại", "danger"),
    ("skipped", "Bỏ qua", "warn"),
]

NOTIFICATION_EVENT_LABELS = {
    code: label for code, label in NOTIFICATION_EVENT_DEFS
}
NOTIFICATION_EVENT_ORDER = {
    code: index for index, (code, _) in enumerate(NOTIFICATION_EVENT_DEFS, start=1)
}

NOTIFICATION_STATUS_LABELS = {
    code: label for code, label, _ in NOTIFICATION_STATUS_DEFS
}
NOTIFICATION_STATUS_SEVERITIES = {
    code: severity for code, _, severity in NOTIFICATION_STATUS_DEFS
}
NOTIFICATION_STATUS_ORDER = {
    code: index for index, (code, _, _) in enumerate(NOTIFICATION_STATUS_DEFS, start=1)
}
