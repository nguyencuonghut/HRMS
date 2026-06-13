"""Schemas cho Import/Export nhân viên (3.7)."""

from pydantic import BaseModel

IMPORT_MAX_ROWS = 1000
EXPORT_MAX_ROWS = 5000

GENDER_MAP = {"nam": "male", "nữ": "female", "nu": "female", "khác": "other", "khac": "other"}
STATUS_MAP = {"probation": "probation", "official": "official", "long_leave": "long_leave"}

# Header cột trong file mẫu — thứ tự phải khớp với template
IMPORT_COLUMNS = [
    "Họ và tên",
    "Họ",
    "Tên",
    "Ngày sinh",
    "Giới tính",
    "Số CCCD/CMND",
    "Ngày cấp CCCD",
    "Nơi cấp CCCD",
    "Trạng thái",
    "Ngày vào làm",
    "Số điện thoại",
    "Email cá nhân",
    "Mã số thuế",
    "Số BHXH",
    "Quốc tịch",
    "Dân tộc",
    "Tôn giáo",
    "Phòng ban",
    "Chức danh",
    "Vị trí công việc",
    "Hệ mã nhân viên",
    "Số thứ tự mã NV",
    "Mã NV hiện hữu",
    "Ngày bắt đầu thử việc",
    "Ngày kết thúc thử việc",
]

REQUIRED_COLUMNS = {
    "Họ và tên", "Họ", "Tên", "Ngày sinh", "Giới tính",
    "Số CCCD/CMND", "Ngày cấp CCCD", "Nơi cấp CCCD",
    "Trạng thái", "Ngày vào làm",
}


class ImportRowError(BaseModel):
    row:     int
    column:  str
    message: str


class ImportResult(BaseModel):
    total:       int
    success:     int
    failed:      int
    errors:      list[ImportRowError]
    created_ids: list[int]
