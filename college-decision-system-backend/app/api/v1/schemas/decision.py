from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


RECOMMEND_PROGRAMS_REQUEST_EXAMPLE = {
    "certificate_type": "Egyptian Thanaweya Amma (Science)",
    "high_school_percentage": 85,
    "student_group": "other_states",
    "budget": 5000,
    "preferred_branch": "Abukir",
    "preferred_city": "Alexandria",
    "interests": ["AI", "software"],
    "track_type": "regular",
    "max_results": 5,
    "min_results": 3,
}


PROGRAM_RECOMMENDATION_EXAMPLE = {
    "program_id": "CCIT_ABUKIR__ARTIFICIAL_INTELLIGENCE",
    "program_name": "Artificial Intelligence",
    "college_id": "CCIT_ABUKIR",
    "college_name": "College of Computing and Information Technology",
    "confidence_level": "Medium",
    "score": 77.12,
    "recommendation_score": 77.12,
    "fee_category": "egyptian_secondary_or_nile_or_stem_or_azhar",
    "fee_category_confidence": "resolved",
    "fee_resolution_reason": (
        "Normalized certificate type 'Egyptian Thanaweya Amma (Science)' to "
        "'egyptian_secondary_or_nile_or_stem_or_azhar'. Rule matched the provided "
        "certificate type, score, and student group."
    ),
    "matched_fee_category": "egyptian_secondary_or_nile_or_stem_or_azhar",
    "estimated_semester_fee": 5165.0,
    "additional_recurring_fees": 0.0,
    "additional_one_time_fees": 0.0,
    "additional_one_time_fees_total": 0.0,
    "additional_one_time_fees_breakdown": [],
    "one_time_fees": 0.0,
    "currency": "USD",
    "academic_year": "2024/2025",
    "fee_mode": "semester",
    "fee_match_level": "program",
    "fee_match_source": "program_inferred",
    "fee_match_confidence": "high",
    "tuition_unavailable": False,
    "fee_data_incomplete": False,
    "used_college_fallback": False,
    "warnings": [
        "Training intensity was derived from partial data and blended with neutral defaults.",
        "Requested certificate type was not found in the college's accepted certificate list.",
        "Recommendation confidence was reduced because decision data was incomplete.",
    ],
    "affordability_label": "stretch",
    "training_intensity": "high",
    "derived_training_intensity_label": "high",
    "score_breakdown": {
        "interest_alignment": 96.64,
        "interest_alignment_contribution": 30.92,
        "affordability": 70.0,
        "affordability_contribution": 19.6,
        "employment_outlook": 80.0,
        "employment_outlook_contribution": 16.0,
        "location_preference": 55.0,
        "location_preference_contribution": 5.5,
        "career_flexibility": 75.0,
        "career_flexibility_contribution": 3.75,
        "certificate_compatibility": 35.0,
        "certificate_compatibility_contribution": 1.75,
        "training_intensity_signal": 74.4,
        "decision_data_completeness": 95.0,
        "missing_data_penalty": 0.4,
        "total": 77.12,
    },
    "explanation_summary": (
        "Matched interests: AI. Estimated semester tuition is close to the stated "
        "budget. Employment outlook is strong relative to other options. "
        "Derived training intensity is high."
    ),
    "matched_interests": ["AI"],
    "fee_resolution_note": "Used a confident program-level fee mapping inferred from the fee dataset.",
    "fee_details": {
        "fee_category": "egyptian_secondary_or_nile_or_stem_or_azhar",
        "fee_category_confidence": "resolved",
        "fee_resolution_reason": (
            "Normalized certificate type 'Egyptian Thanaweya Amma (Science)' to "
            "'egyptian_secondary_or_nile_or_stem_or_azhar'. Rule matched the provided "
            "certificate type, score, and student group."
        ),
        "fee_match_level": "program",
        "fee_match_source": "program_inferred",
        "fee_match_confidence": "high",
        "estimated_semester_fee": 5165.0,
        "recurring_total": 5165.0,
        "additional_recurring_fees_total": 0.0,
        "additional_recurring_fees_breakdown": [],
        "additional_one_time_fees_total": 0.0,
        "additional_one_time_fees_breakdown": [],
        "unknown_frequency_fees_total": 0.0,
        "unknown_frequency_fees_breakdown": [],
        "currency": "USD",
        "academic_year": "2024/2025",
        "fee_mode": "semester",
        "tuition_unavailable": False,
        "fee_data_incomplete": False,
        "used_college_fallback": False,
        "warnings": [],
    },
    "decision_data_completeness": {
        "has_profile": True,
        "has_training_data": True,
        "has_employment_data": True,
        "has_admission_data": True,
        "completeness_score": 95.0,
        "missing_fields": ["decision_training_and_practice.field_or_sea_training"],
        "warnings": [
            "Training intensity was derived from partial data and blended with neutral defaults.",
            "Recommendation confidence was reduced because decision data was incomplete.",
        ],
    },
    "location_note": "Preferred city matched Alexandria.",
}


