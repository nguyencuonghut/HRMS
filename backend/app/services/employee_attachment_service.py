"""Service cho hồ sơ đính kèm nhân viên (3.5)."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_attachment import DOCUMENT_TYPE_LABELS, EmployeeAttachment
from app.schemas.employee_attachment import EmployeeAttachmentRead


def _to_read(att: EmployeeAttachment, employee_id: int) -> EmployeeAttachmentRead:
    return EmployeeAttachmentRead(
        id=att.id,
        employee_id=att.employee_id,
        document_type=att.document_type,
        document_type_label=DOCUMENT_TYPE_LABELS.get(att.document_type, att.document_type),
        description=att.description,
        file_name=att.file_name,
        file_path=att.file_path,
        file_size=att.file_size,
        mime_type=att.mime_type,
        uploaded_at=att.uploaded_at,
        download_url=f"/api/v1/employees/{employee_id}/attachments/{att.id}/download",
    )


async def get_attachments(
    session: AsyncSession,
    employee_id: int,
    document_type: Optional[str] = None,
) -> list[EmployeeAttachmentRead]:
    q = (
        select(EmployeeAttachment)
        .where(EmployeeAttachment.employee_id == employee_id)
        .order_by(EmployeeAttachment.document_type, EmployeeAttachment.uploaded_at.desc())
    )
    if document_type:
        q = q.where(EmployeeAttachment.document_type == document_type)
    rows = (await session.execute(q)).scalars().all()
    return [_to_read(r, employee_id) for r in rows]


async def get_attachment_or_404(
    session: AsyncSession,
    employee_id: int,
    att_id: int,
) -> EmployeeAttachment:
    att = await session.get(EmployeeAttachment, att_id)
    if not att or att.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu")
    return att


async def create_attachment(
    session: AsyncSession,
    employee_id: int,
    document_type: str,
    description: Optional[str],
    file_name: str,
    file_path: str,
    file_size: int,
    mime_type: Optional[str],
) -> EmployeeAttachmentRead:
    att = EmployeeAttachment(
        employee_id=employee_id,
        document_type=document_type,
        description=description,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
    )
    session.add(att)
    await session.flush()
    return _to_read(att, employee_id)
