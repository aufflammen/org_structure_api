"""FastAPI dependencies for sessions and services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..services import DepartmentService, EmployeeService


async def get_department_service(
        session: Annotated[AsyncSession, Depends(get_session)]
) -> DepartmentService:
    return DepartmentService(session)


async def get_employee_service(
        session: Annotated[AsyncSession, Depends(get_session)],
) -> EmployeeService:
    return EmployeeService(session)
