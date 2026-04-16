from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.session import Base

from .decision_common import DecisionTimestampMixin


class DecisionScholarshipModel(Base, DecisionTimestampMixin):
    __tablename__ = "decision_scholarships"
    __table_args__ = (
        UniqueConstraint("scholarship_id", name="uq_decision_scholarships_scholarship_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scholarship_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    eligibility_entries: Mapped[list["DecisionScholarshipEligibilityModel"]] = relationship(
        "DecisionScholarshipEligibilityModel",
        back_populates="scholarship",
        cascade="all, delete-orphan",
        order_by="DecisionScholarshipEligibilityModel.sort_order",
    )


class DecisionScholarshipEligibilityModel(Base):
    __tablename__ = "decision_scholarship_eligibility"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scholarship_id: Mapped[int] = mapped_column(
        ForeignKey("decision_scholarships.id"),
        nullable=False,
    )
    eligibility_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    scholarship: Mapped["DecisionScholarshipModel"] = relationship(
        "DecisionScholarshipModel",
        back_populates="eligibility_entries",
    )


__all__ = [
    "DecisionScholarshipEligibilityModel",
    "DecisionScholarshipModel",
]
