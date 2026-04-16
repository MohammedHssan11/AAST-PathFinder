from __future__ import annotations

from decimal import Decimal

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint, text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from app.infrastructure.db.session import Base

from .decision_common import (
    DecisionTimestampMixin,
    PROGRAM_TRAIT_TYPES,
    SafeNumeric,
    validate_allowed_value,
)


class DecisionProgramModel(Base, DecisionTimestampMixin):
    __tablename__ = "decision_programs"
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            "program_name",
            name="uq_decision_programs_college_id_program_name",
        ),
        Index("ix_decision_programs_college_id", "college_id"),
        Index("ix_decision_programs_program_family", "program_family"),
        Index("ix_decision_programs_program_name", "program_name"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    program_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    program_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    degree_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    study_duration_years: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 1), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    differentiation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_percentage: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    allowed_tracks: Mapped[str | None] = mapped_column(Text, nullable=True)
    program_fees: Mapped[Decimal | None] = mapped_column(SafeNumeric(10, 2), nullable=True)

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="programs",
    )
    decision_profile: Mapped["DecisionProgramDecisionProfileModel | None"] = relationship(
        "DecisionProgramDecisionProfileModel",
        back_populates="program",
        uselist=False,
        cascade="all, delete-orphan",
    )
    career_paths: Mapped[list["DecisionProgramCareerPathModel"]] = relationship(
        "DecisionProgramCareerPathModel",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="DecisionProgramCareerPathModel.sort_order",
    )
    traits: Mapped[list["DecisionProgramTraitModel"]] = relationship(
        "DecisionProgramTraitModel",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="DecisionProgramTraitModel.sort_order",
    )
    employment_outlook: Mapped["DecisionEmploymentOutlookModel | None"] = relationship(
        "DecisionEmploymentOutlookModel",
        back_populates="program",
        uselist=False,
        cascade="all, delete-orphan",
    )
    matched_fee_items: Mapped[list["DecisionFeeItemModel"]] = relationship(
        "DecisionFeeItemModel",
        back_populates="matched_program",
        foreign_keys="DecisionFeeItemModel.source_program_match_id",
    )


class DecisionProgramDecisionProfileModel(Base):
    __tablename__ = "decision_program_decision_profiles"

    program_id: Mapped[str] = mapped_column(
        ForeignKey("decision_programs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    theoretical_depth: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    math_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    physics_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    programming_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    design_creativity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    lab_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    field_work_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    management_exposure: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    workload_difficulty: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    career_flexibility: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    ai_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    data_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    software_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    security_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    hardware_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    business_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    finance_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    logistics_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    maritime_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    healthcare_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    creativity_design_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    language_communication_focus: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )
    law_policy_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    research_orientation: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    entrepreneurship_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    international_work_readiness: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )
    remote_work_fit: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    biology_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    energy_sector_focus: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    international_trade_focus: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )
    transport_operations_focus: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )

    program: Mapped["DecisionProgramModel"] = relationship(
        "DecisionProgramModel",
        back_populates="decision_profile",
    )


class DecisionProgramCareerPathModel(Base):
    __tablename__ = "decision_program_career_paths"
    __table_args__ = (
        Index("ix_decision_program_career_paths_program_id", "program_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[str] = mapped_column(
        ForeignKey("decision_programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    career_title: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    program: Mapped["DecisionProgramModel"] = relationship(
        "DecisionProgramModel",
        back_populates="career_paths",
    )


class DecisionProgramTraitModel(Base):
    __tablename__ = "decision_program_traits"
    __table_args__ = (
        Index("ix_decision_program_traits_program_id", "program_id"),
        Index("ix_decision_program_traits_trait_type", "trait_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[str] = mapped_column(
        ForeignKey("decision_programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    trait_type: Mapped[str] = mapped_column(Text, nullable=False)
    trait_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    program: Mapped["DecisionProgramModel"] = relationship(
        "DecisionProgramModel",
        back_populates="traits",
    )

    @validates("trait_type")
    def validate_trait_type(self, _: str, value: str) -> str:
        return validate_allowed_value("trait_type", value, PROGRAM_TRAIT_TYPES)


class DecisionEmploymentOutlookModel(Base):
    __tablename__ = "decision_employment_outlooks"
    __table_args__ = (
        Index(
            "ix_decision_employment_outlooks_program_id",
            "program_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[str] = mapped_column(
        ForeignKey("decision_programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    egypt_market_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    egypt_market_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    egypt_market_score: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    international_market_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    international_market_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    international_market_score: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )

    program: Mapped["DecisionProgramModel"] = relationship(
        "DecisionProgramModel",
        back_populates="employment_outlook",
    )


__all__ = [
    "DecisionEmploymentOutlookModel",
    "DecisionProgramCareerPathModel",
    "DecisionProgramDecisionProfileModel",
    "DecisionProgramModel",
    "DecisionProgramTraitModel",
]
