from typing import Annotated
from fastapi import APIRouter, status, Depends

from ..dependencies import get_employee_service
from ...schemas import EmployeeCreate, EmployeeResponse
from ...services import EmployeeService

router = APIRouter(prefix="/departments", tags=["Employees"])


@router.post(
    "/{department_id}/employees/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee in department",
)
async def create_employee_for_department(
        department_id: int,
        payload: EmployeeCreate,
        service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeResponse:
    """Create employee for department"""
    return await service.create_for_department(department_id, payload)
