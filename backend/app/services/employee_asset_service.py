"""Service cho thông tin tài sản cấp phát của nhân viên."""

from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_asset import EmployeeAsset
from app.schemas.employee import AssetCreate, AssetUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_assets(
    session: AsyncSession,
    employee_id: int,
) -> list[EmployeeAsset]:
    """Lấy danh sách tài sản cấp phát của một nhân viên."""
    rows = (
        await session.execute(
            select(EmployeeAsset)
            .where(EmployeeAsset.employee_id == employee_id)
            .order_by(EmployeeAsset.handover_date.desc(), EmployeeAsset.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


async def create_asset(
    session: AsyncSession,
    employee_id: int,
    payload: AssetCreate,
) -> EmployeeAsset:
    """Tạo mới một bản ghi cấp phát tài sản."""
    asset = EmployeeAsset(
        employee_id=employee_id,
        asset_name=payload.asset_name,
        asset_type=payload.asset_type,
        handover_date=payload.handover_date,
        status=payload.status,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(asset)
    return asset


async def _get_asset_or_404(
    session: AsyncSession,
    employee_id: int,
    asset_id: int,
) -> EmployeeAsset:
    asset = await session.get(EmployeeAsset, asset_id)
    if not asset or asset.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài sản cấp phát")
    return asset


async def update_asset(
    session: AsyncSession,
    employee_id: int,
    asset_id: int,
    payload: AssetUpdate,
) -> EmployeeAsset:
    """Cập nhật thông tin cấp phát/thu hồi tài sản."""
    asset = await _get_asset_or_404(session, employee_id, asset_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    asset.updated_at = _utcnow()
    return asset


async def delete_asset(
    session: AsyncSession,
    employee_id: int,
    asset_id: int,
) -> None:
    """Xóa bản ghi cấp phát tài sản."""
    asset = await _get_asset_or_404(session, employee_id, asset_id)
    await session.delete(asset)
