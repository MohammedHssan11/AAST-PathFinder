from fastapi import APIRouter, status

from app.api.v1.schemas.student import StudentInputSchema


router = APIRouter(
    prefix="/students",
    tags=["students"],
)


@router.post(
    "/evaluate",
    status_code=status.HTTP_200_OK,
    summary="Validate the student payload schema",
    description=(
        "Utility endpoint for demos and contract checks. It validates the "
        "student payload shape and echoes it back; it is not part of the "
        "decision recommendation runtime."
    ),
)
def validate_student_payload(student: StudentInputSchema):
    """Validate and echo the student schema payload."""
    return {
        "message": "Student endpoint wired correctly",
        "received_student": student.model_dump(),
    }
