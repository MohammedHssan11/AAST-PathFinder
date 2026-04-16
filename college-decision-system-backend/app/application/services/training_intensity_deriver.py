from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.application.services.decision_numeric_normalizer import DecisionNumericNormalizer
from app.infrastructure.db.models.decision_program import DecisionProgramModel


@dataclass(frozen=True)
class DerivedTrainingIntensity:
    training_intensity_score: float | None
    training_intensity_label: str
    signal_coverage: float
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class TrainingIntensityDeriver:
    """Derive runtime training intensity from program and college signals."""

    def __init__(self, *, numeric_normalizer: DecisionNumericNormalizer | None = None) -> None:
        self.numeric_normalizer = numeric_normalizer or DecisionNumericNormalizer()

    def derive(self, program: DecisionProgramModel) -> DerivedTrainingIntensity:
        signals: list[Decimal] = []
        missing_fields: list[str] = []
        warnings: list[str] = []
        expected_signal_count = 5

        profile = program.decision_profile
        if profile is not None:
            for field_name in ("lab_intensity", "field_work_intensity"):
                normalized = self.numeric_normalizer.normalize(
                    getattr(profile, field_name, None),
                    field_path=f"decision_program_decision_profiles.{field_name}",
                )
                warnings.extend(normalized.warnings)
                if normalized.ten_point_value is not None:
                    scaled = Decimal(str(normalized.ten_point_value))
                    signals.append(scaled)
                else:
                    missing_fields.append(f"decision_program_decision_profiles.{field_name}")
        else:
            missing_fields.extend(
                [
                    "decision_program_decision_profiles",
                    "decision_program_decision_profiles.lab_intensity",
                    "decision_program_decision_profiles.field_work_intensity",
                ]
            )
            warnings.append(
                "Decision profile data was missing, so training intensity confidence is reduced."
            )

        training = program.college.training_and_practice if program.college is not None else None
        if training is not None:
            for field_name in (
                "mandatory_training",
                "industry_training",
                "field_or_sea_training",
            ):
                flag = getattr(training, field_name, None)
                if flag is not None:
                    signals.append(Decimal("10") if flag else Decimal("0"))
                else:
                    missing_fields.append(f"decision_training_and_practice.{field_name}")
        else:
            missing_fields.extend(
                [
                    "decision_training_and_practice",
                    "decision_training_and_practice.mandatory_training",
                    "decision_training_and_practice.industry_training",
                    "decision_training_and_practice.field_or_sea_training",
                ]
            )
            warnings.append(
                "Training and practice metadata was missing, so training intensity is reported conservatively."
            )

        if not signals:
            return DerivedTrainingIntensity(
                training_intensity_score=None,
                training_intensity_label="unknown",
                signal_coverage=0.0,
                missing_fields=self._dedupe(missing_fields),
                warnings=self._dedupe(warnings),
            )

        signal_coverage = len(signals) / expected_signal_count
        score = (
            sum(signals) + (Decimal("5") * Decimal(expected_signal_count - len(signals)))
        ) / Decimal(expected_signal_count)
        score = max(Decimal("0"), min(score, Decimal("10")))
        label = self._label_for_score(score)
        if len(signals) < expected_signal_count:
            warnings.append(
                "Training intensity was derived from partial data and blended with neutral defaults."
            )

        return DerivedTrainingIntensity(
            training_intensity_score=round(float(score), 2),
            training_intensity_label=label,
            signal_coverage=round(signal_coverage, 4),
            missing_fields=self._dedupe(missing_fields),
            warnings=self._dedupe(warnings),
        )

    def _label_for_score(self, score: Decimal) -> str:
        if score < Decimal("3.5"):
            return "low"
        if score < Decimal("6.5"):
            return "medium"
        return "high"

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
