from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..enums import DeleteMode
from .employee import EmployeeResponse


class DepartmentCreate(BaseModel):
    """Payload for creating a department."""

    name: Annotated[str, Field(min_length=1, max_length=200)]
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class DepartmentResponse(BaseModel):
    """Returned after department creation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    created_at: datetime


class DepartmentTreeQuery(BaseModel):
    depth: Annotated[int, Field(ge=1, le=5)] = 1
    include_employees: bool = True


class DepartmentTreeResponse(BaseModel):
    """Recursive department tree node."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    employees: list[EmployeeResponse]
    children: list[DepartmentTreeResponse]


class DepartmentUpdateQuery(BaseModel):
    """Partial update for department."""

    name: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None


class DepartmentDeleteQuery(BaseModel):
    mode: DeleteMode = Field(description="Deletion strategy")
    reassign_to_department_id: int | None = Field(
        default=None,
        description="Required when mode=reassign",
    )
