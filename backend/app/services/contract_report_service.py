"""Service Báo cáo Hợp đồng (11.5)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import and_, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from dateutil.relativedelta import relativedelta

from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.employee_contract import EmployeeContract
from app.models.catalog import ContractCategory
from app.models.org import Department
from app.schemas.contract_report import (
    ContractSummaryOut,
    ContractExpiringRow,
    ContractExpiringPage,
    ContractByTypeOut,
    ContractTypeBreakdown,
    ContractForecastOut,
    ForecastMonthItem,
    ContractHistoryOut,
    ContractHistoryItem,
)
from app.services import employee_code_service


async def get_summary(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
) -> ContractSummaryOut:
    """Lấy dữ liệu KPI tổng quan về hợp đồng lao động gốc của nhân viên active."""
    today = date.today()
    d30 = today + timedelta(days=30)
    d31 = today + timedelta(days=31)
    d60 = today + timedelta(days=60)
    d61 = today + timedelta(days=61)
    d90 = today + timedelta(days=90)

    # Biểu thức điều kiện đếm theo từng bucket
    cond_active = sa.case((EmployeeContract.status == "active", 1), else_=None)
    cond_0_30 = sa.case(
        (
            and_(
                EmployeeContract.status == "active",
                EmployeeContract.effective_to.isnot(None),
                EmployeeContract.effective_to >= today,
                EmployeeContract.effective_to <= d30,
            ),
            1,
        ),
        else_=None,
    )
    cond_31_60 = sa.case(
        (
            and_(
                EmployeeContract.status == "active",
                EmployeeContract.effective_to.isnot(None),
                EmployeeContract.effective_to >= d31,
                EmployeeContract.effective_to <= d60,
            ),
            1,
        ),
        else_=None,
    )
    cond_61_90 = sa.case(
        (
            and_(
                EmployeeContract.status == "active",
                EmployeeContract.effective_to.isnot(None),
                EmployeeContract.effective_to >= d61,
                EmployeeContract.effective_to <= d90,
            ),
            1,
        ),
        else_=None,
    )
    cond_expired = sa.case(
        (
            and_(
                EmployeeContract.status.in_(["active", "expired"]),
                EmployeeContract.effective_to.isnot(None),
                EmployeeContract.effective_to < today,
            ),
            1,
        ),
        else_=None,
    )

    stmt = select(
        func.count(cond_active).label("total_active"),
        func.count(cond_0_30).label("expiring_0_30"),
        func.count(cond_31_60).label("expiring_31_60"),
        func.count(cond_61_90).label("expiring_61_90"),
        func.count(cond_expired).label("already_expired"),
    ).join(Employee, Employee.id == EmployeeContract.employee_id)

    # Chỉ tính HĐ gốc của nhân viên active
    stmt = stmt.where(
        EmployeeContract.document_kind == "labor_contract",
        EmployeeContract.parent_contract_id.is_(None),
        Employee.is_active == True,
    )

    if department_id is not None:
        stmt = stmt.join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,
            ),
        ).where(EmployeeJobRecord.department_id == department_id)

    res = (await session.execute(stmt)).one()

    total_active = res.total_active or 0
    expiring_0_30 = res.expiring_0_30 or 0
    expiring_31_60 = res.expiring_31_60 or 0
    expiring_61_90 = res.expiring_61_90 or 0
    already_expired = res.already_expired or 0

    # ── Tính tỉ lệ gia hạn (renewal_rate) ──
    # Số nhân viên có HĐ cũ hết hạn và đã được ký HĐ mới active sau đó
    renewed_stmt = (
        select(func.count(sa.distinct(EmployeeContract.employee_id)))
        .join(Employee, Employee.id == EmployeeContract.employee_id)
        .join(
            EmployeeContract.__table__.alias("e2"),
            sa.text("e2.employee_id = employee_contracts.employee_id")
        )
        .where(
            EmployeeContract.document_kind == "labor_contract",
            EmployeeContract.parent_contract_id.is_(None),
            EmployeeContract.effective_to.isnot(None),
            EmployeeContract.effective_to < today,
            Employee.is_active == True,
            sa.text("e2.status = 'active'"),
            sa.text("e2.document_kind = 'labor_contract'"),
            sa.text("e2.parent_contract_id IS NULL"),
            sa.text("e2.effective_from >= employee_contracts.effective_to"),
        )
    )

    # Tổng số nhân viên đã có HĐ hết hạn từ trước tới nay
    expired_stmt = (
        select(func.count(sa.distinct(EmployeeContract.employee_id)))
        .join(Employee, Employee.id == EmployeeContract.employee_id)
        .where(
            EmployeeContract.document_kind == "labor_contract",
            EmployeeContract.parent_contract_id.is_(None),
            EmployeeContract.effective_to.isnot(None),
            EmployeeContract.effective_to < today,
            Employee.is_active == True,
        )
    )

    if department_id is not None:
        renewed_stmt = renewed_stmt.join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,
            ),
        ).where(EmployeeJobRecord.department_id == department_id)

        expired_stmt = expired_stmt.join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,
            ),
        ).where(EmployeeJobRecord.department_id == department_id)

    renewed_count = (await session.execute(renewed_stmt)).scalar() or 0
    expired_total = (await session.execute(expired_stmt)).scalar() or 0

    renewal_rate = 0.0
    if expired_total > 0:
        renewal_rate = round((renewed_count / expired_total) * 100, 1)

    return ContractSummaryOut(
        total_active=total_active,
        expiring_0_30=expiring_0_30,
        expiring_31_60=expiring_31_60,
        expiring_61_90=expiring_61_90,
        already_expired=already_expired,
        renewal_rate=renewal_rate,
        as_of_date=today,
    )


async def get_expiring(
    session: AsyncSession,
    *,
    days_ahead: int = 90,
    department_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> ContractExpiringPage:
    """Lấy danh sách hợp đồng gốc sắp hết hạn, hỗ trợ phân trang và tìm kiếm."""
    today = date.today()
    limit_date = today + timedelta(days=days_ahead)

    stmt = (
        select(
            EmployeeContract,
            Employee,
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            ContractCategory.name.label("category_name"),
            ContractCategory.business_group.label("business_group"),
        )
        .join(Employee, Employee.id == EmployeeContract.employee_id)
        .join(ContractCategory, ContractCategory.id == EmployeeContract.contract_category_id)
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,
            ),
        )
        .join(Department, Department.id == EmployeeJobRecord.department_id)
        .where(
            EmployeeContract.document_kind == "labor_contract",
            EmployeeContract.parent_contract_id.is_(None),
            Employee.is_active == True,
            EmployeeContract.status == "active",
            EmployeeContract.effective_to.isnot(None),
            EmployeeContract.effective_to >= today,
            EmployeeContract.effective_to <= limit_date,
        )
    )

    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)

    if keyword:
        kw = keyword.strip().lower()
        keyword_clean = f"%{kw}%"
        if kw.isdigit():
            stmt = stmt.where(
                or_(
                    func.lower(Employee.full_name).like(keyword_clean),
                    func.lower(EmployeeContract.contract_number).like(keyword_clean),
                    sa.cast(Employee.employee_seq, sa.String).like(keyword_clean),
                )
            )
        else:
            stmt = stmt.where(
                or_(
                    func.lower(Employee.full_name).like(keyword_clean),
                    func.lower(EmployeeContract.contract_number).like(keyword_clean),
                    func.lower(Employee.normalized_name).like(keyword_clean),
                )
            )

    # Đếm tổng
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # Phân trang và sắp xếp
    stmt = stmt.order_by(EmployeeContract.effective_to.asc(), EmployeeContract.id.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = (await session.execute(stmt)).all()

    # Build display codes
    employees_list = [r.Employee for r in rows]
    code_map = await employee_code_service.batch_build_employee_display_codes(session, employees_list)

    items = []
    for r in rows:
        ec: EmployeeContract = r.EmployeeContract
        emp: Employee = r.Employee
        dept_id: int = r.department_id
        dept_name: str = r.department_name
        cat_name: str = r.category_name
        biz_group: str = r.business_group

        days_rem = (ec.effective_to - today).days
        urgency = "CRITICAL" if days_rem <= 7 else "WARNING" if days_rem <= 30 else "NOTICE"

        items.append(
            ContractExpiringRow(
                contract_id=ec.id,
                contract_number=ec.contract_number,
                employee_id=emp.id,
                employee_code=code_map.get(emp.id, ""),
                employee_name=emp.full_name,
                department_id=dept_id,
                department_name=dept_name,
                category_name=cat_name,
                business_group=biz_group or "",
                effective_from=ec.effective_from,
                effective_to=ec.effective_to,
                days_remaining=days_rem,
                urgency=urgency,
                signed_date=ec.signed_date,
                insurance_salary=ec.insurance_salary,
            )
        )

    return ContractExpiringPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        days_ahead=days_ahead,
    )


async def get_by_type(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
    year: Optional[int] = None,
) -> ContractByTypeOut:
    """Thống kê cơ cấu loại hợp đồng lao động gốc."""
    # 1. Tính tổng số hợp đồng để tính tỷ lệ phần trăm (%)
    total_stmt = (
        select(func.count(EmployeeContract.id))
        .join(Employee, Employee.id == EmployeeContract.employee_id)
        .where(
            EmployeeContract.document_kind == "labor_contract",
            EmployeeContract.parent_contract_id.is_(None),
            Employee.is_active == True,
        )
    )

    if department_id is not None:
        total_stmt = total_stmt.join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,
            ),
        ).where(EmployeeJobRecord.department_id == department_id)

    if year is not None:
        total_stmt = total_stmt.where(func.extract("year", EmployeeContract.signed_date) == year)

    total_contracts = (await session.execute(total_stmt)).scalar() or 0

    # 2. Nhóm theo loại hợp đồng (ContractCategory)
    stmt = (
        select(
            ContractCategory.id.label("category_id"),
            ContractCategory.name.label("category_name"),
            ContractCategory.business_group.label("business_group"),
            ContractCategory.legal_contract_type.label("legal_contract_type"),
            func.count(EmployeeContract.id).label("total"),
            func.count(sa.case((EmployeeContract.status == "active", 1), else_=None)).label("active"),
            func.count(sa.case((EmployeeContract.status == "expired", 1), else_=None)).label("expired"),
            func.count(sa.case((EmployeeContract.status == "terminated", 1), else_=None)).label("terminated"),
        )
        .select_from(ContractCategory)
        .join(EmployeeContract, EmployeeContract.contract_category_id == ContractCategory.id)
        .join(Employee, Employee.id == EmployeeContract.employee_id)
        .where(
            EmployeeContract.document_kind == "labor_contract",
            EmployeeContract.parent_contract_id.is_(None),
            Employee.is_active == True,
        )
    )

    if department_id is not None:
        stmt = stmt.join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,
            ),
        ).where(EmployeeJobRecord.department_id == department_id)

    if year is not None:
        stmt = stmt.where(func.extract("year", EmployeeContract.signed_date) == year)

    stmt = stmt.group_by(
        ContractCategory.id,
        ContractCategory.name,
        ContractCategory.business_group,
        ContractCategory.legal_contract_type,
    ).order_by(ContractCategory.sort_order, ContractCategory.name)

    rows = (await session.execute(stmt)).all()

    items = []
    for r in rows:
        percentage = 0.0
        if total_contracts > 0:
            percentage = round((r.total / total_contracts) * 100, 2)

        items.append(
            ContractTypeBreakdown(
                category_id=r.category_id,
                category_name=r.category_name,
                business_group=r.business_group or "",
                legal_contract_type=r.legal_contract_type,
                total=r.total,
                active=r.active,
                expired=r.expired,
                terminated=r.terminated,
                percentage=percentage,
            )
        )

    return ContractByTypeOut(
        items=items,
        total_contracts=total_contracts,
        department_id=department_id,
        year=year,
    )


async def get_expiry_forecast(
    session: AsyncSession,
    *,
    months_ahead: int = 12,
) -> ContractForecastOut:
    """Dự báo số lượng hợp đồng gốc hết hạn trong các tháng tiếp theo."""
    today = date.today()
    start_date = today.replace(day=1)
    end_date = start_date + relativedelta(months=months_ahead)

    stmt = (
        select(
            func.date_trunc("month", EmployeeContract.effective_to).label("month_trunc"),
            func.count(EmployeeContract.id).label("count"),
        )
        .join(Employee, Employee.id == EmployeeContract.employee_id)
        .where(
            EmployeeContract.status == "active",
            EmployeeContract.document_kind == "labor_contract",
            EmployeeContract.parent_contract_id.is_(None),
            EmployeeContract.effective_to.isnot(None),
            EmployeeContract.effective_to >= today,
            EmployeeContract.effective_to < end_date,
            Employee.is_active == True,
        )
        .group_by(sa.text("month_trunc"))
        .order_by(sa.text("month_trunc"))
    )

    rows = (await session.execute(stmt)).all()

    db_results = {}
    for r in rows:
        if r.month_trunc:
            ym_str = r.month_trunc.strftime("%Y-%m")
            db_results[ym_str] = r.count

    months_list = []
    total_expiring = 0

    for i in range(months_ahead):
        m_date = start_date + relativedelta(months=i)
        ym_key = m_date.strftime("%Y-%m")
        count = db_results.get(ym_key, 0)
        total_expiring += count
        months_list.append(
            ForecastMonthItem(
                year_month=ym_key,
                expiring_count=count,
            )
        )

    return ContractForecastOut(
        months=months_list,
        months_ahead=months_ahead,
        total_expiring=total_expiring,
    )


async def get_history(
    session: AsyncSession,
    *,
    employee_id: int,
) -> ContractHistoryOut:
    """Lấy danh sách toàn bộ lịch sử hợp đồng và phụ lục hợp đồng của nhân viên."""
    emp_stmt = select(Employee).where(Employee.id == employee_id)
    emp = (await session.execute(emp_stmt)).scalar_one_or_none()
    if not emp:
        raise ValueError("Nhân viên không tồn tại")

    display_code = await employee_code_service.build_employee_display_code(session, emp)

    stmt = (
        select(
            EmployeeContract,
            ContractCategory.name.label("category_name"),
        )
        .join(ContractCategory, ContractCategory.id == EmployeeContract.contract_category_id)
        .where(EmployeeContract.employee_id == employee_id)
        .order_by(EmployeeContract.effective_from.desc(), EmployeeContract.id.desc())
    )

    rows = (await session.execute(stmt)).all()

    items = []
    for r in rows:
        ec: EmployeeContract = r.EmployeeContract
        cat_name: str = r.category_name

        is_appendix = (ec.parent_contract_id is not None) or (ec.document_kind == "contract_appendix")

        items.append(
            ContractHistoryItem(
                contract_id=ec.id,
                contract_number=ec.contract_number,
                category_name=cat_name,
                document_kind=ec.document_kind,
                is_appendix=is_appendix,
                parent_contract_id=ec.parent_contract_id,
                effective_from=ec.effective_from,
                effective_to=ec.effective_to,
                signed_date=ec.signed_date,
                status=ec.status,
                insurance_salary=ec.insurance_salary,
                file_name=ec.file_name,
            )
        )

    return ContractHistoryOut(
        employee_id=emp.id,
        employee_code=display_code,
        employee_name=emp.full_name,
        items=items,
        total=len(items),
    )
