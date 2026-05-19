from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.employee_code_rule import EmployeeCodeSequenceRead
from app.services import employee_code_rule_service

router = APIRouter()


@router.get("", response_model=list[EmployeeCodeSequenceRead], summary="Danh sách hệ mã nhân viên")
async def list_employee_code_sequences(
    session: AsyncSession = Depends(get_session),
):
    return await employee_code_rule_service.list_sequences(session)
