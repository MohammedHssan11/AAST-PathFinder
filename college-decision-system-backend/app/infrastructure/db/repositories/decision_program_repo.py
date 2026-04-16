from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.infrastructure.db.models.decision_college import (
    DecisionAdmissionRequirementModel,
    DecisionCollegeModel,
)
from app.infrastructure.db.models.decision_program import (
    DecisionEmploymentOutlookModel,
    DecisionProgramModel,
    DecisionProgramTraitModel,
)


class DecisionProgramRepository:
    """Repository for normalized decision programs and their runtime joins."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, program_id: str) -> DecisionProgramModel | None:
        return (
            self.db.query(DecisionProgramModel)
            .filter(DecisionProgramModel.id == program_id)
            .first()
        )

    def list_all(self) -> list[DecisionProgramModel]:
        return (
            self.db.query(DecisionProgramModel)
            .order_by(DecisionProgramModel.program_name, DecisionProgramModel.id)
            .all()
        )

    def list_by_college(self, college_id: str) -> list[DecisionProgramModel]:
        return (
            self.db.query(DecisionProgramModel)
            .filter(DecisionProgramModel.college_id == college_id)
            .order_by(DecisionProgramModel.program_name, DecisionProgramModel.id)
            .all()
        )

    def list_with_profiles(self) -> list[DecisionProgramModel]:
        return (
            self._runtime_query()
            .order_by(DecisionProgramModel.program_name, DecisionProgramModel.id)
            .all()
        )

    def search_candidates(
        self,
        *,
        query_text: str | None = None,
        college_id: str | None = None,
        city: str | None = None,
        branch: str | None = None,
        interest_terms: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> list[DecisionProgramModel]:
        query = self._runtime_query()

        should_join_college = any(
            value
            for value in (
                query_text,
                college_id,
                city,
                branch,
                interest_terms,
            )
        )
        if should_join_college:
            query = query.join(DecisionProgramModel.college)

        if college_id:
            query = query.filter(DecisionProgramModel.college_id == college_id)

        if city:
            city_pattern = f"%{city.strip().lower()}%"
            query = query.filter(func.lower(DecisionCollegeModel.city).like(city_pattern))

        if branch:
            branch_pattern = f"%{branch.strip().lower()}%"
            query = query.filter(func.lower(DecisionCollegeModel.branch).like(branch_pattern))

        terms = [
            term.strip().lower()
            for term in [query_text, *(interest_terms or [])]
            if isinstance(term, str) and term.strip()
        ]
        if terms:
            clauses = []
            for term in terms:
                pattern = f"%{term}%"
                clauses.extend(
                    [
                        func.lower(DecisionProgramModel.program_name).like(pattern),
                        func.lower(DecisionProgramModel.program_family).like(pattern),
                        func.lower(DecisionProgramModel.summary).like(pattern),
                        func.lower(DecisionProgramModel.differentiation_notes).like(pattern),
                        func.lower(DecisionCollegeModel.college_name).like(pattern),
                    ]
                )
            query = query.filter(or_(*clauses))

        query = query.distinct().order_by(DecisionProgramModel.program_name, DecisionProgramModel.id)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_program_with_profile(self, program_id: str) -> DecisionProgramModel | None:
        return (
            self._runtime_query()
            .filter(DecisionProgramModel.id == program_id)
            .first()
        )

    def get_program_traits(self, program_id: str) -> list[DecisionProgramTraitModel]:
        return (
            self.db.query(DecisionProgramTraitModel)
            .filter(DecisionProgramTraitModel.program_id == program_id)
            .order_by(DecisionProgramTraitModel.sort_order, DecisionProgramTraitModel.id)
            .all()
        )

    def get_program_employment_outlook(self, program_id: str) -> DecisionEmploymentOutlookModel | None:
        return (
            self.db.query(DecisionEmploymentOutlookModel)
            .filter(DecisionEmploymentOutlookModel.program_id == program_id)
            .first()
        )

    def _runtime_query(self):
        return self.db.query(DecisionProgramModel).options(
            joinedload(DecisionProgramModel.decision_profile),
            selectinload(DecisionProgramModel.career_paths),
            selectinload(DecisionProgramModel.traits),
            joinedload(DecisionProgramModel.employment_outlook),
            joinedload(DecisionProgramModel.college).joinedload(
                DecisionCollegeModel.training_and_practice
            ),
            joinedload(DecisionProgramModel.college).joinedload(
                DecisionCollegeModel.level_profile
            ),
            joinedload(DecisionProgramModel.college)
            .joinedload(DecisionCollegeModel.admission_requirement)
            .selectinload(DecisionAdmissionRequirementModel.accepted_certificates),
        )
