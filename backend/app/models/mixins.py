"""Shared model mixins (H5 — Production Improvements: Soft Delete).

SoftDeleteMixin thêm `deleted_at` vào model — cho phép "xóa mềm":
- Record không bị xóa khỏi DB, chỉ đánh dấu `deleted_at = NOW()`
- Mọi list/lookup query phải filter `WHERE deleted_at IS NULL`
- Tuân thủ compliance: dữ liệu nhân sự giữ ≥ 10 năm
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SoftDeleteMixin:
    """
    Thêm field `deleted_at` vào SQLModel table class.

    Cách dùng:
        class Department(SoftDeleteMixin, SQLModel, table=True): ...

    Rules:
    - `deleted_at IS NULL`  → record đang active
    - `deleted_at IS NOT NULL` → đã "xóa mềm"
    - KHÔNG xóa record khỏi DB — chỉ set deleted_at

    Pattern trong service:
        # Xóa mềm:
        entity.deleted_at = _utcnow()
        await session.commit()

        # Filter trong list query:
        .where(MyModel.deleted_at.is_(None))
    """

    # Dùng Field đơn giản (không sa_column) để tránh sharing Column instance
    # giữa các subclass — SQLModel tự suy ra kiểu từ type annotation
    deleted_at: Optional[datetime] = Field(default=None, index=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Đánh dấu record là đã xóa."""
        self.deleted_at = _utcnow()
