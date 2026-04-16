from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.infrastructure.db.repositories.decision_fee_repo import DecisionFeeRepository
from app.infrastructure.db.repositories.decision_program_repo import DecisionProgramRepository

EGYPTIAN_SECONDARY_CERTIFICATE = "egyptian_secondary_or_nile_or_stem_or_azhar"
EQUIVALENT_CERTIFICATES = "equivalent_certificates"


@dataclass(frozen=True)
class ResolvedFeeCategoryResult:
    matched_fee_category: str | None
    rule_id: str | None
    resolution_note: str | None
    fee_category_confidence: str
    resolution_reason: str | None
    normalized_certificate_type: str | None
    data_quality_status: str | None
    data_quality_note: str | None
    fallback_level: str | None = None
    estimated_average_fee: Decimal | None = None
    college_fallback_fee: Decimal | None = None
    branch_fallback_fee: Decimal | None = None


class FeeCategoryResolver:
    """Resolve the fee category used by runtime recommendation flow."""

    def __init__(
        self,
        *,
        program_repository: DecisionProgramRepository,
        fee_repository: DecisionFeeRepository,
    ) -> None:
        self.program_repository = program_repository
        self.fee_repository = fee_repository

    def resolve(
        self,
        *,
        certificate_type: str | None,
        high_school_percentage: Decimal | None,
        student_group: str | None,
        target_college_id: str | None = None,
        target_program_id: str | None = None,
        branch_scope: str | None = None,
    ) -> ResolvedFeeCategoryResult:
        # Diagnostic prints for calibration debugging
        print(f"\n[DEBUG] FeeCategoryResolver.resolve START")
        print(f"  Input Cert: {certificate_type}")
        print(f"  Input Group: {student_group}")
        print(f"  Input Score: {high_school_percentage}")
        print(f"  College ID: {target_college_id}")
        
        college_id = target_college_id
        if college_id is None and target_program_id is not None:
            program = self.program_repository.get_by_id(target_program_id)
            if program is not None:
                college_id = program.college_id

        if college_id is None:
            return ResolvedFeeCategoryResult(
                matched_fee_category=None,
                rule_id=None,
                resolution_note="No target college could be resolved for fee-category lookup.",
                fee_category_confidence="unresolved",
                resolution_reason="No target college could be resolved for fee-category lookup.",
                normalized_certificate_type=None,
                data_quality_status=None,
                data_quality_note=None,
            )

        normalized_certificate_type = self._normalize_certificate_type(certificate_type)
        print(f"  Normalized Cert: {normalized_certificate_type}")
        
        if not certificate_type:
            return ResolvedFeeCategoryResult(
                matched_fee_category=None,
                rule_id=None,
                resolution_note="Fee category could not be resolved because certificate_type was missing.",
                fee_category_confidence="unresolved",
                resolution_reason="Fee category could not be resolved because certificate_type was missing.",
                normalized_certificate_type=normalized_certificate_type,
                data_quality_status=None,
                data_quality_note=None,
            )
        if high_school_percentage is None:
            return ResolvedFeeCategoryResult(
                matched_fee_category=None,
                rule_id=None,
                resolution_note="Fee category could not be resolved because high_school_percentage was missing.",
                fee_category_confidence="unresolved",
                resolution_reason="Fee category could not be resolved because high_school_percentage was missing.",
                normalized_certificate_type=normalized_certificate_type,
                data_quality_status=None,
                data_quality_note=None,
            )
        if not student_group:
            return ResolvedFeeCategoryResult(
                matched_fee_category=None,
                rule_id=None,
                resolution_note="Fee category could not be resolved because student_group was missing.",
                fee_category_confidence="unresolved",
                resolution_reason="Fee category could not be resolved because student_group was missing.",
                normalized_certificate_type=normalized_certificate_type,
                data_quality_status=None,
                data_quality_note=None,
            )

        resolution = self.fee_repository.resolve_fee_category_for_student(
            target_college_id=college_id,
            certificate_type=normalized_certificate_type,
            high_school_percentage=high_school_percentage,
            student_group=student_group,
            branch_scope=branch_scope,
        )
        print(f"  Resolution Match: {resolution.rule_id if resolution else 'NONE'}")
        if resolution:
             print(f"  Matched Category: {resolution.fee_category}")
             
        local_branch_scope = branch_scope
        if local_branch_scope is None:
            local_branch_scope = "alamein_only" if "alamein" in (college_id or "").lower() else "all_branches_except_alamein"

        college_fallback_fee = self.fee_repository.calculate_fallback_average_fee(
            college_id=college_id,
            branch_scope=local_branch_scope,
            student_group=student_group,
            fallback_scope="college"
        )
        branch_fallback_fee = self.fee_repository.calculate_fallback_average_fee(
            college_id=college_id,
            branch_scope=local_branch_scope,
            student_group=student_group,
            fallback_scope="branch"
        )
        
        if resolution is None:
            failure_reason = (
                "No applicable fee-category rule matched the provided certificate type, score, and student group."
            )
            
            # 1. College Fallback
            if college_fallback_fee is not None:
                return ResolvedFeeCategoryResult(
                    matched_fee_category=None,
                    rule_id=None,
                    resolution_note="Resolved via College Fallback (Average Fee)",
                    fee_category_confidence="medium",
                    resolution_reason=failure_reason + " Used average fee for the college.",
                    normalized_certificate_type=normalized_certificate_type,
                    data_quality_status=None,
                    data_quality_note=None,
                    fallback_level="college_fallback",
                    estimated_average_fee=college_fallback_fee,
                    college_fallback_fee=college_fallback_fee,
                    branch_fallback_fee=branch_fallback_fee,
                )
            
            # 2. Branch Fallback
            if branch_fallback_fee is not None:
                return ResolvedFeeCategoryResult(
                    matched_fee_category=None,
                    rule_id=None,
                    resolution_note="Resolved via Branch Fallback (Average Fee)",
                    fee_category_confidence="low",
                    resolution_reason=failure_reason + " Used global average fee for the branch.",
                    normalized_certificate_type=normalized_certificate_type,
                    data_quality_status=None,
                    data_quality_note=None,
                    fallback_level="branch_fallback",
                    estimated_average_fee=branch_fallback_fee,
                    college_fallback_fee=college_fallback_fee,
                    branch_fallback_fee=branch_fallback_fee,
                )

            return ResolvedFeeCategoryResult(
                matched_fee_category=None,
                rule_id=None,
                resolution_note=failure_reason,
                fee_category_confidence="unresolved",
                resolution_reason=failure_reason,
                normalized_certificate_type=normalized_certificate_type,
                data_quality_status=None,
                data_quality_note=None,
                college_fallback_fee=college_fallback_fee,
                branch_fallback_fee=branch_fallback_fee,
            )

        resolution_reason = self._build_resolution_reason(
            raw_certificate_type=certificate_type,
            normalized_certificate_type=normalized_certificate_type,
            resolution_reason=resolution.resolution_reason,
        )
        return ResolvedFeeCategoryResult(
            matched_fee_category=resolution.fee_category,
            rule_id=resolution.rule_id,
            resolution_note=resolution_reason,
            fee_category_confidence=resolution.confidence,
            resolution_reason=resolution_reason,
            normalized_certificate_type=normalized_certificate_type,
            data_quality_status=resolution.data_quality_status,
            data_quality_note=resolution.data_quality_note,
            college_fallback_fee=college_fallback_fee,
            branch_fallback_fee=branch_fallback_fee,
        )

    def _build_resolution_reason(
        self,
        *,
        raw_certificate_type: str | None,
        normalized_certificate_type: str | None,
        resolution_reason: str,
    ) -> str:
        if not raw_certificate_type or not normalized_certificate_type:
            return resolution_reason
        if self._normalize_lookup_text(raw_certificate_type) == normalized_certificate_type:
            return resolution_reason
        return (
            f"Normalized certificate type '{raw_certificate_type}' to "
            f"'{normalized_certificate_type}'. {resolution_reason}"
        )

    def _normalize_certificate_type(self, certificate_type: str | None) -> str | None:
        normalized = self._normalize_lookup_text(certificate_type)
        if not normalized:
            return certificate_type

        if normalized in {
            "egyptian secondary or nile or stem or azhar",
            "egyptian secondary",
            "egyptian thanaweya amma",
            "egyptian thanaweya amma science",
            "thanaweia amma",
            "thanaweya amma",
            "nile school certificate",
            "stem school certificate",
            "azhar certificate",
        }:
            return EGYPTIAN_SECONDARY_CERTIFICATE

        if normalized in {
            "equivalent certificates",
            "equivalent certificate",
            "american diploma",
            "american diploma science track",
            "american high school diploma",
            "arab high school certificates",
            "arab high school certificates science",
            "french baccalaureate",
            "german abitur",
            "ib",
            "igcse",
            "igcse science track",
            "igcse gcse gce",
            "international baccalaureate",
        }:
            return EQUIVALENT_CERTIFICATES

        if any(token in normalized for token in ("egyptian", "thanaweya", "thanaweia", "nile", "stem", "azhar")):
            return EGYPTIAN_SECONDARY_CERTIFICATE

        equivalent_tokens = (
            "american",
            "baccalaureate",
            "abitur",
            "igcse",
            "gcse",
            "gce",
            "ib",
            "international baccalaureate",
            "arab high school",
            "equivalent",
        )
        if any(token in normalized for token in equivalent_tokens):
            return EQUIVALENT_CERTIFICATES

        return certificate_type

    def _normalize_lookup_text(self, value: str | None) -> str:
        if value is None:
            return ""
        normalized = value.strip().lower().replace("_", " ")
        return " ".join(normalized.split())
