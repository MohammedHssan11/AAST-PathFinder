"""add decision fee schema

Revision ID: c1e7a9d42f51
Revises: 9c8a6d1f4b2a
Create Date: 2026-03-08 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1e7a9d42f51"
down_revision: Union[str, Sequence[str], None] = "9c8a6d1f4b2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_fee_global_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("applies_to", sa.Text(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("policy_id", name="uq_decision_fee_global_policies_policy_id"),
    )

    op.create_table(
        "decision_fee_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("definition_group", sa.Text(), nullable=False),
        sa.Column("definition_key", sa.Text(), nullable=False),
        sa.Column("definition_value", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "decision_fee_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fee_id", sa.Text(), nullable=False),
        sa.Column("academic_year", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("fee_mode", sa.Text(), nullable=False),
        sa.Column("branch_scope", sa.Text(), nullable=False),
        sa.Column("college_id_raw", sa.Text(), nullable=False),
        sa.Column("college_name", sa.Text(), nullable=True),
        sa.Column("program_name", sa.Text(), nullable=True),
        sa.Column("track_type", sa.Text(), nullable=False),
        sa.Column("partner_university", sa.Text(), nullable=True),
        sa.Column("source_college_match_id", sa.Text(), nullable=True),
        sa.Column("source_program_match_id", sa.Text(), nullable=True),
        sa.Column("data_quality_status", sa.Text(), nullable=True),
        sa.Column("data_quality_note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["source_college_match_id"], ["decision_colleges.id"]),
        sa.ForeignKeyConstraint(["source_program_match_id"], ["decision_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fee_id", name="uq_decision_fee_items_fee_id"),
    )
    op.create_index("ix_decision_fee_items_fee_id", "decision_fee_items", ["fee_id"], unique=False)
    op.create_index(
        "ix_decision_fee_items_college_id_raw",
        "decision_fee_items",
        ["college_id_raw"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_items_source_college_match_id",
        "decision_fee_items",
        ["source_college_match_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_items_source_program_match_id",
        "decision_fee_items",
        ["source_program_match_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_items_track_type",
        "decision_fee_items",
        ["track_type"],
        unique=False,
    )

    op.create_table(
        "decision_fee_amounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fee_item_id", sa.Integer(), nullable=False),
        sa.Column("student_group", sa.Text(), nullable=False),
        sa.Column("fee_category", sa.Text(), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["fee_item_id"], ["decision_fee_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fee_item_id",
            "student_group",
            "fee_category",
            name="uq_decision_fee_amounts_fee_item_student_group_fee_category",
        ),
    )
    op.create_index(
        "ix_decision_fee_amounts_fee_item_id",
        "decision_fee_amounts",
        ["fee_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_amounts_student_group",
        "decision_fee_amounts",
        ["student_group"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_amounts_fee_category",
        "decision_fee_amounts",
        ["fee_category"],
        unique=False,
    )

    op.create_table(
        "decision_fee_additional_fees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fee_item_id", sa.Integer(), nullable=False),
        sa.Column("fee_type", sa.Text(), nullable=False),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["fee_item_id"], ["decision_fee_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "decision_fee_category_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("certificate_type", sa.Text(), nullable=False),
        sa.Column("branch_scope", sa.Text(), nullable=False),
        sa.Column("student_group", sa.Text(), nullable=True),
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
        sa.Column("data_quality_status", sa.Text(), nullable=True),
        sa.Column("data_quality_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", name="uq_decision_fee_category_rules_rule_id"),
    )
    op.create_index(
        "ix_decision_fee_category_rules_rule_id",
        "decision_fee_category_rules",
        ["rule_id"],
        unique=False,
    )

    op.create_table(
        "decision_fee_rule_colleges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fee_rule_id", sa.Integer(), nullable=False),
        sa.Column("college_id_raw", sa.Text(), nullable=False),
        sa.Column("source_college_match_id", sa.Text(), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["fee_rule_id"], ["decision_fee_category_rules.id"]),
        sa.ForeignKeyConstraint(["source_college_match_id"], ["decision_colleges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_fee_rule_colleges_fee_rule_id",
        "decision_fee_rule_colleges",
        ["fee_rule_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_fee_rule_colleges_college_id_raw",
        "decision_fee_rule_colleges",
        ["college_id_raw"],
        unique=False,
    )

    op.create_table(
        "decision_fee_rule_thresholds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fee_rule_id", sa.Integer(), nullable=False),
        sa.Column("fee_category", sa.Text(), nullable=False),
        sa.Column("min_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("max_percent_exclusive", sa.Numeric(5, 2), nullable=True),
        sa.ForeignKeyConstraint(["fee_rule_id"], ["decision_fee_category_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fee_rule_id",
            "fee_category",
            name="uq_decision_fee_rule_thresholds_fee_rule_id_fee_category",
        ),
    )
    op.create_index(
        "ix_decision_fee_rule_thresholds_fee_rule_id",
        "decision_fee_rule_thresholds",
        ["fee_rule_id"],
        unique=False,
    )

    op.create_table(
        "decision_scholarships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scholarship_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("scholarship_id", name="uq_decision_scholarships_scholarship_id"),
    )

    op.create_table(
        "decision_scholarship_eligibility",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scholarship_id", sa.Integer(), nullable=False),
        sa.Column("eligibility_text", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["scholarship_id"], ["decision_scholarships.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("decision_scholarship_eligibility")
    op.drop_table("decision_scholarships")
    op.drop_index(
        "ix_decision_fee_rule_thresholds_fee_rule_id",
        table_name="decision_fee_rule_thresholds",
    )
    op.drop_table("decision_fee_rule_thresholds")
    op.drop_index(
        "ix_decision_fee_rule_colleges_college_id_raw",
        table_name="decision_fee_rule_colleges",
    )
    op.drop_index(
        "ix_decision_fee_rule_colleges_fee_rule_id",
        table_name="decision_fee_rule_colleges",
    )
    op.drop_table("decision_fee_rule_colleges")
    op.drop_index(
        "ix_decision_fee_category_rules_rule_id",
        table_name="decision_fee_category_rules",
    )
    op.drop_table("decision_fee_category_rules")
    op.drop_table("decision_fee_additional_fees")
    op.drop_index(
        "ix_decision_fee_amounts_fee_category",
        table_name="decision_fee_amounts",
    )
    op.drop_index(
        "ix_decision_fee_amounts_student_group",
        table_name="decision_fee_amounts",
    )
    op.drop_index(
        "ix_decision_fee_amounts_fee_item_id",
        table_name="decision_fee_amounts",
    )
    op.drop_table("decision_fee_amounts")
    op.drop_index("ix_decision_fee_items_track_type", table_name="decision_fee_items")
    op.drop_index(
        "ix_decision_fee_items_source_program_match_id",
        table_name="decision_fee_items",
    )
    op.drop_index(
        "ix_decision_fee_items_source_college_match_id",
        table_name="decision_fee_items",
    )
    op.drop_index(
        "ix_decision_fee_items_college_id_raw",
        table_name="decision_fee_items",
    )
    op.drop_index("ix_decision_fee_items_fee_id", table_name="decision_fee_items")
    op.drop_table("decision_fee_items")
    op.drop_table("decision_fee_definitions")
    op.drop_table("decision_fee_global_policies")
