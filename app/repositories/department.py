from collections import deque

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Department, Employee


class DepartmentRepository:
    """CRUD helpers for departments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
            self,
            name: str,
            parent_id: int | None,
    ) -> Department:
        """Create department."""
        department = Department(
            name=name,
            parent_id=parent_id,
        )
        self._session.add(department)
        await self._session.flush()
        await self._session.refresh(department)
        return department

    async def get_by_id(self, department_id: int) -> Department | None:
        """Return department by primary key."""
        result = await self._session.execute(
            select(Department).where(Department.id == department_id),
        )
        return result.scalar_one_or_none()

    async def get_parent_id(self, department_id: int) -> int | None:
        """Return parent_id for a department or None."""
        result = await self._session.execute(
            select(Department.parent_id).where(Department.id == department_id),
        )
        return result.scalar_one_or_none()

    async def exists(self, department_id: int) -> bool:
        """Return True if department exists."""
        department = await self.get_by_id(department_id)
        return department is not None

    async def find_by_name_and_parent(
            self,
            name: str,
            parent_id: int | None,
            *,
            exclude_id: int | None = None,
    ) -> Department | None:
        """Find department by unique (name, parent_id)."""
        department_query = select(Department).where(Department.name == name)

        if parent_id is None:
            department_query = department_query.where(Department.parent_id.is_(None))
        else:
            department_query = department_query.where(Department.parent_id == parent_id)

        if exclude_id is not None:
            department_query = department_query.where(Department.id != exclude_id)

        result = await self._session.execute(department_query)
        return result.scalar_one_or_none()

    async def delete_by_id(self, department_id: int) -> None:
        """Delete row by id (relies on FK CASCADE)."""
        await self._session.execute(
            delete(Department).where(Department.id == department_id),
        )

    async def list_children_ids(self, parent_id: int) -> list[int]:
        """Return all children indices for parent."""
        result = await self._session.execute(
            select(Department.id).where(Department.parent_id == parent_id),
        )
        return list(result.scalars().all())

    async def collect_subtree_ids(self, root_id: int) -> list[int]:
        """Breadth-first collection of department ids in subtree including root."""
        collected: list[int] = []
        queue: deque[int] = deque([root_id])
        seen: set[int] = set()

        while queue:
            current = queue.popleft()
            if current in seen:
                continue

            seen.add(current)
            collected.append(current)

            children = await self.list_children_ids(current)
            queue.extend(children)

        return collected

    async def reparent_children(
            self,
            old_parent_id: int,
            new_parent_id: int | None,
    ) -> None:
        """Set parent_id for all direct children of old_parent_id."""
        await self._session.execute(
            update(Department)
            .where(Department.parent_id == old_parent_id)
            .values(parent_id=new_parent_id),
        )

    async def reassign_employees_to_department(
        self,
        from_department_ids: list[int],
        target_department_id: int,
    ) -> None:
        """Bulk-move employees to another department."""
        if not from_department_ids:
            return
        await self._session.execute(
            update(Employee)
            .where(Employee.department_id.in_(from_department_ids))
            .values(department_id=target_department_id),
        )
