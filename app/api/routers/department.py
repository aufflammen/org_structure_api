from typing import Annotated
from fastapi import APIRouter, status, Depends

from ..dependencies import get_department_service
from ...schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTreeQuery,
    DepartmentTreeResponse,
    DepartmentUpdateQuery,
    DepartmentDeleteQuery,
)
from ...services import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create department",
)
async def create_department(
        payload: DepartmentCreate,
        service: Annotated[DepartmentService, Depends(get_department_service)],
) -> DepartmentResponse:
    """Create department with optional parent."""
    return await service.create(payload)


@router.get(
    "/{department_id}",
    response_model=DepartmentTreeResponse,
    summary="Get department subtree",
)
async def get_department_tree(
        department_id: int,
        query: Annotated[DepartmentTreeQuery, Depends()],
        service: Annotated[DepartmentService, Depends(get_department_service)],
) -> DepartmentTreeResponse:
    """Return department data with nested children up to `depth` levels."""
    return await service.get_tree(department_id, query)


@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Update department",
)
async def update_department(
        department_id: int,
        payload: DepartmentUpdateQuery,
        service: Annotated[DepartmentService, Depends(get_department_service)],
) -> DepartmentResponse:
    """Partial update for department."""
    return await service.update(department_id, payload)


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete department",
)
async def delete_department(
        department_id: int,
        query: Annotated[DepartmentDeleteQuery, Depends()],
        service: Annotated[DepartmentService, Depends(get_department_service)],
) -> None:
    """Delete with cascade or reassign subtree employees."""
    await service.delete(department_id, query)
