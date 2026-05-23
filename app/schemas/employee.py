from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmployeeCreate(BaseModel):
    """Payload for creating an employee under a department."""

    full_name: Annotated[str, Field(min_length=1, max_length=200)]
    position: Annotated[str, Field(min_length=1, max_length=200)]
    hired_at: date | None = None

    @field_validator("full_name", "position", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class EmployeeResponse(BaseModel):
    """Returned after employee creation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    created_at: datetime
