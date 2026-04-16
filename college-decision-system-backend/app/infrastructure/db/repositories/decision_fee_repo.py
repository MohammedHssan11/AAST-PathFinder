from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from functools import cached_property
from typing import Iterable, Sequence

from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.models.decision_college import DecisionCollegeModel
from app.infrastructure.db.models.decision_fee import (
    DecisionFeeAdditionalFeeModel,
    DecisionFeeAmountModel,
    DecisionFeeCategoryRuleModel,
    DecisionFeeItemModel,
    DecisionFeeRuleCollegeModel,
    DecisionFeeRuleThresholdModel,
)
from app.infrastructure.db.models.decision_program import DecisionProgramModel

CONSERVATIVE_BRANCH_SCOPES = frozenset(
    {"alamein_only", "all_branches_except_alamein", "all_branches_where_program_exists"}
)
RECURRING_FREQUENCIES = frozenset({"per_semester", "per_year", "annual", "recurring"})
ONE_TIME_FREQUENCIES = frozenset({"one_time", "one-time", "first_semester_only"})
GENERIC_PROGRAM_MARKERS = (
    "programs",
    "english programs",
    "international transport",
    "london school of economics program",
)
PROGRAM_NAME_EQUIVALENTS = {
    "pharm d": "doctor of pharmacy",
    "clinical pharm d": "doctor of pharmacy clinical pharmacy",
    "bachelor of dentistry": "bachelor of dental surgery",
    "bachelor of medicine": "bachelor of medicine and surgery",
    "fisheries technology": "bachelor of fisheries and aquaculture technology",
}


@dataclass(frozen=True)
class FeeCategoryResolution:
    rule_id: str
    fee_category: str
    certificate_type: str
    student_group: str | None
    confidence: str
    resolution_reason: str
    matched_direct_college: bool
    matched_via_alias: bool
    matched_threshold_min: Decimal | None
    matched_threshold_max_exclusive: Decimal | None
    data_quality_status: str | None
    data_quality_note: str | None


@dataclass(frozen=True)
class EffectiveFeeResult:
    fee_item_id: int
    fee_id: str
    track_type: str
    source_scope: str
    fee_match_level: str
    fee_match_confidence: str
    student_group: str | None
    fee_category: str
    currency: str
    academic_year: str
    fee_mode: str
    base_tuition_usd: Decimal
    recurring_additional_fees_usd: Decimal
    one_time_additional_fees_usd: Decimal
    unknown_frequency_additional_fees_usd: Decimal
    total_recurring_tuition_usd: Decimal
    selection_reason: str
    warnings: tuple[str, ...]
    data_quality_status: str | None
    data_quality_note: str | None
    partner_university: str | None
    recurring_additional_fee_lines: list[dict[str, str | Decimal | None]]
    one_time_additional_fee_lines: list[dict[str, str | Decimal | None]]
    unknown_frequency_fee_lines: list[dict[str, str | Decimal | None]]


@dataclass(frozen=True)
class FeeItemMatchCandidate:
    fee_item: DecisionFeeItemModel
    source_scope: str
    fee_match_level: str
    fee_match_confidence: str
    match_score: float
    match_reason: str


def normalize_lookup_text(value: str | None) -> str:
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    text = ascii_text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    for source_text, replacement_text in PROGRAM_NAME_EQUIVALENTS.items():
        if text == source_text:
            text = replacement_text
            break

    return text


def college_is_alamein(college: DecisionCollegeModel) -> bool:
    haystack = " ".join(
        [
            college.id or "",
            college.college_name or "",
            college.branch or "",
            college.city or "",
        ]
    ).lower()
    return "alamein" in haystack or "el alamein" in haystack


def branch_scope_matches_college(branch_scope: str, college: DecisionCollegeModel) -> bool:
    normalized_scope = (branch_scope or "").strip().lower()
    if normalized_scope not in CONSERVATIVE_BRANCH_SCOPES:
        return True
    if normalized_scope == "alamein_only":
        return college_is_alamein(college)
    if normalized_scope == "all_branches_except_alamein":
        return not college_is_alamein(college)
    return True


