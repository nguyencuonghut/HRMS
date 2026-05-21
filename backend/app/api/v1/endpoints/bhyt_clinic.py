from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.models.bhyt_clinic import BhytClinic
from app.schemas.bhyt_clinic import (
    BhytClinicCreate,
    BhytClinicListPage,
    BhytClinicRead,
    BhytClinicUpdate,
)

router = APIRouter()


@router.get("", response_model=BhytClinicListPage, summary="Danh sách bệnh viện KCB (có phân trang)")
async def list_bhyt_clinics(
    keyword: Optional[str] = Query(None, description="Tìm theo tên hoặc mã"),
    province_code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(BhytClinic)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(BhytClinic.name.ilike(like), BhytClinic.code.ilike(like)))
    if province_code:
        stmt = stmt.where(BhytClinic.province_code == province_code)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(BhytClinic.code).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return BhytClinicListPage(items=rows, total=total, page=page, page_size=page_size)


@router.post("", response_model=BhytClinicRead, status_code=status.HTTP_201_CREATED, summary="Thêm bệnh viện KCB mới")
async def create_bhyt_clinic(
    body: BhytClinicCreate,
    _: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    existing = (await session.execute(select(BhytClinic).where(BhytClinic.code == body.code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Mã bệnh viện '{body.code}' đã tồn tại")
    clinic = BhytClinic(code=body.code, name=body.name, province_code=body.province_code)
    session.add(clinic)
    await session.commit()
    await session.refresh(clinic)
    return clinic


@router.put("/{clinic_id}", response_model=BhytClinicRead, summary="Cập nhật thông tin bệnh viện")
async def update_bhyt_clinic(
    clinic_id: int,
    body: BhytClinicUpdate,
    _: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    clinic = await session.get(BhytClinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh viện")
    if body.name is not None:
        clinic.name = body.name
    if body.province_code is not None:
        clinic.province_code = body.province_code
    await session.commit()
    await session.refresh(clinic)
    return clinic


@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa bệnh viện KCB")
async def delete_bhyt_clinic(
    clinic_id: int,
    _: User = require_permission("catalog:delete"),
    session: AsyncSession = Depends(get_session),
):
    clinic = await session.get(BhytClinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh viện")
    await session.delete(clinic)
    await session.commit()
