"""test: verify GitHub Actions migration workflow

Revision ID: b31b38815aa4
Revises: 410951e71f9d
Create Date: 2026-01-18 05:32:01.292282

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'b31b38815aa4'
down_revision: str | Sequence[str] | None = '410951e71f9d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