class RecommendProgramsRequestSchema(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": RECOMMEND_PROGRAMS_REQUEST_EXAMPLE})

    certificate_type: str | None = Field(
        default=None,
        description=(
            "Raw certificate label from the client. Optional overall, but required for "
            "fee-category resolution and stronger admission compatibility signals."
        ),
    )
    high_school_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Student percentage or score on a 0-100 scale. Optional overall, but required "
            "to resolve fee categories from threshold rules."
        ),
    )
    student_group: Literal["supportive_states", "other_states"] | None = Field(
        default=None,
        description="Student fee group used by the tuition and fee-rule subsystem.",
    )
    budget: float | None = Field(
        default=None,
        ge=0,
        description="Optional semester budget in USD-equivalent values used by affordability scoring.",
    )
    preferred_branch: str | None = Field(
        default=None,
        description="Optional preferred branch or campus label used in location preference scoring.",
    )
    preferred_city: str | None = Field(
        default=None,
        description="Optional preferred city used in location preference scoring.",
    )
    interests: List[str] = Field(
        default_factory=list,
        description=(
            "Student interests used to match program names and decision-profile dimensions "
            "such as AI, business, engineering, logistics, or software."
        ),
    )
    track_type: Literal["regular", "international"] = Field(
        default="regular",
        description="Fee track used by the tuition lookup layer.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=500,
        description="Maximum number of recommendations to return",
    )
    min_results: int = Field(
        default=3,
        ge=1,
        le=25,
        description="Minimum results required before dropping location constraints to prevent zero-result UI states.",
    )

class FeeLineItemSchema(BaseModel):
    fee_type: str = Field(description="Fee label or component name.")
    amount: float = Field(description="Fee amount in the response currency.")
    frequency: str | None = Field(
        default=None,
        description="Recurring cadence when available, for example semester or one_time.",
    )
    note: str | None = Field(default=None, description="Optional source note from the fee dataset.")


class FeeDetailsSchema(BaseModel):
    fee_category: str | None = Field(
        default=None,
        description="Resolved fee category selected from the fee-rule subsystem, if available.",
    )
    fee_category_confidence: str = Field(
        description="Confidence label for fee-category resolution, such as resolved or unresolved."
    )
    fee_resolution_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of how the fee category was resolved.",
    )
    fee_match_level: str = Field(
        description="Whether tuition came from a program match, college fallback, or no fee match."
    )
    fee_match_source: str | None = Field(
        default=None,
        description="Source scope used by the fee lookup, for example program_inferred.",
    )
    fee_match_confidence: str = Field(description="Confidence label for the selected tuition row.")
    estimated_semester_fee: float | None = Field(
        default=None,
        description="Estimated recurring semester tuition when a fee row could be resolved.",
    )
    recurring_total: float | None = Field(
        default=None,
        description="Recurring semester total including the matched tuition amount.",
    )
    additional_recurring_fees_total: float | None = Field(
        default=None,
        description="Additional recurring fees outside the main tuition amount.",
    )
    additional_recurring_fees_breakdown: List[FeeLineItemSchema] = Field(
        default_factory=list,
        description="Recurring fee line items included in the total.",
    )
    additional_one_time_fees_total: float | None = Field(
        default=None,
        description="One-time fees linked to the selected fee item.",
    )
    additional_one_time_fees_breakdown: List[FeeLineItemSchema] = Field(
        default_factory=list,
        description="Breakdown of one-time fee components.",
    )
    unknown_frequency_fees_total: float | None = Field(
        default=None,
        description="Fees captured from the dataset when a frequency could not be classified safely.",
    )
    unknown_frequency_fees_breakdown: List[FeeLineItemSchema] = Field(
        default_factory=list,
        description="Breakdown of fees with unknown or ambiguous frequency labels.",
    )
    currency: str | None = Field(default=None, description="Currency label for returned fee amounts.")
    academic_year: str | None = Field(
        default=None,
        description="Academic year attached to the selected fee item, when available.",
    )
    fee_mode: str | None = Field(
        default=None,
        description="Fee cadence label from the fee dataset, such as semester.",
    )
    tuition_unavailable: bool = Field(
        description="True when no safe tuition estimate could be resolved."
    )
    fee_data_incomplete: bool = Field(
        description="True when the fee result relied on incomplete or suspicious fee data."
    )
    used_college_fallback: bool = Field(
        description="True when the system fell back from a program-level fee match to a college-level fee item."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Fee-related warnings surfaced to the client.",
    )


class DecisionDataCompletenessSchema(BaseModel):
    has_profile: bool = Field(
        description="True when the program has usable decision-profile data for runtime scoring."
    )
    has_training_data: bool = Field(
        description="True when the college has usable training and practice metadata."
    )
    has_employment_data: bool = Field(
        description="True when the program has usable employment-outlook data."
    )
    has_admission_data: bool = Field(
        description="True when admission data and accepted certificate values are available."
    )
    completeness_score: float = Field(description="Overall runtime completeness score from 0 to 100.")
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Decision fields or related rows that were missing or unusable at runtime.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Completeness and missing-data warnings surfaced during recommendation scoring.",
    )


