from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.catalog import (
    EducationLevelCreate,
    EducationLevelListPage,
    EducationLevelRead,
    EducationLevelUpdate,
    EducationMajorCreate,
    EducationMajorListPage,
    EducationMajorRead,
    EducationMajorUpdate,
    EducationalInstitutionCreate,
    EducationalInstitutionListPage,
    EducationalInstitutionRead,
    EducationalInstitutionUpdate,
)
from app.services import auth_service, education_catalog_service

level_router = APIRouter()
institution_router = APIRouter()
major_router = APIRouter()
lookup_router = APIRouter()


@level_router.get("", response_model=EducationLevelListPage, summary="Danh sách trình độ học vấn")
async def list_education_levels(
    keyword: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.list_levels_page(
        session,
        keyword=keyword,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@level_router.post("", response_model=EducationLevelRead, status_code=status.HTTP_201_CREATED, summary="Tạo trình độ học vấn")
async def create_education_level(
    body: EducationLevelCreate,
    request: Request,
    current_user: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    row = await education_catalog_service.create_level(session, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "CREATE",
        entity_type="education_level",
        entity_id=row.id,
        entity_name=row.name,
        new_data={"code": row.code, "rank_no": row.rank_no, "is_active": row.is_active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(row)
    return row


@level_router.get("/{level_id}", response_model=EducationLevelRead, summary="Chi tiết trình độ học vấn")
async def get_education_level(
    level_id: int,
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.get_level_by_id(session, level_id)


@level_router.put("/{level_id}", response_model=EducationLevelRead, summary="Cập nhật trình độ học vấn")
async def update_education_level(
    level_id: int,
    body: EducationLevelUpdate,
    request: Request,
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    existing = await education_catalog_service.get_level_by_id(session, level_id)
    old_data = {"name": existing.name, "rank_no": existing.rank_no, "is_active": existing.is_active}
    row = await education_catalog_service.update_level(session, level_id, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "UPDATE",
        entity_type="education_level",
        entity_id=row.id,
        entity_name=row.name,
        old_data=old_data,
        new_data={"name": row.name, "rank_no": row.rank_no, "is_active": row.is_active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(row)
    return row


@level_router.delete("/{level_id}", summary="Khóa trình độ học vấn")
async def delete_education_level(
    level_id: int,
    request: Request,
    current_user: User = require_permission("catalog:delete"),
    session: AsyncSession = Depends(get_session),
):
    row = await education_catalog_service.get_level_by_id(session, level_id)
    result = await education_catalog_service.soft_delete_level(session, level_id)
    await auth_service.log_audit(
        session,
        current_user.id,
        "DELETE",
        entity_type="education_level",
        entity_id=row.id,
        entity_name=row.name,
        old_data={"is_active": True},
        new_data={"is_active": False},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return result


@institution_router.get("", response_model=EducationalInstitutionListPage, summary="Danh sách trường học")
async def list_educational_institutions(
    keyword: Optional[str] = Query(None),
    institution_type: Optional[str] = Query(None),
    country_code: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.list_institutions_page(
        session,
        keyword=keyword,
        institution_type=institution_type,
        country_code=country_code,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@institution_router.post("", response_model=EducationalInstitutionRead, status_code=status.HTTP_201_CREATED, summary="Tạo trường học")
async def create_educational_institution(
    body: EducationalInstitutionCreate,
    request: Request,
    current_user: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    row = await education_catalog_service.create_institution(session, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "CREATE",
        entity_type="educational_institution",
        entity_id=row.id,
        entity_name=row.name,
        new_data={
            "code": row.code,
            "institution_type": row.institution_type,
            "country_code": row.country_code,
            "province_code": row.province_code,
            "is_active": row.is_active,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(row)
    return row


@institution_router.get("/{institution_id}", response_model=EducationalInstitutionRead, summary="Chi tiết trường học")
async def get_educational_institution(
    institution_id: int,
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.get_institution_by_id(session, institution_id)


@institution_router.put("/{institution_id}", response_model=EducationalInstitutionRead, summary="Cập nhật trường học")
async def update_educational_institution(
    institution_id: int,
    body: EducationalInstitutionUpdate,
    request: Request,
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    existing = await education_catalog_service.get_institution_by_id(session, institution_id)
    old_data = {
        "name": existing.name,
        "short_name": existing.short_name,
        "institution_type": existing.institution_type,
        "country_code": existing.country_code,
        "province_code": existing.province_code,
        "is_active": existing.is_active,
    }
    row = await education_catalog_service.update_institution(session, institution_id, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "UPDATE",
        entity_type="educational_institution",
        entity_id=row.id,
        entity_name=row.name,
        old_data=old_data,
        new_data={
            "name": row.name,
            "short_name": row.short_name,
            "institution_type": row.institution_type,
            "country_code": row.country_code,
            "province_code": row.province_code,
            "is_active": row.is_active,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(row)
    return row


@institution_router.delete("/{institution_id}", summary="Khóa trường học")
async def delete_educational_institution(
    institution_id: int,
    request: Request,
    current_user: User = require_permission("catalog:delete"),
    session: AsyncSession = Depends(get_session),
):
    row = await education_catalog_service.get_institution_by_id(session, institution_id)
    result = await education_catalog_service.soft_delete_institution(session, institution_id)
    await auth_service.log_audit(
        session,
        current_user.id,
        "DELETE",
        entity_type="educational_institution",
        entity_id=row.id,
        entity_name=row.name,
        old_data={"is_active": True},
        new_data={"is_active": False},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return result


@major_router.get("", response_model=EducationMajorListPage, summary="Danh sách chuyên ngành")
async def list_education_majors(
    keyword: Optional[str] = Query(None),
    major_group: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.list_majors_page(
        session,
        keyword=keyword,
        major_group=major_group,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@major_router.post("", response_model=EducationMajorRead, status_code=status.HTTP_201_CREATED, summary="Tạo chuyên ngành")
async def create_education_major(
    body: EducationMajorCreate,
    request: Request,
    current_user: User = require_permission("catalog:create"),
    session: AsyncSession = Depends(get_session),
):
    row = await education_catalog_service.create_major(session, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "CREATE",
        entity_type="education_major",
        entity_id=row.id,
        entity_name=row.name,
        new_data={"code": row.code, "major_group": row.major_group, "is_active": row.is_active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(row)
    return row


@major_router.get("/{major_id}", response_model=EducationMajorRead, summary="Chi tiết chuyên ngành")
async def get_education_major(
    major_id: int,
    _: User = require_permission("catalog:view"),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.get_major_by_id(session, major_id)


@major_router.put("/{major_id}", response_model=EducationMajorRead, summary="Cập nhật chuyên ngành")
async def update_education_major(
    major_id: int,
    body: EducationMajorUpdate,
    request: Request,
    current_user: User = require_permission("catalog:edit"),
    session: AsyncSession = Depends(get_session),
):
    existing = await education_catalog_service.get_major_by_id(session, major_id)
    old_data = {"name": existing.name, "major_group": existing.major_group, "is_active": existing.is_active}
    row = await education_catalog_service.update_major(session, major_id, body)
    await auth_service.log_audit(
        session,
        current_user.id,
        "UPDATE",
        entity_type="education_major",
        entity_id=row.id,
        entity_name=row.name,
        old_data=old_data,
        new_data={"name": row.name, "major_group": row.major_group, "is_active": row.is_active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    await session.refresh(row)
    return row


@major_router.delete("/{major_id}", summary="Khóa chuyên ngành")
async def delete_education_major(
    major_id: int,
    request: Request,
    current_user: User = require_permission("catalog:delete"),
    session: AsyncSession = Depends(get_session),
):
    row = await education_catalog_service.get_major_by_id(session, major_id)
    result = await education_catalog_service.soft_delete_major(session, major_id)
    await auth_service.log_audit(
        session,
        current_user.id,
        "DELETE",
        entity_type="education_major",
        entity_id=row.id,
        entity_name=row.name,
        old_data={"is_active": True},
        new_data={"is_active": False},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return result


@lookup_router.get("/lookups/education-levels", response_model=list[EducationLevelRead], summary="Lookup trình độ học vấn")
async def lookup_education_levels(
    keyword: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.lookup_levels(session, keyword=keyword, limit=limit)


@lookup_router.get("/lookups/educational-institutions", response_model=list[EducationalInstitutionRead], summary="Lookup trường học")
async def lookup_educational_institutions(
    keyword: Optional[str] = Query(None),
    institution_type: Optional[str] = Query(None),
    country_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.lookup_institutions(
        session,
        keyword=keyword,
        institution_type=institution_type,
        country_code=country_code,
        limit=limit,
    )


@lookup_router.get("/lookups/education-majors", response_model=list[EducationMajorRead], summary="Lookup chuyên ngành")
async def lookup_education_majors(
    keyword: Optional[str] = Query(None),
    major_group: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await education_catalog_service.lookup_majors(
        session,
        keyword=keyword,
        major_group=major_group,
        limit=limit,
    )
