import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.v1.schemas.normalization import BaseNormalization
from app.infrastructure.db.models.decision_college import (
    DecisionAdmissionRequirementModel,
    DecisionCollegeAccreditationModel,
    DecisionCollegeLevelProfileModel as DecisionCollegeProfileModel,
    DecisionCollegeModel,
    DecisionTrainingAndPracticeModel,
)
from app.infrastructure.db.models.decision_fee import DecisionFeeItemModel
from app.infrastructure.db.models.decision_program import (
    DecisionEmploymentOutlookModel,
    DecisionProgramCareerPathModel,
    DecisionProgramModel,
    DecisionProgramDecisionProfileModel as DecisionProgramProfileModel,
    DecisionProgramTraitModel,
)

logger = logging.getLogger(__name__)


class IngestionIntegrityReport:
    """Pre-flight JSON validation report."""

    def __init__(self) -> None:
        self.total_programs: int = 0
        self.valid_programs: int = 0
        self.invalid_programs: int = 0
        self.programs_missing_tuition: int = 0
        self.validation_errors: list[str] = []

    def summary(self) -> str:
        return (
            f"Pre-flight Report:\n"
            f"  Total Programs Found: {self.total_programs}\n"
            f"  Valid Programs: {self.valid_programs}\n"
            f"  Invalid Programs: {self.invalid_programs}\n"
            f"  Programs Missing Tuition (Will receive Heavy Penalty): {self.programs_missing_tuition}\n"
            f"  Schema Errors Captured: {len(self.validation_errors)}"
        )


class IngestionService:
    """Handles parsing, validating, and ingesting raw JSON exports into the Decision SQL database."""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def pre_flight_check(self, raw_json: dict) -> IngestionIntegrityReport:
        """Scan a raw dictionary against BaseNormalization and return a stats report."""
        report = IngestionIntegrityReport()
        try:
            validated_data = BaseNormalization.model_validate(raw_json)
        except ValidationError as e:
            report.validation_errors.append(f"Root JSON failed schema validation: {e}")
            return report

        if validated_data.official_data and validated_data.official_data.degrees_programs:
            all_programs = (
                validated_data.official_data.degrees_programs.undergraduate
                + validated_data.official_data.degrees_programs.postgraduate
                + validated_data.official_data.degrees_programs.professional_certificates
            )
            report.total_programs = len(all_programs)

            for program in all_programs:
                report.valid_programs += 1
                if not program.tuition:
                    report.programs_missing_tuition += 1

        return report

    def process_and_save(self, raw_json: dict) -> None:
        """Fully ingest a rigorously validated dictionary into SQLAlchemy models."""
        try:
            validated = BaseNormalization.model_validate(raw_json)
        except ValidationError as e:
            logger.error(f"Ingestion Aborted: Invalid JSON shape: {e}")
            raise ValueError(f"Aborting save: Invalid JSON structure: {e}")

        college_id = validated.entity.college_id
        if not college_id:
            logger.error("Ingestion Aborted: Missing college_id.")
            return

        college_model = self.db.query(DecisionCollegeModel).filter_by(id=college_id).first()
        if not college_model:
            college_model = DecisionCollegeModel(id=college_id)
            self.db.add(college_model)

        college_model.college_name = validated.entity.college_name or "Unknown College"

        # Apply nested entity relationships
        self._upsert_college_nested_data(college_model, validated)
        self._upsert_programs(college_model, validated)

        self.db.commit()
        logger.info(f"Successfully ingested data for college '{college_id}'")

    def _upsert_college_nested_data(self, college: DecisionCollegeModel, data: BaseNormalization) -> None:
        off = data.official_data
        ds = data.decision_support

        if off:
            if off.location:
                college.city = off.location.city
                college.country = off.location.country
                college.branch = off.location.branch

            if off.overview:
                college.short_description = off.overview.short_description

            if off.admission_requirements:
                if not college.admission_requirement:
                    college.admission_requirement = DecisionAdmissionRequirementModel()
                # Assuming `accepted_certificates` is stored in a related model, we pass it down
                # For this simple fix we'll skip complex relation mapping for certificates unless needed
                pass

            if off.training_and_practice:
                if not college.training_and_practice:
                    college.training_and_practice = DecisionTrainingAndPracticeModel()
                college.training_and_practice.mandatory_training = off.training_and_practice.mandatory_training
                college.training_and_practice.industry_training = off.training_and_practice.industry_training
                college.training_and_practice.field_or_sea_training = off.training_and_practice.field_or_sea_training

            if off.accreditation:
                if not college.accreditation:
                    college.accreditation = DecisionCollegeAccreditationModel()
                college.accreditation.national_json = off.accreditation.national
                college.accreditation.international_json = off.accreditation.international

        if ds and ds.college_level_profile:
            if not college.level_profile:
                college.level_profile = DecisionCollegeProfileModel()
            prof = ds.college_level_profile
            college.level_profile.theoretical_depth = prof.theoretical_depth
            college.level_profile.math_intensity = prof.math_intensity
            college.level_profile.practical_intensity = prof.practical_intensity
            college.level_profile.field_work_intensity = prof.field_work_intensity
            college.level_profile.research_orientation = prof.research_orientation
            college.level_profile.career_flexibility = prof.career_flexibility

    def _upsert_programs(self, college: DecisionCollegeModel, data: BaseNormalization) -> None:
        if not data.official_data or not data.official_data.degrees_programs:
            return

        all_programs = (
            data.official_data.degrees_programs.undergraduate
            + data.official_data.degrees_programs.postgraduate
            + data.official_data.degrees_programs.professional_certificates
        )

        for p_data in all_programs:
            if not p_data.program_base_id:
                continue

            prog_id = f"{college.id}__{p_data.program_base_id}"
            prog_model = self.db.query(DecisionProgramModel).filter_by(id=prog_id).first()
            if not prog_model:
                prog_model = DecisionProgramModel(id=prog_id, college_id=college.id)
                self.db.add(prog_model)

            prog_model.program_name = p_data.program_name
            prog_model.program_family = p_data.program_family
            prog_model.degree_type = p_data.degree_type
            prog_model.study_duration_years = p_data.study_duration_years

            if p_data.profile:
                if not prog_model.profile:
                    prog_model.profile = DecisionProgramProfileModel()
                prog_model.profile.theoretical_depth = p_data.profile.theoretical_depth
                prog_model.profile.career_flexibility = p_data.profile.career_flexibility

            # Flush standard old traits
            self.db.query(DecisionProgramTraitModel).filter_by(program_id=prog_id).delete()
            for trait in p_data.traits:
                new_trait = DecisionProgramTraitModel(
                    program_id=prog_model.id,
                    trait_name=trait.trait_name,
                    relevance_score=trait.relevance_score,
                )
                self.db.add(new_trait)

            # Insert raw tuition directly against the program logic if needed
            self.db.query(DecisionFeeItemModel).filter_by(target_program_id=prog_id).delete()
            for t_data in p_data.tuition:
                new_fee = DecisionFeeItemModel(
                    target_college_id=college.id,
                    target_program_id=prog_id,
                    student_group=t_data.group,
                    fee_category=t_data.fee_category,
                    track_type=t_data.track,
                    academic_year=t_data.academic_year,
                    estimated_tuition=t_data.estimated_tuition,
                    currency=t_data.currency,
                    fee_mode=t_data.fee_mode,
                )
                self.db.add(new_fee)
