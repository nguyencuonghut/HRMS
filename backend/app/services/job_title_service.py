from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.models.org import JobTitle, OrgChangeLog
from app.schemas.job_title import JobTitleCreate, JobTitleUpdate

_CACHE_KEY = "cache:job_titles:{suffix}"
_CACHE_TTL = 3600


async def _invalidate_cache() -> None:
    await cache_delete_pattern("cache:job_titles:*")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_dict(jt: JobTitle) -> dict:
    return {
        "id":        jt.id,
        "code":      jt.code,
        "name":      jt.name,
        "level":     jt.level,
        "is_active": jt.is_active,
    }


async def _log(
    session: AsyncSession,
    jt: JobTitle,
    action: str,
    old_data: Optional[dict],
    new_data: Optional[dict],
    changed_by: Optional[int],
) -> None:
    session.add(OrgChangeLog(
        entity_type="job_title",
        entity_id=jt.id,
        entity_name=jt.name,
        action=action,
        changed_by=changed_by,
        old_data=old_data,
        new_data=new_data,
    ))


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_by_id(session: AsyncSession, jt_id: int) -> JobTitle:
    result = await session.execute(
        select(JobTitle).where(JobTitle.id == jt_id, JobTitle.deleted_at.is_(None))
    )
    jt = result.scalar_one_or_none()
    if not jt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chức danh")
    return jt


async def get_list(
    session: AsyncSession,
    is_active: Optional[bool] = None,
) -> list[JobTitle]:
    cache_key = _CACHE_KEY.format(suffix=f"list:{is_active}")
    cached = await cache_get(cache_key)
    if cached is not None:
        return [JobTitle.model_validate(d) for d in cached]

    q = select(JobTitle).where(JobTitle.deleted_at.is_(None))
    if is_active is not None:
        q = q.where(JobTitle.is_active == is_active)
    q = q.order_by(JobTitle.level, JobTitle.name)
    result = await session.execute(q)
    rows = list(result.scalars().all())

    await cache_set(cache_key, [_to_dict(r) for r in rows], _CACHE_TTL)
    return rows


async def create(
    session: AsyncSession,
    data: JobTitleCreate,
    changed_by: Optional[int] = None,
) -> JobTitle:
    existing = await session.execute(
        select(JobTitle).where(JobTitle.code == data.code, JobTitle.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Mã chức danh '{data.code}' đã tồn tại",
        )

    jt = JobTitle(code=data.code, name=data.name, level=data.level)
    session.add(jt)
    await session.flush()

    await _log(session, jt, "create", None, _to_dict(jt), changed_by)
    await session.commit()
    await session.refresh(jt)
    await _invalidate_cache()
    return jt


async def update(
    session: AsyncSession,
    jt_id: int,
    data: JobTitleUpdate,
    changed_by: Optional[int] = None,
) -> JobTitle:
    jt = await get_by_id(session, jt_id)
    old_snapshot = _to_dict(jt)
    provided = data.model_fields_set

    if "name" in provided and data.name is not None:
        jt.name = data.name
    if "level" in provided and data.level is not None:
        jt.level = data.level
    if "is_active" in provided and data.is_active is not None:
        jt.is_active = data.is_active

    jt.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await _log(session, jt, "update", old_snapshot, _to_dict(jt), changed_by)
    await session.commit()
    await session.refresh(jt)
    await _invalidate_cache()
    return jt


async def delete(
    session: AsyncSession,
    jt_id: int,
    changed_by: Optional[int] = None,
) -> dict:
    jt = await get_by_id(session, jt_id)

    # Chặn xóa nếu đang được dùng bởi vị trí công việc chưa bị xóa mềm
    pos_count_result = await session.execute(
        text("SELECT COUNT(*) FROM job_positions WHERE job_title_id = :jt_id AND deleted_at IS NULL"),
        {"jt_id": jt_id},
    )
    pos_count = pos_count_result.scalar_one()
    if pos_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa: chức danh này đang được dùng bởi {pos_count} vị trí công việc",
        )

    old_snapshot = _to_dict(jt)
    jt_name = jt.name

    await _log(session, jt, "delete", old_snapshot, None, changed_by)
    # Soft delete — không xóa khỏi DB
    jt.soft_delete()
    await session.commit()
    await _invalidate_cache()

    return {"message": f"Đã xóa chức danh '{jt_name}' thành công"}
