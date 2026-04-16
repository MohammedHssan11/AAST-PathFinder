from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.infrastructure.db.repositories.decision_fee_repo import DecisionFeeRepository
from app.application.services.fee_category_resolver import ResolvedFeeCategoryResult


@dataclass(frozen=True)
class FeeLineItem:
    fee_type: str
    amount: Decimal
    frequency: str | None
    note: str | None


@dataclass(frozen=True)
class TuitionCalculationResult:
    matched_fee_category: str | None
    estimated_semester_fee: Decimal | None
    additional_recurring_fees: Decimal | None
    one_time_fees: Decimal | None
    unknown_frequency_fees: Decimal | None
    currency: str | None
    academic_year: str | None
    fee_mode: str | None
    fee_match_level: str
    fee_match_source: str | None
    fee_match_confidence: str
    tuition_unavailable: bool
    fee_data_incomplete: bool
    used_college_fallback: bool
    recurring_fee_breakdown: tuple[FeeLineItem, ...]
    one_time_fee_breakdown: tuple[FeeLineItem, ...]
    unknown_frequency_fee_breakdown: tuple[FeeLineItem, ...]
    warnings: tuple[str, ...]
    fee_resolution_note: str | None
    data_quality_status: str | None
    data_quality_note: str | None
    source_scope: str | None


