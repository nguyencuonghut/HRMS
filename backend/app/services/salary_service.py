from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_insurance import EmployeeInsuranceProfile
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobPosition
from app.schemas.salary import (
    BhxhSalaryHistoryItem,
    SalaryBhxhBasisDetail,
    SalaryEmployeeListPage,
    SalaryEmployeeRow,
)
from app.services import employee_code_service


def _has_discrepancy(
    basis_amount: Optional[Decimal],
    basis_source: Optional[str],
    contract_salary: Optional[Decimal],
) -> bool:
    """Cảnh báo chỉ khi source=manual_fixed nhưng khác mức trong hợp đồng đang hiệu lực."""
    return (
        basis_source == "manual_fixed"
        and basis_amount is not None
        and contract_salary is not None
        and basis_amount != contract_salary
    )


async def _get_active_contract(
    session: AsyncSession, employee_id: int
) -> Optional[EmployeeContract]:
    row = (
        await session.execute(
            select(EmployeeContract)
            .where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.status == "active",
                EmployeeContract.insurance_salary.is_not(None),
            )
            .order_by(EmployeeContract.effective_from.desc())
            .limit(1)
        )
    ).scalars().first()
    return row


async def list_salary_employees(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    participation_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> SalaryEmployeeListPage:
    stmt = (
        select(
            Employee,
            EmployeeInsuranceProfile,
            Department.id.label("dept_id"),
            Department.name.label("department_name"),
            JobPosition.name.label("position_title"),
        )
        .outerjoin(EmployeeInsuranceProfile, EmployeeInsuranceProfile.employee_id == Employee.id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current.is_(True),
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
        .where(Employee.status != "resigned")
    )

    if search:
        kw = f"%{search.strip().lower()}%"
        stmt = stmt.where(Employee.normalized_name.ilike(kw))

    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)

    if participation_status is not None:
        stmt = stmt.where(EmployeeInsuranceProfile.participation_status == participation_status)

    from sqlalchemy import func
    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(Employee.full_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    # Batch build employee codes
    emp_ids = [r.Employee.id for r in rows]
    emp_objects = [r.Employee for r in rows]
    code_map = await employee_code_service.batch_build_employee_display_codes(session, emp_objects)

    # Fetch active contracts for each employee in one query
    active_contracts: dict[int, EmployeeContract] = {}
    if emp_ids:
        # Subquery: most recent active contract per employee
        contract_rows = (
            await session.execute(
                select(EmployeeContract)
                .where(
                    EmployeeContract.employee_id.in_(emp_ids),
                    EmployeeContract.status == "active",
                    EmployeeContract.insurance_salary.is_not(None),
                )
                .order_by(
                    EmployeeContract.employee_id,
                    EmployeeContract.effective_from.desc(),
                )
            )
        ).scalars().all()
        # Keep only the first (newest) per employee
        for c in contract_rows:
            if c.employee_id not in active_contracts:
                active_contracts[c.employee_id] = c

    items = []
    for row in rows:
        emp: Employee = row.Employee
        profile: Optional[EmployeeInsuranceProfile] = row.EmployeeInsuranceProfile
        contract = active_contracts.get(emp.id)
        contract_salary = contract.insurance_salary if contract else None
        basis_amount = profile.insurance_basis_amount if profile else None
        basis_source = profile.insurance_basis_source if profile else None

        items.append(SalaryEmployeeRow(
            employee_id=emp.id,
            employee_code=code_map.get(emp.id, str(emp.employee_seq)),
            full_name=emp.full_name,
            department_id=row.dept_id,
            department_name=row.department_name,
            position_title=row.position_title,
            insurance_basis_amount=basis_amount,
            insurance_basis_source=basis_source,
            participation_status=profile.participation_status if profile else None,
            active_contract_insurance_salary=contract_salary,
            has_discrepancy=_has_discrepancy(basis_amount, basis_source, contract_salary),
        ))

    return SalaryEmployeeListPage(items=items, total=total, page=page, page_size=page_size)


async def get_employee_bhxh_basis(
    session: AsyncSession,
    employee_id: int,
) -> SalaryBhxhBasisDetail:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    profile = (
        await session.execute(
            select(EmployeeInsuranceProfile).where(
                EmployeeInsuranceProfile.employee_id == employee_id
            )
        )
    ).scalars().first()

    job_row = (
        await session.execute(
            select(EmployeeJobRecord, Department, JobPosition)
            .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
            .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
            .where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current.is_(True),
            )
        )
    ).first()

    dept_name: Optional[str] = None
    pos_title: Optional[str] = None
    if job_row:
        dept_name = job_row.Department.name if job_row.Department else None
        pos_title = job_row.JobPosition.name if job_row.JobPosition else None

    contract = await _get_active_contract(session, employee_id)

    basis_amount = profile.insurance_basis_amount if profile else None
    basis_source = profile.insurance_basis_source if profile else None
    contract_salary = contract.insurance_salary if contract else None

    employee_code = await employee_code_service.build_employee_display_code(session, emp)

    contract_type: Optional[str] = None
    if contract:
        from app.models.catalog import ContractCategory
        cat = await session.get(ContractCategory, contract.contract_category_id)
        contract_type = cat.name if cat else None

    return SalaryBhxhBasisDetail(
        employee_id=emp.id,
        employee_code=employee_code,
        full_name=emp.full_name,
        department_name=dept_name,
        position_title=pos_title,
        insurance_basis_amount=basis_amount,
        insurance_basis_source=basis_source,
        participation_status=profile.participation_status if profile else None,
        active_contract_id=contract.id if contract else None,
        active_contract_type=contract_type,
        active_contract_insurance_salary=contract_salary,
        active_contract_effective_from=contract.effective_from if contract else None,
        has_discrepancy=_has_discrepancy(basis_amount, basis_source, contract_salary),
    )


async def get_employee_bhxh_history(
    session: AsyncSession,
    employee_id: int,
) -> list[BhxhSalaryHistoryItem]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    items: list[BhxhSalaryHistoryItem] = []

    # Nguồn 1: contracts với insurance_salary
    from app.models.catalog import ContractCategory
    contract_rows = (
        await session.execute(
            select(EmployeeContract, ContractCategory)
            .outerjoin(ContractCategory, ContractCategory.id == EmployeeContract.contract_category_id)
            .where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.insurance_salary.is_not(None),
            )
            .order_by(EmployeeContract.effective_from.desc())
            .limit(50)
        )
    ).all()

    for contract, cat in contract_rows:
        items.append(BhxhSalaryHistoryItem(
            effective_date=contract.effective_from,
            basis_amount=contract.insurance_salary,
            source_type="contract",
            note=cat.name if cat else None,
            decision_number=None,
            old_basis_amount=None,
            created_by_name=None,
        ))

    # Nguồn 2: BhxhSalaryAdjustment (7.2) — conditional: bảng có thể chưa tồn tại
    try:
        from app.models.salary_adjustment import BhxhSalaryAdjustment
        from app.models.auth import User as AuthUser
        adj_rows = (
            await session.execute(
                select(BhxhSalaryAdjustment, AuthUser)
                .outerjoin(AuthUser, AuthUser.id == BhxhSalaryAdjustment.created_by_id)
                .where(BhxhSalaryAdjustment.employee_id == employee_id)
                .order_by(BhxhSalaryAdjustment.effective_date.desc())
                .limit(50)
            )
        ).all()
        for adj, creator in adj_rows:
            items.append(BhxhSalaryHistoryItem(
                effective_date=adj.effective_date,
                basis_amount=adj.new_basis_amount,
                source_type="manual_adjustment",
                note=adj.reason,
                decision_number=adj.decision_number,
                old_basis_amount=adj.old_basis_amount,
                created_by_name=creator.full_name if creator else None,
            ))
    except (ImportError, Exception):
        # 7.2 chưa được triển khai — bỏ qua adjustments
        pass

    # Sắp xếp theo effective_date giảm dần
    items.sort(key=lambda x: x.effective_date, reverse=True)
    return items
