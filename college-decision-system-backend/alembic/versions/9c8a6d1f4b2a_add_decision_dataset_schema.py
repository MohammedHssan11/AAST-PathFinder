"""add decision dataset schema

Revision ID: 9c8a6d1f4b2a
Revises: 377dbfa7c09e
Create Date: 2026-03-08 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c8a6d1f4b2a"
down_revision: Union[str, Sequence[str], None] = "377dbfa7c09e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_colleges",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("college_name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("year_established", sa.Integer(), nullable=True),
        sa.Column("parent_institution", sa.Text(), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("current_status", sa.Text(), nullable=True),
        sa.Column("future_prospectus", sa.Text(), nullable=True),
        sa.Column("vision", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "decision_college_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_path", sa.Text(), nullable=True),
        sa.Column("source_file_name", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "college_id",
            name="uq_decision_college_sources_college_id",
        ),
    )

    op.create_table(
        "decision_college_leadership",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("leader_name", sa.Text(), nullable=False),
        sa.Column("leader_title", sa.Text(), nullable=True),
        sa.Column("period", sa.Text(), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "decision_programs",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("program_name", sa.Text(), nullable=False),
        sa.Column("program_family", sa.Text(), nullable=True),
        sa.Column("degree_type", sa.Text(), nullable=True),
        sa.Column("study_duration_years", sa.Numeric(4, 1), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("differentiation_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "college_id",
            "program_name",
            name="uq_decision_programs_college_id_program_name",
        ),
    )
    op.create_index(
        "ix_decision_programs_college_id",
        "decision_programs",
        ["college_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_programs_program_family",
        "decision_programs",
        ["program_family"],
        unique=False,
    )
    op.create_index(
        "ix_decision_programs_program_name",
        "decision_programs",
        ["program_name"],
        unique=False,
    )

    op.create_table(
        "decision_program_decision_profiles",
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("theoretical_depth", sa.Numeric(4, 2), nullable=True),
        sa.Column("math_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("physics_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("programming_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("design_creativity", sa.Numeric(4, 2), nullable=True),
        sa.Column("lab_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("field_work_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("management_exposure", sa.Numeric(4, 2), nullable=True),
        sa.Column("workload_difficulty", sa.Numeric(4, 2), nullable=True),
        sa.Column("career_flexibility", sa.Numeric(4, 2), nullable=True),
        sa.Column("ai_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("data_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("software_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("security_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("hardware_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("business_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("finance_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("logistics_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("maritime_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("healthcare_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("creativity_design_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("language_communication_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("law_policy_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("research_orientation", sa.Numeric(4, 2), nullable=True),
        sa.Column("entrepreneurship_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("international_work_readiness", sa.Numeric(4, 2), nullable=True),
        sa.Column("remote_work_fit", sa.Numeric(4, 2), nullable=True),
        sa.Column("biology_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("energy_sector_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("international_trade_focus", sa.Numeric(4, 2), nullable=True),
        sa.Column("transport_operations_focus", sa.Numeric(4, 2), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["decision_programs.id"]),
        sa.PrimaryKeyConstraint("program_id"),
    )

    op.create_table(
        "decision_program_career_paths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("career_title", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["program_id"], ["decision_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_program_career_paths_program_id",
        "decision_program_career_paths",
        ["program_id"],
        unique=False,
    )

    op.create_table(
        "decision_program_traits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("trait_type", sa.Text(), nullable=False),
        sa.Column("trait_text", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["program_id"], ["decision_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_program_traits_program_id",
        "decision_program_traits",
        ["program_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_program_traits_trait_type",
        "decision_program_traits",
        ["trait_type"],
        unique=False,
    )

    op.create_table(
        "decision_employment_outlooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("egypt_market_level", sa.Text(), nullable=True),
        sa.Column("egypt_market_label", sa.Text(), nullable=True),
        sa.Column("egypt_market_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("international_market_level", sa.Text(), nullable=True),
        sa.Column("international_market_label", sa.Text(), nullable=True),
        sa.Column("international_market_score", sa.Numeric(4, 2), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["decision_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_employment_outlooks_program_id",
        "decision_employment_outlooks",
        ["program_id"],
        unique=True,
    )

    op.create_table(
        "decision_college_level_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("theoretical_depth", sa.Numeric(4, 2), nullable=True),
        sa.Column("math_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("practical_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("field_work_intensity", sa.Numeric(4, 2), nullable=True),
        sa.Column("research_orientation", sa.Numeric(4, 2), nullable=True),
        sa.Column("career_flexibility", sa.Numeric(4, 2), nullable=True),
        sa.Column("egypt_employability_level", sa.Text(), nullable=True),
        sa.Column("egypt_employability_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("international_employability_level", sa.Text(), nullable=True),
        sa.Column("international_employability_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("international_mobility_strength_level", sa.Text(), nullable=True),
        sa.Column("international_mobility_strength_label", sa.Text(), nullable=True),
        sa.Column("international_mobility_strength_score", sa.Numeric(4, 2), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "college_id",
            name="uq_decision_college_level_profiles_college_id",
        ),
    )

    op.create_table(
        "decision_training_and_practice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("mandatory_training", sa.Boolean(), nullable=True),
        sa.Column("industry_training", sa.Boolean(), nullable=True),
        sa.Column("field_or_sea_training", sa.Boolean(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "college_id",
            name="uq_decision_training_and_practice_college_id",
        ),
    )

    op.create_table(
        "decision_admission_requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("entry_exams_required", sa.Boolean(), nullable=True),
        sa.Column("medical_fitness_required", sa.Boolean(), nullable=True),
        sa.Column("age_limit", sa.Integer(), nullable=True),
        sa.Column("other_conditions", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "college_id",
            name="uq_decision_admission_requirements_college_id",
        ),
    )

    op.create_table(
        "decision_accepted_certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admission_requirement_id", sa.Integer(), nullable=False),
        sa.Column("certificate_name", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(
            ["admission_requirement_id"],
            ["decision_admission_requirements.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "decision_college_accreditations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("accreditation_scope", sa.Text(), nullable=False),
        sa.Column("accreditation_text", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_college_accreditations_college_id",
        "decision_college_accreditations",
        ["college_id"],
        unique=False,
    )

    op.create_table(
        "decision_college_facilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("facility_text", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_college_facilities_college_id",
        "decision_college_facilities",
        ["college_id"],
        unique=False,
    )

    op.create_table(
        "decision_college_research_focus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("research_focus_text", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "decision_college_mobility",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Text(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "college_id",
            name="uq_decision_college_mobility_college_id",
        ),
    )

    op.create_table(
        "decision_college_mobility_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mobility_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("item_text", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(
            ["mobility_id"],
            ["decision_college_mobility.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("decision_college_mobility_items")
    op.drop_table("decision_college_mobility")
    op.drop_table("decision_college_research_focus")
    op.drop_index(
        "ix_decision_college_facilities_college_id",
        table_name="decision_college_facilities",
    )
    op.drop_table("decision_college_facilities")
    op.drop_index(
        "ix_decision_college_accreditations_college_id",
        table_name="decision_college_accreditations",
    )
    op.drop_table("decision_college_accreditations")
    op.drop_table("decision_accepted_certificates")
    op.drop_table("decision_admission_requirements")
    op.drop_table("decision_training_and_practice")
    op.drop_table("decision_college_level_profiles")
    op.drop_index(
        "ix_decision_employment_outlooks_program_id",
        table_name="decision_employment_outlooks",
    )
    op.drop_table("decision_employment_outlooks")
    op.drop_index(
        "ix_decision_program_traits_trait_type",
        table_name="decision_program_traits",
    )
    op.drop_index(
        "ix_decision_program_traits_program_id",
        table_name="decision_program_traits",
    )
    op.drop_table("decision_program_traits")
    op.drop_index(
        "ix_decision_program_career_paths_program_id",
        table_name="decision_program_career_paths",
    )
    op.drop_table("decision_program_career_paths")
    op.drop_table("decision_program_decision_profiles")
    op.drop_index("ix_decision_programs_program_name", table_name="decision_programs")
    op.drop_index(
        "ix_decision_programs_program_family",
        table_name="decision_programs",
    )
    op.drop_index("ix_decision_programs_college_id", table_name="decision_programs")
    op.drop_table("decision_programs")
    op.drop_table("decision_college_leadership")
    op.drop_table("decision_college_sources")
    op.drop_table("decision_colleges")
