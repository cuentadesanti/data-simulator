"""test: verify GitHub Actions migration workflow

Revision ID: b31b38815aa4
Revises: 410951e71f9d
Create Date: 2026-01-18 05:32:01.292282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b31b38815aa4'
down_revision: Union[str, Sequence[str], None] = '410951e71f9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
