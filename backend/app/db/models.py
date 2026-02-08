"""SQLAlchemy ORM models for database persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
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

    # Relationship to pipelines
    pipelines: Mapped[list["Pipeline"]] = relationship(
        "Pipeline",
        back_populates="project",
        cascade="all, delete-orphan",
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
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parent_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dag_versions.id", ondelete="SET NULL"), nullable=True
    )
    dag_definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    dag_diff: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship back to project
    project: Mapped["Project"] = relationship("Project", back_populates="versions")

    def __repr__(self) -> str:
        return f"<DAGVersion(id={self.id}, project_id={self.project_id}, version={self.version_number})>"


# =============================================================================
# Pipeline Models
# =============================================================================


class Pipeline(Base):
    """Pipeline model for storing versioned transform pipelines.
    
    A pipeline is created from a simulation run and tracks transform steps
    that derive new columns from the source data.
    """

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="simulation"
    )  # "simulation" | "upload"
    current_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pipeline_versions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="pipelines")
    versions: Mapped[list["PipelineVersion"]] = relationship(
        "PipelineVersion",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        foreign_keys="PipelineVersion.pipeline_id",
        order_by="desc(PipelineVersion.version_number)",
    )
    current_version: Mapped["PipelineVersion | None"] = relationship(
        "PipelineVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )

    def __repr__(self) -> str:
        return f"<Pipeline(id={self.id}, name={self.name}, source_type={self.source_type})>"


class PipelineVersion(Base):
    """Pipeline version model for storing versioned transform steps.
    
    Each version contains a list of transform steps that derive new columns,
    along with schema information and lineage tracking.
    """

    __tablename__ = "pipeline_versions"
    __table_args__ = (
        Index("ix_pipeline_versions_pipeline_id", "pipeline_id"),
        Index("ix_pipeline_versions_unique_version", "pipeline_id", "version_number", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Transform steps: list of {step_id, type, output_column, params, order, created_at}
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    
    # Schema information
    input_schema: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )  # list[{name, dtype}]
    output_schema: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )  # list[{name, dtype}]
    
    # Lineage: list[{output_col, inputs:[col], step_id, transform_name}]
    lineage: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    
    # Source information (for simulation source type)
    source_dag_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Fingerprints for reproducibility
    source_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hex
    steps_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 hex
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship back to pipeline
    pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline", 
        back_populates="versions",
        foreign_keys=[pipeline_id],
    )
    
    # Relationship to model fits
    model_fits: Mapped[list["ModelFit"]] = relationship(
        "ModelFit",
        back_populates="pipeline_version",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PipelineVersion(id={self.id}, pipeline_id={self.pipeline_id}, version={self.version_number})>"


class ModelFit(Base):
    """Model fit record for storing trained model metadata and artifacts.
    
    Stores the results of fitting a sklearn model on pipeline data,
    including metrics, coefficients, and the serialized model artifact.
    """

    __tablename__ = "model_fits"
    __table_args__ = (
        Index("ix_model_fits_pipeline_version_id", "pipeline_version_id"),
        Index("ix_model_fits_model_type", "model_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pipeline_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_versions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "linear_regression"
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "regression" | "classification"
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Feature specification
    feature_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Train/test split specification
    split_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Model hyperparameters
    model_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    
    # Model artifact storage
    artifact_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    artifact_blob: Mapped[str | None] = mapped_column(Text, nullable=True)  # Base64 pickle for dev
    
    # Results
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    coefficients: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    diagnostics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship back to pipeline version
    pipeline_version: Mapped["PipelineVersion"] = relationship(
        "PipelineVersion", back_populates="model_fits"
    )

    def __repr__(self) -> str:
        return f"<ModelFit(id={self.id}, name={self.name}, model_type={self.model_type})>"
