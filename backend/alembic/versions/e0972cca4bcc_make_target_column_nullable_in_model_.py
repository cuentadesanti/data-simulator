"""make target_column nullable in model_fits

Revision ID: e0972cca4bcc
Revises: 75a253f883d5
Create Date: 2026-01-22 02:46:49.775235

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e0972cca4bcc'
down_revision: str | Sequence[str] | None = '75a253f883d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('model_fits', schema=None) as batch_op:
        batch_op.alter_column('target_column',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)

    # Add the foreign key from pipeline_versions to pipelines
    # This was not included in the initial migration due to circular dependency
    with op.batch_alter_table('pipeline_versions', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_pipeline_versions_pipeline_id',
            'pipelines',
            ['pipeline_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('pipeline_versions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_pipeline_versions_pipeline_id', type_='foreignkey')

    with op.batch_alter_table('model_fits', schema=None) as batch_op:
        batch_op.alter_column('target_column',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
