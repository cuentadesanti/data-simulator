"""add uploaded_sources and ux_events

Revision ID: 9c1a2f7e4b11
Revises: 6feacc458288
Create Date: 2026-02-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c1a2f7e4b11"
down_revision: str | Sequence[str] | None = "6feacc458288"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "uploaded_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_uri", sa.String(length=500), nullable=False),
        sa.Column("schema_json", sqlite.JSON(), nullable=False),
        sa.Column("upload_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uploaded_sources_project_id", "uploaded_sources", ["project_id"], unique=False)
    op.create_index("ix_uploaded_sources_created_by", "uploaded_sources", ["created_by"], unique=False)

    op.create_table(
        "ux_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("path_id", sa.String(length=100), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", sqlite.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ux_events_created_at", "ux_events", ["created_at"], unique=False)
    op.create_index("ix_ux_events_user_id", "ux_events", ["user_id"], unique=False)
    op.create_index("ix_ux_events_path_id", "ux_events", ["path_id"], unique=False)

    with op.batch_alter_table("pipeline_versions") as batch_op:
        batch_op.add_column(sa.Column("source_upload_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_pipeline_versions_source_upload_id",
            "uploaded_sources",
            ["source_upload_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("pipeline_versions") as batch_op:
        batch_op.drop_constraint("fk_pipeline_versions_source_upload_id", type_="foreignkey")
        batch_op.drop_column("source_upload_id")

    op.drop_index("ix_ux_events_path_id", table_name="ux_events")
    op.drop_index("ix_ux_events_user_id", table_name="ux_events")
    op.drop_index("ix_ux_events_created_at", table_name="ux_events")
    op.drop_table("ux_events")

    op.drop_index("ix_uploaded_sources_created_by", table_name="uploaded_sources")
    op.drop_index("ix_uploaded_sources_project_id", table_name="uploaded_sources")
    op.drop_table("uploaded_sources")

