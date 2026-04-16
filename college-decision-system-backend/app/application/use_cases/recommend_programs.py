from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.application.services.decision_numeric_normalizer import DecisionNumericNormalizer
from app.application.services.fee_category_resolver import (
    FeeCategoryResolver,
    ResolvedFeeCategoryResult,
)
from app.application.services.training_intensity_deriver import (
    DerivedTrainingIntensity,
    TrainingIntensityDeriver,
)
from app.application.services.tuition_calculator import (
    FeeLineItem,
    TuitionCalculationResult,
    TuitionCalculator,
)
from app.infrastructure.db.models.decision_college import DecisionCollegeModel
from app.infrastructure.db.models.decision_program import DecisionProgramModel
from app.infrastructure.db.repositories.decision_college_repo import DecisionCollegeRepository
from app.infrastructure.db.repositories.decision_program_repo import DecisionProgramRepository

from app.application.services.interest_expansion_service import InterestExpansionService
from thefuzz import process


@dataclass(frozen=True)
class RecommendProgramsRequest:
    certificate_type: str | None
    high_school_percentage: Decimal | None
    student_group: str | None
    budget: Decimal | None = None
    preferred_branch: str | None = None
    preferred_city: str | None = None
    interests: list[str] = field(default_factory=list)
    track_type: str = "regular"
    max_results: int = 10
    min_results: int = 3


@dataclass(frozen=True)
class ProgramFeeDetails:
    fee_category: str | None
    fee_category_confidence: str
    fee_resolution_reason: str | None
    fee_match_level: str
    fee_match_source: str | None
    fee_match_confidence: str
    estimated_semester_fee: Decimal | None
    recurring_total: Decimal | None
    additional_recurring_fees_total: Decimal | None
    additional_recurring_fees_breakdown: list[FeeLineItem]
    additional_one_time_fees_total: Decimal | None
    additional_one_time_fees_breakdown: list[FeeLineItem]
    unknown_frequency_fees_total: Decimal | None
    unknown_frequency_fees_breakdown: list[FeeLineItem]
    currency: str | None
    academic_year: str | None
    fee_mode: str | None
    tuition_unavailable: bool
    fee_data_incomplete: bool
    used_college_fallback: bool
    warnings: list[str]


@dataclass(frozen=True)
class ProgramRecommendation:
    program_id: str
    program_name: str
    college_id: str
    college_name: str
    confidence_level: str
    score: float
    recommendation_score: float
    match_type: str
    fee_category: str | None
    fee_category_confidence: str
    fee_resolution_reason: str | None
    matched_fee_category: str | None
    estimated_semester_fee: Decimal | None
    additional_recurring_fees: Decimal | None
    additional_one_time_fees: Decimal | None
    additional_one_time_fees_total: Decimal | None
    additional_one_time_fees_breakdown: list[FeeLineItem]
    one_time_fees: Decimal | None
    currency: str | None
    academic_year: str | None
    fee_mode: str | None
    fee_match_level: str
    fee_match_source: str | None
    fee_match_confidence: str
    tuition_unavailable: bool
    fee_data_incomplete: bool
    used_college_fallback: bool
    warnings: list[str]
    affordability_label: str
    training_intensity: str
    derived_training_intensity_label: str
    score_breakdown: dict[str, float | str]
    explanation_summary: str
    matched_interests: list[str]
    fee_resolution_note: str | None
    fee_details: ProgramFeeDetails
    decision_data_completeness: "DecisionDataCompleteness"
    location_note: str | None


@dataclass(frozen=True)
class ExcludedProgram:
    program_id: str
    program_name: str
    college_id: str
    college_name: str
    reason: str


