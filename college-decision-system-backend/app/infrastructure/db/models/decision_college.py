from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.infrastructure.db.session import Base

from .decision_common import (
    ACCREDITATION_SCOPES,
    MOBILITY_ITEM_TYPES,
    DecisionTimestampMixin,
    SafeNumeric,
    validate_allowed_value,
)


class DecisionCollegeModel(Base, DecisionTimestampMixin):
    __tablename__ = "decision_colleges"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    college_name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    year_established: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_institution: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    future_prospectus: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["DecisionCollegeSourceModel | None"] = relationship(
        "DecisionCollegeSourceModel",
        back_populates="college",
        uselist=False,
        cascade="all, delete-orphan",
    )
    leadership_entries: Mapped[list["DecisionCollegeLeadershipModel"]] = relationship(
        "DecisionCollegeLeadershipModel",
        back_populates="college",
        cascade="all, delete-orphan",
        order_by="DecisionCollegeLeadershipModel.sort_order",
    )
    programs: Mapped[list["DecisionProgramModel"]] = relationship(
        "DecisionProgramModel",
        back_populates="college",
        cascade="all, delete-orphan",
        order_by="DecisionProgramModel.program_name",
    )
    level_profile: Mapped["DecisionCollegeLevelProfileModel | None"] = relationship(
        "DecisionCollegeLevelProfileModel",
        back_populates="college",
        uselist=False,
        cascade="all, delete-orphan",
    )
    training_and_practice: Mapped["DecisionTrainingAndPracticeModel | None"] = relationship(
        "DecisionTrainingAndPracticeModel",
        back_populates="college",
        uselist=False,
        cascade="all, delete-orphan",
    )
    admission_requirement: Mapped["DecisionAdmissionRequirementModel | None"] = relationship(
        "DecisionAdmissionRequirementModel",
        back_populates="college",
        uselist=False,
        cascade="all, delete-orphan",
    )
    accreditations: Mapped[list["DecisionCollegeAccreditationModel"]] = relationship(
        "DecisionCollegeAccreditationModel",
        back_populates="college",
        cascade="all, delete-orphan",
        order_by="DecisionCollegeAccreditationModel.sort_order",
    )
    facilities: Mapped[list["DecisionCollegeFacilityModel"]] = relationship(
        "DecisionCollegeFacilityModel",
        back_populates="college",
        cascade="all, delete-orphan",
        order_by="DecisionCollegeFacilityModel.sort_order",
    )
    research_focus_items: Mapped[list["DecisionCollegeResearchFocusModel"]] = relationship(
        "DecisionCollegeResearchFocusModel",
        back_populates="college",
        cascade="all, delete-orphan",
        order_by="DecisionCollegeResearchFocusModel.sort_order",
    )
    mobility: Mapped["DecisionCollegeMobilityModel | None"] = relationship(
        "DecisionCollegeMobilityModel",
        back_populates="college",
        uselist=False,
        cascade="all, delete-orphan",
    )
    matched_fee_items: Mapped[list["DecisionFeeItemModel"]] = relationship(
        "DecisionFeeItemModel",
        back_populates="matched_college",
        foreign_keys="DecisionFeeItemModel.source_college_match_id",
    )
    matched_fee_rule_colleges: Mapped[list["DecisionFeeRuleCollegeModel"]] = relationship(
        "DecisionFeeRuleCollegeModel",
        back_populates="matched_college",
        foreign_keys="DecisionFeeRuleCollegeModel.source_college_match_id",
    )


class DecisionCollegeSourceModel(Base):
    __tablename__ = "decision_college_sources"
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            name="uq_decision_college_sources_college_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    input_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="source",
    )


class DecisionCollegeLeadershipModel(Base):
    __tablename__ = "decision_college_leadership"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    leader_name: Mapped[str] = mapped_column(Text, nullable=False)
    leader_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="leadership_entries",
    )


class DecisionCollegeLevelProfileModel(Base):
    __tablename__ = "decision_college_level_profiles"
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            name="uq_decision_college_level_profiles_college_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    theoretical_depth: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    math_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    practical_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    field_work_intensity: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    research_orientation: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    career_flexibility: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    egypt_employability_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    egypt_employability_score: Mapped[Decimal | None] = mapped_column(SafeNumeric(4, 2), nullable=True)
    international_employability_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    international_employability_score: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )
    international_mobility_strength_level: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    international_mobility_strength_label: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    international_mobility_strength_score: Mapped[Decimal | None] = mapped_column(
        SafeNumeric(4, 2),
        nullable=True,
    )

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="level_profile",
    )


