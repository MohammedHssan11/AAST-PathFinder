"""Add program_fees

Revision ID: 4a4dbd1d4c6c
Revises: 41d5ba5c5a79
Create Date: 2026-04-10 13:03:14.377584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a4dbd1d4c6c'
down_revision: Union[str, Sequence[str], None] = '41d5ba5c5a79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import app.infrastructure.db.models.decision_common

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('decision_programs', sa.Column('program_fees', app.infrastructure.db.models.decision_common.SafeNumeric(precision=10, scale=2), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('decision_programs', 'program_fees')
