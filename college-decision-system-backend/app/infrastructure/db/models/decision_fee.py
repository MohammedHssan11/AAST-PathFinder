from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.infrastructure.db.session import Base

from .decision_common import DecisionTimestampMixin, validate_allowed_value

FEE_CATEGORY_VALUES = frozenset({"A", "B", "C"})
FEE_STUDENT_GROUP_VALUES = frozenset({"supportive_states", "other_states"})
FEE_TRACK_TYPE_VALUES = frozenset({"regular", "international"})


class DecisionFeeGlobalPolicyModel(Base, DecisionTimestampMixin):
    __tablename__ = "decision_fee_global_policies"
    __table_args__ = (
        UniqueConstraint("policy_id", name="uq_decision_fee_global_policies_policy_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    applies_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)


class DecisionFeeItemModel(Base, DecisionTimestampMixin):
    __tablename__ = "decision_fee_items"
    __table_args__ = (
        UniqueConstraint("fee_id", name="uq_decision_fee_items_fee_id"),
        Index("ix_decision_fee_items_fee_id", "fee_id"),
        Index("ix_decision_fee_items_college_id_raw", "college_id_raw"),
        Index("ix_decision_fee_items_source_college_match_id", "source_college_match_id"),
        Index("ix_decision_fee_items_source_program_match_id", "source_program_match_id"),
        Index("ix_decision_fee_items_track_type", "track_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fee_id: Mapped[str] = mapped_column(Text, nullable=False)
    academic_year: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    fee_mode: Mapped[str] = mapped_column(Text, nullable=False)
    branch_scope: Mapped[str] = mapped_column(Text, nullable=False)
    college_id_raw: Mapped[str] = mapped_column(Text, nullable=False)
    college_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    program_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    track_type: Mapped[str] = mapped_column(Text, nullable=False)
    partner_university: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_college_match_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=True,
    )
    source_program_match_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_programs.id"),
        nullable=True,
    )
    data_quality_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_quality_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    matched_college = relationship(
        "DecisionCollegeModel",
        back_populates="matched_fee_items",
        foreign_keys=[source_college_match_id],
    )
    matched_program = relationship(
        "DecisionProgramModel",
        back_populates="matched_fee_items",
        foreign_keys=[source_program_match_id],
    )
    amounts: Mapped[list["DecisionFeeAmountModel"]] = relationship(
        "DecisionFeeAmountModel",
        back_populates="fee_item",
        cascade="all, delete-orphan",
        order_by="DecisionFeeAmountModel.id",
    )
    additional_fees: Mapped[list["DecisionFeeAdditionalFeeModel"]] = relationship(
        "DecisionFeeAdditionalFeeModel",
        back_populates="fee_item",
        cascade="all, delete-orphan",
        order_by="DecisionFeeAdditionalFeeModel.sort_order",
    )

    @validates("track_type")
    def validate_track_type(self, _: str, value: str) -> str:
        return validate_allowed_value("track_type", value, FEE_TRACK_TYPE_VALUES)


class DecisionFeeAmountModel(Base):
    __tablename__ = "decision_fee_amounts"
    __table_args__ = (
        UniqueConstraint(
            "fee_item_id",
            "student_group",
            "fee_category",
            name="uq_decision_fee_amounts_fee_item_student_group_fee_category",
        ),
        Index("ix_decision_fee_amounts_fee_item_id", "fee_item_id"),
        Index("ix_decision_fee_amounts_student_group", "student_group"),
        Index("ix_decision_fee_amounts_fee_category", "fee_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fee_item_id: Mapped[int] = mapped_column(
        ForeignKey("decision_fee_items.id"),
        nullable=False,
    )
    student_group: Mapped[str] = mapped_column(Text, nullable=False)
    fee_category: Mapped[str] = mapped_column(Text, nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    fee_item: Mapped["DecisionFeeItemModel"] = relationship(
        "DecisionFeeItemModel",
        back_populates="amounts",
    )

    @validates("student_group")
    def validate_student_group(self, _: str, value: str) -> str:
        return validate_allowed_value("student_group", value, FEE_STUDENT_GROUP_VALUES)

    @validates("fee_category")
    def validate_fee_category(self, _: str, value: str) -> str:
        return validate_allowed_value("fee_category", value, FEE_CATEGORY_VALUES)


class DecisionFeeAdditionalFeeModel(Base):
    __tablename__ = "decision_fee_additional_fees"
    __table_args__ = (
        Index("ix_decision_fee_additional_fees_fee_item_id", "fee_item_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fee_item_id: Mapped[int] = mapped_column(
        ForeignKey("decision_fee_items.id"),
        nullable=False,
    )
    fee_type: Mapped[str] = mapped_column(Text, nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    frequency: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    fee_item: Mapped["DecisionFeeItemModel"] = relationship(
        "DecisionFeeItemModel",
        back_populates="additional_fees",
    )


class DecisionFeeCategoryRuleModel(Base, DecisionTimestampMixin):
    __tablename__ = "decision_fee_category_rules"
    __table_args__ = (
        UniqueConstraint("rule_id", name="uq_decision_fee_category_rules_rule_id"),
        Index("ix_decision_fee_category_rules_rule_id", "rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[str] = mapped_column(Text, nullable=False)
    certificate_type: Mapped[str] = mapped_column(Text, nullable=False)
    branch_scope: Mapped[str] = mapped_column(Text, nullable=False)
    student_group: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_quality_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_quality_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    colleges: Mapped[list["DecisionFeeRuleCollegeModel"]] = relationship(
        "DecisionFeeRuleCollegeModel",
        back_populates="fee_rule",
        cascade="all, delete-orphan",
        order_by="DecisionFeeRuleCollegeModel.sort_order",
    )
    thresholds: Mapped[list["DecisionFeeRuleThresholdModel"]] = relationship(
        "DecisionFeeRuleThresholdModel",
        back_populates="fee_rule",
        cascade="all, delete-orphan",
        order_by="DecisionFeeRuleThresholdModel.id",
    )

    @validates("student_group")
    def validate_student_group(self, _: str, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_allowed_value("student_group", value, FEE_STUDENT_GROUP_VALUES)


class DecisionFeeRuleCollegeModel(Base):
    __tablename__ = "decision_fee_rule_colleges"
    __table_args__ = (
        Index("ix_decision_fee_rule_colleges_fee_rule_id", "fee_rule_id"),
        Index("ix_decision_fee_rule_colleges_college_id_raw", "college_id_raw"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fee_rule_id: Mapped[int] = mapped_column(
        ForeignKey("decision_fee_category_rules.id"),
        nullable=False,
    )
    college_id_raw: Mapped[str] = mapped_column(Text, nullable=False)
    source_college_match_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    fee_rule: Mapped["DecisionFeeCategoryRuleModel"] = relationship(
        "DecisionFeeCategoryRuleModel",
        back_populates="colleges",
    )
    matched_college = relationship(
        "DecisionCollegeModel",
        back_populates="matched_fee_rule_colleges",
        foreign_keys=[source_college_match_id],
    )


class DecisionFeeRuleThresholdModel(Base):
    __tablename__ = "decision_fee_rule_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "fee_rule_id",
            "fee_category",
            name="uq_decision_fee_rule_thresholds_fee_rule_id_fee_category",
        ),
        Index("ix_decision_fee_rule_thresholds_fee_rule_id", "fee_rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fee_rule_id: Mapped[int] = mapped_column(
        ForeignKey("decision_fee_category_rules.id"),
        nullable=False,
    )
    fee_category: Mapped[str] = mapped_column(Text, nullable=False)
    min_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_percent_exclusive: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    fee_rule: Mapped["DecisionFeeCategoryRuleModel"] = relationship(
        "DecisionFeeCategoryRuleModel",
        back_populates="thresholds",
    )

    @validates("fee_category")
    def validate_fee_category(self, _: str, value: str) -> str:
        return validate_allowed_value("fee_category", value, FEE_CATEGORY_VALUES)


class DecisionFeeDefinitionModel(Base):
    __tablename__ = "decision_fee_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    definition_group: Mapped[str] = mapped_column(Text, nullable=False)
    definition_key: Mapped[str] = mapped_column(Text, nullable=False)
    definition_value: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )


__all__ = [
    "DecisionFeeAdditionalFeeModel",
    "DecisionFeeAmountModel",
    "DecisionFeeCategoryRuleModel",
    "DecisionFeeDefinitionModel",
    "DecisionFeeGlobalPolicyModel",
    "DecisionFeeItemModel",
    "DecisionFeeRuleCollegeModel",
    "DecisionFeeRuleThresholdModel",
    "FEE_CATEGORY_VALUES",
    "FEE_STUDENT_GROUP_VALUES",
    "FEE_TRACK_TYPE_VALUES",
]
