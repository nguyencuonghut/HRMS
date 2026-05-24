"""Endpoints hiệu suất KPI (10.1 + 10.2 + 10.3)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.performance import (
    DepartmentKpiStat,
    KpiImportResult,
    KpiMonthlyCreate,
    KpiMonthlyListPage,
    KpiMonthlyRead,
    KpiMonthlyUpdate,
    MonthlyKpiTrend,
    RatingDistributionReport,
    RewardFromReviewRequest,
    TrainingFromReviewRequest,
    YearlyKpiSummary,
    YearlyReviewCreate,
    YearlyReviewListPage,
    YearlyReviewRead,
    YearlyReviewUpdate,
)
from app.schemas.reward import RewardRead
from app.schemas.training import TrainingRecordRead
from app.services import kpi_service, link_service, performance_report_service, yearly_review_service
from app.services.performance_export_service import export_performance_excel

router = APIRouter()
employee_perf_router = APIRouter()

_TAG = "Hiệu suất KPI"


# ── KPI Tháng (10.1) ─────────────────────────────────────────────────────────

@router.get(
    "/kpi",
    response_model=KpiMonthlyListPage,
    tags=[_TAG],
    summary="Danh sách KPI tháng",
)
async def list_kpi(
    year:          Optional[int] = Query(None),
    month:         Optional[int] = Query(None, ge=1, le=12),
    department_id: Optional[int] = Query(None),
    search:        Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=200),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await kpi_service.get_kpi_list(
        session,
        year=year,
        month=month,
        department_id=department_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/kpi",
    response_model=KpiMonthlyRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo bản ghi KPI tháng",
)
async def create_kpi(
    body: KpiMonthlyCreate,
    current_user: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    result = await kpi_service.create_kpi(session, body, current_user.id)
    await session.commit()
    return result


@router.post(
    "/kpi/import",
    response_model=KpiImportResult,
    tags=[_TAG],
    summary="Import KPI tháng từ file Excel",
)
async def import_kpi(
    file: UploadFile = File(...),
    current_user: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    content = await file.read()
    result = await kpi_service.import_kpi_excel(session, content, current_user.id)
    await session.commit()
    return result


@router.get(
    "/kpi/template",
    tags=[_TAG],
    summary="Tải file mẫu import KPI",
)
async def download_kpi_template(
    _: User = require_permission("performance:view"),
):
    content = kpi_service.get_kpi_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=\"mau_import_kpi.xlsx\""},
    )


@router.get(
    "/kpi/{kpi_id}",
    response_model=KpiMonthlyRead,
    tags=[_TAG],
    summary="Chi tiết KPI tháng",
)
async def get_kpi(
    kpi_id: int,
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await kpi_service.get_kpi(session, kpi_id)


@router.put(
    "/kpi/{kpi_id}",
    response_model=KpiMonthlyRead,
    tags=[_TAG],
    summary="Cập nhật KPI tháng",
)
async def update_kpi(
    kpi_id: int,
    body: KpiMonthlyUpdate,
    _: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    result = await kpi_service.update_kpi(session, kpi_id, body)
    await session.commit()
    return result


@router.delete(
    "/kpi/{kpi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa KPI tháng",
)
async def delete_kpi(
    kpi_id: int,
    _: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    await kpi_service.delete_kpi(session, kpi_id)
    await session.commit()


# ── Đánh giá cuối năm (10.2) ─────────────────────────────────────────────────

@router.get(
    "/yearly-summary/{employee_id}",
    response_model=YearlyKpiSummary,
    tags=[_TAG],
    summary="Tổng hợp KPI năm của nhân viên (on-the-fly)",
)
async def get_yearly_summary(
    employee_id: int,
    year: int = Query(..., ge=2000, le=2100),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await yearly_review_service.get_yearly_kpi_summary(session, employee_id, year)


@router.get(
    "/yearly-reviews",
    response_model=YearlyReviewListPage,
    tags=[_TAG],
    summary="Danh sách đánh giá cuối năm",
)
async def list_yearly_reviews(
    year:          Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    rating:        Optional[str] = Query(None),
    search:        Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=200),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await yearly_review_service.get_yearly_reviews(
        session,
        year=year,
        department_id=department_id,
        rating=rating,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/yearly-reviews",
    response_model=YearlyReviewRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Lưu đánh giá cuối năm",
)
async def create_yearly_review(
    body: YearlyReviewCreate,
    current_user: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    result = await yearly_review_service.create_review(session, body, current_user.id)
    await session.commit()
    return result


@router.get(
    "/yearly-reviews/{review_id}",
    response_model=YearlyReviewRead,
    tags=[_TAG],
    summary="Chi tiết đánh giá cuối năm",
)
async def get_yearly_review(
    review_id: int,
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await yearly_review_service.get_yearly_review(session, review_id)


@router.put(
    "/yearly-reviews/{review_id}",
    response_model=YearlyReviewRead,
    tags=[_TAG],
    summary="Cập nhật đánh giá cuối năm",
)
async def update_yearly_review(
    review_id: int,
    body: YearlyReviewUpdate,
    _: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    result = await yearly_review_service.update_review(session, review_id, body)
    await session.commit()
    return result


@router.delete(
    "/yearly-reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa đánh giá cuối năm",
)
async def delete_yearly_review(
    review_id: int,
    _: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    await yearly_review_service.delete_review(session, review_id)
    await session.commit()


# ── Liên kết kết quả đánh giá (10.3) ─────────────────────────────────────────

@router.post(
    "/yearly-reviews/{review_id}/create-reward",
    response_model=RewardRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo khen thưởng từ kết quả đánh giá",
)
async def create_reward_from_review(
    review_id: int,
    body: RewardFromReviewRequest,
    current_user: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    result = await link_service.create_reward_from_review(session, review_id, body, current_user.id)
    await session.commit()
    return result


@router.post(
    "/yearly-reviews/{review_id}/create-training",
    response_model=TrainingRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Đề xuất đào tạo từ kết quả đánh giá",
)
async def create_training_from_review(
    review_id: int,
    body: TrainingFromReviewRequest,
    current_user: User = require_permission("performance:manage_kpi"),
    session: AsyncSession = Depends(get_session),
):
    result = await link_service.create_training_from_review(session, review_id, body, current_user.id)
    await session.commit()
    return result


# ── Lịch sử KPI / đánh giá theo nhân viên (10.3) ────────────────────────────

@employee_perf_router.get(
    "/{employee_id}/performance/kpi",
    response_model=List[KpiMonthlyRead],
    tags=[_TAG],
    summary="Lịch sử KPI tháng của nhân viên",
)
async def get_employee_kpi_history(
    employee_id: int,
    year: Optional[int] = Query(None),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await link_service.get_employee_kpi_history(session, employee_id, year)


@employee_perf_router.get(
    "/{employee_id}/performance/reviews",
    response_model=List[YearlyReviewRead],
    tags=[_TAG],
    summary="Lịch sử đánh giá cuối năm của nhân viên",
)
async def get_employee_review_history(
    employee_id: int,
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await link_service.get_employee_review_history(session, employee_id)


# ── Báo cáo hiệu suất (10.4) ─────────────────────────────────────────────────

@router.get(
    "/report/rating-distribution",
    response_model=RatingDistributionReport,
    tags=[_TAG],
    summary="Phân phối xếp loại toàn công ty theo năm",
)
async def get_rating_distribution(
    year: int = Query(..., ge=2000, le=2100),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await performance_report_service.get_rating_distribution(session, year)


@router.get(
    "/report/department-kpi",
    response_model=List[DepartmentKpiStat],
    tags=[_TAG],
    summary="Điểm KPI trung bình theo phòng ban",
)
async def get_department_kpi(
    year:          int           = Query(..., ge=2000, le=2100),
    month:         Optional[int] = Query(None, ge=1, le=12),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await performance_report_service.get_department_kpi_stats(
        session, year, month=month, department_id=department_id
    )


@router.get(
    "/report/monthly-trend",
    response_model=MonthlyKpiTrend,
    tags=[_TAG],
    summary="Xu hướng KPI theo tháng trong năm",
)
async def get_monthly_trend(
    year:          int           = Query(..., ge=2000, le=2100),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await performance_report_service.get_monthly_trend(
        session, year, department_id=department_id
    )


@router.get(
    "/report/export",
    tags=[_TAG],
    summary="Xuất báo cáo hiệu suất ra Excel",
)
async def export_report(
    year: int = Query(..., ge=2000, le=2100),
    _: User = require_permission("performance:view"),
    session: AsyncSession = Depends(get_session),
):
    content = await export_performance_excel(session, year)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="bao_cao_hieu_suat_{year}.xlsx"'},
    )
