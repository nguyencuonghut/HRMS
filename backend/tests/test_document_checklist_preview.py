import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import Headers, UploadFile

from app.core.config import settings
from app.models.employee import Employee
from app.models.recruitment import DocumentChecklistType, EmployeeDocumentChecklist
from app.seeds.document_checklist_types import seed_required_document_checklist_types
from app.services.document_checklist_service import get_employee_checklist, upload_document_file


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_upload_document_file_exposes_mime_type_in_checklist_read():
    async with _make_session()() as session:
        await seed_required_document_checklist_types(session)

        employee = (await session.execute(select(Employee).order_by(Employee.id))).scalars().first()
        assert employee is not None

        dtype = (
            await session.execute(
                select(DocumentChecklistType)
                .where(DocumentChecklistType.is_active == True)
                .order_by(DocumentChecklistType.sort_order, DocumentChecklistType.id)
            )
        ).scalars().first()
        assert dtype is not None

        item = (
            await session.execute(
                select(EmployeeDocumentChecklist).where(
                    EmployeeDocumentChecklist.employee_id == employee.id,
                    EmployeeDocumentChecklist.document_type_id == dtype.id,
                )
            )
        ).scalars().first()
        assert item is not None

        upload = UploadFile(
            file=io.BytesIO(b"png-bytes"),
            filename="preview-checklist.png",
            headers=Headers({"content-type": "image/png"}),
        )

        result = await upload_document_file(session, employee.id, item.id, upload, user_id=1)
        await session.commit()

        assert result.has_file is True
        assert result.file_name == "preview-checklist.png"
        assert result.mime_type == "image/png"

        rows = await get_employee_checklist(session, employee.id)
        refreshed = next(row for row in rows if row.id == item.id)
        assert refreshed.mime_type == "image/png"

