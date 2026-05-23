from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .employee import Employee


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        foreign_keys=[parent_id],
        remote_side=[id],
        back_populates="children",
    )

    children: Mapped[list[Department]] = relationship(
        "Department",
        foreign_keys=[parent_id],
        back_populates="parent",
        passive_deletes=True,
    )

    employees: Mapped[list[Employee]] = relationship(
        "Employee",
        back_populates="department",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_departments_name_root",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index(
            "ix_departments_name_under_parent",
            "name",
            "parent_id",
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
        ),
    )
