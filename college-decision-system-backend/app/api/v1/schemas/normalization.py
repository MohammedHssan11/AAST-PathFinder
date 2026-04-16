from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class NormalizationSourceSchema(BaseModel):
    source_file_name: str | None = None
    input_path: str | None = None
    generated_at: str | datetime | None = None


class NormalizationEntitySchema(BaseModel):
    entity_type: str = Field(default="college")
    college_id: str | None = None
    college_name: str | None = None


class CollegeLocationSchema(BaseModel):
    city: str | None = None
    country: str | None = None
    branch: str | None = None


class CollegeEstablishmentSchema(BaseModel):
    year_established: int | None = None
    parent_institution: str | None = None


class CollegeOverviewSchema(BaseModel):
    short_description: str | None = None
    current_status: str | None = None
    future_prospectus: str | None = None


class CollegeAccreditationSchema(BaseModel):
    national: list[str] = Field(default_factory=list)
    international: list[str] = Field(default_factory=list)


class StandardizedFeeSchema(BaseModel):
    group: str
    fee_category: str | None = None
    track: str = "regular"
    academic_year: str | None = None
    estimated_tuition: float | None = None
    currency: str | None = None
    fee_mode: str | None = None
    additional_recurring_fees: float | None = None
    additional_one_time_fees: float | None = None
    note: str | None = None
    unclassified_frequencies_total: float | None = None
    detailed_line_items: list[dict] = Field(default_factory=list)


class CollegeAdmissionSchema(BaseModel):
    accepted_certificates: list[str] = Field(default_factory=list)
    entry_exams_required: bool | None = None
    medical_fitness_required: bool | None = None
    age_limit: int | None = None
    other_conditions: list[str] = Field(default_factory=list)


class DecisionCollegeProfileSchema(BaseModel):
    theoretical_depth: float | None = None
    math_intensity: float | None = None
    practical_intensity: float | None = None
    field_work_intensity: float | None = None
    research_orientation: float | None = None
    career_flexibility: float | None = None
    egypt_employability: dict[str, float | str | None] | None = None
    international_employability: dict[str, float | str | None] | None = None
    international_mobility_strength: dict[str, float | str | None] | None = None


class DecisionProgramProfileSchema(BaseModel):
    theoretical_depth: float | None = None
    math_intensity: float | None = None
    practical_intensity: float | None = None
    field_work_intensity: float | None = None
    research_orientation: float | None = None
    career_flexibility: float | None = None


class DecisionProgramCareerPathSchema(BaseModel):
    role_name: str
    growth_potential: float | None = None


class DecisionProgramTraitSchema(BaseModel):
    trait_name: str
    relevance_score: float | None = None


class DecisionEmploymentOutlookSchema(BaseModel):
    egypt_employability_score: float | None = None
    international_employability_score: float | None = None
    international_mobility_strength: float | None = None
    primary_hiring_sectors: list[str] = Field(default_factory=list)


class StandardizedProgramSchema(BaseModel):
    program_base_id: str | None = None
    program_name: str
    program_family: str | None = None
    degree_type: str | None = None
    study_duration_years: float | None = None
    is_stem: bool | None = None
    tuition: list[StandardizedFeeSchema] = Field(default_factory=list)
    profile: DecisionProgramProfileSchema | None = None
    career_paths: list[DecisionProgramCareerPathSchema] = Field(default_factory=list)
    traits: list[DecisionProgramTraitSchema] = Field(default_factory=list)
    employment_outlook: DecisionEmploymentOutlookSchema | None = None
    searchable_terms: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    tags: list[str] | None = Field(default_factory=list)


class CollegeDegreesProgramsSchema(BaseModel):
    undergraduate: list[StandardizedProgramSchema] = Field(default_factory=list)
    postgraduate: list[StandardizedProgramSchema] = Field(default_factory=list)
    professional_certificates: list[StandardizedProgramSchema] = Field(default_factory=list)


class CollegeStudentRegulationsSchema(BaseModel):
    add_course_deadline_week: int | None = None
    withdraw_deadline_week: int | None = None
    max_absence_percent: float | None = None
    postponement_policy: str | None = None
    readmission_policy: str | None = None
    special_conditions: list[str] = Field(default_factory=list)


class CollegeTrainingPracticeSchema(BaseModel):
    mandatory_training: bool | None = None
    industry_training: bool | None = None
    field_or_sea_training: bool | None = None
    description: str | None = None


class OfficialDataSchema(BaseModel):
    location: CollegeLocationSchema | None = None
    establishment: CollegeEstablishmentSchema | None = None
    overview: CollegeOverviewSchema | None = None
    degrees_programs: CollegeDegreesProgramsSchema | None = None
    accreditation: CollegeAccreditationSchema | None = None
    admission_requirements: CollegeAdmissionSchema | None = None
    student_regulations: CollegeStudentRegulationsSchema | None = None
    training_and_practice: CollegeTrainingPracticeSchema | None = None
    international_mobility: dict | None = None
    research_and_innovation: dict | None = None
    facilities_and_resources: list | None = Field(default_factory=list)
    industry_and_external_relations: list | None = Field(default_factory=list)
    vision_mission: dict | None = None
    leadership: list | None = Field(default_factory=list)
    tuition_fees: list[StandardizedFeeSchema] = Field(default_factory=list)


class DecisionSupportSchema(BaseModel):
    heuristic_basis_note: str | None = None
    college_level_profile: DecisionCollegeProfileSchema | None = None


class QualityCheckSchema(BaseModel):
    duplicate_content_removed: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    uncertain_items: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BaseNormalization(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: str | None = None
    source: NormalizationSourceSchema | None = None
    entity: NormalizationEntitySchema
    official_data: OfficialDataSchema
    decision_support: DecisionSupportSchema | None = None
    text_artifacts: dict | None = None
    traceability: dict | None = None
    quality_check: QualityCheckSchema | None = None
