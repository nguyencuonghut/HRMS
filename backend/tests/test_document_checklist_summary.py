from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee
from app.models.recruitment import DocumentChecklistType, EmployeeDocumentChecklist
from app.seeds.document_checklist_types import seed_required_document_checklist_types
from app.services.document_checklist_service import get_missing_documents_report


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_missing_documents_report_includes_missing_document_names():
    async with _make_session()() as session:
        await seed_required_document_checklist_types(session)

        employee = (
            await session.execute(
                select(Employee)
                .where(Employee.status.in_(["probation", "official"]))
                .order_by(Employee.id)
            )
        ).scalars().first()
        assert employee is not None

        required_types = (
            await session.execute(
                select(DocumentChecklistType)
                .where(
                    DocumentChecklistType.is_active == True,
                    DocumentChecklistType.is_required == True,
                )
                .order_by(DocumentChecklistType.sort_order, DocumentChecklistType.id)
            )
        ).scalars().all()
        assert len(required_types) >= 2

        checklist_items = (
            await session.execute(
                select(EmployeeDocumentChecklist)
                .where(EmployeeDocumentChecklist.employee_id == employee.id)
                .order_by(EmployeeDocumentChecklist.document_type_id)
            )
        ).scalars().all()
        assert checklist_items

        item_by_type_id = {item.document_type_id: item for item in checklist_items}
        target_missing_names: list[str] = []

        for index, dtype in enumerate(required_types):
            item = item_by_type_id.get(dtype.id)
            assert item is not None
            if index < 2:
                item.status = "not_submitted"
                item.expires_at = None
                target_missing_names.append(dtype.name)
            else:
                item.status = "submitted"
                item.expires_at = None

        await session.commit()

        rows = await get_missing_documents_report(session, search=employee.full_name)
        row = next(item for item in rows if item.employee_id == employee.id)

        assert sorted(row.missing_document_names) == sorted(target_missing_names)
        assert row.missing_count == len(target_missing_names)
