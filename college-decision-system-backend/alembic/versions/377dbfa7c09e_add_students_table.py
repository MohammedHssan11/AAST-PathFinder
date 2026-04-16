"""add students table

Revision ID: 377dbfa7c09e
Revises: 3d6b8e491c76
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "377dbfa7c09e"
down_revision = "3d6b8e491c76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.String(), primary_key=True),

        sa.Column("certificate_type", sa.String(), nullable=False),
        sa.Column("stream", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),

        sa.Column("subjects", sa.Text(), nullable=True),
        sa.Column("personality_traits", sa.Text(), nullable=True),
        sa.Column("location_preferences", sa.Text(), nullable=True),
        sa.Column("career_goals", sa.Text(), nullable=True),

        sa.Column("study_style_preference", sa.String(), nullable=True),
        sa.Column("pressure_tolerance", sa.Integer(), nullable=True),

        sa.Column("fee_category", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("students")