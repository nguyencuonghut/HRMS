from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


ENTITY_TYPE_LABELS = {
    "department":    "Phòng/Ban",
    "job_title":     "Chức danh",
    "job_position":  "Vị trí công việc",
}

ACTION_LABELS = {
    "create": "Tạo mới",
    "update": "Cập nhật",
    "delete": "Xóa",
}


class OrgHistoryRead(BaseModel):
    id:           int
    entity_type:  str
    entity_label: str          # "Phòng/Ban", "Chức danh", ...
    entity_id:    int
    entity_name:  str
    action:       str
    action_label: str          # "Tạo mới", "Cập nhật", "Xóa"
    changed_by:   Optional[int]
    changed_at:   datetime
    old_data:     Optional[Any]
    new_data:     Optional[Any]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: Any) -> "OrgHistoryRead":
        return cls(
            id=row.id,
            entity_type=row.entity_type,
            entity_label=ENTITY_TYPE_LABELS.get(row.entity_type, row.entity_type),
            entity_id=row.entity_id,
            entity_name=row.entity_name,
            action=row.action,
            action_label=ACTION_LABELS.get(row.action, row.action),
            changed_by=row.changed_by,
            changed_at=row.changed_at,
            old_data=row.old_data,
            new_data=row.new_data,
        )
