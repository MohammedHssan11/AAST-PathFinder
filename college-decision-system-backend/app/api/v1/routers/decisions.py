from decimal import Decimal

from fastapi import APIRouter

from app.api.v1.schemas.decision import (
    DecisionDataCompletenessSchema,
    FeeDetailsSchema,
    FeeLineItemSchema,
    ProgramRecommendationSchema,
    RecommendProgramsRequestSchema,
    RecommendProgramsResponseSchema,
)
from app.application.services.fee_category_resolver import FeeCategoryResolver
from app.application.services.training_intensity_deriver import TrainingIntensityDeriver
from app.application.services.tuition_calculator import TuitionCalculator
from app.application.use_cases.recommend_programs import (
    RecommendProgramsRequest,
    RecommendProgramsUseCase,
)
from app.infrastructure.db.repositories.decision_college_repo import DecisionCollegeRepository
from app.infrastructure.db.repositories.decision_fee_repo import DecisionFeeRepository
from app.infrastructure.db.repositories.decision_program_repo import DecisionProgramRepository
from app.infrastructure.db.session import SessionLocal


router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post(
    "/recommend",
    response_model=RecommendProgramsResponseSchema,
    summary="Recommend programs from the active decision schema",
    description=(
        "Ranks programs using the decision_* dataset, fee resolution rules, "
        "training-intensity derivation, and decision-data completeness safeguards. "
        "The response includes explainable score breakdowns, fee details, "
        "completeness metadata, and warnings when the underlying data is partial."
    ),
    response_description=(
        "Ranked recommendation list with fee details, score breakdowns, "
        "decision-data completeness signals, and warnings."
    ),
)
def recommend_programs(payload: RecommendProgramsRequestSchema):
    """Recommend real programs from the normalized decision_* and decision_fee_* schema."""
    db = SessionLocal()
    try:
        college_repo = DecisionCollegeRepository(db)
        program_repo = DecisionProgramRepository(db)
        fee_repo = DecisionFeeRepository(db)

        use_case = RecommendProgramsUseCase(
            college_repository=college_repo,
            program_repository=program_repo,
            fee_category_resolver=FeeCategoryResolver(
                program_repository=program_repo,
                fee_repository=fee_repo,
            ),
            tuition_calculator=TuitionCalculator(fee_repository=fee_repo),
            training_intensity_deriver=TrainingIntensityDeriver(),
        )

        result = use_case.execute(
            RecommendProgramsRequest(
                certificate_type=payload.certificate_type,
                high_school_percentage=(
                    Decimal(str(payload.high_school_percentage))
                    if payload.high_school_percentage is not None
                    else None
                ),
                student_group=payload.student_group,
                budget=Decimal(str(payload.budget)) if payload.budget is not None else None,
                preferred_branch=payload.preferred_branch,
                preferred_city=payload.preferred_city,
                interests=list(payload.interests),
                track_type=payload.track_type,
                max_results=payload.max_results,
                min_results=payload.min_results,
            )
        )

        return RecommendProgramsResponseSchema(
            total_candidates_considered=result.total_candidates_considered,
            recommendations=[
                ProgramRecommendationSchema(
                    program_id=item.program_id,
                    program_name=item.program_name,
                    college_id=item.college_id,
                    college_name=item.college_name,
                    confidence_level=item.confidence_level,
                    score=item.score,
                    recommendation_score=item.recommendation_score,
                    match_type=item.match_type,
                    fee_category=item.fee_category,
                    fee_category_confidence=item.fee_category_confidence,
                    fee_resolution_reason=item.fee_resolution_reason,
                    matched_fee_category=item.matched_fee_category,
                    estimated_semester_fee=_serialize_decimal(item.estimated_semester_fee),
                    additional_recurring_fees=_serialize_decimal(item.additional_recurring_fees),
                    additional_one_time_fees=_serialize_decimal(item.additional_one_time_fees),
                    additional_one_time_fees_total=_serialize_decimal(item.additional_one_time_fees_total),
                    additional_one_time_fees_breakdown=_serialize_fee_lines(
                        item.additional_one_time_fees_breakdown
                    ),
                    one_time_fees=_serialize_decimal(item.one_time_fees),
                    currency=item.currency,
                    academic_year=item.academic_year,
                    fee_mode=item.fee_mode,
                    fee_match_level=item.fee_match_level,
                    fee_match_source=item.fee_match_source,
                    fee_match_confidence=item.fee_match_confidence,
                    tuition_unavailable=item.tuition_unavailable,
                    fee_data_incomplete=item.fee_data_incomplete,
                    used_college_fallback=item.used_college_fallback,
                    warnings=item.warnings,
                    affordability_label=item.affordability_label,
                    training_intensity=item.training_intensity,
                    derived_training_intensity_label=item.derived_training_intensity_label,
                    score_breakdown=item.score_breakdown,
                    explanation_summary=item.explanation_summary,
                    matched_interests=item.matched_interests,
                    fee_resolution_note=item.fee_resolution_note,
                    fee_details=FeeDetailsSchema(
                        fee_category=item.fee_details.fee_category,
                        fee_category_confidence=item.fee_details.fee_category_confidence,
                        fee_resolution_reason=item.fee_details.fee_resolution_reason,
                        fee_match_level=item.fee_details.fee_match_level,
                        fee_match_source=item.fee_details.fee_match_source,
                        fee_match_confidence=item.fee_details.fee_match_confidence,
                        estimated_semester_fee=_serialize_decimal(
                            item.fee_details.estimated_semester_fee
                        ),
                        recurring_total=_serialize_decimal(item.fee_details.recurring_total),
                        additional_recurring_fees_total=_serialize_decimal(
                            item.fee_details.additional_recurring_fees_total
                        ),
                        additional_recurring_fees_breakdown=_serialize_fee_lines(
                            item.fee_details.additional_recurring_fees_breakdown
                        ),
                        additional_one_time_fees_total=_serialize_decimal(
                            item.fee_details.additional_one_time_fees_total
                        ),
                        additional_one_time_fees_breakdown=_serialize_fee_lines(
                            item.fee_details.additional_one_time_fees_breakdown
                        ),
                        unknown_frequency_fees_total=_serialize_decimal(
                            item.fee_details.unknown_frequency_fees_total
                        ),
                        unknown_frequency_fees_breakdown=_serialize_fee_lines(
                            item.fee_details.unknown_frequency_fees_breakdown
                        ),
                        currency=item.fee_details.currency,
                        academic_year=item.fee_details.academic_year,
                        fee_mode=item.fee_details.fee_mode,
                        tuition_unavailable=item.fee_details.tuition_unavailable,
                        fee_data_incomplete=item.fee_details.fee_data_incomplete,
                        used_college_fallback=item.fee_details.used_college_fallback,
                        warnings=item.fee_details.warnings,
                    ),
                    decision_data_completeness=DecisionDataCompletenessSchema(
                        has_profile=item.decision_data_completeness.has_profile,
                        has_training_data=item.decision_data_completeness.has_training_data,
                        has_employment_data=item.decision_data_completeness.has_employment_data,
                        has_admission_data=item.decision_data_completeness.has_admission_data,
                        completeness_score=item.decision_data_completeness.completeness_score,
                        missing_fields=item.decision_data_completeness.missing_fields,
                        warnings=item.decision_data_completeness.warnings,
                    ),
                    location_note=item.location_note,
                )
                for item in result.recommendations
            ],
        )
    finally:
        db.close()


def _serialize_decimal(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _serialize_fee_lines(lines) -> list[FeeLineItemSchema]:
    return [
        FeeLineItemSchema(
            fee_type=line.fee_type,
            amount=float(line.amount),
            frequency=line.frequency,
            note=line.note,
        )
        for line in lines
    ]