class TuitionCalculator:
    """Quote recurring and one-time tuition components from the fee layer."""

    def __init__(self, *, fee_repository: DecisionFeeRepository) -> None:
        self.fee_repository = fee_repository

    def calculate_for_program(
        self,
        *,
        program_id: str,
        fee_resolution: ResolvedFeeCategoryResult,
        student_group: str | None,
        track_type: str = "regular",
    ) -> TuitionCalculationResult:
        if fee_resolution.matched_fee_category is None:
            if fee_resolution.fallback_level:
                return TuitionCalculationResult(
                    matched_fee_category=None,
                    estimated_semester_fee=fee_resolution.estimated_average_fee,
                    additional_recurring_fees=Decimal("0"),
                    one_time_fees=Decimal("0"),
                    unknown_frequency_fees=Decimal("0"),
                    currency="USD",
                    academic_year=None,
                    fee_mode="per_semester",
                    fee_match_level=fee_resolution.fallback_level,
                    fee_match_source=fee_resolution.fallback_level,
                    fee_match_confidence=fee_resolution.fee_category_confidence,
                    tuition_unavailable=False,
                    fee_data_incomplete=False,
                    used_college_fallback=(fee_resolution.fallback_level == "college_fallback"),
                    recurring_fee_breakdown=(),
                    one_time_fee_breakdown=(),
                    unknown_frequency_fee_breakdown=(),
                    warnings=(f"Estimated fee based on {fee_resolution.fallback_level} average.",),
                    fee_resolution_note=fee_resolution.resolution_note,
                    data_quality_status=None,
                    data_quality_note=None,
                    source_scope=fee_resolution.fallback_level,
                )

            return TuitionCalculationResult(
                matched_fee_category=None,
                estimated_semester_fee=None,
                additional_recurring_fees=None,
                one_time_fees=None,
                unknown_frequency_fees=None,
                currency=None,
                academic_year=None,
                fee_mode=None,
                fee_match_level="none",
                fee_match_source=None,
                fee_match_confidence="unresolved",
                tuition_unavailable=True,
                fee_data_incomplete=False,
                used_college_fallback=False,
                recurring_fee_breakdown=(),
                one_time_fee_breakdown=(),
                unknown_frequency_fee_breakdown=(),
                warnings=("No fee category could be resolved for this request.",),
                fee_resolution_note="No fee category could be resolved for this request.",
                data_quality_status=None,
                data_quality_note=None,
                source_scope=None,
            )
        if not student_group:
            return TuitionCalculationResult(
                matched_fee_category=fee_resolution.matched_fee_category,
                estimated_semester_fee=None,
                additional_recurring_fees=None,
                one_time_fees=None,
                unknown_frequency_fees=None,
                currency=None,
                academic_year=None,
                fee_mode=None,
                fee_match_level="none",
                fee_match_source=None,
                fee_match_confidence="unresolved",
                tuition_unavailable=True,
                fee_data_incomplete=False,
                used_college_fallback=False,
                recurring_fee_breakdown=(),
                one_time_fee_breakdown=(),
                unknown_frequency_fee_breakdown=(),
                warnings=("student_group is required to select a tuition amount row.",),
                fee_resolution_note="student_group is required to select a tuition amount row.",
                data_quality_status=None,
                data_quality_note=None,
                source_scope=None,
            )

        fee_result = self.fee_repository.get_effective_fee_for_program(
            program_id=program_id,
            resolved_fee_category=fee_resolution.matched_fee_category,
            student_group=student_group,
            track_type=track_type,
        )
        if fee_result is None:
            if fee_resolution.college_fallback_fee is not None:
                return TuitionCalculationResult(
                    matched_fee_category=fee_resolution.matched_fee_category,
                    estimated_semester_fee=fee_resolution.college_fallback_fee,
                    additional_recurring_fees=Decimal("0"),
                    one_time_fees=Decimal("0"),
                    unknown_frequency_fees=Decimal("0"),
                    currency="USD",
                    academic_year=None,
                    fee_mode="per_semester",
                    fee_match_level="college_fallback",
                    fee_match_source="college_fallback",
                    fee_match_confidence="medium",
                    tuition_unavailable=False,
                    fee_data_incomplete=False,
                    used_college_fallback=True,
                    recurring_fee_breakdown=(),
                    one_time_fee_breakdown=(),
                    unknown_frequency_fee_breakdown=(),
                    warnings=("Estimated fee based on college average because specific program fee was missing.",),
                    fee_resolution_note="Estimated fee based on college average because specific program fee was missing.",
                    data_quality_status=None,
                    data_quality_note=None,
                    source_scope="college_fallback",
                )
            elif fee_resolution.branch_fallback_fee is not None:
                return TuitionCalculationResult(
                    matched_fee_category=fee_resolution.matched_fee_category,
                    estimated_semester_fee=fee_resolution.branch_fallback_fee,
                    additional_recurring_fees=Decimal("0"),
                    one_time_fees=Decimal("0"),
                    unknown_frequency_fees=Decimal("0"),
                    currency="USD",
                    academic_year=None,
                    fee_mode="per_semester",
                    fee_match_level="branch_fallback",
                    fee_match_source="branch_fallback",
                    fee_match_confidence="low",
                    tuition_unavailable=False,
                    fee_data_incomplete=False,
                    used_college_fallback=False,
                    recurring_fee_breakdown=(),
                    one_time_fee_breakdown=(),
                    unknown_frequency_fee_breakdown=(),
                    warnings=("Estimated fee based on branch average because specific program fee was missing.",),
                    fee_resolution_note="Estimated fee based on branch average because specific program fee was missing.",
                    data_quality_status=None,
                    data_quality_note=None,
                    source_scope="branch_fallback",
                )
                
            return TuitionCalculationResult(
                matched_fee_category=fee_resolution.matched_fee_category,
                estimated_semester_fee=None,
                additional_recurring_fees=None,
                one_time_fees=None,
                unknown_frequency_fees=None,
                currency=None,
                academic_year=None,
                fee_mode=None,
                fee_match_level="none",
                fee_match_source=None,
                fee_match_confidence="unresolved",
                tuition_unavailable=True,
                fee_data_incomplete=False,
                used_college_fallback=False,
                recurring_fee_breakdown=(),
                one_time_fee_breakdown=(),
                unknown_frequency_fee_breakdown=(),
                warnings=(
                    "No confident fee item matched this program, and no conservative college-level fallback was available.",
                ),
                fee_resolution_note=(
                    "No confident fee item matched this program, and no conservative college-level "
                    "fallback was available."
                ),
                data_quality_status=None,
                data_quality_note=None,
                source_scope=None,
            )

        recurring_breakdown = self._build_fee_lines(fee_result.recurring_additional_fee_lines)
        one_time_breakdown = self._build_fee_lines(fee_result.one_time_additional_fee_lines)
        unknown_breakdown = self._build_fee_lines(fee_result.unknown_frequency_fee_lines)
        fee_data_incomplete = bool(
            fee_result.data_quality_status or fee_result.data_quality_note or fee_result.unknown_frequency_additional_fees_usd
        )
        return TuitionCalculationResult(
            matched_fee_category=fee_resolution.matched_fee_category,
            estimated_semester_fee=fee_result.total_recurring_tuition_usd,
            additional_recurring_fees=fee_result.recurring_additional_fees_usd,
            one_time_fees=fee_result.one_time_additional_fees_usd,
            unknown_frequency_fees=fee_result.unknown_frequency_additional_fees_usd,
            currency=fee_result.currency,
            academic_year=fee_result.academic_year,
            fee_mode=fee_result.fee_mode,
            fee_match_level=fee_result.fee_match_level,
            fee_match_source=fee_result.source_scope,
            fee_match_confidence=fee_result.fee_match_confidence,
            tuition_unavailable=False,
            fee_data_incomplete=fee_data_incomplete,
            used_college_fallback=fee_result.fee_match_level == "college",
            recurring_fee_breakdown=recurring_breakdown,
            one_time_fee_breakdown=one_time_breakdown,
            unknown_frequency_fee_breakdown=unknown_breakdown,
            warnings=fee_result.warnings,
            fee_resolution_note=self._build_resolution_note(
                source_scope=fee_result.source_scope,
                selection_reason=fee_result.selection_reason,
            ),
            data_quality_status=fee_result.data_quality_status,
            data_quality_note=fee_result.data_quality_note,
            source_scope=fee_result.source_scope,
        )

    def _build_fee_lines(
        self,
        raw_lines: Iterable[dict[str, str | Decimal | None]],
    ) -> tuple[FeeLineItem, ...]:
        return tuple(
            FeeLineItem(
                fee_type=str(line["fee_type"]),
                amount=Decimal(str(line["amount_usd"])),
                frequency=None if line["frequency"] is None else str(line["frequency"]),
                note=None if line["note"] is None else str(line["note"]),
            )
            for line in raw_lines
        )

    def _build_resolution_note(self, *, source_scope: str, selection_reason: str) -> str:
        if source_scope == "program_direct":
            return f"Used a direct program-level fee mapping. {selection_reason}"
        if source_scope == "program_inferred":
            return f"Used a confident program-level fee mapping inferred from the fee dataset. {selection_reason}"
        return f"Used a conservative college-level fee fallback. {selection_reason}"
