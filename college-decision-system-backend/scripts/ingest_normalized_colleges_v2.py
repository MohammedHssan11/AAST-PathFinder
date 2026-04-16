from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.db.models import (
    DecisionAcceptedCertificateModel,
    DecisionAdmissionRequirementModel,
    DecisionCollegeAccreditationModel,
    DecisionCollegeFacilityModel,
    DecisionCollegeLeadershipModel,
    DecisionCollegeLevelProfileModel,
    DecisionCollegeMobilityItemModel,
    DecisionCollegeMobilityModel,
    DecisionCollegeModel,
    DecisionCollegeResearchFocusModel,
    DecisionCollegeSourceModel,
    DecisionEmploymentOutlookModel,
    DecisionProgramCareerPathModel,
    DecisionProgramDecisionProfileModel,
    DecisionProgramModel,
    DecisionProgramTraitModel,
    DecisionTrainingAndPracticeModel,
)
from app.infrastructure.db.session import SessionLocal

LOGGER = logging.getLogger("scripts.ingest_normalized_colleges_v2")

DEFAULT_DATA_DIR = ROOT_DIR.parent / "normalized_college_v2"
EXPECTED_SCHEMA_VERSION = "college_normalized_v2"
EXCLUDED_FILE_NAMES = {
    "_progress.json",
    "fees.normalized.v2.json",
    "tuition_fees_2025_2026.normalized.v2.json",
}

PROGRAM_DECISION_PROFILE_FIELDS = (
    "theoretical_depth",
    "math_intensity",
    "physics_intensity",
    "programming_intensity",
    "design_creativity",
    "lab_intensity",
    "field_work_intensity",
    "management_exposure",
    "workload_difficulty",
    "career_flexibility",
    "ai_focus",
    "data_focus",
    "software_focus",
    "security_focus",
    "hardware_focus",
    "business_focus",
    "finance_focus",
    "logistics_focus",
    "maritime_focus",
    "healthcare_focus",
    "creativity_design_focus",
    "language_communication_focus",
    "law_policy_focus",
    "research_orientation",
    "entrepreneurship_focus",
    "international_work_readiness",
    "remote_work_fit",
    "biology_focus",
    "energy_sector_focus",
    "international_trade_focus",
    "transport_operations_focus",
)

COLLEGE_LEVEL_PROFILE_SCORE_FIELDS = (
    "theoretical_depth",
    "math_intensity",
    "practical_intensity",
    "field_work_intensity",
    "research_orientation",
    "career_flexibility",
)


class IngestionValidationError(ValueError):
    """Raised when a single file fails validation or normalization."""


class SkipFile(Exception):
    """Raised when a file is intentionally skipped by CLI filters."""

    def __init__(self, message: str, college_id: str | None = None) -> None:
        super().__init__(message)
        self.college_id = college_id


@dataclass
class FailureRecord:
    file_name: str
    college_id: str | None
    error_message: str


