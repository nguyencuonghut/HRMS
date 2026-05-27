"""API endpoints cho Onboarding Checklist (Plan 14.1)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.onboarding import (
    OnboardingChecklistCreate,
    OnboardingChecklistPage,
    OnboardingChecklistRead,
    OnboardingChecklistUpdate,
    OnboardingChecklistItemRead,
    OnboardingChecklistItemUpdate,
    OnboardingTaskCreate,
    OnboardingTaskRead,
    OnboardingTaskUpdate,
)
import app.services.onboarding_service as svc

_TAG_CHECKLIST = "Onboarding — Checklist"
_TAG_TASKS = "Onboarding — Task templates"

router = APIRouter()

# ── Task templates ────────────────────────────────────────────────────────────


@router.get("/tasks", response_model=List[OnboardingTaskRead], tags=[_TAG_TASKS])
async def list_tasks(
    is_active: Optional[bool] = Query(default=None),
    group: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_tasks(session, is_active=is_active, group=group)


@router.post(
    "/tasks",
    response_model=OnboardingTaskRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG_TASKS],
)
async def create_task(
    data: OnboardingTaskCreate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await svc.create_task(session, data)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("/tasks/{task_id}", response_model=OnboardingTaskRead, tags=[_TAG_TASKS])
async def update_task(
    task_id: int,
    data: OnboardingTaskUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await svc.update_task(session, task_id, data)
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG_TASKS],
)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        await svc.delete_task(session, task_id)
        await session.commit()
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Checklists ────────────────────────────────────────────────────────────────


@router.get("", response_model=OnboardingChecklistPage, tags=[_TAG_CHECKLIST])
async def list_checklists(
    status: Optional[str] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    days_until_completion: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_checklists(
        session,
        status=status,
        department_id=department_id,
        days_until_completion=days_until_completion,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=OnboardingChecklistRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG_CHECKLIST],
)
async def create_checklist(
    data: OnboardingChecklistCreate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await svc.create_checklist(
            session,
            employee_id=data.employee_id,
            hiring_decision_id=data.hiring_decision_id,
            buddy_user_id=data.buddy_user_id,
        )
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{checklist_id}", response_model=OnboardingChecklistRead, tags=[_TAG_CHECKLIST])
async def get_checklist(
    checklist_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await svc.get_checklist_detail(session, checklist_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/employee/{employee_id}",
    response_model=OnboardingChecklistRead,
    tags=[_TAG_CHECKLIST],
)
async def get_checklist_by_employee(
    employee_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await svc.get_checklist_by_employee(session, employee_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{checklist_id}", response_model=OnboardingChecklistRead, tags=[_TAG_CHECKLIST])
async def update_checklist(
    checklist_id: int,
    data: OnboardingChecklistUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await svc.update_checklist(session, checklist_id, data)
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch(
    "/{checklist_id}/items/{item_id}",
    response_model=OnboardingChecklistItemRead,
    tags=[_TAG_CHECKLIST],
)
async def update_item(
    checklist_id: int,
    item_id: int,
    data: OnboardingChecklistItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await svc.update_item_status(session, item_id, data)
        if result.checklist_id != checklist_id:
            raise HTTPException(status_code=404, detail="Item không thuộc checklist này")
        await session.commit()
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
