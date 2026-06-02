from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


DOCUMENT_TYPE_LABELS: dict[str, str] = {
    "avatar":        "Ảnh thẻ",
    "id_card_front": "CCCD — Mặt trước",
    "id_card_back":  "CCCD — Mặt sau",
    "passport":      "Hộ chiếu",
    "work_permit":   "Giấy phép lao động (legacy)",
    "degree":        "Bằng cấp",
    "certificate":   "Chứng chỉ",
    "resume":        "Sơ yếu lý lịch",
    "other":         "Khác (legacy)",
}


class EmployeeAttachment(SQLModel, table=True):
    __tablename__ = "employee_attachments"
    __table_args__ = (
        sa.Index("ix_emp_attachments_employee_id", "employee_id"),
        sa.Index("ix_emp_attachments_doc_type", "employee_id", "document_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    )
    document_type: str = Field(max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    file_name: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: Optional[int] = Field(default=None)
    mime_type: Optional[str] = Field(default=None, max_length=100)
    uploaded_at: datetime = Field(default_factory=_utcnow)