@dataclass(frozen=True)
class RecommendProgramsResult:
    total_candidates_considered: int
    recommendations: list[ProgramRecommendation]
    excluded_programs: list[ExcludedProgram] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionDataCompleteness:
    has_profile: bool
    has_training_data: bool
    has_employment_data: bool
    has_admission_data: bool
    completeness_score: float
    missing_fields: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class ScoredDecisionComponent:
    score: float
    source: str
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InterestAlignmentResult:
    matched_interests: list[str]
    score: float
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RecommendProgramsUseCase:
    """Rank real normalized programs for a student-style request."""

    def __init__(
        self,
        *,
        college_repository: DecisionCollegeRepository,
        program_repository: DecisionProgramRepository,
        fee_category_resolver: FeeCategoryResolver,
        tuition_calculator: TuitionCalculator,
        training_intensity_deriver: TrainingIntensityDeriver,
        interest_expansion_service: InterestExpansionService | None = None,
    ) -> None:
        self.college_repository = college_repository
        self.program_repository = program_repository
        self.fee_category_resolver = fee_category_resolver
        self.tuition_calculator = tuition_calculator
        self.training_intensity_deriver = training_intensity_deriver
        self.interest_expansion_service = interest_expansion_service or InterestExpansionService()
        self.numeric_normalizer = DecisionNumericNormalizer()

    def execute(self, request: RecommendProgramsRequest) -> RecommendProgramsResult:
        candidate_limit = max(200, request.max_results * 20)
        # Initial strict search
        candidates = self.program_repository.search_candidates(
            city=request.preferred_city,
            branch=request.preferred_branch,
            limit=candidate_limit,
        )
        
        # Constraint Relaxation
        relaxed_location = False
        if len(candidates) < request.min_results and (request.preferred_city or request.preferred_branch):
            relaxed_location = True
            # Fetch again without strict geographical constraints
            candidates = self.program_repository.search_candidates(
                city=None,
                branch=None,
                limit=candidate_limit,
            )

        fee_resolution_cache: dict[str, ResolvedFeeCategoryResult] = {}
        recommendations: list[ProgramRecommendation] = []
        excluded_programs_list: list[ExcludedProgram] = []

        for program in candidates:
            college = self._resolve_college(program)
            if college is None:
                continue

            # --- Hard Gatekeeper Filter ---
            excluded = False
            exclusion_reason = ""
            
            if program.min_percentage is not None and request.high_school_percentage is not None:
                if request.high_school_percentage < program.min_percentage:
                    excluded = True
                    exclusion_reason = f"Requires a minimum high school percentage of {program.min_percentage}%"
            
            if not excluded and program.allowed_tracks and request.track_type:
                try:
                    # e.g. program.allowed_tracks = "['science', 'math']"
                    tracks_list = json.loads(program.allowed_tracks)
                    if not isinstance(tracks_list, list):
                        tracks_list = [str(tracks_list)]
                except Exception:
                    tracks_list = [program.allowed_tracks]
                
                # Check for match
                match = process.extractOne(request.track_type, tracks_list)
                if match is None or match[1] < 80: # 80 is a reasonable fuzzy threshold
                    excluded = True
                    exclusion_reason = f"Track '{request.track_type}' not strictly allowed. Requires one of: {', '.join(tracks_list)}"
                    
            if excluded:
                excluded_programs_list.append(ExcludedProgram(
                    program_id=program.id,
                    program_name=program.program_name,
                    college_id=college.id,
                    college_name=college.college_name,
                    reason=exclusion_reason
                ))
                continue
            # --- End Gatekeeper Filter ---

            fee_resolution = fee_resolution_cache.get(college.id)
            if fee_resolution is None:
                fee_resolution = self.fee_category_resolver.resolve(
                    target_college_id=college.id,
                    certificate_type=request.certificate_type,
                    high_school_percentage=request.high_school_percentage,
                    student_group=request.student_group,
                )
                fee_resolution_cache[college.id] = fee_resolution

            tuition = self.tuition_calculator.calculate_for_program(
                program_id=program.id,
                fee_resolution=fee_resolution,
                student_group=request.student_group,
                track_type=request.track_type,
            )
            fee_details = self._build_fee_details(
                fee_resolution=fee_resolution,
                tuition=tuition,
            )
            training = self.training_intensity_deriver.derive(program)

            interest_result = self._score_interest_alignment(
                program=program,
                interests=request.interests,
            )
            location_score, location_note = self._score_location_preference(
                college=college,
                preferred_city=request.preferred_city,
                preferred_branch=request.preferred_branch,
            )
            affordability_label, affordability_score = self._score_affordability(
                budget=request.budget,
                estimated_semester_fee=tuition.estimated_semester_fee,
            )
            employment_result = self._score_employment_outlook(program)
            flexibility_result = self._score_career_flexibility(program)
            admission_result = self._score_certificate_compatibility(
                college=college,
                certificate_type=request.certificate_type,
            )
            completeness = self._build_decision_data_completeness(
                program=program,
                request=request,
                interest_result=interest_result,
                training=training,
                employment_result=employment_result,
                admission_result=admission_result,
            )
            # Fetch the final derived penalty and the confidence label via weighted methodology
            missing_data_penalty, confidence_level = self._compute_missing_data_penalty(
                program=program,
                completeness=completeness,
                fee_details=fee_details,
            )

            # 1. Hard Minimum for Interest alignment (Discard if < 50%)
            if interest_result.score < 0.5:
                continue

            # 2. Track-based compatibility restriction
            # (Science track students from Egyptian Thanaweya Amma cannot join Engineering)
            if not self._is_track_compatible(program, college, request.certificate_type):
                continue

            weighted_score = (
                interest_result.score * 0.60
                + affordability_score * 0.20
                + employment_result.score * 0.10
                + location_score * 0.05
                + flexibility_result.score * 0.025
                + admission_result.score * 0.025
            )
            final_score = max(0.0, weighted_score - missing_data_penalty)
            score_value = round(final_score * 100, 2)
            decision_warnings = self._merge_messages(
                interest_result.warnings,
                training.warnings,
                employment_result.warnings,
                flexibility_result.warnings,
                admission_result.warnings,
                completeness.warnings,
            )
            score_breakdown = self._build_score_breakdown(
                interest_score=interest_result.score,
                affordability_score=affordability_score,
                employment_score=employment_result.score,
                location_score=location_score,
                flexibility_score=flexibility_result.score,
                admission_score=admission_result.score,
                training=training,
                completeness=completeness,
                missing_data_penalty=missing_data_penalty,
                final_score=final_score,
                fee_match_level=tuition.fee_match_level,
            )

            # Assign dynamic match_type based on explicit boundaries and leniency
            is_affordable = affordability_label in ("affordable", "unknown")
            is_stretch = affordability_label == "stretch"
            
            # Did they fall outside location?
            missed_location = False
            if relaxed_location and (request.preferred_city or request.preferred_branch):
                if request.preferred_city and college.city and self._normalize_text(request.preferred_city) != self._normalize_text(college.city):
                    missed_location = True
                if request.preferred_branch and college.branch and self._normalize_text(request.preferred_branch) != self._normalize_text(college.branch):
                    missed_location = True

            match_type = "Exact"
            if not is_affordable and not is_stretch:
                match_type = "Alternative"
            elif missed_location:
                match_type = "Partial"
            elif is_stretch:
                match_type = "Stretch"

            recommendations.append(
                ProgramRecommendation(
                    program_id=program.id,
                    program_name=program.program_name,
                    college_id=college.id,
                    college_name=college.college_name,
                    confidence_level=confidence_level,
                    score=score_value,
                    recommendation_score=score_value,
                    match_type=match_type,
                    fee_category=fee_resolution.matched_fee_category,
                    fee_category_confidence=fee_resolution.fee_category_confidence,
                    fee_resolution_reason=fee_resolution.resolution_reason,
                    matched_fee_category=fee_resolution.matched_fee_category,
                    estimated_semester_fee=tuition.estimated_semester_fee,
                    additional_recurring_fees=tuition.additional_recurring_fees,
                    additional_one_time_fees=tuition.one_time_fees,
                    additional_one_time_fees_total=tuition.one_time_fees,
                    additional_one_time_fees_breakdown=list(tuition.one_time_fee_breakdown),
                    one_time_fees=tuition.one_time_fees,
                    currency=tuition.currency,
                    academic_year=tuition.academic_year,
                    fee_mode=tuition.fee_mode,
                    fee_match_level=tuition.fee_match_level,
                    fee_match_source=tuition.fee_match_source,
                    fee_match_confidence=tuition.fee_match_confidence,
                    tuition_unavailable=tuition.tuition_unavailable,
                    fee_data_incomplete=fee_details.fee_data_incomplete,
                    used_college_fallback=tuition.used_college_fallback,
                    warnings=self._merge_messages(fee_details.warnings, decision_warnings),
                    affordability_label=affordability_label,
                    training_intensity=training.training_intensity_label,
                    derived_training_intensity_label=training.training_intensity_label,
                    score_breakdown=score_breakdown,
                    explanation_summary=self._build_explanation_summary(
                        matched_interests=interest_result.matched_interests,
                        affordability_label=affordability_label,
                        employment_score=employment_result.score,
                        training=training,
                        location_note=location_note,
                        completeness=completeness,
                        missing_data_penalty=missing_data_penalty,
                    ),
                    matched_interests=interest_result.matched_interests,
                    fee_resolution_note=self._build_fee_note(fee_resolution, tuition),
                    fee_details=fee_details,
                    decision_data_completeness=completeness,
                    location_note=location_note,
                )
            )

        recommendations.sort(
            key=lambda item: (
                -item.score,
                ["High", "Medium", "Low"].index(item.confidence_level) if item.confidence_level in ("High", "Medium", "Low") else 2,
                float(item.estimated_semester_fee) if item.estimated_semester_fee is not None else float("inf"),
                item.college_name,
                item.program_name,
                item.program_id,
            )
        )
        return RecommendProgramsResult(
            total_candidates_considered=len(candidates),
            recommendations=recommendations[: request.max_results],
            excluded_programs=excluded_programs_list,
        )

    def _resolve_college(self, program: DecisionProgramModel) -> DecisionCollegeModel | None:
        if program.college is not None:
            return program.college
        return self.college_repository.get_with_training_and_admission(program.college_id)

    def _score_interest_alignment(
        self,
        *,
        program: DecisionProgramModel,
        interests: list[str],
    ) -> InterestAlignmentResult:
        cleaned_interests = [interest.strip() for interest in interests if interest and interest.strip()]
        if not cleaned_interests:
            return InterestAlignmentResult(matched_interests=[], score=0.55)

        searchable_text = self._build_interest_searchable_text(program)
        searchable_tokens = set(searchable_text.split())
        matched_interests: list[str] = []
        interest_scores: list[float] = []
        missing_fields: list[str] = []
        warnings: list[str] = []

        for interest in cleaned_interests:
            normalized_interest = self._normalize_text(interest)
            if not normalized_interest:
                continue

            canonical_interest = self.interest_expansion_service.canonicalize(normalized_interest)
            expanded_terms = self.interest_expansion_service.expand(normalized_interest)
            text_match_score = max(
                (
                    self.interest_expansion_service.fuzzy_score_against_text(
                        term=term,
                        searchable_text=searchable_text,
                        searchable_tokens=searchable_tokens,
                    )
                    for term in expanded_terms
                ),
                default=0.0,
            )
            profile_match = self._score_interest_from_profile(
                program=program,
                normalized_interest=normalized_interest,
                canonical_interest=canonical_interest,
            )
            missing_fields.extend(profile_match.missing_fields)
            warnings.extend(profile_match.warnings)
            if text_match_score > 0:
                best_score = round(
                    min(1.0, (text_match_score * 0.7) + (profile_match.score * 0.3)),
                    4,
                )
            else:
                profile_only_cap = self.interest_expansion_service.get_profile_cap(canonical_interest or "")
                best_score = round(min(profile_match.score, profile_only_cap), 4)
            interest_scores.append(best_score)

            if best_score >= 0.65:
                matched_interests.append(interest.strip())

        if not interest_scores:
            return InterestAlignmentResult(matched_interests=[], score=0.55)

        average_score = sum(interest_scores) / len(interest_scores)
        return InterestAlignmentResult(
            matched_interests=matched_interests,
            score=round(0.2 + (0.8 * average_score), 4),
            missing_fields=self._dedupe_list(missing_fields),
            warnings=self._dedupe_list(warnings),
        )

    def _score_location_preference(
        self,
        *,
        college: DecisionCollegeModel,
        preferred_city: str | None,
        preferred_branch: str | None,
    ) -> tuple[float, str | None]:
        scores: list[float] = []
        notes: list[str] = []

        if preferred_city:
            normalized_city = self._normalize_text(preferred_city)
            college_city = self._normalize_text(college.city)
            if normalized_city and college_city and normalized_city == college_city:
                scores.append(1.0)
                notes.append(f"Preferred city matched {college.city}.")
            else:
                scores.append(0.35)

        if preferred_branch:
            normalized_branch = self._normalize_text(preferred_branch)
            college_branch = self._normalize_text(college.branch)
            if normalized_branch and college_branch and normalized_branch == college_branch:
                scores.append(1.0)
                notes.append(f"Preferred branch matched {college.branch}.")
            else:
                scores.append(0.3)

        if not scores:
            return 0.55, None
        return round(sum(scores) / len(scores), 4), " ".join(notes) or None

    def _score_affordability(
        self,
        *,
        budget: Decimal | None,
        estimated_semester_fee: Decimal | None,
    ) -> tuple[str, float]:
        if budget is None or estimated_semester_fee is None:
            return "unknown", 0.55 if budget is None else 0.15

        if estimated_semester_fee <= budget:
            return "affordable", 1.0
        if estimated_semester_fee <= budget * Decimal("1.15"):
            return "stretch", 0.7
        return "not_affordable", 0.2

    def _score_employment_outlook(self, program: DecisionProgramModel) -> ScoredDecisionComponent:
        outlook = program.employment_outlook
        if outlook is None:
            return self._fallback_employment_outlook_from_college(
                program=program,
                missing_fields=["decision_employment_outlooks"],
                warnings=[
                    "Program employment outlook data was missing, so a conservative fallback was used."
                ],
            )

        normalized_scores: list[float] = []
        present_values = 0
        missing_fields: list[str] = []
        warnings: list[str] = []
        for field_name in ("egypt_market_score", "international_market_score"):
            normalized = self.numeric_normalizer.normalize(
                getattr(outlook, field_name, None),
                field_path=f"decision_employment_outlooks.{field_name}",
            )
            warnings.extend(normalized.warnings)
            if normalized.unit_value is None:
                missing_fields.append(f"decision_employment_outlooks.{field_name}")
                normalized_scores.append(0.45)
            else:
                present_values += 1
                normalized_scores.append(normalized.unit_value)

        if present_values == 0:
            return self._fallback_employment_outlook_from_college(
                program=program,
                missing_fields=self._dedupe_list(missing_fields),
                warnings=self._merge_messages(
                    warnings,
                    [
                        "Program employment outlook values were invalid or missing, so a conservative fallback was used."
                    ],
                ),
            )

        if present_values < 2:
            warnings.append(
                "Employment outlook was derived from partial program data and blended with neutral defaults."
            )
        return ScoredDecisionComponent(
            score=round(sum(normalized_scores) / len(normalized_scores), 4),
            source="program_employment_outlook",
            missing_fields=self._dedupe_list(missing_fields),
            warnings=self._dedupe_list(warnings),
        )

    def _score_career_flexibility(self, program: DecisionProgramModel) -> ScoredDecisionComponent:
        profile = program.decision_profile
        if profile is None:
            return self._fallback_career_flexibility_from_college(
                program=program,
                missing_fields=["decision_program_decision_profiles"],
                warnings=[
                    "Program career-flexibility data was missing, so a conservative fallback was used."
                ],
            )

        normalized = self.numeric_normalizer.normalize(
            profile.career_flexibility,
            field_path="decision_program_decision_profiles.career_flexibility",
        )
        if normalized.unit_value is None:
            return self._fallback_career_flexibility_from_college(
                program=program,
                missing_fields=["decision_program_decision_profiles.career_flexibility"],
                warnings=self._merge_messages(
                    normalized.warnings,
                    [
                        "Program career-flexibility value was invalid or missing, so a conservative fallback was used."
                    ],
                ),
            )
        return ScoredDecisionComponent(
            score=round(normalized.unit_value, 4),
            source="program_decision_profile",
            warnings=list(normalized.warnings),
        )

    def _score_certificate_compatibility(
        self,
        *,
        college: DecisionCollegeModel,
        certificate_type: str | None,
    ) -> ScoredDecisionComponent:
        normalized_request = self._normalize_text(certificate_type)
        if not normalized_request:
            return ScoredDecisionComponent(score=0.55, source="student_input_missing")

        admission = college.admission_requirement
        if admission is None:
            return ScoredDecisionComponent(
                score=0.45,
                source="missing_admission_data",
                missing_fields=["decision_admission_requirements"],
                warnings=[
                    "Admission requirement data was missing, so certificate compatibility was scored conservatively."
                ],
            )

        accepted = [
            self._normalize_text(item.certificate_name)
            for item in admission.accepted_certificates
            if item.certificate_name
        ]
        if not accepted:
            return ScoredDecisionComponent(
                score=0.45,
                source="missing_accepted_certificates",
                missing_fields=["decision_accepted_certificates.certificate_name"],
                warnings=[
                    "Accepted certificate data was missing, so certificate compatibility was scored conservatively."
                ],
            )
        if any(
            normalized_request == entry
            or normalized_request in entry
            or entry in normalized_request
            for entry in accepted
        ):
            return ScoredDecisionComponent(score=1.0, source="certificate_match")
        return ScoredDecisionComponent(
            score=0.35,
            source="certificate_mismatch",
            warnings=[
                "Requested certificate type was not found in the college's accepted certificate list."
            ],
        )

    def _build_decision_data_completeness(
        self,
        *,
        program: DecisionProgramModel,
        request: RecommendProgramsRequest,
        interest_result: InterestAlignmentResult,
        training: DerivedTrainingIntensity,
        employment_result: ScoredDecisionComponent,
        admission_result: ScoredDecisionComponent,
    ) -> DecisionDataCompleteness:
        profile_expected_fields = self._profile_fields_relevant_to_request(request.interests)
        profile_missing_fields: list[str] = []
        profile_valid_count = 0
        if program.decision_profile is None:
            profile_missing_fields.extend(["decision_program_decision_profiles", *profile_expected_fields])
        else:
            for field_path in profile_expected_fields:
                field_name = field_path.rsplit(".", 1)[-1]
                normalized = self.numeric_normalizer.normalize(
                    getattr(program.decision_profile, field_name, None),
                    field_path=field_path,
                )
                if normalized.unit_value is None:
                    profile_missing_fields.append(field_path)
                else:
                    profile_valid_count += 1

        profile_ratio = (
            profile_valid_count / len(profile_expected_fields)
            if profile_expected_fields
            else 1.0
        )

        training_row = program.college.training_and_practice if program.college is not None else None
        training_expected_fields = (
            "decision_training_and_practice.mandatory_training",
            "decision_training_and_practice.industry_training",
            "decision_training_and_practice.field_or_sea_training",
        )
        training_valid_count = 0
        training_missing_fields: list[str] = []
        if training_row is None:
            training_missing_fields.extend(["decision_training_and_practice", *training_expected_fields])
        else:
            for field_path in training_expected_fields:
                field_name = field_path.rsplit(".", 1)[-1]
                if getattr(training_row, field_name, None) is None:
                    training_missing_fields.append(field_path)
                else:
                    training_valid_count += 1

        employment_expected_fields = (
            "decision_employment_outlooks.egypt_market_score",
            "decision_employment_outlooks.international_market_score",
        )
        employment_valid_count = 0
        employment_missing_fields: list[str] = []
        if program.employment_outlook is None:
            employment_missing_fields.extend(["decision_employment_outlooks", *employment_expected_fields])
        else:
            for field_path in employment_expected_fields:
                field_name = field_path.rsplit(".", 1)[-1]
                normalized = self.numeric_normalizer.normalize(
                    getattr(program.employment_outlook, field_name, None),
                    field_path=field_path,
                )
                if normalized.unit_value is None:
                    employment_missing_fields.append(field_path)
                else:
                    employment_valid_count += 1

        admission = program.college.admission_requirement if program.college is not None else None
        accepted_certs = (
            [
                item.certificate_name
                for item in admission.accepted_certificates
                if item.certificate_name and item.certificate_name.strip()
            ]
            if admission is not None
            else []
        )
        admission_ratio = 1.0 if admission is not None and accepted_certs else 0.0
        admission_missing_fields = []
        if admission is None:
            admission_missing_fields.append("decision_admission_requirements")
        if not accepted_certs:
            admission_missing_fields.append("decision_accepted_certificates.certificate_name")

        completeness_ratio = (
            (profile_ratio * 0.35)
            + ((training_valid_count / len(training_expected_fields)) * 0.15)
            + ((employment_valid_count / len(employment_expected_fields)) * 0.30)
            + (admission_ratio * 0.20)
        )
        missing_fields = self._merge_messages(
            profile_missing_fields,
            training_missing_fields,
            employment_missing_fields,
            interest_result.missing_fields,
            training.missing_fields,
            employment_result.missing_fields,
            admission_result.missing_fields,
        )
        warnings = self._merge_messages(
            interest_result.warnings,
            training.warnings,
            employment_result.warnings,
            admission_result.warnings,
        )
        if completeness_ratio < 1:
            warnings.append(
                "Recommendation confidence was reduced because decision data was incomplete."
            )

        return DecisionDataCompleteness(
            has_profile=program.decision_profile is not None and profile_valid_count > 0,
            has_training_data=training_row is not None and training_valid_count > 0,
            has_employment_data=program.employment_outlook is not None and employment_valid_count > 0,
            has_admission_data=admission is not None and bool(accepted_certs),
            completeness_score=round(completeness_ratio * 100, 2),
            missing_fields=self._dedupe_list(missing_fields),
            warnings=self._dedupe_list(warnings),
        )

    def _compute_missing_data_penalty(
        self,
        *,
        program: DecisionProgramModel,
        completeness: DecisionDataCompleteness,
        fee_details: ProgramFeeDetails,
    ) -> tuple[float, str]:
        # Weighted penalty points
        penalty = 0.0

        if not completeness.has_profile:
            penalty += 0.05
        if not completeness.has_training_data:
            penalty += 0.10
        if not completeness.has_employment_data:
            penalty += 0.05
        if not completeness.has_admission_data:
            penalty += 0.05
            
        if fee_details.tuition_unavailable:
            penalty += 0.30  # Heavy penalty for hiding/missing tuition fees
        elif fee_details.fee_match_level == "branch_fallback":
            penalty += 0.15
        elif fee_details.fee_match_level == "college_fallback" or fee_details.used_college_fallback:
            penalty += 0.05
        elif fee_details.fee_data_incomplete:
            penalty += 0.10
            
        print(f"  [DEBUG] Missing Data Penalty Base: {penalty}, Unavailable: {fee_details.tuition_unavailable}, Incomplete: {fee_details.fee_data_incomplete}")

        # Age dampener (reduce penalty for programs added in the last 30 days)
        now = datetime.now(timezone.utc)
        program_age_days = (now - program.created_at).days if program.created_at.tzinfo else (now.replace(tzinfo=None) - program.created_at).days
        is_new_program = program_age_days <= 30

        if is_new_program:
            # Forgive a large portion of the penalty for recently added ingestion streams
            penalty *= 0.5 

        # Establish Confidence Level
        # 0.0 -> High (Perfect or close to perfect)
        # 0.01 to 0.15 -> Medium
        # > 0.15 -> Low (High risk due to missing tuition or heavily incomplete data)
        if penalty == 0.0:
            confidence_level = "High"
        elif penalty <= 0.15:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

        return round(min(max(0.0, penalty), 1.0), 4), confidence_level

    def _fallback_employment_outlook_from_college(
        self,
        *,
        program: DecisionProgramModel,
        missing_fields: list[str],
        warnings: list[str],
    ) -> ScoredDecisionComponent:
        level_profile = program.college.level_profile if program.college is not None else None
        if level_profile is None:
            return ScoredDecisionComponent(
                score=0.4,
                source="missing_employment_data",
                missing_fields=self._dedupe_list(missing_fields),
                warnings=self._dedupe_list(warnings),
            )

        normalized_scores: list[float] = []
        for field_name in ("egypt_employability_score", "international_employability_score"):
            normalized = self.numeric_normalizer.normalize(
                getattr(level_profile, field_name, None),
                field_path=f"decision_college_level_profiles.{field_name}",
            )
            warnings.extend(normalized.warnings)
            if normalized.unit_value is not None:
                normalized_scores.append(normalized.unit_value)

        if not normalized_scores:
            return ScoredDecisionComponent(
                score=0.4,
                source="missing_employment_data",
                missing_fields=self._dedupe_list(missing_fields),
                warnings=self._dedupe_list(warnings),
            )

        warnings.append(
            "College-level employability context was used because program-level employment data was incomplete."
        )
        dampened_score = min(sum(normalized_scores) / len(normalized_scores), 0.7)
        return ScoredDecisionComponent(
            score=round(dampened_score, 4),
            source="college_level_profile",
            missing_fields=self._dedupe_list(missing_fields),
            warnings=self._dedupe_list(warnings),
        )

    def _fallback_career_flexibility_from_college(
        self,
        *,
        program: DecisionProgramModel,
        missing_fields: list[str],
        warnings: list[str],
    ) -> ScoredDecisionComponent:
        level_profile = program.college.level_profile if program.college is not None else None
        if level_profile is None:
            return ScoredDecisionComponent(
                score=0.45,
                source="missing_career_flexibility",
                missing_fields=self._dedupe_list(missing_fields),
                warnings=self._dedupe_list(warnings),
            )

        normalized = self.numeric_normalizer.normalize(
            level_profile.career_flexibility,
            field_path="decision_college_level_profiles.career_flexibility",
        )
        warnings.extend(normalized.warnings)
        if normalized.unit_value is None:
            return ScoredDecisionComponent(
                score=0.45,
                source="missing_career_flexibility",
                missing_fields=self._dedupe_list(missing_fields),
                warnings=self._dedupe_list(warnings),
            )

        warnings.append(
            "College-level career-flexibility context was used because program-level data was incomplete."
        )
        return ScoredDecisionComponent(
            score=round(min(normalized.unit_value, 0.7), 4),
            source="college_level_profile",
            missing_fields=self._dedupe_list(missing_fields),
            warnings=self._dedupe_list(warnings),
        )

    def _build_fee_note(
        self,
        fee_resolution: ResolvedFeeCategoryResult,
        tuition: TuitionCalculationResult,
    ) -> str | None:
        notes = [
            note
            for note in (
                fee_resolution.resolution_reason,
                tuition.fee_resolution_note,
                fee_resolution.data_quality_note,
                tuition.data_quality_note,
            )
            if note
        ]
        return " ".join(notes) if notes else None

    def _build_fee_details(
        self,
        *,
        fee_resolution: ResolvedFeeCategoryResult,
        tuition: TuitionCalculationResult,
    ) -> ProgramFeeDetails:
        warnings = list(tuition.warnings)
        if fee_resolution.data_quality_status:
            warnings.append(
                f"Fee-category rule carries data-quality status {fee_resolution.data_quality_status}."
            )
        if fee_resolution.data_quality_note:
            warnings.append(fee_resolution.data_quality_note)

        return ProgramFeeDetails(
            fee_category=fee_resolution.matched_fee_category,
            fee_category_confidence=fee_resolution.fee_category_confidence,
            fee_resolution_reason=fee_resolution.resolution_reason,
            fee_match_level=tuition.fee_match_level,
            fee_match_source=tuition.fee_match_source,
            fee_match_confidence=tuition.fee_match_confidence,
            estimated_semester_fee=tuition.estimated_semester_fee,
            recurring_total=tuition.estimated_semester_fee,
            additional_recurring_fees_total=tuition.additional_recurring_fees,
            additional_recurring_fees_breakdown=list(tuition.recurring_fee_breakdown),
            additional_one_time_fees_total=tuition.one_time_fees,
            additional_one_time_fees_breakdown=list(tuition.one_time_fee_breakdown),
            unknown_frequency_fees_total=tuition.unknown_frequency_fees,
            unknown_frequency_fees_breakdown=list(tuition.unknown_frequency_fee_breakdown),
            currency=tuition.currency,
            academic_year=tuition.academic_year,
            fee_mode=tuition.fee_mode,
            tuition_unavailable=tuition.tuition_unavailable,
            fee_data_incomplete=(
                tuition.fee_data_incomplete or fee_resolution.data_quality_status is not None
            ),
            used_college_fallback=tuition.used_college_fallback,
            warnings=warnings,
        )

    def _build_explanation_summary(
        self,
        *,
        matched_interests: list[str],
        affordability_label: str,
        employment_score: float,
        training: DerivedTrainingIntensity,
        location_note: str | None,
        completeness: DecisionDataCompleteness,
        missing_data_penalty: float,
    ) -> str:
        reasons: list[str] = []
        if matched_interests:
            reasons.append(f"Matched interests: {', '.join(matched_interests[:3])}.")
        if affordability_label == "affordable":
            reasons.append("Estimated semester tuition fits the stated budget.")
        elif affordability_label == "stretch":
            reasons.append("Estimated semester tuition is close to the stated budget.")
        elif affordability_label == "not_affordable":
            reasons.append("Estimated semester tuition is above the stated budget.")

        if employment_score >= 0.7:
            reasons.append("Employment outlook is strong relative to other options.")
        elif employment_score >= 0.5:
            reasons.append("Employment outlook is moderate.")

        if location_note:
            reasons.append(location_note)

        if training.training_intensity_label == "unknown":
            reasons.append("Training intensity is unknown because training metadata is incomplete.")
        else:
            reasons.append(
                f"Derived training intensity is {training.training_intensity_label}."
            )
        if completeness.completeness_score < 100:
            reasons.append(
                f"Decision-data completeness is {completeness.completeness_score:.0f}% and partial data reduced the score by {round(missing_data_penalty * 100, 2):.2f} points."
            )
        return " ".join(reasons[:4])

    def _build_score_breakdown(
        self,
        *,
        interest_score: float,
        affordability_score: float,
        employment_score: float,
        location_score: float,
        flexibility_score: float,
        admission_score: float,
        training: DerivedTrainingIntensity,
        completeness: DecisionDataCompleteness,
        missing_data_penalty: float,
        final_score: float,
        fee_match_level: str,
    ) -> dict[str, float | str]:
        fee_status = "Estimated" if fee_match_level in ("college_fallback", "branch_fallback") else "Verified"
        return {
            "interest_alignment": round(interest_score * 100, 2),
            "interest_alignment_contribution": round(interest_score * 0.32 * 100, 2),
            "affordability": round(affordability_score * 100, 2),
            "affordability_contribution": round(affordability_score * 0.28 * 100, 2),
            "employment_outlook": round(employment_score * 100, 2),
            "employment_outlook_contribution": round(employment_score * 0.20 * 100, 2),
            "location_preference": round(location_score * 100, 2),
            "location_preference_contribution": round(location_score * 0.10 * 100, 2),
            "career_flexibility": round(flexibility_score * 100, 2),
            "career_flexibility_contribution": round(flexibility_score * 0.05 * 100, 2),
            "certificate_compatibility": round(admission_score * 100, 2),
            "certificate_compatibility_contribution": round(admission_score * 0.05 * 100, 2),
            "training_intensity_signal": round(
                (training.training_intensity_score if training.training_intensity_score is not None else 5.0)
                * 10,
                2,
            ),
            "decision_data_completeness": round(completeness.completeness_score, 2),
            "missing_data_penalty": round(missing_data_penalty * 100, 2),
            "total": round(final_score * 100, 2),
            "fee_status": fee_status,
        }

    def _build_searchable_text(self, program: DecisionProgramModel) -> str:
        fields = [
            program.program_name,
            program.program_family,
            program.summary,
            program.differentiation_notes,
            program.college.college_name if program.college is not None else None,
            " ".join(path.career_title for path in program.career_paths),
            " ".join(trait.trait_text for trait in program.traits),
        ]
        return self._normalize_text(" ".join(value for value in fields if value))

    def _build_interest_searchable_text(self, program: DecisionProgramModel) -> str:
        fields = [
            program.program_name,
            program.program_family,
            program.degree_type,
            program.summary,
            program.differentiation_notes,
            program.college.college_name if program.college is not None else None,
            " ".join(path.career_title for path in program.career_paths),
            " ".join(trait.trait_text for trait in program.traits),
        ]
        return self._normalize_text(" ".join(value for value in fields if value))



    def _score_interest_from_profile(
        self,
        *,
        program: DecisionProgramModel,
        normalized_interest: str,
        canonical_interest: str | None = None,
    ) -> ScoredDecisionComponent:
        profile = program.decision_profile
        canonical_interest = (
            canonical_interest
            or self.interest_expansion_service.canonicalize(normalized_interest)
        )
        if canonical_interest is None:
            return ScoredDecisionComponent(score=0.0, source="no_profile_mapping")

        fields = self.interest_expansion_service.get_profile_fields(canonical_interest)
        if profile is None:
            return ScoredDecisionComponent(
                score=0.0,
                source="missing_decision_profile",
                missing_fields=[
                    "decision_program_decision_profiles",
                    *[
                        f"decision_program_decision_profiles.{field_name}"
                        for field_name in fields
                    ],
                ],
                warnings=[
                    f"{canonical_interest.title()} interest scoring lacked program decision-profile data."
                ],
            )

        normalized_scores: list[float] = []
        present_values = 0
        missing_fields: list[str] = []
        warnings: list[str] = []
        for field_name in fields:
            field_path = f"decision_program_decision_profiles.{field_name}"
            normalized = self.numeric_normalizer.normalize(
                getattr(profile, field_name, None),
                field_path=field_path,
            )
            warnings.extend(normalized.warnings)
            if normalized.unit_value is None:
                missing_fields.append(field_path)
                normalized_scores.append(0.45)
            else:
                present_values += 1
                normalized_scores.append(normalized.unit_value)

        if present_values == 0:
            warnings.append(
                f"{canonical_interest.title()} interest scoring had no valid decision-profile signals."
            )
            return ScoredDecisionComponent(
                score=0.0,
                source="missing_interest_profile_values",
                missing_fields=self._dedupe_list(missing_fields),
                warnings=self._dedupe_list(warnings),
            )

        if present_values < len(fields):
            warnings.append(
                f"{canonical_interest.title()} interest scoring used neutral defaults for missing profile dimensions."
            )
        return ScoredDecisionComponent(
            score=round(sum(normalized_scores) / len(normalized_scores), 4),
            source="program_decision_profile",
            missing_fields=self._dedupe_list(missing_fields),
            warnings=self._dedupe_list(warnings),
        )

    def _profile_fields_relevant_to_request(self, interests: list[str]) -> list[str]:
        requested_fields = {
            "decision_program_decision_profiles.career_flexibility",
            "decision_program_decision_profiles.lab_intensity",
            "decision_program_decision_profiles.field_work_intensity",
        }
        for interest in interests:
            normalized_interest = self._normalize_text(interest)
            canonical_interest = self.interest_expansion_service.canonicalize(normalized_interest)
            if canonical_interest is None:
                continue
            requested_fields.update(
                f"decision_program_decision_profiles.{field_name}"
                for field_name in self.interest_expansion_service.get_profile_fields(canonical_interest)
            )
        return sorted(requested_fields)

    def _merge_messages(self, *groups: list[str] | tuple[str, ...]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group:
                if item and item not in seen:
                    seen.add(item)
                    merged.append(item)
        return merged

    def _dedupe_list(self, items: list[str]) -> list[str]:
        return self._merge_messages(items)

    def _is_track_compatible(
        self,
        program: DecisionProgramModel,
        college: DecisionCollegeModel,
        certificate_type: str | None,
    ) -> bool:
        """Enforce strict track-based eligibility rules (e.g., Science vs Math tracks)."""
        if not certificate_type:
            return True

        normalized_cert = self._normalize_text(certificate_type)
        
        # Egyptian tracks
        is_egyptian = any(t in normalized_cert for t in ("thanaweya", "thanaweia", "egyp"))
        is_science = "science" in normalized_cert
        is_math = "math" in normalized_cert or "mathematics" in normalized_cert

        if not is_egyptian:
            return True
            
        college_id_lower = (college.id or "").lower()
        college_name_lower = (college.college_name or "").lower()
        
        # 1. Science Track Logic (علوم)
        if is_science:
            # Block Engineering
            engineering_tokens = ("engineering", "cet_")
            if any(token in college_name_lower or token in college_id_lower for token in engineering_tokens):
                return False
                
        # 2. Math Track Logic (رياضة)
        if is_math:
            # Block Medical (Medicine, Pharmacy, Dentistry)
            medical_tokens = ("pharmacy", "pharm_", "dentistry", "dent_", "medicine", "med_")
            if any(token in college_name_lower or token in college_id_lower for token in medical_tokens):
                return False
                
        return True

    def _normalize_text(self, value: str | None) -> str:
        if value is None:
            return ""
        normalized = unicodedata.normalize("NFKD", value)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        text = ascii_text.lower()
        text = text.replace("&", " and ")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()