class DecisionTrainingAndPracticeModel(Base):
    __tablename__ = "decision_training_and_practice"
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            name="uq_decision_training_and_practice_college_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    mandatory_training: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    industry_training: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    field_or_sea_training: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="training_and_practice",
    )


class DecisionAdmissionRequirementModel(Base):
    __tablename__ = "decision_admission_requirements"
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            name="uq_decision_admission_requirements_college_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    entry_exams_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    medical_fitness_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    age_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    other_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="admission_requirement",
    )
    accepted_certificates: Mapped[list["DecisionAcceptedCertificateModel"]] = relationship(
        "DecisionAcceptedCertificateModel",
        back_populates="admission_requirement",
        cascade="all, delete-orphan",
        order_by="DecisionAcceptedCertificateModel.sort_order",
    )


class DecisionAcceptedCertificateModel(Base):
    __tablename__ = "decision_accepted_certificates"
    __table_args__ = (
        Index(
            "ix_decision_accepted_certificates_admission_requirement_id",
            "admission_requirement_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admission_requirement_id: Mapped[int] = mapped_column(
        ForeignKey("decision_admission_requirements.id"),
        nullable=False,
    )
    certificate_name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    admission_requirement: Mapped["DecisionAdmissionRequirementModel"] = relationship(
        "DecisionAdmissionRequirementModel",
        back_populates="accepted_certificates",
    )


class DecisionCollegeAccreditationModel(Base):
    __tablename__ = "decision_college_accreditations"
    __table_args__ = (
        Index(
            "ix_decision_college_accreditations_college_id",
            "college_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    accreditation_scope: Mapped[str] = mapped_column(Text, nullable=False)
    accreditation_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="accreditations",
    )

    @validates("accreditation_scope")
    def validate_scope(self, _: str, value: str) -> str:
        return validate_allowed_value(
            "accreditation_scope",
            value,
            ACCREDITATION_SCOPES,
        )


class DecisionCollegeFacilityModel(Base):
    __tablename__ = "decision_college_facilities"
    __table_args__ = (
        Index("ix_decision_college_facilities_college_id", "college_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    facility_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="facilities",
    )


class DecisionCollegeResearchFocusModel(Base):
    __tablename__ = "decision_college_research_focus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    research_focus_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="research_focus_items",
    )


class DecisionCollegeMobilityModel(Base):
    __tablename__ = "decision_college_mobility"
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            name="uq_decision_college_mobility_college_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("decision_colleges.id"),
        nullable=False,
    )
    available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    college: Mapped["DecisionCollegeModel"] = relationship(
        "DecisionCollegeModel",
        back_populates="mobility",
    )
    items: Mapped[list["DecisionCollegeMobilityItemModel"]] = relationship(
        "DecisionCollegeMobilityItemModel",
        back_populates="mobility",
        cascade="all, delete-orphan",
        order_by="DecisionCollegeMobilityItemModel.sort_order",
    )


class DecisionCollegeMobilityItemModel(Base):
    __tablename__ = "decision_college_mobility_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mobility_id: Mapped[int] = mapped_column(
        ForeignKey("decision_college_mobility.id"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    mobility: Mapped["DecisionCollegeMobilityModel"] = relationship(
        "DecisionCollegeMobilityModel",
        back_populates="items",
    )

    @validates("item_type")
    def validate_item_type(self, _: str, value: str) -> str:
        return validate_allowed_value("item_type", value, MOBILITY_ITEM_TYPES)


__all__ = [
    "DecisionAcceptedCertificateModel",
    "DecisionAdmissionRequirementModel",
    "DecisionCollegeAccreditationModel",
    "DecisionCollegeFacilityModel",
    "DecisionCollegeLeadershipModel",
    "DecisionCollegeLevelProfileModel",
    "DecisionCollegeMobilityItemModel",
    "DecisionCollegeMobilityModel",
    "DecisionCollegeModel",
    "DecisionCollegeResearchFocusModel",
    "DecisionCollegeSourceModel",
    "DecisionTrainingAndPracticeModel",
]
