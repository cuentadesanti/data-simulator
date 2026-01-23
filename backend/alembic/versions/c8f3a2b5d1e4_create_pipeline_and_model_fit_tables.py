"""create pipeline and model_fit tables

Revision ID: c8f3a2b5d1e4
Revises: b31b38815aa4
Create Date: 2026-01-22 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "c8f3a2b5d1e4"
down_revision: Union[str, Sequence[str], None] = "b31b38815aa4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pipeline_versions table first (pipelines references it)
    op.create_table(
        "pipeline_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("steps", sqlite.JSON(), nullable=False),
        sa.Column("input_schema", sqlite.JSON(), nullable=False),
        sa.Column("output_schema", sqlite.JSON(), nullable=False),
        sa.Column("lineage", sqlite.JSON(), nullable=False),
        sa.Column("source_dag_version_id", sa.String(length=36), nullable=True),
        sa.Column("source_seed", sa.Integer(), nullable=True),
        sa.Column("source_sample_size", sa.Integer(), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("steps_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_versions_pipeline_id",
        "pipeline_versions",
        ["pipeline_id"],
        unique=False,
    )

    # Create pipelines table
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("current_version_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["current_version_id"],
            ["pipeline_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Now add foreign key from pipeline_versions to pipelines
    # SQLite doesn't support adding foreign key constraints after table creation,
    # so we handle this via the ORM relationship

    # Create model_fits table
    op.create_table(
        "model_fits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_version_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model_type", sa.String(length=100), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("target_column", sa.String(length=255), nullable=False),
        sa.Column("feature_spec", sqlite.JSON(), nullable=False),
        sa.Column("split_spec", sqlite.JSON(), nullable=False),
        sa.Column("model_params", sqlite.JSON(), nullable=False),
        sa.Column("artifact_uri", sa.String(length=500), nullable=True),
        sa.Column("artifact_blob", sa.Text(), nullable=True),
        sa.Column("metrics", sqlite.JSON(), nullable=False),
        sa.Column("coefficients", sqlite.JSON(), nullable=True),
        sa.Column("diagnostics", sqlite.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_version_id"],
            ["pipeline_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_fits_pipeline_version_id",
        "model_fits",
        ["pipeline_version_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_model_fits_pipeline_version_id", table_name="model_fits")
    op.drop_table("model_fits")
    op.drop_table("pipelines")
    op.drop_index("ix_pipeline_versions_pipeline_id", table_name="pipeline_versions")
    op.drop_table("pipeline_versions")
