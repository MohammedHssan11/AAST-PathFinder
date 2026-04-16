"""drop legacy MVP tables

Revision ID: f4c2d7e9b3a1
Revises: e6f3d9a8b1c2
Create Date: 2026-03-08 00:00:03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4c2d7e9b3a1"
down_revision: Union[str, Sequence[str], None] = "e6f3d9a8b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("tuition_fees")
    op.drop_table("students")
    op.drop_table("programs")
    op.drop_table("campus_colleges")
    op.drop_table("colleges")
    op.drop_table("campuses")


def downgrade() -> None:
    op.create_table(
        "campuses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("governorate", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "colleges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("vision", sa.Text(), nullable=False),
        sa.Column("mission", sa.Text(), nullable=False),
        sa.Column("parent_institution", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "campus_colleges",
        sa.Column("campus_id", sa.String(length=36), nullable=False),
        sa.Column("college_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"]),
        sa.PrimaryKeyConstraint("campus_id", "college_id"),
    )
    op.create_table(
        "programs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("college_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("discipline", sa.String(length=100), nullable=False),
        sa.Column("duration_years", sa.Integer(), nullable=False),
        sa.Column("teaching_language", sa.String(length=50), nullable=False),
        sa.Column("min_score", sa.Float(), nullable=False),
        sa.Column("certificate_types", sa.JSON(), nullable=False),
        sa.Column("mandatory_subjects", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tuition_fees",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("program_id", sa.String(length=36), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=1), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("per_semester", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
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
