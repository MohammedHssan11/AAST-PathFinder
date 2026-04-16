from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.db.models.decision_college import (
    DecisionAdmissionRequirementModel,
    DecisionCollegeModel,
)


class DecisionCollegeRepository:
    """Repository for normalized decision colleges and college-level metadata."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, college_id: str) -> DecisionCollegeModel | None:
        return (
            self.db.query(DecisionCollegeModel)
            .filter(DecisionCollegeModel.id == college_id)
            .first()
        )

    def list_all(self) -> list[DecisionCollegeModel]:
        return (
            self.db.query(DecisionCollegeModel)
            .order_by(DecisionCollegeModel.college_name, DecisionCollegeModel.id)
            .all()
        )

    def search_by_name(self, query: str) -> list[DecisionCollegeModel]:
        normalized = (query or "").strip().lower()
        if not normalized:
            return self.list_all()

        pattern = f"%{normalized}%"
        return (
            self.db.query(DecisionCollegeModel)
            .filter(
                or_(
                    func.lower(DecisionCollegeModel.college_name).like(pattern),
                    func.lower(DecisionCollegeModel.branch).like(pattern),
                    func.lower(DecisionCollegeModel.city).like(pattern),
                )
            )
            .order_by(DecisionCollegeModel.college_name, DecisionCollegeModel.id)
            .all()
        )

    def get_with_training_and_admission(self, college_id: str) -> DecisionCollegeModel | None:
        return (
            self.db.query(DecisionCollegeModel)
            .options(
                selectinload(DecisionCollegeModel.training_and_practice),
                selectinload(DecisionCollegeModel.level_profile),
                selectinload(DecisionCollegeModel.admission_requirement).selectinload(
                    DecisionAdmissionRequirementModel.accepted_certificates
                ),
            )
            .filter(DecisionCollegeModel.id == college_id)
            .first()
        )