def raw_aliases_for_decision_college(college: DecisionCollegeModel) -> set[str]:
    aliases: set[str] = set()
    college_id = college.id.upper()

    if college_id.startswith("CET_"):
        aliases.add("ENGINEERING_AND_TECHNOLOGY")
        if college_is_alamein(college):
            aliases.add("ENGINEERING_AND_TECHNOLOGY_ALAMEIN")
    elif college_id.startswith("CCIT_"):
        aliases.add("CCIT")
    elif college_id.startswith("PHARM_"):
        aliases.add("PHARMACY")
    elif college_id == "DENT_ELALAMEIN":
        aliases.add("DENTISTRY_ALAMEIN")
    elif college_id.startswith("CMT_"):
        aliases.add("MANAGEMENT_AND_TECHNOLOGY")
        if college_is_alamein(college):
            aliases.add("MANAGEMENT_AND_TECHNOLOGY_ALAMEIN")
    elif college_id.startswith("CITL_"):
        aliases.add("CITL")
        if college_is_alamein(college):
            aliases.add("CITL_ALAMEIN")
    elif college_id.startswith("CLC_"):
        aliases.add("LANGUAGE_AND_MEDIA")
    elif college_id == "CFAT_ABUKIR":
        aliases.add("FISHERIES_AND_AQUACULTURE")
    elif college_id == "LAW_SMART_VILLAGE":
        aliases.add("LAW")
    elif college_id == "CAD_SMART_VILLAGE":
        aliases.add("ART_AND_DESIGN")
    elif college_id.startswith("MED_ELALAMEIN"):
        aliases.add("MEDICINE_ALAMEIN")
    elif college_id.startswith("CAI_"):
        aliases.add("AI")
        if college_is_alamein(college):
            aliases.add("AI_ALAMEIN")

    return aliases


def is_generic_fee_program_name(program_name: str | None) -> bool:
    normalized = normalize_lookup_text(program_name)
    if not normalized:
        return True
    return any(marker in normalized for marker in GENERIC_PROGRAM_MARKERS)


def expand_fee_program_segments(program_name: str | None) -> list[str]:
    if program_name is None:
        return []

    stripped = program_name.strip()
    if not stripped:
        return []

    without_parenthetical = re.sub(r"\([^)]*\)", " ", stripped)
    parts = [
        part.strip()
        for part in re.split(r"\s*/\s*|\s*;\s*", without_parenthetical)
        if part.strip()
    ]
    return parts or [stripped]


def score_direct_program_match(raw_program_name: str | None, decision_program_name: str) -> float:
    raw_name = normalize_lookup_text(raw_program_name)
    candidate_name = normalize_lookup_text(decision_program_name)
    if not raw_name or not candidate_name:
        return 0.0
    if raw_name == candidate_name:
        return 1.0

    raw_tokens = set(raw_name.split())
    candidate_tokens = set(candidate_name.split())
    if not raw_tokens or not candidate_tokens:
        return 0.0

    shared_tokens = raw_tokens & candidate_tokens
    overlap_ratio = len(shared_tokens) / max(len(raw_tokens), len(candidate_tokens))
    subset_bonus = 0.0
    if raw_tokens.issubset(candidate_tokens) or candidate_tokens.issubset(raw_tokens):
        subset_bonus = 0.12

    sequence_ratio = SequenceMatcher(None, raw_name, candidate_name).ratio()
    return max(overlap_ratio + subset_bonus, sequence_ratio)


def score_fee_program_match(raw_program_name: str | None, decision_program_name: str) -> float:
    candidate_name = normalize_lookup_text(decision_program_name)
    if not candidate_name:
        return 0.0

    best_score = 0.0
    for segment in expand_fee_program_segments(raw_program_name):
        raw_name = normalize_lookup_text(segment)
        if not raw_name:
            continue
        if raw_name == candidate_name:
            return 1.0

        raw_tokens = set(raw_name.split())
        candidate_tokens = set(candidate_name.split())
        if not raw_tokens or not candidate_tokens:
            continue

        shared_tokens = raw_tokens & candidate_tokens
        overlap_ratio = len(shared_tokens) / max(len(raw_tokens), len(candidate_tokens))
        subset_bonus = 0.0
        if raw_tokens.issubset(candidate_tokens) or candidate_tokens.issubset(raw_tokens):
            subset_bonus = 0.12

        sequence_ratio = SequenceMatcher(None, raw_name, candidate_name).ratio()
        best_score = max(best_score, overlap_ratio + subset_bonus, sequence_ratio)

    return best_score


