from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import DepartmentRepository, EmployeeRepository
from ..schemas import EmployeeCreate, EmployeeResponse

from ..utils import DomainNotFoundError


class EmployeeService:
    """Employee business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._departments = DepartmentRepository(session)
        self._employees = EmployeeRepository(session)

    async def create_for_department(
            self,
            department_id: int,
            payload: EmployeeCreate,
    ) -> EmployeeResponse:
        """Create employee under `department_id` if department exists."""
        if not await self._departments.exists(department_id):
            raise DomainNotFoundError("Department not found")

        employee = await self._employees.create(
            department_id=department_id,
            full_name=payload.full_name,
            position=payload.position,
            hired_at=payload.hired_at,
        )
        await self._session.commit()
        return EmployeeResponse.model_validate(employee)
