from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.models.decision_program import DecisionProgramModel
from pydantic import BaseModel
from decimal import Decimal

router = APIRouter(prefix="/admin", tags=["admin"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ProgramUpdateRequest(BaseModel):
    min_percentage: Decimal | None = None
    program_fees: Decimal | None = None
    allowed_tracks: str | None = None

@router.get("/programs")
def get_programs(db: Session = Depends(get_db)):
    programs = db.query(DecisionProgramModel).all()
    return [{
        "id": p.id,
        "program_name": p.program_name,
        "college_id": p.college_id,
        "min_percentage": float(p.min_percentage) if p.min_percentage is not None else None,
        "program_fees": float(p.program_fees) if p.program_fees is not None else None,
        "allowed_tracks": p.allowed_tracks
    } for p in programs]

@router.put("/programs/{program_id}")
def update_program(program_id: str, request: ProgramUpdateRequest, db: Session = Depends(get_db)):
    program = db.query(DecisionProgramModel).filter(DecisionProgramModel.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
        
    program.min_percentage = request.min_percentage
    program.program_fees = request.program_fees
    program.allowed_tracks = request.allowed_tracks
    db.commit()
    db.refresh(program)
    return {"status": "success"}
