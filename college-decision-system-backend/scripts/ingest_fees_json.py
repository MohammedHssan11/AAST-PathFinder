from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.db.models import (
    DecisionFeeAdditionalFeeModel,
    DecisionFeeAmountModel,
    DecisionFeeCategoryRuleModel,
    DecisionFeeDefinitionModel,
    DecisionFeeGlobalPolicyModel,
    DecisionFeeItemModel,
    DecisionFeeRuleCollegeModel,
    DecisionFeeRuleThresholdModel,
    DecisionScholarshipEligibilityModel,
    DecisionScholarshipModel,
)
from app.infrastructure.db.repositories.decision_fee_repo import (
    DecisionFeeRepository,
    is_generic_fee_program_name,
)
from app.infrastructure.db.session import SessionLocal

LOGGER = logging.getLogger("scripts.ingest_fees_json")

DEFAULT_FEES_FILE = ROOT_DIR.parent / "normalized_college_v2" / "fees.json"
EXPECTED_SCHEMA_VERSION = "fees_normalized_v1"


class IngestionValidationError(ValueError):
    """Raised when the fees dataset is malformed or cannot be normalized."""


@dataclass
class IngestionSummary:
    fee_items_loaded: int = 0
    fee_amount_rows_loaded: int = 0
    additional_fee_rows_loaded: int = 0
    fee_rules_loaded: int = 0
    rule_college_rows_loaded: int = 0
    thresholds_loaded: int = 0
    policies_loaded: int = 0
    definition_rows_loaded: int = 0
    matched_colleges_count: int = 0
    matched_programs_count: int = 0
    failed_mappings_count: int = 0
    scholarships_loaded: int = 0
    scholarship_eligibility_rows_loaded: int = 0


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest normalized fees.json into decision_fee_* tables.")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FEES_FILE,
        help="Path to the normalized fees.json file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, validate, and stage ORM inserts without committing database changes.",
    )
    return parser.parse_args()


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fees file does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise IngestionValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise IngestionValidationError("Root JSON value must be an object")

    return payload


