"""Service quản lý chứng chỉ nhân viên (9.3)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import String, and_, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.auth import User
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.training import EmployeeTrainingCertificate, TrainingCourse
from app.schemas.training import (
    EXPIRY_SOON_DAYS,
    CertificateCreate,
    CertificateListPage,
    CertificateRead,
    CertificateUpdate,
    compute_days_until_expiry,
    compute_expiry_status,
)
from app.services import employee_code_service

log = logging.getLogger(__name__)

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_or_404(session: AsyncSession, cert_id: int) -> EmployeeTrainingCertificate:
    cert = await session.get(EmployeeTrainingCertificate, cert_id)
    if not cert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chứng chỉ")
    return cert


async def _build_read(session: AsyncSession, cert: EmployeeTrainingCertificate) -> CertificateRead:
    today = date.today()
    emp = await session.get(Employee, cert.employee_id)
    course = await session.get(TrainingCourse, cert.related_course_id) if cert.related_course_id else None
    creator: Optional[User] = await session.get(User, cert.created_by_id) if cert.created_by_id else None

    emp_code = ""
    dept_name: Optional[str] = None
    if emp:
        emp_code = await employee_code_service.build_employee_display_code(session, emp)
        jr = (
            await session.execute(
                select(EmployeeJobRecord)
                .where(
                    EmployeeJobRecord.employee_id == emp.id,
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if jr and jr.department_id:
            dept = await session.get(Department, jr.department_id)
            dept_name = dept.name if dept else None

    return CertificateRead(
        id=cert.id,
        employee_id=cert.employee_id,
        employee_code=emp_code,
        employee_name=emp.full_name if emp else "",
        department_name=dept_name,
        certificate_name=cert.certificate_name,
        issuing_organization=cert.issuing_organization,
        issued_date=cert.issued_date,
        expiry_date=cert.expiry_date,
        expiry_status=compute_expiry_status(cert.expiry_date, today),
        days_until_expiry=compute_days_until_expiry(cert.expiry_date, today),
        related_course_id=cert.related_course_id,
        related_course_name=course.name if course else None,
        note=cert.note,
        has_file=cert.file_path is not None,
        file_name=cert.file_name,
        file_size=cert.file_size,
        created_by_name=getattr(creator, "full_name", None) or (creator.email if creator else None),
        created_at=cert.created_at,
    )


async def get_certificates(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    expiry_status: Optional[str] = None,
    department_id: Optional[int] = None,
    from_issued: Optional[date] = None,
    to_issued: Optional[date] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> CertificateListPage:
    today = date.today()

    stmt = (
        select(EmployeeTrainingCertificate)
        .join(Employee, Employee.id == EmployeeTrainingCertificate.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
    )

    if employee_id is not None:
        stmt = stmt.where(EmployeeTrainingCertificate.employee_id == employee_id)
    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)
    if from_issued is not None:
        stmt = stmt.where(EmployeeTrainingCertificate.issued_date >= from_issued)
    if to_issued is not None:
        stmt = stmt.where(EmployeeTrainingCertificate.issued_date <= to_issued)

    if expiry_status is not None:
        from datetime import timedelta
        soon = today + timedelta(days=EXPIRY_SOON_DAYS)
        if expiry_status == "no_expiry":
            stmt = stmt.where(EmployeeTrainingCertificate.expiry_date.is_(None))
        elif expiry_status == "expired":
            stmt = stmt.where(EmployeeTrainingCertificate.expiry_date < today)
        elif expiry_status == "expiring_soon":
            stmt = stmt.where(
                EmployeeTrainingCertificate.expiry_date >= today,
                EmployeeTrainingCertificate.expiry_date <= soon,
            )
        elif expiry_status == "valid":
            stmt = stmt.where(EmployeeTrainingCertificate.expiry_date > soon)

    if search:
        from app.services.administrative_import_service import normalize_text
        kw = f"%{search.strip()}%"
        norm_kw = f"%{normalize_text(search.strip())}%"
        dept_prefix = func.coalesce(
            func.nullif(func.btrim(Department.display_prefix), ""),
            Department.code,
        )
        generated_code = dept_prefix + func.lpad(
            sa_cast(Employee.employee_seq, String), 4, "0"
        )
        stmt = stmt.where(
            or_(
                EmployeeTrainingCertificate.certificate_name.ilike(kw),
                Employee.full_name.ilike(kw),
                Employee.normalized_name.ilike(norm_kw),
                generated_code.ilike(kw),
            )
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(EmployeeTrainingCertificate.issued_date.desc(), EmployeeTrainingCertificate.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    items: List[CertificateRead] = []
    for row in rows:
        items.append(await _build_read(session, row))

    return CertificateListPage(items=items, total=total, page=page, page_size=page_size)


async def get_certificate(session: AsyncSession, cert_id: int) -> CertificateRead:
    cert = await _get_or_404(session, cert_id)
    return await _build_read(session, cert)


async def create_certificate(
    session: AsyncSession,
    data: CertificateCreate,
    created_by_id: int,
    file: Optional[UploadFile] = None,
) -> CertificateRead:
    emp = await session.get(Employee, data.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    if data.related_course_id is not None:
        course = await session.get(TrainingCourse, data.related_course_id)
        if not course:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khóa đào tạo liên quan")

    cert = EmployeeTrainingCertificate(
        employee_id=data.employee_id,
        certificate_name=data.certificate_name,
        issuing_organization=data.issuing_organization,
        issued_date=data.issued_date,
        expiry_date=data.expiry_date,
        related_course_id=data.related_course_id,
        note=data.note,
        created_by_id=created_by_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(cert)
    await session.flush()  # get cert.id

    if file and file.filename:
        # Peek size before upload
        content = await file.read()
        if len(content) > _MAX_FILE_SIZE:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File không được vượt quá 10MB")
        from io import BytesIO
        from starlette.datastructures import Headers as StarletteHeaders
        ct = file.content_type or "application/octet-stream"
        file_copy = UploadFile(
            filename=file.filename,
            file=BytesIO(content),
            headers=StarletteHeaders({"content-type": ct}),
        )
        object_name, file_size = await storage.save_certificate_file(cert.id, file_copy)
        cert.file_path = object_name
        cert.file_name = file.filename
        cert.file_size = file_size
        cert.mime_type = ct
        session.add(cert)
        await session.flush()

    return await _build_read(session, cert)


async def update_certificate(
    session: AsyncSession,
    cert_id: int,
    data: CertificateUpdate,
    file: Optional[UploadFile] = None,
) -> CertificateRead:
    cert = await _get_or_404(session, cert_id)

    if data.certificate_name is not None:
        cert.certificate_name = data.certificate_name
    if data.issuing_organization is not None:
        cert.issuing_organization = data.issuing_organization
    if data.issued_date is not None:
        cert.issued_date = data.issued_date
    if data.expiry_date is not None:
        cert.expiry_date = data.expiry_date
    if data.related_course_id is not None:
        course = await session.get(TrainingCourse, data.related_course_id)
        if not course:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khóa đào tạo liên quan")
        cert.related_course_id = data.related_course_id
    if data.note is not None:
        cert.note = data.note

    # Re-validate dates
    eff_issued = cert.issued_date
    eff_expiry = cert.expiry_date
    if eff_expiry is not None and eff_expiry <= eff_issued:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expiry_date phải sau issued_date",
        )

    if file and file.filename:
        content = await file.read()
        if len(content) > _MAX_FILE_SIZE:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File không được vượt quá 10MB")
        if cert.file_path:
            storage.delete_attachment(cert.file_path)
        from io import BytesIO
        from starlette.datastructures import Headers as StarletteHeaders
        ct = file.content_type or "application/octet-stream"
        file_copy = UploadFile(
            filename=file.filename,
            file=BytesIO(content),
            headers=StarletteHeaders({"content-type": ct}),
        )
        object_name, file_size = await storage.save_certificate_file(cert.id, file_copy)
        cert.file_path = object_name
        cert.file_name = file.filename
        cert.file_size = file_size
        cert.mime_type = ct

    cert.updated_at = _utcnow()
    session.add(cert)
    await session.flush()
    return await _build_read(session, cert)


async def delete_certificate(session: AsyncSession, cert_id: int) -> None:
    cert = await _get_or_404(session, cert_id)
    if cert.file_path:
        try:
            storage.delete_attachment(cert.file_path)
        except Exception:
            log.warning("Failed to delete MinIO object %s", cert.file_path)
    await session.delete(cert)


async def download_certificate_file(session: AsyncSession, cert_id: int):
    cert = await _get_or_404(session, cert_id)
    if not cert.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chứng chỉ này không có file đính kèm")
    return cert.file_path, cert.file_name or "certificate", cert.mime_type or "application/octet-stream"


async def get_employee_certificates(session: AsyncSession, employee_id: int) -> List[CertificateRead]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    stmt = (
        select(EmployeeTrainingCertificate)
        .where(EmployeeTrainingCertificate.employee_id == employee_id)
        .order_by(EmployeeTrainingCertificate.issued_date.desc(), EmployeeTrainingCertificate.id.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [await _build_read(session, r) for r in rows]
