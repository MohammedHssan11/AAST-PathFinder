"""Add min_percentage and allowed_tracks to decision_programs

Revision ID: 41d5ba5c5a79
Revises: 1c26e9f9d3c2
Create Date: 2026-04-01 17:02:10.623010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.infrastructure.db.models.decision_common


# revision identifiers, used by Alembic.
revision: str = '41d5ba5c5a79'
down_revision: Union[str, Sequence[str], None] = '1c26e9f9d3c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('decision_programs', sa.Column('min_percentage', app.infrastructure.db.models.decision_common.SafeNumeric(precision=4, scale=2), nullable=True))
    op.add_column('decision_programs', sa.Column('allowed_tracks', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('decision_programs', 'allowed_tracks')
    op.drop_column('decision_programs', 'min_percentage')
