from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.employee_attachment import DOCUMENT_TYPE_LABELS

VALID_DOCUMENT_TYPES = set(DOCUMENT_TYPE_LABELS.keys())

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class EmployeeAttachmentRead(BaseModel):
    id: int
    employee_id: int
    document_type: str
    document_type_label: str
    description: Optional[str]
    file_name: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    uploaded_at: datetime
    download_url: str

    model_config = {"from_attributes": True}
