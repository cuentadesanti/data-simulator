"""add dag version metadata and diff

Revision ID: f3b7c5e2a1d4
Revises: 51a385b65326
Create Date: 2026-02-08 14:40:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f3b7c5e2a1d4"
down_revision = "51a385b65326"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dag_versions") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("description", sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column("parent_version_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("dag_diff", sa.JSON(), nullable=True))
        batch_op.create_index("ix_dag_versions_parent_version_id", ["parent_version_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_dag_versions_parent_version_id",
            "dag_versions",
            ["parent_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "uq_dag_versions_one_current_per_project",
        "dag_versions",
        ["project_id"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_dag_versions_one_current_per_project", table_name="dag_versions")
    with op.batch_alter_table("dag_versions") as batch_op:
        batch_op.drop_constraint("fk_dag_versions_parent_version_id", type_="foreignkey")
        batch_op.drop_index("ix_dag_versions_parent_version_id")
        batch_op.drop_column("dag_diff")
        batch_op.drop_column("parent_version_id")
        batch_op.drop_column("description")
        batch_op.drop_column("name")