class ProgramRecommendationSchema(BaseModel):
    program_id: str = Field(description="Stable program identifier from decision_programs.")
    program_name: str = Field(description="Human-readable program name.")
    college_id: str = Field(description="Stable college identifier from decision_colleges.")
    college_name: str = Field(description="Human-readable college name.")
    confidence_level: str = Field(
        description="Data confidence label reflecting metadata completeness: High, Medium, or Low."
    )
    score: float = Field(description="Final recommendation score on a 0-100 scale.")
    recommendation_score: float = Field(
        description="Backwards-compatible alias for the final recommendation score."
    )
    match_type: str = Field(
        default="Exact",
        description="Match categorization: Exact, Partial, Stretch, or Alternative.",
    )
    fee_category: str | None = Field(
        default=None,
        description="Resolved fee category used for tuition lookup, if available.",
    )
    fee_category_confidence: str = Field(description="Confidence label for fee-category resolution.")
    fee_resolution_reason: str | None = Field(
        default=None,
        description="Human-readable explanation for fee-category resolution.",
    )
    matched_fee_category: str | None = Field(
        default=None,
        description="Fee category ultimately matched by the fee subsystem.",
    )
    estimated_semester_fee: float | None = Field(
        default=None,
        description="Estimated semester tuition for this recommendation, when available.",
    )
    additional_recurring_fees: float | None = Field(
        default=None,
        description="Recurring fees outside the main semester tuition.",
    )
    additional_one_time_fees: float | None = Field(
        default=None,
        description="Backwards-compatible one-time fee total.",
    )
    additional_one_time_fees_total: float | None = Field(
        default=None,
        description="One-time fee total for the selected program or college fallback item.",
    )
    additional_one_time_fees_breakdown: List[FeeLineItemSchema] = Field(
        default_factory=list,
        description="Breakdown of one-time fees.",
    )
    one_time_fees: float | None = Field(
        default=None,
        description="Backwards-compatible alias for the one-time fee total.",
    )
    currency: str | None = Field(default=None, description="Currency for fee amounts.")
    academic_year: str | None = Field(
        default=None,
        description="Academic year attached to the selected fee item.",
    )
    fee_mode: str | None = Field(
        default=None,
        description="Fee cadence label from the tuition data source.",
    )
    fee_match_level: str = Field(
        description="Where the tuition estimate was matched: program, college, or none."
    )
    fee_match_source: str | None = Field(
        default=None,
        description="Specific fee lookup source such as program_direct, program_inferred, or college_fallback.",
    )
    fee_match_confidence: str = Field(description="Confidence label for the selected fee item.")
    tuition_unavailable: bool = Field(
        description="True when no safe tuition estimate was available."
    )
    fee_data_incomplete: bool = Field(
        description="True when fee data quality issues were present."
    )
    used_college_fallback: bool = Field(
        description="True when the recommendation used a college-level fee fallback."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Merged fee, completeness, and scoring warnings for this recommendation.",
    )
    affordability_label: str = Field(
        description="Budget fit label such as affordable, stretch, not_affordable, or unknown."
    )
    training_intensity: str = Field(
        description="Derived runtime training intensity label: low, medium, high, or unknown."
    )
    derived_training_intensity_label: str = Field(
        description="Backwards-compatible alias of training_intensity."
    )
    score_breakdown: dict[str, float | str] = Field(
        default_factory=dict,
        description=(
            "Explainability map showing major factors, weighted contributions, "
            "decision-data completeness, and missing-data penalty."
        ),
    )
    explanation_summary: str = Field(
        description="Short natural-language explanation of why the program ranked as it did."
    )
    matched_interests: List[str] = Field(
        default_factory=list,
        description="Submitted interests that matched the program strongly enough to be surfaced.",
    )
    fee_resolution_note: str | None = Field(
        default=None,
        description="Combined note about fee-category resolution and tuition selection.",
    )
    fee_details: FeeDetailsSchema = Field(
        description="Structured fee subsystem output used to build tuition-related fields."
    )
    decision_data_completeness: DecisionDataCompletenessSchema = Field(
        description="Structured completeness metadata for decision-profile runtime inputs."
    )
    location_note: str | None = Field(
        default=None,
        description="Optional note about city or branch preference matching.",
    )


class RecommendProgramsResponseSchema(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_candidates_considered": 133,
                "recommendations": [PROGRAM_RECOMMENDATION_EXAMPLE],
            }
        }
    )

    total_candidates_considered: int = Field(
        description="Number of candidate programs considered before top-N truncation."
    )
    recommendations: List[ProgramRecommendationSchema] = Field(
        description="Ranked recommendation results in deterministic order."
    )
