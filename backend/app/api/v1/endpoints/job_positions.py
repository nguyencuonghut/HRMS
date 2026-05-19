from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.storage import delete_attachment, get_object_stream, save_attachment
from app.models.org import JobPositionAttachment
from app.schemas.employee_code_rule import EmployeeCodeSequenceRuleRead, EmployeeCodeSequenceRuleUpsert
from app.schemas.job_position import (
    AttachmentRead,
    JobPositionCreate,
    JobPositionListItem,
    JobPositionRead,
    JobPositionUpdate,
)
from app.services import employee_code_rule_service, job_position_service

router = APIRouter()


@router.get("", response_model=list[JobPositionListItem], summary="Danh sách vị trí công việc")
async def list_job_positions(
    department_id: Optional[int]  = Query(None, description="Lọc theo phòng/ban"),
    is_active:     Optional[bool] = Query(None, description="Lọc theo trạng thái"),
    search:        Optional[str]  = Query(None, description="Tìm theo mã hoặc tên"),
    session: AsyncSession = Depends(get_session),
):
    return await job_position_service.get_list(
        session,
        department_id=department_id,
        is_active=is_active,
        search=search,
    )


@router.get("/{pos_id}", response_model=JobPositionRead, summary="Chi tiết vị trí công việc")
async def get_job_position(
    pos_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await job_position_service.get_by_id(session, pos_id)


@router.post("", response_model=JobPositionRead, status_code=status.HTTP_201_CREATED, summary="Tạo vị trí mới")
async def create_job_position(
    body: JobPositionCreate,
    session: AsyncSession = Depends(get_session),
):
    return await job_position_service.create(session, body)


@router.put("/{pos_id}", response_model=JobPositionRead, summary="Cập nhật vị trí công việc")
async def update_job_position(
    pos_id: int,
    body: JobPositionUpdate,
    session: AsyncSession = Depends(get_session),
):
    return await job_position_service.update(session, pos_id, body)


@router.delete("/{pos_id}", summary="Xóa vị trí công việc")
async def delete_job_position(
    pos_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await job_position_service.delete(session, pos_id)


@router.get(
    "/{pos_id}/employee-code-rule",
    response_model=EmployeeCodeSequenceRuleRead | None,
    summary="Rule hệ mã của vị trí công việc",
)
async def get_job_position_employee_code_rule(
    pos_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.get_job_position_rule(session, pos_id)


@router.put(
    "/{pos_id}/employee-code-rule",
    response_model=EmployeeCodeSequenceRuleRead,
    summary="Tạo/cập nhật rule hệ mã cho vị trí công việc",
)
async def upsert_job_position_employee_code_rule(
    pos_id: int,
    body: EmployeeCodeSequenceRuleUpsert,
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.upsert_job_position_rule(session, pos_id, body)


@router.delete(
    "/{pos_id}/employee-code-rule",
    summary="Xóa rule hệ mã của vị trí công việc",
)
async def delete_job_position_employee_code_rule(
    pos_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.delete_job_position_rule(session, pos_id)


# ── Attachments ────────────────────────────────────────────────────────────────

def _att_to_read(att: JobPositionAttachment, pos_id: int) -> AttachmentRead:
    """Chuyển ORM object → AttachmentRead. download_url là API endpoint proxy."""
    return AttachmentRead(
        id=att.id,
        file_name=att.file_name,
        file_path=att.file_path,
        file_size=att.file_size,
        uploaded_at=att.uploaded_at,
        download_url=f"/api/v1/job-positions/{pos_id}/attachments/{att.id}/download",
    )


@router.get(
    "/{pos_id}/attachments",
    response_model=list[AttachmentRead],
    summary="Danh sách file đính kèm",
)
async def list_attachments(
    pos_id: int,
    session: AsyncSession = Depends(get_session),
):
    await job_position_service.get_by_id(session, pos_id)  # 404 nếu không tồn tại
    atts = await job_position_service.get_attachments(session, pos_id)
    return [_att_to_read(a, pos_id) for a in atts]


@router.post(
    "/{pos_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file đính kèm",
)
async def upload_attachment(
    pos_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    await job_position_service.get_by_id(session, pos_id)  # 404 nếu không tồn tại
    object_name, file_size = await save_attachment(pos_id, file)
    att = JobPositionAttachment(
        job_position_id=pos_id,
        file_name=file.filename or "file",
        file_path=object_name,
        file_size=file_size,
    )
    session.add(att)
    await session.commit()
    await session.refresh(att)
    return _att_to_read(att, pos_id)


@router.get(
    "/{pos_id}/attachments/{att_id}/download",
    summary="Tải file đính kèm",
)
async def download_attachment(
    pos_id: int,
    att_id: int,
    session: AsyncSession = Depends(get_session),
):
    att = await job_position_service.get_attachment_by_id(session, pos_id, att_id)
    filename = att.file_name.encode("utf-8").decode("latin-1", errors="replace")
    return StreamingResponse(
        get_object_stream(att.file_path),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{pos_id}/attachments/{att_id}",
    summary="Xóa file đính kèm",
)
async def delete_attachment_endpoint(
    pos_id: int,
    att_id: int,
    session: AsyncSession = Depends(get_session),
):
    att = await job_position_service.get_attachment_by_id(session, pos_id, att_id)
    delete_attachment(att.file_path)
    await session.delete(att)
    await session.commit()
    return {"message": "Đã xóa file đính kèm"}