def validate_root(payload: dict[str, Any]) -> dict[str, Any]:
    schema_version = payload.get("schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise IngestionValidationError(
            f"schema_version must be {EXPECTED_SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    tuition_fees = ensure_dict(payload.get("tuition_fees"), "tuition_fees")
    if not tuition_fees:
        raise IngestionValidationError("tuition_fees block is required")
    return tuition_fees


def ensure_dict(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise IngestionValidationError(f"{field_name} must be an object")
    return value


def ensure_list(value: Any, field_name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise IngestionValidationError(f"{field_name} must be a list")
    return value


def normalize_required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise IngestionValidationError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise IngestionValidationError(f"{field_name} must be a non-empty string")
    return normalized


def normalize_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise IngestionValidationError(f"{field_name} must be a string or null")
    normalized = value.strip()
    return normalized or None


def coerce_decimal(
    value: Any,
    field_name: str,
    *,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal:
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise IngestionValidationError(f"{field_name} must be numeric") from exc

    if minimum is not None and decimal_value < minimum:
        raise IngestionValidationError(f"{field_name} must be >= {minimum}")
    if maximum is not None and decimal_value > maximum:
        raise IngestionValidationError(f"{field_name} must be <= {maximum}")
    return decimal_value


def coerce_optional_decimal(
    value: Any,
    field_name: str,
    *,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return coerce_decimal(value, field_name, minimum=minimum, maximum=maximum)


def serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def parse_data_quality(raw_data_quality: Any, field_name: str) -> tuple[str | None, str | None]:
    data_quality = ensure_dict(raw_data_quality, field_name)
    status = normalize_optional_string(data_quality.get("status"), f"{field_name}.status")
    note = normalize_optional_string(data_quality.get("note"), f"{field_name}.note")
    return status, note


def normalize_academic_year(item: dict[str, Any], default_year: str) -> str:
    direct_year = normalize_optional_string(item.get("academic_year"), "items[].academic_year")
    if direct_year is not None:
        return direct_year

    year_list = ensure_list(item.get("academic_years"), "items[].academic_years")
    if year_list:
        return normalize_required_string(year_list[0], "items[].academic_years[0]")
    return default_year


def clear_existing_fee_tables(session) -> None:
    delete_order = [
        DecisionFeeAmountModel,
        DecisionFeeAdditionalFeeModel,
        DecisionFeeRuleThresholdModel,
        DecisionFeeRuleCollegeModel,
        DecisionScholarshipEligibilityModel,
        DecisionFeeItemModel,
        DecisionFeeCategoryRuleModel,
        DecisionScholarshipModel,
        DecisionFeeGlobalPolicyModel,
        DecisionFeeDefinitionModel,
    ]
    for model in delete_order:
        session.query(model).delete()


def build_definition_rows(raw_definitions: dict[str, Any], summary: IngestionSummary) -> list[DecisionFeeDefinitionModel]:
    rows: list[DecisionFeeDefinitionModel] = []

    for definition_group, definition_value in raw_definitions.items():
        if isinstance(definition_value, dict):
            for sort_order, (definition_key, text_value) in enumerate(definition_value.items()):
                rows.append(
                    DecisionFeeDefinitionModel(
                        definition_group=definition_group,
                        definition_key=normalize_required_string(
                            definition_key,
                            f"definitions.{definition_group}.key",
                        ),
                        definition_value=normalize_required_string(
                            text_value,
                            f"definitions.{definition_group}.{definition_key}",
                        ),
                        sort_order=sort_order,
                    )
                )
        elif isinstance(definition_value, list):
            for sort_order, item in enumerate(definition_value):
                text_value = normalize_required_string(
                    item,
                    f"definitions.{definition_group}[{sort_order}]",
                )
                rows.append(
                    DecisionFeeDefinitionModel(
                        definition_group=definition_group,
                        definition_key=text_value,
                        definition_value=text_value,
                        sort_order=sort_order,
                    )
                )
        else:
            raise IngestionValidationError(f"definitions.{definition_group} must be a list or object")

    summary.definition_rows_loaded += len(rows)
    return rows


def build_policy_rows(raw_policies: list[Any], summary: IngestionSummary) -> list[DecisionFeeGlobalPolicyModel]:
    rows: list[DecisionFeeGlobalPolicyModel] = []

    for index, raw_policy in enumerate(raw_policies):
        policy = ensure_dict(raw_policy, f"tuition_fees.global_fee_policies[{index}]")
        details = policy.get("details")
        if details is None:
            details = {
                key: value
                for key, value in policy.items()
                if key not in {"policy_id", "title", "applies_to"}
            }

        rows.append(
            DecisionFeeGlobalPolicyModel(
                policy_id=normalize_required_string(
                    policy.get("policy_id"),
                    f"tuition_fees.global_fee_policies[{index}].policy_id",
                ),
                title=normalize_required_string(
                    policy.get("title"),
                    f"tuition_fees.global_fee_policies[{index}].title",
                ),
                applies_to=normalize_optional_string(
                    policy.get("applies_to"),
                    f"tuition_fees.global_fee_policies[{index}].applies_to",
                ),
                details_json=serialize_json(details),
            )
        )

    summary.policies_loaded += len(rows)
    return rows


def build_fee_item_rows(
    raw_items: list[Any],
    *,
    default_academic_year: str,
    default_currency: str,
    default_fee_mode: str,
    repo: DecisionFeeRepository,
    summary: IngestionSummary,
) -> list[DecisionFeeItemModel]:
    rows: list[DecisionFeeItemModel] = []

    for index, raw_item in enumerate(raw_items):
        item = ensure_dict(raw_item, f"tuition_fees.items[{index}]")
        fee_id = normalize_required_string(item.get("fee_id"), f"tuition_fees.items[{index}].fee_id")
        branch_scope = normalize_required_string(
            item.get("branch_scope"),
            f"tuition_fees.items[{index}].branch_scope",
        )
        college_id_raw = normalize_required_string(
            item.get("college_id"),
            f"tuition_fees.items[{index}].college_id",
        )
        program_name = normalize_optional_string(
            item.get("program_name"),
            f"tuition_fees.items[{index}].program_name",
        )
        track_type = normalize_required_string(
            item.get("track_type"),
            f"tuition_fees.items[{index}].track_type",
        )

        source_college_match_id = repo.find_confident_college_match_id(
            raw_college_id=college_id_raw,
            branch_scope=branch_scope,
        )
        if source_college_match_id is not None:
            summary.matched_colleges_count += 1
        else:
            summary.failed_mappings_count += 1

        source_program_match_id = repo.find_confident_program_match_id(
            raw_college_id=college_id_raw,
            branch_scope=branch_scope,
            program_name=program_name,
        )
        if source_program_match_id is not None:
            summary.matched_programs_count += 1
        elif program_name and not is_generic_fee_program_name(program_name):
            summary.failed_mappings_count += 1

        status, note = parse_data_quality(
            item.get("data_quality"),
            f"tuition_fees.items[{index}].data_quality",
        )

        fee_item = DecisionFeeItemModel(
            fee_id=fee_id,
            academic_year=normalize_academic_year(item, default_academic_year),
            currency=normalize_optional_string(item.get("currency"), f"tuition_fees.items[{index}].currency")
            or default_currency,
            fee_mode=normalize_optional_string(item.get("fee_mode"), f"tuition_fees.items[{index}].fee_mode")
            or default_fee_mode,
            branch_scope=branch_scope,
            college_id_raw=college_id_raw,
            college_name=normalize_optional_string(
                item.get("college_name"),
                f"tuition_fees.items[{index}].college_name",
            ),
            program_name=program_name,
            track_type=track_type,
            partner_university=normalize_optional_string(
                item.get("partner_university"),
                f"tuition_fees.items[{index}].partner_university",
            ),
            source_college_match_id=source_college_match_id,
            source_program_match_id=source_program_match_id,
            data_quality_status=status,
            data_quality_note=note,
            amounts=build_fee_amount_rows(
                item.get("student_group_fees"),
                item_index=index,
                summary=summary,
            ),
            additional_fees=build_additional_fee_rows(
                item.get("additional_fees"),
                item_index=index,
                summary=summary,
            ),
        )
        rows.append(fee_item)

    summary.fee_items_loaded += len(rows)
    return rows


def build_fee_amount_rows(
    raw_student_group_fees: Any,
    *,
    item_index: int,
    summary: IngestionSummary,
) -> list[DecisionFeeAmountModel]:
    student_group_fees = ensure_dict(
        raw_student_group_fees,
        f"tuition_fees.items[{item_index}].student_group_fees",
    )
    rows: list[DecisionFeeAmountModel] = []

    for student_group, raw_categories in student_group_fees.items():
        categories = ensure_dict(
            raw_categories,
            f"tuition_fees.items[{item_index}].student_group_fees.{student_group}",
        )
        for fee_category, raw_amount in categories.items():
            rows.append(
                DecisionFeeAmountModel(
                    student_group=normalize_required_string(
                        student_group,
                        f"tuition_fees.items[{item_index}].student_group_fees.student_group",
                    ),
                    fee_category=normalize_required_string(
                        fee_category,
                        f"tuition_fees.items[{item_index}].student_group_fees.{student_group}.fee_category",
                    ),
                    amount_usd=coerce_decimal(
                        raw_amount,
                        f"tuition_fees.items[{item_index}].student_group_fees.{student_group}.{fee_category}",
                        minimum=Decimal("0"),
                    ),
                )
            )

    summary.fee_amount_rows_loaded += len(rows)
    return rows


def build_additional_fee_rows(
    raw_additional_fees: Any,
    *,
    item_index: int,
    summary: IngestionSummary,
) -> list[DecisionFeeAdditionalFeeModel]:
    additional_fees = ensure_list(raw_additional_fees, f"tuition_fees.items[{item_index}].additional_fees")
    rows: list[DecisionFeeAdditionalFeeModel] = []

    for sort_order, raw_fee in enumerate(additional_fees):
        fee = ensure_dict(raw_fee, f"tuition_fees.items[{item_index}].additional_fees[{sort_order}]")
        rows.append(
            DecisionFeeAdditionalFeeModel(
                fee_type=normalize_required_string(
                    fee.get("type"),
                    f"tuition_fees.items[{item_index}].additional_fees[{sort_order}].type",
                ),
                amount_usd=coerce_decimal(
                    fee.get("amount_usd"),
                    f"tuition_fees.items[{item_index}].additional_fees[{sort_order}].amount_usd",
                    minimum=Decimal("0"),
                ),
                frequency=normalize_optional_string(
                    fee.get("frequency"),
                    f"tuition_fees.items[{item_index}].additional_fees[{sort_order}].frequency",
                ),
                note=normalize_optional_string(
                    fee.get("note"),
                    f"tuition_fees.items[{item_index}].additional_fees[{sort_order}].note",
                ),
                sort_order=sort_order,
            )
        )

    summary.additional_fee_rows_loaded += len(rows)
    return rows


def build_fee_rule_rows(
    raw_rules: list[Any],
    *,
    repo: DecisionFeeRepository,
    summary: IngestionSummary,
) -> list[DecisionFeeCategoryRuleModel]:
    rows: list[DecisionFeeCategoryRuleModel] = []

    for index, raw_rule in enumerate(raw_rules):
        rule = ensure_dict(raw_rule, f"fee_category_rules[{index}]")
        status, note = parse_data_quality(
            rule.get("data_quality"),
            f"fee_category_rules[{index}].data_quality",
        )
        rule_row = DecisionFeeCategoryRuleModel(
            rule_id=normalize_required_string(rule.get("rule_id"), f"fee_category_rules[{index}].rule_id"),
            certificate_type=normalize_required_string(
                rule.get("certificate_type"),
                f"fee_category_rules[{index}].certificate_type",
            ),
            branch_scope=normalize_required_string(
                rule.get("branch_scope"),
                f"fee_category_rules[{index}].branch_scope",
            ),
            student_group=normalize_optional_string(
                rule.get("student_group"),
                f"fee_category_rules[{index}].student_group",
            ),
            data_quality_status=status,
            data_quality_note=note,
            colleges=build_rule_college_rows(
                rule.get("college_ids"),
                rule_index=index,
                branch_scope=normalize_required_string(
                    rule.get("branch_scope"),
                    f"fee_category_rules[{index}].branch_scope",
                ),
                repo=repo,
                summary=summary,
            ),
            thresholds=build_threshold_rows(
                rule.get("thresholds"),
                rule_index=index,
                summary=summary,
            ),
        )
        rows.append(rule_row)

    summary.fee_rules_loaded += len(rows)
    return rows


def build_rule_college_rows(
    raw_college_ids: Any,
    *,
    rule_index: int,
    branch_scope: str,
    repo: DecisionFeeRepository,
    summary: IngestionSummary,
) -> list[DecisionFeeRuleCollegeModel]:
    college_ids = ensure_list(raw_college_ids, f"fee_category_rules[{rule_index}].college_ids")
    rows: list[DecisionFeeRuleCollegeModel] = []

    for sort_order, raw_college_id in enumerate(college_ids):
        college_id_raw = normalize_required_string(
            raw_college_id,
            f"fee_category_rules[{rule_index}].college_ids[{sort_order}]",
        )
        source_college_match_id = repo.find_confident_college_match_id(
            raw_college_id=college_id_raw,
            branch_scope=branch_scope,
        )
        if source_college_match_id is not None:
            summary.matched_colleges_count += 1
        else:
            summary.failed_mappings_count += 1

        rows.append(
            DecisionFeeRuleCollegeModel(
                college_id_raw=college_id_raw,
                source_college_match_id=source_college_match_id,
                sort_order=sort_order,
            )
        )

    summary.rule_college_rows_loaded += len(rows)
    return rows


def build_threshold_rows(
    raw_thresholds: Any,
    *,
    rule_index: int,
    summary: IngestionSummary,
) -> list[DecisionFeeRuleThresholdModel]:
    thresholds = ensure_dict(raw_thresholds, f"fee_category_rules[{rule_index}].thresholds")
    rows: list[DecisionFeeRuleThresholdModel] = []

    for fee_category, raw_band in thresholds.items():
        band = ensure_dict(raw_band, f"fee_category_rules[{rule_index}].thresholds.{fee_category}")
        rows.append(
            DecisionFeeRuleThresholdModel(
                fee_category=normalize_required_string(
                    fee_category,
                    f"fee_category_rules[{rule_index}].thresholds.fee_category",
                ),
                min_percent=coerce_optional_decimal(
                    band.get("min_percent"),
                    f"fee_category_rules[{rule_index}].thresholds.{fee_category}.min_percent",
                    minimum=Decimal("0"),
                    maximum=Decimal("100"),
                ),
                max_percent_exclusive=coerce_optional_decimal(
                    band.get("max_percent_exclusive"),
                    f"fee_category_rules[{rule_index}].thresholds.{fee_category}.max_percent_exclusive",
                    minimum=Decimal("0"),
                    maximum=Decimal("100"),
                ),
            )
        )

    summary.thresholds_loaded += len(rows)
    return rows


def build_scholarship_rows(raw_scholarships: Any, summary: IngestionSummary) -> list[DecisionScholarshipModel]:
    scholarships = ensure_list(raw_scholarships, "scholarships")
    rows: list[DecisionScholarshipModel] = []

    for index, raw_scholarship in enumerate(scholarships):
        scholarship = ensure_dict(raw_scholarship, f"scholarships[{index}]")
        eligibility_values = ensure_list(
            scholarship.get("eligibility"),
            f"scholarships[{index}].eligibility",
        )
        rows.append(
            DecisionScholarshipModel(
                scholarship_id=normalize_required_string(
                    scholarship.get("scholarship_id"),
                    f"scholarships[{index}].scholarship_id",
                ),
                name=normalize_required_string(
                    scholarship.get("name"),
                    f"scholarships[{index}].name",
                ),
                eligibility_entries=[
                    DecisionScholarshipEligibilityModel(
                        eligibility_text=normalize_required_string(
                            item,
                            f"scholarships[{index}].eligibility[{sort_order}]",
                        ),
                        sort_order=sort_order,
                    )
                    for sort_order, item in enumerate(eligibility_values)
                ],
            )
        )

    summary.scholarships_loaded += len(rows)
    summary.scholarship_eligibility_rows_loaded += sum(
        len(row.eligibility_entries) for row in rows
    )
    return rows


def ingest_fees_file(*, fees_file: Path, dry_run: bool) -> IngestionSummary:
    payload = load_json_file(fees_file)
    tuition_fees = validate_root(payload)

    academic_years = ensure_list(payload.get("academic_years"), "academic_years")
    default_academic_year = normalize_required_string(
        academic_years[0] if academic_years else None,
        "academic_years[0]",
    )
    default_currency = normalize_required_string(payload.get("currency"), "currency")
    default_fee_mode = normalize_required_string(payload.get("fee_mode_default"), "fee_mode_default")

    summary = IngestionSummary()

    with SessionLocal() as session:
        repo = DecisionFeeRepository(session)
        definition_rows = build_definition_rows(
            ensure_dict(tuition_fees.get("definitions"), "tuition_fees.definitions"),
            summary,
        )
        policy_rows = build_policy_rows(
            ensure_list(tuition_fees.get("global_fee_policies"), "tuition_fees.global_fee_policies"),
            summary,
        )
        fee_item_rows = build_fee_item_rows(
            ensure_list(tuition_fees.get("items"), "tuition_fees.items"),
            default_academic_year=default_academic_year,
            default_currency=default_currency,
            default_fee_mode=default_fee_mode,
            repo=repo,
            summary=summary,
        )
        rule_rows = build_fee_rule_rows(
            ensure_list(payload.get("fee_category_rules"), "fee_category_rules"),
            repo=repo,
            summary=summary,
        )
        scholarship_rows = build_scholarship_rows(
            payload.get("scholarships") or tuition_fees.get("scholarships"),
            summary,
        )

        try:
            clear_existing_fee_tables(session)
            session.add_all(definition_rows)
            session.add_all(policy_rows)
            session.add_all(fee_item_rows)
            session.add_all(rule_rows)
            session.add_all(scholarship_rows)
            session.flush()
            if dry_run:
                session.rollback()
            else:
                session.commit()
        except Exception:
            session.rollback()
            raise

    return summary


def print_summary(summary: IngestionSummary, *, dry_run: bool) -> None:
    print(f"fee_items loaded: {summary.fee_items_loaded}")
    print(f"fee_amount rows loaded: {summary.fee_amount_rows_loaded}")
    print(f"additional fee rows loaded: {summary.additional_fee_rows_loaded}")
    print(f"fee rules loaded: {summary.fee_rules_loaded}")
    print(f"rule-college rows loaded: {summary.rule_college_rows_loaded}")
    print(f"thresholds loaded: {summary.thresholds_loaded}")
    print(f"policies loaded: {summary.policies_loaded}")
    print(f"definition rows loaded: {summary.definition_rows_loaded}")
    print(f"matched colleges count: {summary.matched_colleges_count}")
    print(f"matched programs count: {summary.matched_programs_count}")
    print(f"failed mappings count: {summary.failed_mappings_count}")
    if summary.scholarships_loaded or summary.scholarship_eligibility_rows_loaded:
        print(f"scholarships loaded: {summary.scholarships_loaded}")
        print(
            "scholarship eligibility rows loaded: "
            f"{summary.scholarship_eligibility_rows_loaded}"
        )
    if dry_run:
        print("mode: dry-run (validated and flushed, then rolled back)")


def main() -> int:
    configure_logging()
    args = parse_args()
    LOGGER.info("Loading fees dataset from %s", args.file)
    summary = ingest_fees_file(fees_file=args.file, dry_run=args.dry_run)
    print_summary(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
