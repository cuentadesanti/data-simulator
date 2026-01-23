"""add_unique_constraint_to_pipeline_version

Revision ID: 75a253f883d5
Revises: c8f3a2b5d1e4
Create Date: 2026-01-22 02:32:20.964481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75a253f883d5'
down_revision: Union[str, Sequence[str], None] = 'c8f3a2b5d1e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the unique index on pipeline_id and version_number
    op.create_index('ix_pipeline_versions_unique_version', 'pipeline_versions', ['pipeline_id', 'version_number'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the unique index
    op.drop_index('ix_pipeline_versions_unique_version', table_name='pipeline_versions')
