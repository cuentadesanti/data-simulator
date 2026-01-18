"""SQLAlchemy ORM models for database persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    pass


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Project(Base):
    """Project model for storing DAG projects."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationship to versions with cascade delete
    versions: Mapped[list["DAGVersion"]] = relationship(
        "DAGVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(DAGVersion.version_number)",
    )

    @property
    def current_version(self) -> "DAGVersion | None":
        """Get the current (active) version."""
        for version in self.versions:
            if version.is_current:
                return version
        return None

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"


class DAGVersion(Base):
    """DAG version model for storing versioned DAG definitions."""

    __tablename__ = "dag_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    dag_definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship back to project
    project: Mapped["Project"] = relationship("Project", back_populates="versions")

    def __repr__(self) -> str:
        return f"<DAGVersion(id={self.id}, project_id={self.project_id}, version={self.version_number})>"
