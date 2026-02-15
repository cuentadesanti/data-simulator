"""add tenant ownership, visibility, and project forking metadata

Revision ID: a7c1f2d4e9b3
Revises: 9c1a2f7e4b11
Create Date: 2026-02-15 10:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c1f2d4e9b3"
down_revision: Union[str, Sequence[str], None] = "9c1a2f7e4b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.Text(), nullable=True, server_default="legacy"))
        batch_op.add_column(sa.Column("visibility", sa.Text(), nullable=False, server_default="private"))
        batch_op.add_column(sa.Column("forked_from_project_id", sa.String(length=36), nullable=True))

    op.execute("UPDATE projects SET owner_user_id = 'legacy' WHERE owner_user_id IS NULL OR TRIM(owner_user_id) = ''")
    op.execute("UPDATE projects SET visibility = 'private' WHERE visibility IS NULL")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("owner_user_id", nullable=False, server_default=None)
        batch_op.create_index("ix_projects_owner_user_id", ["owner_user_id"], unique=False)
        batch_op.create_index("ix_projects_visibility", ["visibility"], unique=False)
        batch_op.create_index("ix_projects_forked_from_project_id", ["forked_from_project_id"], unique=False)
        batch_op.create_check_constraint(
            "ck_projects_visibility",
            "visibility IN ('private', 'public')",
        )
        batch_op.create_foreign_key(
            "fk_projects_forked_from_project_id",
            "projects",
            ["forked_from_project_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_forked_from_project_id", type_="foreignkey")
        batch_op.drop_constraint("ck_projects_visibility", type_="check")
        batch_op.drop_index("ix_projects_forked_from_project_id")
        batch_op.drop_index("ix_projects_visibility")
        batch_op.drop_index("ix_projects_owner_user_id")
        batch_op.drop_column("forked_from_project_id")
        batch_op.drop_column("visibility")
        batch_op.drop_column("owner_user_id")
