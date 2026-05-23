from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Employee


class EmployeeRepository:
    """CRUD helpers for employees."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        department_id: int,
        full_name: str,
        position: str,
        hired_at: date | None,
    ) -> Employee:
        """Create employee."""
        employee = Employee(
            department_id=department_id,
            full_name=full_name,
            position=position,
            hired_at=hired_at,
        )
        self._session.add(employee)
        await self._session.flush()
        await self._session.refresh(employee)
        return employee

    async def list_for_department(self, department_id: int) -> list[Employee]:
        """Return all employees in a department."""
        result = await self._session.execute(
            select(Employee).where(Employee.department_id == department_id),
        )
        return list(result.scalars().all())
