"""add dag version public sharing

Revision ID: 6feacc458288
Revises: f3b7c5e2a1d4
Create Date: 2026-02-08 17:46:41.122281

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6feacc458288'
down_revision: str | Sequence[str] | None = 'f3b7c5e2a1d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("dag_versions") as batch_op:
        batch_op.add_column(
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("share_token", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint("uq_dag_versions_share_token", ["share_token"])

    with op.batch_alter_table("dag_versions") as batch_op:
        batch_op.alter_column("is_public", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("dag_versions") as batch_op:
        batch_op.drop_constraint("uq_dag_versions_share_token", type_="unique")
        batch_op.drop_column("share_token")
        batch_op.drop_column("is_public")
