"""Endpoints đào tạo (9.1 + 9.2 + 9.4)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.training import (
    BulkAssignRequest,
    BulkAssignResult,
    CourseCreate,
    CourseListPage,
    CourseRead,
    CourseUpdate,
    PlanCourseCreate,
    PlanCourseRead,
    PlanCourseUpdate,
    PlanCreate,
    PlanListPage,
    PlanRead,
    PlanReadDetail,
    PlanUpdate,
    TrainingRecordCreate,
    TrainingRecordListPage,
    TrainingRecordRead,
    TrainingRecordUpdate,
)
from app.schemas.training_report import IncompleteMandatoryEmployee, TrainingReportSummary
from app.services import (
    auth_service,
    training_course_service,
    training_export_service,
    training_plan_service,
    training_record_service,
    training_report_service,
)

router = APIRouter()
_TAG = "Đào tạo"


# ── Course endpoints ──────────────────────────────────────────────────────────


@router.get("/courses", response_model=CourseListPage, tags=[_TAG], summary="Danh sách khóa học")
async def list_courses(
    search: Optional[str] = Query(None),
    course_type: Optional[str] = Query(None),
    is_mandatory: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_course_service.list_courses(
        session,
        search=search,
        course_type=course_type,
        is_mandatory=is_mandatory,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/courses",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo khóa học",
)
async def create_course(
    body: CourseCreate,
    request: Request,
    current_user: User = require_permission("training:manage_courses"),
    session: AsyncSession = Depends(get_session),
):
    course = await training_course_service.create_course(session, body)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="training_course", entity_id=course.id, entity_name=course.name,
    )
    await session.commit()
    await session.refresh(course)
    return training_course_service._build_read(course)


@router.get(
    "/courses/{course_id}",
    response_model=CourseRead,
    tags=[_TAG],
    summary="Chi tiết khóa học",
)
async def get_course(
    course_id: int,
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_course_service.get_course(session, course_id)


@router.put(
    "/courses/{course_id}",
    response_model=CourseRead,
    tags=[_TAG],
    summary="Cập nhật khóa học",
)
async def update_course(
    course_id: int,
    body: CourseUpdate,
    request: Request,
    current_user: User = require_permission("training:manage_courses"),
    session: AsyncSession = Depends(get_session),
):
    course = await training_course_service.update_course(session, course_id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="training_course", entity_id=course.id, entity_name=course.name,
    )
    await session.commit()
    await session.refresh(course)
    return training_course_service._build_read(course)


@router.delete(
    "/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa khóa học",
)
async def delete_course(
    course_id: int,
    request: Request,
    current_user: User = require_permission("training:manage_courses"),
    session: AsyncSession = Depends(get_session),
):
    result = await training_course_service.delete_course(session, course_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="training_course", entity_id=course_id,
        entity_name=f"delete:{result}",
    )
    await session.commit()


# ── Plan endpoints ────────────────────────────────────────────────────────────


@router.get("/plans", response_model=PlanListPage, tags=[_TAG], summary="Danh sách kế hoạch đào tạo")
async def list_plans(
    year: Optional[int] = Query(None),
    quarter: Optional[int] = Query(None, ge=0, le=4),
    department_id: Optional[int] = Query(None),
    plan_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_plan_service.list_plans(
        session,
        year=year,
        quarter=quarter,
        department_id=department_id,
        status=plan_status,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/plans",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo kế hoạch đào tạo",
)
async def create_plan(
    body: PlanCreate,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    plan = await training_plan_service.create_plan(session, body, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="training_plan", entity_id=plan.id, entity_name=plan.title,
    )
    await session.commit()
    return await training_plan_service.get_plan(session, plan.id)


@router.get(
    "/plans/{plan_id}",
    response_model=PlanReadDetail,
    tags=[_TAG],
    summary="Chi tiết kế hoạch đào tạo",
)
async def get_plan_detail(
    plan_id: int,
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_plan_service.get_plan_detail(session, plan_id)


@router.put(
    "/plans/{plan_id}",
    response_model=PlanRead,
    tags=[_TAG],
    summary="Cập nhật kế hoạch đào tạo",
)
async def update_plan(
    plan_id: int,
    body: PlanUpdate,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    plan = await training_plan_service.update_plan(session, plan_id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="training_plan", entity_id=plan.id, entity_name=plan.title,
    )
    await session.commit()
    return await training_plan_service.get_plan(session, plan_id)


@router.delete(
    "/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa kế hoạch đào tạo",
)
async def delete_plan(
    plan_id: int,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    await training_plan_service.delete_plan(session, plan_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="training_plan", entity_id=plan_id,
    )
    await session.commit()


@router.post(
    "/plans/{plan_id}/approve",
    response_model=PlanRead,
    tags=[_TAG],
    summary="Phê duyệt kế hoạch đào tạo",
)
async def approve_plan(
    plan_id: int,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    plan = await training_plan_service.approve_plan(session, plan_id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="training_plan", entity_id=plan.id, entity_name="approve",
    )
    await session.commit()
    return await training_plan_service.get_plan(session, plan_id)


@router.post(
    "/plans/{plan_id}/cancel",
    response_model=PlanRead,
    tags=[_TAG],
    summary="Hủy kế hoạch đào tạo",
)
async def cancel_plan(
    plan_id: int,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    plan = await training_plan_service.cancel_plan(session, plan_id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="training_plan", entity_id=plan.id, entity_name="cancel",
    )
    await session.commit()
    return await training_plan_service.get_plan(session, plan_id)


# ── Plan-courses endpoints ────────────────────────────────────────────────────


@router.get(
    "/plans/{plan_id}/courses",
    response_model=list[PlanCourseRead],
    tags=[_TAG],
    summary="Danh sách khóa học trong kế hoạch",
)
async def list_plan_courses(
    plan_id: int,
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_plan_service.list_plan_courses(session, plan_id)


@router.post(
    "/plans/{plan_id}/courses",
    response_model=PlanCourseRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Thêm khóa học vào kế hoạch",
)
async def add_course_to_plan(
    plan_id: int,
    body: PlanCourseCreate,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    pc = await training_plan_service.add_course_to_plan(session, plan_id, body)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="training_plan_course",
        entity_id=pc.id,
        entity_name=f"plan:{plan_id},course:{body.course_id}",
    )
    await session.commit()
    # Re-fetch with course details
    courses = await training_plan_service.list_plan_courses(session, plan_id)
    for c in courses:
        if c.course_id == body.course_id:
            return c
    return courses[-1]


@router.put(
    "/plans/{plan_id}/courses/{course_id}",
    response_model=PlanCourseRead,
    tags=[_TAG],
    summary="Cập nhật khóa học trong kế hoạch",
)
async def update_plan_course(
    plan_id: int,
    course_id: int,
    body: PlanCourseUpdate,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    await training_plan_service.update_plan_course(session, plan_id, course_id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="training_plan_course",
        entity_name=f"plan:{plan_id},course:{course_id}",
    )
    await session.commit()
    courses = await training_plan_service.list_plan_courses(session, plan_id)
    for c in courses:
        if c.course_id == course_id:
            return c
    raise Exception("Unexpected: plan course not found after update")


@router.delete(
    "/plans/{plan_id}/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa khóa học khỏi kế hoạch",
)
async def remove_course_from_plan(
    plan_id: int,
    course_id: int,
    request: Request,
    current_user: User = require_permission("training:manage_plans"),
    session: AsyncSession = Depends(get_session),
):
    await training_plan_service.remove_course_from_plan(session, plan_id, course_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="training_plan_course",
        entity_name=f"plan:{plan_id},course:{course_id}",
    )
    await session.commit()


# ── Record endpoints (9.2) ────────────────────────────────────────────────────


@router.get("/records", response_model=TrainingRecordListPage, tags=[_TAG], summary="Danh sách bản ghi đào tạo")
async def list_records(
    employee_id:   Optional[int]  = Query(None),
    course_id:     Optional[int]  = Query(None),
    plan_id:       Optional[int]  = Query(None),
    rec_status:    Optional[str]  = Query(None, alias="status"),
    result:        Optional[str]  = Query(None),
    department_id: Optional[int]  = Query(None),
    from_date:     Optional[date] = Query(None),
    to_date:       Optional[date] = Query(None),
    search:        Optional[str]  = Query(None),
    page:          int            = Query(1, ge=1),
    page_size:     int            = Query(20, ge=1, le=200),
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_record_service.get_records(
        session,
        employee_id=employee_id,
        course_id=course_id,
        plan_id=plan_id,
        status=rec_status,
        result=result,
        department_id=department_id,
        from_date=from_date,
        to_date=to_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/records",
    response_model=TrainingRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo bản ghi đào tạo",
)
async def create_record(
    body: TrainingRecordCreate,
    current_user: User = require_permission("training:manage_records"),
    session: AsyncSession = Depends(get_session),
):
    read = await training_record_service.create_record(session, body, current_user.id)
    await session.commit()
    return read


@router.get(
    "/records/{record_id}",
    response_model=TrainingRecordRead,
    tags=[_TAG],
    summary="Chi tiết bản ghi đào tạo",
)
async def get_record(
    record_id: int,
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_record_service.get_record(session, record_id)


@router.put(
    "/records/{record_id}",
    response_model=TrainingRecordRead,
    tags=[_TAG],
    summary="Cập nhật bản ghi đào tạo",
)
async def update_record(
    record_id: int,
    body: TrainingRecordUpdate,
    _: User = require_permission("training:manage_records"),
    session: AsyncSession = Depends(get_session),
):
    read = await training_record_service.update_record(session, record_id, body)
    await session.commit()
    return read


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa bản ghi đào tạo",
)
async def delete_record(
    record_id: int,
    _: User = require_permission("training:manage_records"),
    session: AsyncSession = Depends(get_session),
):
    await training_record_service.delete_record(session, record_id)
    await session.commit()


@router.post(
    "/plans/{plan_id}/assign",
    response_model=BulkAssignResult,
    tags=[_TAG],
    summary="Gán nhân viên vào khóa học trong kế hoạch",
)
async def bulk_assign(
    plan_id: int,
    body: BulkAssignRequest,
    current_user: User = require_permission("training:manage_records"),
    session: AsyncSession = Depends(get_session),
):
    if body.plan_id != plan_id:
        body = body.model_copy(update={"plan_id": plan_id})
    result_obj = await training_record_service.bulk_assign(session, body, current_user.id)
    await session.commit()
    return result_obj


@router.get(
    "/passport/{employee_id}",
    response_model=list[TrainingRecordRead],
    tags=[_TAG],
    summary="Training Passport — toàn bộ lịch sử đào tạo của nhân viên",
)
async def get_training_passport(
    employee_id: int,
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_record_service.get_training_passport(session, employee_id)


# ── Report endpoints (9.4) ────────────────────────────────────────────────────


@router.get(
    "/report/summary",
    response_model=TrainingReportSummary,
    tags=[_TAG],
    summary="Báo cáo tổng hợp đào tạo",
)
async def get_report_summary(
    from_date:     date           = Query(...),
    to_date:       date           = Query(...),
    department_id: Optional[int]  = Query(None),
    course_id:     Optional[int]  = Query(None),
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_report_service.get_training_report_summary(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        course_id=course_id,
    )


@router.get(
    "/report/incomplete-mandatory",
    response_model=list[IncompleteMandatoryEmployee],
    tags=[_TAG],
    summary="Danh sách NV chưa hoàn thành đào tạo bắt buộc",
)
async def get_incomplete_mandatory(
    department_id: Optional[int] = Query(None),
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    return await training_report_service.get_incomplete_mandatory_employees(
        session,
        department_id=department_id,
    )


@router.get(
    "/report/export",
    tags=[_TAG],
    summary="Xuất Excel báo cáo đào tạo",
)
async def export_report(
    from_date:     date           = Query(...),
    to_date:       date           = Query(...),
    department_id: Optional[int]  = Query(None),
    course_id:     Optional[int]  = Query(None),
    _: User = require_permission("training:view"),
    session: AsyncSession = Depends(get_session),
):
    content = await training_export_service.export_training_excel(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        course_id=course_id,
    )
    filename = f"bao_cao_dao_tao_{from_date}_{to_date}.xlsx"
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