@dataclass
class IngestionSummary:
    total_files_discovered: int = 0
    total_files_processed: int = 0
    skipped_files: int = 0
    succeeded_files: int = 0
    failed_files: int = 0
    total_colleges_imported: int = 0
    total_programs_imported: int = 0
    failures: list[FailureRecord] = field(default_factory=list)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest normalized college v2 JSON files into decision_* tables."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing *.normalized.v2.json files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and stage inserts without committing any database changes.",
    )
    parser.add_argument(
        "--only-college-id",
        type=str,
        default=None,
        help="Process only the specified college_id.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of files to process after filtering.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    return args


def discover_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists() or not data_dir.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    files = sorted(data_dir.glob("*.normalized.v2.json"), key=lambda path: path.name.lower())
    return [
        path
        for path in files
        if path.name.lower() not in EXCLUDED_FILE_NAMES
    ]


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise IngestionValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise IngestionValidationError("Root JSON value must be an object")

    return payload


def extract_college_id(payload: dict[str, Any]) -> str | None:
    entity = payload.get("entity")
    if not isinstance(entity, dict):
        return None

    college_id = entity.get("college_id")
    if not isinstance(college_id, str):
        return None

    college_id = college_id.strip()
    return college_id or None


def validate_root(payload: dict[str, Any]) -> tuple[str, str]:
    schema_version = payload.get("schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise IngestionValidationError(
            f"schema_version must be {EXPECTED_SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    entity = ensure_dict(payload.get("entity"), "entity")
    college_id = normalize_required_string(entity.get("college_id"), "entity.college_id")
    college_name = normalize_required_string(entity.get("college_name"), "entity.college_name")
    return college_id, college_name


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


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise IngestionValidationError(f"{field_name} must be a non-empty string")
    normalized = collapse_whitespace(value)
    if not normalized:
        raise IngestionValidationError(f"{field_name} must be a non-empty string")
    return normalized


def normalize_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise IngestionValidationError(f"{field_name} must be a string or null")
    normalized = collapse_whitespace(value)
    return normalized or None


def normalize_text_value(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = collapse_whitespace(value)
        return normalized or None
    if isinstance(value, list):
        parts = normalize_string_list(value, field_name)
        return " ".join(parts) if parts else None
    raise IngestionValidationError(f"{field_name} must be a string, list, or null")


def normalize_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = collapse_whitespace(value)
        return [normalized] if normalized else []
    if not isinstance(value, list):
        raise IngestionValidationError(f"{field_name} must be a string, list, or null")

    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise IngestionValidationError(
                f"{field_name}[{index}] must be a string, got {type(item).__name__}"
            )
        normalized = collapse_whitespace(item)
        if normalized:
            items.append(normalized)
    return items


def normalize_optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise IngestionValidationError(f"{field_name} must be a boolean or null")


def coerce_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise IngestionValidationError(f"{field_name} must be an integer or null")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return int(normalized)
        except ValueError as exc:
            raise IngestionValidationError(
                f"{field_name} must be coercible to int"
            ) from exc
    raise IngestionValidationError(f"{field_name} must be coercible to int")


def coerce_decimal(
    value: Any,
    field_name: str,
    *,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise IngestionValidationError(f"{field_name} must be numeric or null")

    if isinstance(value, Decimal):
        decimal_value = value
    else:
        try:
            decimal_value = Decimal(str(value).strip())
        except (InvalidOperation, AttributeError) as exc:
            raise IngestionValidationError(
                f"{field_name} must be coercible to Decimal"
            ) from exc

    if minimum is not None and decimal_value < minimum:
        raise IngestionValidationError(
            f"{field_name} must be between {minimum} and {maximum}"
        )
    if maximum is not None and decimal_value > maximum:
        raise IngestionValidationError(
            f"{field_name} must be between {minimum} and {maximum}"
        )

    return decimal_value


def normalize_optional_datetime(value: Any, field_name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        raise IngestionValidationError(f"{field_name} must be an ISO-8601 string or null")

    normalized = value.strip()
    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IngestionValidationError(f"{field_name} must be a valid datetime") from exc

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def stringify_optional(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = collapse_whitespace(value)
        return normalized or None
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return str(value)
    raise IngestionValidationError(f"{field_name} must be a scalar value or null")


def has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def normalize_program_name(value: Any, field_name: str) -> str:
    return normalize_required_string(value, field_name)


def build_program_name_token(program_name: str) -> str:
    token = program_name.strip().upper()
    token = re.sub(r"[\s-]+", "_", token)
    token = re.sub(r"[^A-Z0-9_]", "", token)
    token = re.sub(r"_+", "_", token)
    token = token.strip("_")
    if not token:
        raise IngestionValidationError(
            f"Program name {program_name!r} does not yield a valid normalized token"
        )
    return token


def generate_program_id(college_id: str, program_name: str) -> str:
    return f"{college_id}__{build_program_name_token(program_name)}"


def build_college_model(payload: dict[str, Any]) -> tuple[DecisionCollegeModel, int]:
    college_id, college_name = validate_root(payload)

    entity = ensure_dict(payload.get("entity"), "entity")
    source_data = ensure_dict(payload.get("source"), "source")
    official_data = ensure_dict(payload.get("official_data"), "official_data")
    decision_support = ensure_dict(payload.get("decision_support"), "decision_support")

    location = ensure_dict(official_data.get("location"), "official_data.location")
    establishment = ensure_dict(
        official_data.get("establishment"),
        "official_data.establishment",
    )
    overview = ensure_dict(official_data.get("overview"), "official_data.overview")
    vision_mission = ensure_dict(
        official_data.get("vision_mission"),
        "official_data.vision_mission",
    )

    programs = build_program_models(
        college_id=college_id,
        raw_program_profiles=decision_support.get("program_profiles"),
    )

    college = DecisionCollegeModel(
        id=college_id,
        schema_version=EXPECTED_SCHEMA_VERSION,
        entity_type=normalize_required_string(entity.get("entity_type"), "entity.entity_type"),
        college_name=college_name,
        city=normalize_optional_string(location.get("city"), "official_data.location.city"),
        country=normalize_optional_string(
            location.get("country"),
            "official_data.location.country",
        ),
        branch=normalize_optional_string(location.get("branch"), "official_data.location.branch"),
        year_established=coerce_int(
            establishment.get("year_established"),
            "official_data.establishment.year_established",
        ),
        parent_institution=normalize_optional_string(
            establishment.get("parent_institution"),
            "official_data.establishment.parent_institution",
        ),
        short_description=normalize_text_value(
            overview.get("short_description"),
            "official_data.overview.short_description",
        ),
        current_status=normalize_text_value(
            overview.get("current_status"),
            "official_data.overview.current_status",
        ),
        future_prospectus=normalize_text_value(
            overview.get("future_prospectus"),
            "official_data.overview.future_prospectus",
        ),
        vision=normalize_text_value(
            vision_mission.get("vision"),
            "official_data.vision_mission.vision",
        ),
        mission=normalize_text_value(
            vision_mission.get("mission"),
            "official_data.vision_mission.mission",
        ),
        source=build_college_source(college_id, source_data),
        leadership_entries=build_leadership_entries(
            college_id,
            official_data.get("leadership"),
        ),
        programs=programs,
        level_profile=build_college_level_profile(
            college_id,
            decision_support.get("college_level_profile"),
        ),
        training_and_practice=build_training_and_practice(
            college_id,
            official_data.get("training_and_practice"),
        ),
        admission_requirement=build_admission_requirement(
            college_id,
            official_data.get("admission_requirements"),
        ),
        accreditations=build_accreditations(
            college_id,
            official_data.get("accreditation"),
        ),
        facilities=build_facilities(
            college_id,
            official_data.get("facilities_and_resources"),
        ),
        research_focus_items=build_research_focus_items(
            college_id,
            official_data.get("research_and_innovation"),
        ),
        mobility=build_college_mobility(
            college_id,
            official_data.get("international_mobility"),
        ),
    )
    return college, len(programs)


def build_college_source(
    college_id: str,
    source_data: dict[str, Any],
) -> DecisionCollegeSourceModel | None:
    generated_at = normalize_optional_datetime(source_data.get("generated_at"), "source.generated_at")
    input_path = normalize_optional_string(source_data.get("input_path"), "source.input_path")
    source_file_name = normalize_optional_string(
        source_data.get("source_file_name"),
        "source.source_file_name",
    )

    if not any(has_meaningful_value(value) for value in (generated_at, input_path, source_file_name)):
        return None

    return DecisionCollegeSourceModel(
        college_id=college_id,
        generated_at=generated_at,
        input_path=input_path,
        source_file_name=source_file_name,
    )


def build_leadership_entries(
    college_id: str,
    raw_leadership: Any,
) -> list[DecisionCollegeLeadershipModel]:
    entries = ensure_list(raw_leadership, "official_data.leadership")
    models: list[DecisionCollegeLeadershipModel] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            leader_name, leader_title = normalize_leadership_string(
                entry,
                f"official_data.leadership[{index}]",
            )
            models.append(
                DecisionCollegeLeadershipModel(
                    college_id=college_id,
                    leader_name=leader_name,
                    leader_title=leader_title,
                    period=None,
                    sort_order=index,
                )
            )
            continue

        item = ensure_dict(entry, f"official_data.leadership[{index}]")
        models.append(
            DecisionCollegeLeadershipModel(
                college_id=college_id,
                leader_name=normalize_required_string(
                    item.get("name"),
                    f"official_data.leadership[{index}].name",
                ),
                leader_title=normalize_optional_string(
                    item.get("title"),
                    f"official_data.leadership[{index}].title",
                ),
                period=normalize_optional_string(
                    item.get("period"),
                    f"official_data.leadership[{index}].period",
                ),
                sort_order=index,
            )
        )
    return models


def normalize_leadership_string(value: str, field_name: str) -> tuple[str, str | None]:
    normalized = normalize_required_string(value, field_name)
    parts = re.split(r"\s[–-]\s", normalized, maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return normalized, None


def build_college_level_profile(
    college_id: str,
    raw_profile: Any,
) -> DecisionCollegeLevelProfileModel | None:
    profile = ensure_dict(raw_profile, "decision_support.college_level_profile")
    if not profile:
        return None

    egypt_employability = ensure_dict(
        profile.get("egypt_employability"),
        "decision_support.college_level_profile.egypt_employability",
    )
    international_employability = ensure_dict(
        profile.get("international_employability"),
        "decision_support.college_level_profile.international_employability",
    )
    mobility_strength = ensure_dict(
        profile.get("international_mobility_strength"),
        "decision_support.college_level_profile.international_mobility_strength",
    )

    kwargs = {
        field: coerce_decimal(
            profile.get(field),
            f"decision_support.college_level_profile.{field}",
            minimum=Decimal("0"),
            maximum=Decimal("10"),
        )
        for field in COLLEGE_LEVEL_PROFILE_SCORE_FIELDS
    }
    kwargs.update(
        {
            "college_id": college_id,
            "egypt_employability_level": stringify_optional(
                egypt_employability.get("level"),
                "decision_support.college_level_profile.egypt_employability.level",
            ),
            "egypt_employability_score": coerce_decimal(
                egypt_employability.get("score"),
                "decision_support.college_level_profile.egypt_employability.score",
                minimum=Decimal("0"),
                maximum=Decimal("10"),
            ),
            "international_employability_level": stringify_optional(
                international_employability.get("level"),
                "decision_support.college_level_profile.international_employability.level",
            ),
            "international_employability_score": coerce_decimal(
                international_employability.get("score"),
                "decision_support.college_level_profile.international_employability.score",
                minimum=Decimal("0"),
                maximum=Decimal("10"),
            ),
            "international_mobility_strength_level": stringify_optional(
                mobility_strength.get("level"),
                "decision_support.college_level_profile.international_mobility_strength.level",
            ),
            "international_mobility_strength_label": normalize_optional_string(
                mobility_strength.get("label"),
                "decision_support.college_level_profile.international_mobility_strength.label",
            ),
            "international_mobility_strength_score": coerce_decimal(
                mobility_strength.get("score"),
                "decision_support.college_level_profile.international_mobility_strength.score",
                minimum=Decimal("0"),
                maximum=Decimal("10"),
            ),
        }
    )

    return DecisionCollegeLevelProfileModel(**kwargs)


def build_training_and_practice(
    college_id: str,
    raw_training: Any,
) -> DecisionTrainingAndPracticeModel | None:
    training = ensure_dict(raw_training, "official_data.training_and_practice")
    if not training:
        return None

    mandatory_training = normalize_optional_bool(
        training.get("mandatory_training"),
        "official_data.training_and_practice.mandatory_training",
    )
    industry_training = normalize_optional_bool(
        training.get("industry_training"),
        "official_data.training_and_practice.industry_training",
    )
    field_or_sea_training = normalize_optional_bool(
        training.get("field_or_sea_training"),
        "official_data.training_and_practice.field_or_sea_training",
    )
    description = normalize_text_value(
        training.get("description"),
        "official_data.training_and_practice.description",
    )

    if not any(
        has_meaningful_value(value)
        for value in (
            mandatory_training,
            industry_training,
            field_or_sea_training,
            description,
        )
    ):
        return None

    return DecisionTrainingAndPracticeModel(
        college_id=college_id,
        mandatory_training=mandatory_training,
        industry_training=industry_training,
        field_or_sea_training=field_or_sea_training,
        description=description,
    )


def build_admission_requirement(
    college_id: str,
    raw_admission: Any,
) -> DecisionAdmissionRequirementModel | None:
    admission = ensure_dict(raw_admission, "official_data.admission_requirements")
    if not admission:
        return None

    accepted_certificates = normalize_string_list(
        admission.get("accepted_certificates"),
        "official_data.admission_requirements.accepted_certificates",
    )
    other_conditions = normalize_text_value(
        admission.get("other_conditions"),
        "official_data.admission_requirements.other_conditions",
    )
    entry_exams_required = normalize_optional_bool(
        admission.get("entry_exams_required"),
        "official_data.admission_requirements.entry_exams_required",
    )
    medical_fitness_required = normalize_optional_bool(
        admission.get("medical_fitness_required"),
        "official_data.admission_requirements.medical_fitness_required",
    )
    age_limit = coerce_int(
        admission.get("age_limit"),
        "official_data.admission_requirements.age_limit",
    )

    if not any(
        has_meaningful_value(value)
        for value in (
            entry_exams_required,
            medical_fitness_required,
            age_limit,
            other_conditions,
            accepted_certificates,
        )
    ):
        return None

    requirement = DecisionAdmissionRequirementModel(
        college_id=college_id,
        entry_exams_required=entry_exams_required,
        medical_fitness_required=medical_fitness_required,
        age_limit=age_limit,
        other_conditions=other_conditions,
        accepted_certificates=[
            DecisionAcceptedCertificateModel(
                certificate_name=certificate_name,
                sort_order=index,
            )
            for index, certificate_name in enumerate(accepted_certificates)
        ],
    )
    return requirement


def build_accreditations(
    college_id: str,
    raw_accreditation: Any,
) -> list[DecisionCollegeAccreditationModel]:
    accreditation = ensure_dict(raw_accreditation, "official_data.accreditation")
    national_items = normalize_string_list(
        accreditation.get("national"),
        "official_data.accreditation.national",
    )
    international_items = normalize_string_list(
        accreditation.get("international"),
        "official_data.accreditation.international",
    )

    models: list[DecisionCollegeAccreditationModel] = []
    for scope, items in (("national", national_items), ("international", international_items)):
        for index, item_text in enumerate(items):
            models.append(
                DecisionCollegeAccreditationModel(
                    college_id=college_id,
                    accreditation_scope=scope,
                    accreditation_text=item_text,
                    sort_order=index,
                )
            )
    return models


def build_facilities(
    college_id: str,
    raw_facilities: Any,
) -> list[DecisionCollegeFacilityModel]:
    raw_items = ensure_list(raw_facilities, "official_data.facilities_and_resources")
    facilities = [
        normalize_facility_text(item, f"official_data.facilities_and_resources[{index}]")
        for index, item in enumerate(raw_items)
    ]
    return [
        DecisionCollegeFacilityModel(
            college_id=college_id,
            facility_text=item,
            sort_order=index,
        )
        for index, item in enumerate(facilities)
    ]


def normalize_facility_text(value: Any, field_name: str) -> str:
    if isinstance(value, str):
        return normalize_required_string(value, field_name)

    item = ensure_dict(value, field_name)
    name = normalize_optional_string(item.get("name"), f"{field_name}.name")
    features = normalize_string_list(item.get("features"), f"{field_name}.features")

    if name and features:
        return f"{name}: {'; '.join(features)}"
    if name:
        return name
    if features:
        return "; ".join(features)

    raise IngestionValidationError(f"{field_name} must include a facility name or features")


def build_research_focus_items(
    college_id: str,
    raw_research_and_innovation: Any,
) -> list[DecisionCollegeResearchFocusModel]:
    research_and_innovation = ensure_dict(
        raw_research_and_innovation,
        "official_data.research_and_innovation",
    )
    research_focus = normalize_string_list(
        research_and_innovation.get("research_focus"),
        "official_data.research_and_innovation.research_focus",
    )
    return [
        DecisionCollegeResearchFocusModel(
            college_id=college_id,
            research_focus_text=item,
            sort_order=index,
        )
        for index, item in enumerate(research_focus)
    ]


def build_college_mobility(
    college_id: str,
    raw_mobility: Any,
) -> DecisionCollegeMobilityModel | None:
    mobility = ensure_dict(raw_mobility, "official_data.international_mobility")
    if not mobility:
        return None

    available = normalize_optional_bool(
        mobility.get("available"),
        "official_data.international_mobility.available",
    )
    mobility_types = normalize_string_list(
        mobility.get("mobility_types"),
        "official_data.international_mobility.mobility_types",
    )
    partner_bodies = normalize_string_list(
        mobility.get("partner_bodies"),
        "official_data.international_mobility.partner_bodies",
    )
    regions = normalize_string_list(
        mobility.get("regions"),
        "official_data.international_mobility.regions",
    )
    evidence_notes = normalize_string_list(
        mobility.get("evidence_based_notes"),
        "official_data.international_mobility.evidence_based_notes",
    )

    if not any(
        has_meaningful_value(value)
        for value in (
            available,
            mobility_types,
            partner_bodies,
            regions,
            evidence_notes,
        )
    ):
        return None

    items: list[DecisionCollegeMobilityItemModel] = []
    for item_type, values in (
        ("mobility_type", mobility_types),
        ("partner_body", partner_bodies),
        ("region", regions),
        ("evidence_note", evidence_notes),
    ):
        for index, item_text in enumerate(values):
            items.append(
                DecisionCollegeMobilityItemModel(
                    item_type=item_type,
                    item_text=item_text,
                    sort_order=index,
                )
            )

    return DecisionCollegeMobilityModel(
        college_id=college_id,
        available=available,
        items=items,
    )


def build_program_models(
    *,
    college_id: str,
    raw_program_profiles: Any,
) -> list[DecisionProgramModel]:
    profiles = ensure_list(raw_program_profiles, "decision_support.program_profiles")
    programs: list[DecisionProgramModel] = []
    seen_program_ids: set[str] = set()
    seen_program_names: set[str] = set()

    for index, raw_profile in enumerate(profiles):
        profile = ensure_dict(raw_profile, f"decision_support.program_profiles[{index}]")
        program_name = normalize_program_name(
            profile.get("program_name"),
            f"decision_support.program_profiles[{index}].program_name",
        )
        program_name_key = program_name.upper()
        if program_name_key in seen_program_names:
            raise IngestionValidationError(
                f"Duplicate normalized program_name {program_name!r} in college {college_id}"
            )
        seen_program_names.add(program_name_key)

        program_id = generate_program_id(college_id, program_name)
        if program_id in seen_program_ids:
            raise IngestionValidationError(
                f"Duplicate generated program_id {program_id!r} in college {college_id}"
            )
        seen_program_ids.add(program_id)

        decision_profile = profile.get("decision_profile")
        if decision_profile is None:
            raise IngestionValidationError(
                f"decision_support.program_profiles[{index}].decision_profile is required"
            )

        program = DecisionProgramModel(
            id=program_id,
            college_id=college_id,
            program_name=program_name,
            program_family=normalize_optional_string(
                profile.get("program_family"),
                f"decision_support.program_profiles[{index}].program_family",
            ),
            degree_type=normalize_optional_string(
                profile.get("degree_type"),
                f"decision_support.program_profiles[{index}].degree_type",
            ),
            study_duration_years=coerce_decimal(
                profile.get("study_duration_years"),
                f"decision_support.program_profiles[{index}].study_duration_years",
            ),
            summary=normalize_text_value(
                profile.get("summary"),
                f"decision_support.program_profiles[{index}].summary",
            ),
            differentiation_notes=normalize_text_value(
                profile.get("differentiation_notes"),
                f"decision_support.program_profiles[{index}].differentiation_notes",
            ),
            decision_profile=build_program_decision_profile(
                decision_profile,
                program_id,
                index,
            ),
            career_paths=build_program_career_paths(
                profile.get("career_paths"),
                program_id,
                index,
            ),
            traits=build_program_traits(
                profile,
                program_id,
                index,
            ),
            employment_outlook=build_employment_outlook(
                profile.get("employment_outlook"),
                program_id,
                index,
            ),
        )
        programs.append(program)

    return programs


def build_program_decision_profile(
    raw_profile: Any,
    program_id: str,
    program_index: int,
) -> DecisionProgramDecisionProfileModel:
    profile = ensure_dict(
        raw_profile,
        f"decision_support.program_profiles[{program_index}].decision_profile",
    )
    if not profile:
        raise IngestionValidationError(
            f"decision_support.program_profiles[{program_index}].decision_profile is required"
        )

    kwargs = {
        field: coerce_decimal(
            profile.get(field),
            f"decision_support.program_profiles[{program_index}].decision_profile.{field}",
            minimum=Decimal("0"),
            maximum=Decimal("10"),
        )
        for field in PROGRAM_DECISION_PROFILE_FIELDS
    }
    kwargs["program_id"] = program_id
    return DecisionProgramDecisionProfileModel(**kwargs)


def build_program_career_paths(
    raw_career_paths: Any,
    program_id: str,
    program_index: int,
) -> list[DecisionProgramCareerPathModel]:
    career_paths = normalize_string_list(
        raw_career_paths,
        f"decision_support.program_profiles[{program_index}].career_paths",
    )
    return [
        DecisionProgramCareerPathModel(
            program_id=program_id,
            career_title=career_title,
            sort_order=index,
        )
        for index, career_title in enumerate(career_paths)
    ]


def build_program_traits(
    profile: dict[str, Any],
    program_id: str,
    program_index: int,
) -> list[DecisionProgramTraitModel]:
    models: list[DecisionProgramTraitModel] = []
    trait_fields = (
        ("best_fit", "best_fit_traits"),
        ("avoid_if", "avoid_if"),
        ("close_alternative", "close_alternatives"),
    )

    for trait_type, source_field in trait_fields:
        items = normalize_string_list(
            profile.get(source_field),
            f"decision_support.program_profiles[{program_index}].{source_field}",
        )
        for index, trait_text in enumerate(items):
            models.append(
                DecisionProgramTraitModel(
                    program_id=program_id,
                    trait_type=trait_type,
                    trait_text=trait_text,
                    sort_order=index,
                )
            )

    return models


def build_employment_outlook(
    raw_outlook: Any,
    program_id: str,
    program_index: int,
) -> DecisionEmploymentOutlookModel | None:
    outlook = ensure_dict(
        raw_outlook,
        f"decision_support.program_profiles[{program_index}].employment_outlook",
    )
    if not outlook:
        return None

    egypt_market = ensure_dict(
        outlook.get("egypt_market"),
        f"decision_support.program_profiles[{program_index}].employment_outlook.egypt_market",
    )
    international_market = ensure_dict(
        outlook.get("international_market"),
        "decision_support.program_profiles"
        f"[{program_index}].employment_outlook.international_market",
    )

    egypt_market_level = stringify_optional(
        egypt_market.get("level"),
        f"decision_support.program_profiles[{program_index}].employment_outlook.egypt_market.level",
    )
    egypt_market_label = normalize_optional_string(
        egypt_market.get("label"),
        f"decision_support.program_profiles[{program_index}].employment_outlook.egypt_market.label",
    )
    egypt_market_score = coerce_decimal(
        egypt_market.get("score"),
        f"decision_support.program_profiles[{program_index}].employment_outlook.egypt_market.score",
        minimum=Decimal("0"),
        maximum=Decimal("10"),
    )
    international_market_level = stringify_optional(
        international_market.get("level"),
        "decision_support.program_profiles"
        f"[{program_index}].employment_outlook.international_market.level",
    )
    international_market_label = normalize_optional_string(
        international_market.get("label"),
        "decision_support.program_profiles"
        f"[{program_index}].employment_outlook.international_market.label",
    )
    international_market_score = coerce_decimal(
        international_market.get("score"),
        "decision_support.program_profiles"
        f"[{program_index}].employment_outlook.international_market.score",
        minimum=Decimal("0"),
        maximum=Decimal("10"),
    )

    if not any(
        has_meaningful_value(value)
        for value in (
            egypt_market_level,
            egypt_market_label,
            egypt_market_score,
            international_market_level,
            international_market_label,
            international_market_score,
        )
    ):
        return None

    return DecisionEmploymentOutlookModel(
        program_id=program_id,
        egypt_market_level=egypt_market_level,
        egypt_market_label=egypt_market_label,
        egypt_market_score=egypt_market_score,
        international_market_level=international_market_level,
        international_market_label=international_market_label,
        international_market_score=international_market_score,
    )


def ingest_file(
    *,
    path: Path,
    dry_run: bool,
    only_college_id: str | None,
) -> tuple[str, int]:
    payload = load_json_file(path)
    validated_college_id, _ = validate_root(payload)

    if only_college_id is not None and validated_college_id.upper() != only_college_id.upper():
        raise SkipFile(
            f"Skipping because college_id {validated_college_id!r} does not match filter",
            college_id=validated_college_id,
        )

    college_model, program_count = build_college_model(payload)

    with SessionLocal() as session:
        try:
            existing = session.get(DecisionCollegeModel, validated_college_id)
            if existing is not None:
                session.delete(existing)
                session.flush()

            session.add(college_model)
            session.flush()

            if dry_run:
                session.rollback()
            else:
                session.commit()
        except Exception:
            session.rollback()
            raise

    return validated_college_id, program_count


def record_failure(
    summary: IngestionSummary,
    *,
    file_name: str,
    college_id: str | None,
    error_message: str,
) -> None:
    summary.failed_files += 1
    summary.failures.append(
        FailureRecord(
            file_name=file_name,
            college_id=college_id,
            error_message=error_message,
        )
    )


def print_summary(summary: IngestionSummary, *, dry_run: bool) -> None:
    print(f"total_files_discovered: {summary.total_files_discovered}")
    print(f"total_files_processed: {summary.total_files_processed}")
    print(f"skipped_files: {summary.skipped_files}")
    print(f"succeeded_files: {summary.succeeded_files}")
    print(f"failed_files: {summary.failed_files}")
    print(f"total_colleges_imported: {summary.total_colleges_imported}")
    print(f"total_programs_imported: {summary.total_programs_imported}")

    if dry_run:
        print("mode: dry-run (counts reflect validated records that would be imported)")

    if summary.failures:
        print("failures:")
        for failure in summary.failures:
            print(
                "- "
                f"file={failure.file_name} "
                f"college_id={failure.college_id or 'unknown'} "
                f"error={failure.error_message}"
            )


def run_ingestion(args: argparse.Namespace) -> IngestionSummary:
    files = discover_files(args.data_dir)
    summary = IngestionSummary(total_files_discovered=len(files))

    visited_count = 0
    for path in files:
        if args.limit is not None and summary.total_files_processed >= args.limit:
            break

        visited_count += 1
        try:
            college_id, program_count = ingest_file(
                path=path,
                dry_run=args.dry_run,
                only_college_id=args.only_college_id,
            )
        except SkipFile as exc:
            summary.skipped_files += 1
            LOGGER.info("%s: %s", path.name, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            summary.total_files_processed += 1
            college_id = None
            try:
                college_id = extract_college_id(load_json_file(path))
            except Exception:  # noqa: BLE001
                pass
            record_failure(
                summary,
                file_name=path.name,
                college_id=college_id,
                error_message=str(exc),
            )
            LOGGER.error("%s failed: %s", path.name, exc)
            continue

        summary.total_files_processed += 1
        summary.succeeded_files += 1
        summary.total_colleges_imported += 1
        summary.total_programs_imported += program_count

        action = "validated" if args.dry_run else "imported"
        LOGGER.info(
            "%s %s (%s) with %s programs",
            action.capitalize(),
            path.name,
            college_id,
            program_count,
        )

    summary.skipped_files += max(0, len(files) - visited_count)
    return summary


def main() -> int:
    configure_logging()
    args = parse_args()
    summary = run_ingestion(args)
    print_summary(summary, dry_run=args.dry_run)
    return 1 if summary.failed_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
