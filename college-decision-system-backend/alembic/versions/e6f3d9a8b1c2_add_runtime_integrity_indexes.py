"""add runtime integrity indexes

Revision ID: e6f3d9a8b1c2
Revises: c1e7a9d42f51
Create Date: 2026-03-08 00:00:02
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e6f3d9a8b1c2"
down_revision: Union[str, Sequence[str], None] = "c1e7a9d42f51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_decision_accepted_certificates_admission_requirement_id",
        "decision_accepted_certificates",
        ["admission_requirement_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_additional_fees_fee_item_id",
        "decision_fee_additional_fees",
        ["fee_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_decision_fee_additional_fees_fee_item_id",
        table_name="decision_fee_additional_fees",
    )
    op.drop_index(
        "ix_decision_accepted_certificates_admission_requirement_id",
        table_name="decision_accepted_certificates",
    )
