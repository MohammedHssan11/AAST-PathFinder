from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.chat import ChatRequestSchema, ChatResponseSchema
from app.application.services.agent_service import AgentService
from app.application.use_cases.recommend_programs import RecommendProgramsUseCase
from app.application.services.fee_category_resolver import FeeCategoryResolver
from app.application.services.training_intensity_deriver import TrainingIntensityDeriver
from app.application.services.tuition_calculator import TuitionCalculator
from app.infrastructure.db.repositories.decision_college_repo import DecisionCollegeRepository
from app.infrastructure.db.repositories.decision_fee_repo import DecisionFeeRepository
from app.infrastructure.db.repositories.decision_program_repo import DecisionProgramRepository
from app.infrastructure.db.repositories.chat_repo import ChatRepository
from app.infrastructure.db.session import SessionLocal

router = APIRouter(prefix="/chat", tags=["chat"])

def get_agent_service() -> AgentService:
    db = SessionLocal()
    college_repo = DecisionCollegeRepository(db)
    program_repo = DecisionProgramRepository(db)
    fee_repo = DecisionFeeRepository(db)
    chat_repo = ChatRepository(db)

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
    
    return AgentService(recommend_use_case=use_case, chat_repo=chat_repo)

@router.post(
    "/message",
    response_model=ChatResponseSchema,
    summary="Send a message to the AI Consultant Agent",
    description="Processes user input, triggers recommendation logic using function calling, and returns a natural language explanation."
)
def process_chat_message(
    payload: ChatRequestSchema,
    agent_service: AgentService = Depends(get_agent_service)
) -> ChatResponseSchema:
    try:
        reply, recommendations = agent_service.process_message(
            session_id=payload.session_id,
            message=payload.message
        )
        return ChatResponseSchema(
            session_id=payload.session_id,
            reply=reply,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
