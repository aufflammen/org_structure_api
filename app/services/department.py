from sqlalchemy.ext.asyncio import AsyncSession

from ..enums import DeleteMode
from ..repositories import DepartmentRepository, EmployeeRepository
from ..schemas import (
    DepartmentCreate,
    DepartmentDeleteQuery,
    DepartmentResponse,
    DepartmentTreeQuery,
    DepartmentTreeResponse,
    DepartmentUpdateQuery,
    EmployeeResponse,
)
from ..utils import (
    DomainBadRequestError400,
    DomainConflictError409,
    DomainNotFoundError404,
)


class DepartmentService:
    """Department business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._departments = DepartmentRepository(session)
        self._employees = EmployeeRepository(session)

    async def create(self, payload: DepartmentCreate) -> DepartmentResponse:
        """Create a department after validating uniqueness."""
        if payload.parent_id is not None and not await self._departments.exists(
            payload.parent_id
        ):
            raise DomainNotFoundError404("Parent department not found")

        existing = await self._departments.find_by_name_and_parent(
            name=payload.name,
            parent_id=payload.parent_id,
        )

        if existing is not None:
            raise DomainConflictError409(
                "Duplicate: department name already exists under this parent",
            )

        department = await self._departments.create(
            name=payload.name,
            parent_id=payload.parent_id,
        )
        await self._session.commit()
        return DepartmentResponse.model_validate(department)

    async def get_tree(
        self,
        department_id: int,
        payload: DepartmentTreeQuery,
    ) -> DepartmentTreeResponse:
        """Load recursive department tree to `depth` levels."""
        root = await self._departments.get_by_id(department_id)
        if root is None:
            raise DomainNotFoundError404("Department not found")

        return await self._build_tree_node(
            department_id=root.id,
            depth=payload.depth,
            include_employees=payload.include_employees,
        )

    async def _build_tree_node(
        self,
        department_id: int,
        depth: int,
        include_employees: bool,
    ) -> DepartmentTreeResponse:
        """Recursively build ``DepartmentTree`` nodes."""
        department = await self._departments.get_by_id(department_id)
        if department is None:
            raise DomainNotFoundError404("Department not found")

        employees: list[EmployeeResponse] = []
        if include_employees:
            employees = [
                EmployeeResponse.model_validate(emp)
                for emp in await self._employees.list_for_department(department_id)
            ]
            employees.sort(key=lambda e: e.created_at)

        children: list[DepartmentTreeResponse] = []
        if depth > 0:
            children = [
                await self._build_tree_node(
                    department_id=child_id,
                    depth=depth - 1,
                    include_employees=include_employees,
                )
                for child_id in await self._departments.list_children_ids(department_id)
            ]
        return DepartmentTreeResponse(
            id=department.id,
            name=department.name,
            employees=employees,
            children=children,
        )

    async def _is_descendant(
        self,
        node_id: int,
        potential_ancestor_id: int,
    ) -> bool:
        """
        Return True if node_id is the same as or a descendant of potential_ancestor_id.
        """
        current_id: int | None = node_id

        while current_id is not None:
            if current_id == potential_ancestor_id:
                return True
            current_id = await self._departments.get_parent_id(current_id)
        return False

    async def update(
        self,
        department_id: int,
        payload: DepartmentUpdateQuery,
    ) -> DepartmentResponse:
        """Partially update name and/or parent_id."""
        department = await self._departments.get_by_id(department_id)
        if department is None:
            raise DomainNotFoundError404("Department not found")

        new_name = payload.name or department.name
        new_parent_id = payload.parent_id or department.parent_id

        if new_name == department.name and new_parent_id == department.parent_id:
            return DepartmentResponse.model_validate(department)

        if new_parent_id is not None and not await self._departments.exists(
            new_parent_id
        ):
            raise DomainNotFoundError404("Parent department not found")

        if new_parent_id == department_id:
            raise DomainConflictError409("Department cannot be its own parent")

        if new_parent_id != department.parent_id and await self._is_descendant(
            new_parent_id,  # type: ignore[arg-type]
            department_id,
        ):
            raise DomainConflictError409("Department cycle detected")

        duplicate = await self._departments.find_by_name_and_parent(
            name=new_name,
            parent_id=new_parent_id,
            exclude_id=department_id,
        )

        if duplicate is not None:
            raise DomainConflictError409("Duplicate department name in the same parent")

        department.name = new_name
        department.parent_id = new_parent_id

        await self._session.commit()
        return DepartmentResponse.model_validate(department)

    async def delete(
        self,
        department_id: int,
        payload: DepartmentDeleteQuery,
    ) -> None:
        """Delete department."""
        department = await self._departments.get_by_id(department_id)
        if department is None:
            raise DomainNotFoundError404("Department not found")

        delete_mode = payload.mode

        if delete_mode == DeleteMode.CASCADE:
            await self._departments.delete_by_id(department_id)
            await self._session.commit()

        elif delete_mode == DeleteMode.REASSIGN:
            target_department_id = payload.reassign_to_department_id

            if target_department_id is None:
                raise DomainBadRequestError400(
                    "reassign_to_department_id is required for mode=reassign"
                )

            if department_id == target_department_id:
                raise DomainBadRequestError400(
                    "reassign_to_department_id cannot be equal to deleted department id"
                )

            if not await self._departments.exists(target_department_id):
                raise DomainNotFoundError404("Department not found")

            # subtree_ids = await self._departments.collect_subtree_ids(department_id)
            # if target_department_id in subtree_ids:
            #     raise DomainConflictError409(
            #         "Cannot reassign into a department that is being removed",
            #     )

            await self._departments.reparent_children(
                old_parent_id=department_id,
                new_parent_id=department.parent_id,
            )

            await self._departments.reassign_employees_to_department(
                [department_id],
                target_department_id,
            )

            await self._departments.delete_by_id(department_id)
            await self._session.commit()

        else:
            raise DomainBadRequestError400("Unsupported delete mode")
