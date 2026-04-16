import os
import aiofiles
from decimal import Decimal
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends

from app.api.v1.schemas.decision import RecommendProgramsResponseSchema, ProgramRecommendationSchema
from pydantic import BaseModel

class VoiceResponseSchema(BaseModel):
    reply: str
    recommendations: list[ProgramRecommendationSchema] = []
    transcribed_text: str | None = None

from app.application.services.speech_service import SpeechService
from app.application.use_cases.recommend_programs import (
    RecommendProgramsRequest,
    RecommendProgramsUseCase,
)
from app.infrastructure.db.repositories.decision_college_repo import DecisionCollegeRepository
from app.infrastructure.db.repositories.decision_program_repo import DecisionProgramRepository
from app.infrastructure.db.repositories.decision_fee_repo import DecisionFeeRepository
from app.application.services.fee_category_resolver import FeeCategoryResolver
from app.application.services.tuition_calculator import TuitionCalculator
from app.application.services.training_intensity_deriver import TrainingIntensityDeriver
from app.infrastructure.db.session import SessionLocal

router = APIRouter(tags=["voice"])

speech_service_instance = SpeechService()

def get_recommend_use_case():
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
        yield use_case
    finally:
        db.close()


@router.post(
    "/voice-entry",
    response_model=VoiceResponseSchema,
    summary="Voice-to-Decision Endpoint",
    description="Accepts an audio file, transcribes it, extracts student data, and returns college recommendations.",
)
async def voice_to_decision(
    file: UploadFile = File(...),
    use_case: RecommendProgramsUseCase = Depends(get_recommend_use_case),
):
    if not file.filename.endswith((".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm")):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    temp_file_path = f"temp_{file.filename}"
    try:
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # 1. Transcribe
        transcribed_text = speech_service_instance.transcribe_audio(temp_file_path)
        if not transcribed_text:
             raise HTTPException(status_code=400, detail="Audio was unclear or empty. Please try again.")

        # 2. Extract Data
        try:
            profile = speech_service_instance.extract_profile(transcribed_text)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check Intent early return
        if profile.intent in ["greeting", "irrelevant"]:
            reply_txt = profile.reply_message or (
                "أهلاً بك! أنا مساعد الأكاديمية الذكي، قولي حابب تدرس إيه أو مجموعك كام عشان أساعدك؟" 
                if profile.intent == "greeting" else "عفواً، لم أفهم طلبك. هل تود الاستفسار عن الكليات المتاحة؟"
            )
            return VoiceResponseSchema(
                reply=reply_txt, 
                recommendations=[],
                transcribed_text=transcribed_text
            )

        # Validate GPA
        hs_percentage = None
        if profile.student_gpa is not None:
             # Assume if GPA <= 4.0 or GPA <= 5.0, we might need to convert scale, or just use it if it's percentage.
             # The system uses high_school_percentage (Decimal)
             # E.g. 3.8 / 4.0 -> 95%
             if profile.student_gpa <= 5.0:
                  hs_percentage = Decimal(str(profile.student_gpa / 4.0 * 100))
             else:
                  hs_percentage = Decimal(str(profile.student_gpa))
        
        # Build Request for Recommendation
        request = RecommendProgramsRequest(
            certificate_type="general", # Defaulting to general, or could be extracted
            high_school_percentage=hs_percentage,
            student_group="science", # Defaulting, could also be extracted if needed
            interests=profile.interested_majors,
            preferred_city=profile.preferred_location,
            # constraints might map to track_type or budget, but keeping simple for now
            max_results=10,
            min_results=3,
        )

        # 3. Recommend
        result = use_case.execute(request)
        
        # We need to serialize it correctly using the same method as in decisions.py
        # Or we can just reuse the router logic, but we must return a RecommendProgramsResponseSchema
        from app.api.v1.routers.decisions import _serialize_decimal, _serialize_fee_lines
        from app.api.v1.schemas.decision import ProgramRecommendationSchema, FeeDetailsSchema, DecisionDataCompletenessSchema
        
        # Map to response schema (similar to decisions.py recommend_programs)
        return VoiceResponseSchema(
            reply="I analyzed your voice input. Here are your recommendations:",
            transcribed_text=transcribed_text,
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
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
