from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict


class DecisionContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceInfo(DecisionContractModel):
    file_name: str
    data_source_type: str
    last_updated: str


class CampusInfo(DecisionContractModel):
    campus_id: str
    name: str
    city: str
    country: str


class CollegeInfo(DecisionContractModel):
    college_id: str
    name: str
    parent_institution: str
    branch: str
    overview: str


class AdmissionRules(DecisionContractModel):
    min_score: float | None
    certificate_types: List[str]
    mandatory_subjects: List[str]


class TrainingProfile(DecisionContractModel):
    mandatory_training: bool | None
    industry_training: bool | None
    training_style: str
    industry_alignment: float | None


class CareerOutcomes(DecisionContractModel):
    common_roles: List[str]
    employment_sectors: List[str]
    employability_level: float | None
    international_mobility: float | None


class StudentFitModel(DecisionContractModel):
    best_for: List[str]
    less_suitable_for: List[str]


class DecisionProfile(DecisionContractModel):
    theoretical_intensity: float | None
    practical_intensity: float | None
    technology_dependency: float | None
    project_dependency: float | None
    group_work_dependency: float | None
    research_orientation: float | None

    creative_intensity: float | None
    portfolio_dependency: float | None

    workload_level: float | None
    deadline_pressure: float | None
    evaluation_style: str
    failure_risk: float | None

    training: TrainingProfile
    career_outcomes: CareerOutcomes
    student_fit_model: StudentFitModel


class SystemFlags(DecisionContractModel):
    decision_ready: bool
    data_completeness: str
    supports_cross_college_comparison: bool


class ProgramContract(DecisionContractModel):
    program_id: str
    college_id: str
    name: str
    level: str
    discipline: str
    duration_years: int | None
    teaching_language: str

    admission_rules: AdmissionRules
    decision_profile: DecisionProfile
    system_flags: SystemFlags


class DecisionSchema(DecisionContractModel):
    version: str
    source: SourceInfo
    campus: CampusInfo
    college: CollegeInfo
    programs: List[ProgramContract]
