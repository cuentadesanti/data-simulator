"""add model_type index to model_fits

Revision ID: 51a385b65326
Revises: e0972cca4bcc
Create Date: 2026-01-23 22:51:52.920721

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51a385b65326'
down_revision: Union[str, Sequence[str], None] = 'e0972cca4bcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_model_fits_model_type', 'model_fits', ['model_type'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_model_fits_model_type', table_name='model_fits')