def academic_year_sort_key(academic_year: str | None) -> tuple[int, int, str]:
    if academic_year is None:
        return (0, 0, "")

    numeric_parts = [int(part) for part in re.findall(r"\d{4}", academic_year)]
    if not numeric_parts:
        return (0, 0, academic_year)
    if len(numeric_parts) == 1:
        return (numeric_parts[0], numeric_parts[0], academic_year)
    return (numeric_parts[0], numeric_parts[-1], academic_year)


class DecisionFeeRepository:
    def __init__(self, db: Session):
        self.db = db
        self._fee_items_by_college_cache: dict[str, list[DecisionFeeItemModel]] = {}
        self._fee_items_by_program_cache: dict[str, list[FeeItemMatchCandidate]] = {}

    def _list_decision_colleges(self) -> list[DecisionCollegeModel]:
        return list(self._decision_colleges_by_id.values())

    def _list_decision_programs(self) -> list[DecisionProgramModel]:
        return list(self._decision_programs_by_id.values())

    @cached_property
    def _decision_colleges_by_id(self) -> dict[str, DecisionCollegeModel]:
        colleges = self.db.query(DecisionCollegeModel).all()
        return {college.id: college for college in colleges}

    @cached_property
    def _decision_programs_by_id(self) -> dict[str, DecisionProgramModel]:
        programs = self.db.query(DecisionProgramModel).all()
        return {program.id: program for program in programs}

    @cached_property
    def _fee_category_rules(self) -> list[DecisionFeeCategoryRuleModel]:
        return (
            self.db.query(DecisionFeeCategoryRuleModel)
            .options(
                joinedload(DecisionFeeCategoryRuleModel.colleges),
                joinedload(DecisionFeeCategoryRuleModel.thresholds),
            )
            .all()
        )

    @cached_property
    def _fee_items(self) -> list[DecisionFeeItemModel]:
        return (
            self.db.query(DecisionFeeItemModel)
            .options(
                joinedload(DecisionFeeItemModel.amounts),
                joinedload(DecisionFeeItemModel.additional_fees),
            )
            .all()
        )

    def _get_decision_college(self, college_id: str) -> DecisionCollegeModel | None:
        return self._decision_colleges_by_id.get(college_id)

    def _get_decision_program(self, program_id: str) -> DecisionProgramModel | None:
        return self._decision_programs_by_id.get(program_id)

    def find_college_candidates(
        self,
        *,
        raw_college_id: str,
        branch_scope: str,
    ) -> list[DecisionCollegeModel]:
        raw_id = (raw_college_id or "").strip().upper()
        if not raw_id:
            return []

        candidates = [
            college
            for college in self._list_decision_colleges()
            if raw_id in raw_aliases_for_decision_college(college)
            and branch_scope_matches_college(branch_scope, college)
        ]
        return sorted(candidates, key=lambda college: college.id)

    def find_confident_college_match_id(
        self,
        *,
        raw_college_id: str,
        branch_scope: str,
    ) -> str | None:
        candidates = self.find_college_candidates(
            raw_college_id=raw_college_id,
            branch_scope=branch_scope,
        )
        if len(candidates) != 1:
            return None
        return candidates[0].id

    def find_confident_program_match_id(
        self,
        *,
        raw_college_id: str,
        branch_scope: str,
        program_name: str | None,
    ) -> str | None:
        if is_generic_fee_program_name(program_name):
            return None

        candidate_colleges = self.find_college_candidates(
            raw_college_id=raw_college_id,
            branch_scope=branch_scope,
        )
        candidate_college_ids = {college.id for college in candidate_colleges}
        if candidate_college_ids:
            programs = [
                program
                for program in self._list_decision_programs()
                if program.college_id in candidate_college_ids
            ]
        else:
            programs = []

        scored_matches = sorted(
            (
                (score_direct_program_match(program_name, program.program_name), program.id)
                for program in programs
            ),
            reverse=True,
        )
        if not scored_matches:
            return None

        best_score, best_program_id = scored_matches[0]
        if best_score < 0.88:
            return None
        if len(scored_matches) > 1 and scored_matches[1][0] >= best_score - 0.05:
            return None
        return best_program_id

    def get_fee_items_for_college(self, college_id: str) -> list[DecisionFeeItemModel]:
        if college_id in self._fee_items_by_college_cache:
            return self._fee_items_by_college_cache[college_id]

        college = self._get_decision_college(college_id)
        if college is None:
            return []

        aliases = raw_aliases_for_decision_college(college)
        items = [
            item
            for item in self._fee_items
            if item.source_college_match_id == college_id
            or (
                item.college_id_raw in aliases
                and branch_scope_matches_college(item.branch_scope, college)
            )
        ]
        items.sort(
            key=lambda item: (
                0 if item.source_college_match_id == college_id else 1,
                item.fee_id,
                item.id,
            )
        )
        self._fee_items_by_college_cache[college_id] = items
        return items

    def get_fee_items_for_program(self, program_id: str) -> list[DecisionFeeItemModel]:
        return [candidate.fee_item for candidate in self._get_program_fee_candidates(program_id)]

    def _get_program_fee_candidates(self, program_id: str) -> list[FeeItemMatchCandidate]:
        if program_id in self._fee_items_by_program_cache:
            return self._fee_items_by_program_cache[program_id]

        program = self._get_decision_program(program_id)
        if program is None:
            return []

        college_items = self.get_fee_items_for_college(program.college_id)
        matched_items: list[FeeItemMatchCandidate] = []
        for item in college_items:
            if item.source_program_match_id == program_id:
                matched_items.append(
                    FeeItemMatchCandidate(
                        fee_item=item,
                        source_scope="program_direct",
                        fee_match_level="program",
                        fee_match_confidence="high",
                        match_score=2.0,
                        match_reason=(
                            f"Fee item {item.fee_id} is mapped directly to program {program_id}."
                        ),
                    )
                )
                continue
            if item.source_program_match_id is not None:
                continue

            match_score = score_fee_program_match(item.program_name, program.program_name)
            if match_score >= 0.88:
                matched_items.append(
                    FeeItemMatchCandidate(
                        fee_item=item,
                        source_scope="program_inferred",
                        fee_match_level="program",
                        fee_match_confidence="medium" if match_score < 0.97 else "high",
                        match_score=match_score,
                        match_reason=(
                            f"Fee item {item.fee_id} inferred program match score "
                            f"{match_score:.2f} for program {program.program_name}."
                        ),
                    )
                )

        matched_items.sort(
            key=lambda candidate: (
                -candidate.match_score,
                candidate.fee_item.fee_id,
                candidate.fee_item.id,
            )
        )
        self._fee_items_by_program_cache[program_id] = matched_items
        return matched_items

    def get_additional_fees_for_fee_item(self, fee_item_id: int) -> list[DecisionFeeAdditionalFeeModel]:
        return (
            self.db.query(DecisionFeeAdditionalFeeModel)
            .filter(DecisionFeeAdditionalFeeModel.fee_item_id == fee_item_id)
            .order_by(DecisionFeeAdditionalFeeModel.sort_order, DecisionFeeAdditionalFeeModel.id)
            .all()
        )

    def resolve_fee_category_for_student(
        self,
        *,
        target_college_id: str,
        certificate_type: str | None,
        high_school_percentage: float | Decimal | None,
        student_group: str | None,
        branch_scope: str | None = None,
    ) -> FeeCategoryResolution | None:
        college = self._get_decision_college(target_college_id)
        if college is None:
            return None
        if not certificate_type or high_school_percentage is None:
            return None

        college_aliases = raw_aliases_for_decision_college(college)
        score_value = Decimal(str(high_school_percentage))
        normalized_certificate_type = (certificate_type or "").strip().lower()
        normalized_student_group = (student_group or "").strip() or None

        applicable_rules = [
            rule
            for rule in self._fee_category_rules
            if rule.certificate_type.strip().lower() == normalized_certificate_type
            and (
                (normalized_student_group is not None and (rule.student_group is None or rule.student_group == normalized_student_group))
                or (normalized_student_group is None and rule.student_group is None)
            )
            and branch_scope_matches_college(rule.branch_scope, college)
            and (branch_scope is None or rule.branch_scope == branch_scope)
            and self._rule_applies_to_college(rule.colleges, college_id=college.id, aliases=college_aliases)
        ]

        applicable_rules.sort(
            key=lambda rule: (
                0 if rule.student_group == normalized_student_group else 1,
                0
                if any(link.source_college_match_id == college.id for link in rule.colleges)
                else 1,
                rule.rule_id,
            )
        )

        for rule in applicable_rules:
            threshold = self._resolve_matching_threshold(rule.thresholds, score_value)
            if threshold is None:
                continue
            exact_direct_college = any(
                link.source_college_match_id == college.id for link in rule.colleges
            )
            matched_via_alias = not exact_direct_college
            confidence = self._resolve_fee_category_confidence(
                requested_student_group=normalized_student_group,
                matched_student_group=rule.student_group,
                matched_direct_college=exact_direct_college,
                matched_via_alias=matched_via_alias,
            )
            return FeeCategoryResolution(
                rule_id=rule.rule_id,
                fee_category=threshold.fee_category,
                certificate_type=rule.certificate_type,
                student_group=rule.student_group,
                confidence=confidence,
                resolution_reason=self._build_fee_category_reason(
                    rule=rule,
                    threshold=threshold,
                    matched_direct_college=exact_direct_college,
                    matched_via_alias=matched_via_alias,
                ),
                matched_direct_college=exact_direct_college,
                matched_via_alias=matched_via_alias,
                matched_threshold_min=threshold.min_percent,
                matched_threshold_max_exclusive=threshold.max_percent_exclusive,
                data_quality_status=rule.data_quality_status,
                data_quality_note=rule.data_quality_note,
            )

        return None

    def get_effective_fee_for_program(
        self,
        *,
        program_id: str,
        resolved_fee_category: str,
        student_group: str | None,
        track_type: str = "regular",
        academic_year: str | None = None,
    ) -> EffectiveFeeResult | None:
        if not student_group:
            return None

        candidate_warnings: list[str] = []
        fee_candidates = [
            candidate
            for candidate in self._get_program_fee_candidates(program_id)
            if candidate.fee_item.track_type == track_type
        ]
        direct_candidates = [
            candidate for candidate in fee_candidates if candidate.source_scope == "program_direct"
        ]
        inferred_candidates = [
            candidate for candidate in fee_candidates if candidate.source_scope == "program_inferred"
        ]

        selected_candidate = self._select_best_fee_candidate(
            direct_candidates,
            academic_year=academic_year,
            prefer_fee_mode="per_semester",
        )
        if selected_candidate is None and inferred_candidates:
            if self._has_ambiguous_inferred_match(inferred_candidates):
                candidate_warnings.append(
                    "Multiple inferred program-level fee items matched with similar confidence; "
                    "skipped inferred match and attempted college fallback."
                )
            else:
                selected_candidate = self._select_best_fee_candidate(
                    inferred_candidates,
                    academic_year=academic_year,
                    prefer_fee_mode="per_semester",
                )

        if selected_candidate is None:
            program = self._get_decision_program(program_id)
            if program is None:
                return None
            return self.get_effective_fee_for_college(
                college_id=program.college_id,
                resolved_fee_category=resolved_fee_category,
                student_group=student_group,
                track_type=track_type,
                source_scope="college_fallback",
                academic_year=academic_year,
                existing_warnings=candidate_warnings,
            )

        return self._build_effective_fee_result(
            selected_candidate.fee_item,
            student_group=student_group,
            fee_category=resolved_fee_category,
            source_scope=selected_candidate.source_scope,
            fee_match_level=selected_candidate.fee_match_level,
            fee_match_confidence=selected_candidate.fee_match_confidence,
            selection_reason=selected_candidate.match_reason,
            academic_year=academic_year,
            existing_warnings=candidate_warnings,
        )

    def get_effective_fee_for_college(
        self,
        *,
        college_id: str,
        resolved_fee_category: str,
        student_group: str | None,
        track_type: str = "regular",
        source_scope: str = "college_level",
        academic_year: str | None = None,
        existing_warnings: Sequence[str] = (),
    ) -> EffectiveFeeResult | None:
        if not student_group:
            return None

        fee_items = [
            item
            for item in self.get_fee_items_for_college(college_id)
            if item.track_type == track_type
        ]
        generic_items = [
            item
            for item in fee_items
            if item.source_program_match_id is None and is_generic_fee_program_name(item.program_name)
        ]
        selected_candidate = self._select_best_fee_candidate(
            [
                FeeItemMatchCandidate(
                    fee_item=item,
                    source_scope=source_scope,
                    fee_match_level="college",
                    fee_match_confidence="medium",
                    match_score=1.0,
                    match_reason=(
                        f"Fee item {item.fee_id} selected as a conservative college-level fallback."
                    ),
                )
                for item in generic_items
            ],
            academic_year=academic_year,
            prefer_fee_mode="per_semester",
        )
        if selected_candidate is None:
            return None

        fallback_warnings = list(existing_warnings)
        fallback_warnings.append(
            "Used a college-level fallback because no confident program-level fee item was available."
        )
        return self._build_effective_fee_result(
            selected_candidate.fee_item,
            student_group=student_group,
            fee_category=resolved_fee_category,
            source_scope=selected_candidate.source_scope,
            fee_match_level=selected_candidate.fee_match_level,
            fee_match_confidence=selected_candidate.fee_match_confidence,
            selection_reason=selected_candidate.match_reason,
            academic_year=academic_year,
            existing_warnings=fallback_warnings,
        )

    def get_best_fee_for_program(
        self,
        *,
        program_id: str,
        resolved_fee_category: str,
        student_group: str | None,
        selected_track_type: str,
    ) -> EffectiveFeeResult | None:
        return self.get_effective_fee_for_program(
            program_id=program_id,
            resolved_fee_category=resolved_fee_category,
            student_group=student_group,
            track_type=selected_track_type,
        )

    def get_best_fee_for_college(
        self,
        *,
        college_id: str,
        resolved_fee_category: str,
        student_group: str | None,
        selected_track_type: str,
    ) -> EffectiveFeeResult | None:
        return self.get_effective_fee_for_college(
            college_id=college_id,
            resolved_fee_category=resolved_fee_category,
            student_group=student_group,
            track_type=selected_track_type,
        )

    def _rule_applies_to_college(
        self,
        rule_colleges: Iterable[DecisionFeeRuleCollegeModel],
        *,
        college_id: str,
        aliases: set[str],
    ) -> bool:
        for rule_college in rule_colleges:
            if rule_college.source_college_match_id == college_id:
                return True
            if rule_college.college_id_raw in aliases:
                return True
        return False

    def _resolve_matching_threshold(
        self,
        thresholds: Iterable[DecisionFeeRuleThresholdModel],
        score_value: Decimal,
    ) -> DecisionFeeRuleThresholdModel | None:
        threshold_by_category = {threshold.fee_category: threshold for threshold in thresholds}
        for category in ("A", "B", "C"):
            threshold = threshold_by_category.get(category)
            if threshold is None:
                continue
            if threshold.min_percent is not None and score_value < threshold.min_percent:
                continue
            if (
                threshold.max_percent_exclusive is not None
                and score_value >= threshold.max_percent_exclusive
            ):
                continue
            return threshold
        return None

    def _resolve_fee_category_confidence(
        self,
        *,
        requested_student_group: str | None,
        matched_student_group: str | None,
        matched_direct_college: bool,
        matched_via_alias: bool,
    ) -> str:
        if requested_student_group is None and matched_student_group is None:
            return "low"
        if matched_direct_college and matched_student_group == requested_student_group:
            return "high"
        if matched_via_alias and matched_student_group == requested_student_group:
            return "medium"
        return "medium"

    def _build_fee_category_reason(
        self,
        *,
        rule: DecisionFeeCategoryRuleModel,
        threshold: DecisionFeeRuleThresholdModel,
        matched_direct_college: bool,
        matched_via_alias: bool,
    ) -> str:
        college_scope = "direct college match" if matched_direct_college else "college alias match"
        threshold_parts: list[str] = []
        if threshold.min_percent is not None:
            threshold_parts.append(f"min {threshold.min_percent}")
        if threshold.max_percent_exclusive is not None:
            threshold_parts.append(f"max {threshold.max_percent_exclusive} exclusive")
        threshold_text = ", ".join(threshold_parts) if threshold_parts else "open threshold"
        student_group_text = rule.student_group or "default student-group fallback"
        return (
            f"Rule {rule.rule_id} matched via {college_scope}, student-group {student_group_text}, "
            f"and threshold {threshold_text}."
        )

    def _find_amount_row(
        self,
        amounts: Iterable[DecisionFeeAmountModel],
        *,
        student_group: str | None,
        fee_category: str,
    ) -> DecisionFeeAmountModel | None:
        if not student_group:
            return None
        for amount in amounts:
            if amount.student_group == student_group and amount.fee_category == fee_category:
                return amount
        return None

    def _select_best_fee_candidate(
        self,
        candidates: Sequence[FeeItemMatchCandidate],
        *,
        academic_year: str | None,
        prefer_fee_mode: str,
    ) -> FeeItemMatchCandidate | None:
        supported_candidates = [
            candidate for candidate in candidates if (candidate.fee_item.fee_mode or "").strip().lower() == prefer_fee_mode
        ]
        if not supported_candidates:
            return None

        return sorted(
            supported_candidates,
            key=lambda candidate: self._fee_candidate_sort_key(
                candidate=candidate,
                academic_year=academic_year,
            ),
        )[0]

    def _fee_candidate_sort_key(
        self,
        *,
        candidate: FeeItemMatchCandidate,
        academic_year: str | None,
    ) -> tuple[int, int, int, str, int]:
        item = candidate.fee_item
        year_key = academic_year_sort_key(item.academic_year)
        return (
            0 if academic_year and item.academic_year == academic_year else 1,
            -year_key[1],
            -year_key[0],
            item.fee_id,
            item.id,
        )

    def _has_ambiguous_inferred_match(
        self,
        candidates: Sequence[FeeItemMatchCandidate],
    ) -> bool:
        if len(candidates) < 2:
            return False

        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: (-candidate.match_score, candidate.fee_item.fee_id, candidate.fee_item.id),
        )
        best = ranked_candidates[0]
        best_program_name = normalize_lookup_text(best.fee_item.program_name)
        for contender in ranked_candidates[1:]:
            if best.match_score - contender.match_score > 0.03:
                break
            contender_program_name = normalize_lookup_text(contender.fee_item.program_name)
            if contender_program_name != best_program_name:
                return True
        return False

    def _build_effective_fee_result(
        self,
        fee_item: DecisionFeeItemModel,
        *,
        student_group: str | None,
        fee_category: str,
        source_scope: str,
        fee_match_level: str,
        fee_match_confidence: str,
        selection_reason: str,
        academic_year: str | None,
        existing_warnings: Sequence[str] = (),
    ) -> EffectiveFeeResult | None:
        amount_row = self._find_amount_row(
            fee_item.amounts,
            student_group=student_group,
            fee_category=fee_category,
        )
        if amount_row is None:
            return None

        recurring_total = Decimal("0")
        one_time_total = Decimal("0")
        unknown_frequency_total = Decimal("0")
        recurring_fee_lines: list[dict[str, str | Decimal | None]] = []
        one_time_fee_lines: list[dict[str, str | Decimal | None]] = []
        unknown_frequency_fee_lines: list[dict[str, str | Decimal | None]] = []

        for extra_fee in fee_item.additional_fees:
            normalized_frequency = (extra_fee.frequency or "").strip().lower()
            print(f"  [DEBUG] Additional Fee: {extra_fee.fee_type}, freq='{extra_fee.frequency}', norm='{normalized_frequency}'")
            fee_line = {
                "fee_type": extra_fee.fee_type,
                "amount_usd": extra_fee.amount_usd,
                "frequency": extra_fee.frequency,
                "note": extra_fee.note,
            }
            if normalized_frequency in RECURRING_FREQUENCIES:
                recurring_total += extra_fee.amount_usd
                recurring_fee_lines.append(fee_line)
            elif normalized_frequency in ONE_TIME_FREQUENCIES:
                one_time_total += extra_fee.amount_usd
                one_time_fee_lines.append(fee_line)
            else:
                unknown_frequency_total += extra_fee.amount_usd
                unknown_frequency_fee_lines.append(fee_line)

        warnings = list(existing_warnings)
        if academic_year and fee_item.academic_year != academic_year:
            warnings.append(
                f"Requested academic year {academic_year} was unavailable; used {fee_item.academic_year}."
            )
        if fee_item.data_quality_status:
            warnings.append(
                f"Fee item {fee_item.fee_id} carries data-quality status {fee_item.data_quality_status}."
            )
        if unknown_frequency_total > 0:
            warnings.append(
                "Some additional fee items have unknown frequency and were excluded from the semester estimate."
            )

        return EffectiveFeeResult(
            fee_item_id=fee_item.id,
            fee_id=fee_item.fee_id,
            track_type=fee_item.track_type,
            source_scope=source_scope,
            fee_match_level=fee_match_level,
            fee_match_confidence=fee_match_confidence,
            student_group=student_group,
            fee_category=fee_category,
            currency=fee_item.currency,
            academic_year=fee_item.academic_year,
            fee_mode=fee_item.fee_mode,
            base_tuition_usd=amount_row.amount_usd,
            recurring_additional_fees_usd=recurring_total,
            one_time_additional_fees_usd=one_time_total,
            unknown_frequency_additional_fees_usd=unknown_frequency_total,
            total_recurring_tuition_usd=amount_row.amount_usd + recurring_total,
            selection_reason=selection_reason,
            warnings=tuple(warnings),
            data_quality_status=fee_item.data_quality_status,
            data_quality_note=fee_item.data_quality_note,
            partner_university=fee_item.partner_university,
            recurring_additional_fee_lines=recurring_fee_lines,
            one_time_additional_fee_lines=one_time_fee_lines,
            unknown_frequency_fee_lines=unknown_frequency_fee_lines,
        )

    def _infer_source_scope(self, fee_item: DecisionFeeItemModel) -> str:
        if fee_item.source_program_match_id is not None:
            return "program_direct"
        if fee_item.program_name and not is_generic_fee_program_name(fee_item.program_name):
            return "program_inferred"
        return "college_level"

    def calculate_fallback_average_fee(
        self,
        *,
        college_id: str | None,
        branch_scope: str | None,
        student_group: str,
        fallback_scope: str,
    ) -> Decimal | None:
        if not student_group:
            return None
            
        fee_items_to_consider: list[DecisionFeeItemModel] = []
        
        if fallback_scope == "college" and college_id:
            fee_items_to_consider = self.get_fee_items_for_college(college_id)
        elif fallback_scope == "branch":
            colleges = [
                c for c in self._list_decision_colleges()
                if branch_scope is None or branch_scope_matches_college(branch_scope, c)
            ]
            for c in colleges:
                fee_items_to_consider.extend(self.get_fee_items_for_college(c.id))
        else:
            return None
            
        if not fee_items_to_consider:
            return None
            
        total_usd = Decimal("0")
        count = 0
        
        for item in fee_items_to_consider:
            recurring_add = sum(
                extra.amount_usd for extra in item.additional_fees 
                if (extra.frequency or "").strip().lower() in RECURRING_FREQUENCIES
            )
            item_amounts = [a.amount_usd for a in item.amounts if a.student_group == student_group]
            for amt in item_amounts:
                total_usd += (amt + recurring_add)
                count += 1
                
        if count == 0:
            return None
            
        return (total_usd / count).quantize(Decimal("0.01"))


__all__ = [
    "DecisionFeeRepository",
    "EffectiveFeeResult",
    "FeeCategoryResolution",
    "branch_scope_matches_college",
    "college_is_alamein",
    "expand_fee_program_segments",
    "is_generic_fee_program_name",
    "normalize_lookup_text",
    "raw_aliases_for_decision_college",
    "score_direct_program_match",
    "score_fee_program_match",
]
