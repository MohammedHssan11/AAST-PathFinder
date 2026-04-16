from __future__ import annotations

import copy
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from app.domain.entities.decision_schema import DecisionSchema


MASTER_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "schema" / "decision_schema_v1.json"

QUALITATIVE_TO_NUMERIC: dict[str, float] = {
    "very_low": 0.2,
    "low": 0.35,
    "low_medium": 0.45,
    "medium": 0.5,
    "medium_low": 0.45,
    "medium_high": 0.65,
    "high": 0.8,
    "very_high": 0.9,
    "critical": 1.0,
    "mandatory": 1.0,
    "strong": 0.8,
    "weak": 0.3,
}


def normalize_college_file(input_path: Path) -> dict:
    template = _load_master_template()
    raw_payload = json.loads(input_path.read_text(encoding="utf-8"))

    normalized = {
        "version": template["version"],
        "source": copy.deepcopy(template["source"]),
        "campus": copy.deepcopy(template["campus"]),
        "college": copy.deepcopy(template["college"]),
        "programs": [],
    }

    normalized["source"] = _build_source(raw_payload, input_path.name)
    normalized["campus"] = _build_campus(raw_payload)
    normalized["college"] = _build_college(raw_payload, input_path.stem)

    program_template = template["programs"][0]
    candidates = _extract_program_candidates(raw_payload)

    programs: list[dict] = []
    seen_program_ids: set[str] = set()

    for candidate in candidates:
        program_data = _build_program_from_candidate(
            candidate=candidate,
            raw_payload=raw_payload,
            program_template=program_template,
            college_id=normalized["college"]["college_id"],
        )

        base_program_id = program_data["program_id"]
        if base_program_id in seen_program_ids:
            suffix = 2
            while f"{base_program_id}_{suffix}" in seen_program_ids:
                suffix += 1
            program_data["program_id"] = f"{base_program_id}_{suffix}"

        seen_program_ids.add(program_data["program_id"])
        programs.append(program_data)

    normalized["programs"] = programs

    try:
        validated = DecisionSchema.model_validate(normalized)
    except ValidationError as exc:
        details = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []))
            details.append(f"{loc}: {err.get('msg', 'invalid value')}")
        detail_text = "; ".join(details)
        raise ValueError(f"{input_path.name}: validation failed - {detail_text}") from exc

    return validated.model_dump(mode="json")


def normalize_all_colleges(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in sorted(input_dir.glob("*.json")):
        normalized = normalize_college_file(input_path)

        college_id = _non_empty_string(normalized["college"].get("college_id"))
        output_stem = _safe_filename_token(college_id) if college_id else input_path.stem
        output_path = output_dir / f"{output_stem}.normalized.json"
        output_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def summarize_file_flags(normalized_payload: dict) -> tuple[str, bool]:
    programs = normalized_payload.get("programs", [])
    if not programs:
        return "low", False

    decision_ready = any(
        bool(program.get("system_flags", {}).get("decision_ready"))
        for program in programs
    )

    rank = {"low": 1, "medium": 2, "high": 3}
    values = [
        rank.get(program.get("system_flags", {}).get("data_completeness", "low"), 1)
        for program in programs
    ]

    avg = sum(values) / len(values)
    if avg >= 2.5:
        completeness = "high"
    elif avg >= 1.5:
        completeness = "medium"
    else:
        completeness = "low"

    return completeness, decision_ready


def _load_master_template() -> dict:
    if not MASTER_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Master schema template not found at '{MASTER_TEMPLATE_PATH}'."
        )

    template = json.loads(MASTER_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(template, dict):
        raise ValueError("Master schema template must be a JSON object.")
    return template


def _build_source(raw_payload: Any, file_name: str) -> dict:
    source_type = "official"

    source_section = raw_payload.get("source") if isinstance(raw_payload, dict) else None
    if isinstance(source_section, dict):
        candidate = _non_empty_string(source_section.get("data_source_type"))
        if candidate in {"official", "scraped", "manual"}:
            source_type = candidate

    if source_type == "official" and isinstance(raw_payload, dict):
        for key in ("data_source_type", "source_type"):
            candidate = _non_empty_string(raw_payload.get(key))
            if candidate in {"official", "scraped", "manual"}:
                source_type = candidate
                break

    last_updated = _extract_last_updated(raw_payload)

    return {
        "file_name": file_name,
        "data_source_type": source_type,
        "last_updated": last_updated,
    }


def _build_campus(raw_payload: dict) -> dict:
    campus_template = {
        "campus_id": "",
        "name": "",
        "city": "",
        "country": "Egypt",
    }

    campus_raw = raw_payload.get("campus")
    if isinstance(campus_raw, dict):
        campus_template["campus_id"] = _as_string(campus_raw.get("campus_id"))
        campus_template["name"] = _as_string(campus_raw.get("name"))
        campus_template["city"] = _as_string(campus_raw.get("city"))
        campus_template["country"] = _as_string(campus_raw.get("country")) or "Egypt"
        return campus_template

    location_raw = raw_payload.get("location")
    if isinstance(location_raw, dict):
        campus_template["campus_id"] = _as_string(raw_payload.get("branch"))
        campus_template["name"] = _as_string(location_raw.get("area"))
        campus_template["city"] = _as_string(location_raw.get("city"))
        campus_template["country"] = _as_string(location_raw.get("country")) or "Egypt"
        return campus_template

    graph_context = _extract_graph_context(raw_payload)
    if graph_context:
        campus = graph_context.get("campus")
        if campus:
            campus_template["campus_id"] = _as_string(campus.get("id"))
            props = campus.get("properties", {})
            if isinstance(props, dict):
                campus_template["name"] = _as_string(props.get("name"))
                campus_template["city"] = _as_string(props.get("city"))
                campus_template["country"] = _as_string(props.get("country")) or "Egypt"

    return campus_template


def _build_college(raw_payload: dict, file_stem: str) -> dict:
    college_template = {
        "college_id": "",
        "name": "",
        "parent_institution": "",
        "branch": "",
        "overview": "",
    }

    college_raw = raw_payload.get("college")
    if isinstance(college_raw, dict):
        college_template["college_id"] = _as_string(college_raw.get("college_id"))
        college_template["name"] = _as_string(college_raw.get("name"))
        college_template["parent_institution"] = _as_string(
            college_raw.get("parent_institution")
        )
        college_template["branch"] = _as_string(college_raw.get("branch"))
        college_template["overview"] = _as_string(college_raw.get("overview"))
        if not college_template["overview"]:
            college_template["overview"] = _as_string(college_raw.get("description"))

    if isinstance(raw_payload, dict):
        college_template["college_id"] = (
            college_template["college_id"]
            or _as_string(raw_payload.get("college_id"))
            or file_stem
        )
        college_template["name"] = college_template["name"] or _as_string(
            raw_payload.get("college_name")
        )
        college_template["parent_institution"] = (
            college_template["parent_institution"]
            or _as_string(raw_payload.get("parent_institution"))
            or _as_string(_safe_get(raw_payload, "establishment", "parent_institution"))
        )
        college_template["branch"] = (
            college_template["branch"]
            or _as_string(raw_payload.get("branch"))
            or _as_string(_safe_get(raw_payload, "campus", "branch"))
        )
        college_template["overview"] = (
            college_template["overview"]
            or _as_string(raw_payload.get("overview"))
            or _as_string(_safe_get(raw_payload, "college_identity", "description"))
        )

    graph_context = _extract_graph_context(raw_payload)
    if graph_context:
        college = graph_context.get("college")
        if college:
            props = college.get("properties", {})
            college_template["college_id"] = college_template["college_id"] or _as_string(
                college.get("id")
            )
            if isinstance(props, dict):
                college_template["name"] = college_template["name"] or _as_string(
                    props.get("name")
                )
                college_template["overview"] = college_template["overview"] or _as_string(
                    props.get("description")
                )

    if not college_template["college_id"]:
        college_template["college_id"] = file_stem

    return college_template


def _build_program_from_candidate(
    *,
    candidate: dict,
    raw_payload: dict,
    program_template: dict,
    college_id: str,
) -> dict:
    program = copy.deepcopy(program_template)

    program_name = _as_string(candidate.get("name"))
    level = _normalize_level(
        candidate.get("level")
        or _safe_get(raw_payload, "degree", "level")
        or raw_payload.get("academic_level")
    )

    program["college_id"] = college_id
    program["name"] = program_name
    program["level"] = level

    generated_program_id = _slugify(f"{college_id}_{program_name}_{level}")
    program["program_id"] = generated_program_id or _slugify(program_name) or "program"

    program["discipline"] = _as_string(candidate.get("discipline")).lower() or "unknown"

    duration = _to_int(
        candidate.get("duration_years")
        or candidate.get("study_duration_years")
        or _safe_get(raw_payload, "degree", "duration_years")
    )
    program["duration_years"] = duration

    language = _as_string(candidate.get("teaching_language"))
    if not language:
        language = _as_string(_safe_get(raw_payload, "degree", "teaching_language"))
    if not language:
        language_tracks = _safe_get(raw_payload, "degrees", "language_tracks")
        if isinstance(language_tracks, list) and len(language_tracks) == 1:
            language = _as_string(language_tracks[0])
    program["teaching_language"] = language or "Unknown"

    admission = _extract_admission_rules(raw_payload, candidate)
    program["admission_rules"] = admission

    profile, structured_profile = _extract_decision_profile(raw_payload, candidate)
    program["decision_profile"] = profile

    _set_program_system_flags(
        program=program,
        structured_profile_present=structured_profile,
    )

    return program


def _extract_program_candidates(raw_payload: dict) -> list[dict]:
    candidates: list[dict] = []

    for key in ("programs", "departments_programs"):
        value = raw_payload.get(key)
        if isinstance(value, list):
            for item in value:
                parsed = _program_candidate_from_item(item, level_hint=None)
                if parsed:
                    candidates.append(parsed)

    degrees_programs = raw_payload.get("degrees_programs")
    if isinstance(degrees_programs, dict):
        for level_key, level_programs in degrees_programs.items():
            if isinstance(level_programs, list):
                for item in level_programs:
                    parsed = _program_candidate_from_item(
                        item,
                        level_hint=_normalize_level(level_key),
                    )
                    if parsed:
                        candidates.append(parsed)

    academic_programs = raw_payload.get("academic_programs")
    if isinstance(academic_programs, dict):
        for key in ("majors", "programs", "bachelor_programs"):
            value = academic_programs.get(key)
            if isinstance(value, list):
                for item in value:
                    parsed = _program_candidate_from_item(
                        item,
                        level_hint="Undergraduate",
                    )
                    if parsed:
                        candidates.append(parsed)

    undergraduate_program = raw_payload.get("undergraduate_program")
    if isinstance(undergraduate_program, dict):
        name = _as_string(undergraduate_program.get("program_name"))
        if name:
            candidates.append(
                {
                    "name": name,
                    "level": "Undergraduate",
                }
            )

        majors = undergraduate_program.get("majors")
        if isinstance(majors, list):
            for item in majors:
                parsed = _program_candidate_from_item(item, level_hint="Undergraduate")
                if parsed:
                    candidates.append(parsed)

    graph_context = _extract_graph_context(raw_payload)
    if graph_context:
        for program_node in graph_context.get("program_nodes", []):
            properties = program_node.get("properties", {})
            if not isinstance(properties, dict):
                properties = {}

            level = _resolve_graph_program_level(
                program_node=program_node,
                relationships=graph_context.get("relationships", []),
                node_by_id=graph_context.get("node_by_id", {}),
            )

            candidates.append(
                {
                    "name": _as_string(properties.get("name"))
                    or _as_string(program_node.get("id")),
                    "level": level,
                    "discipline": _as_string(properties.get("discipline")),
                    "study_duration_years": properties.get("duration_years"),
                }
            )

    if not candidates:
        degree_info = raw_payload.get("degree")
        if isinstance(degree_info, dict):
            degree_name = _as_string(degree_info.get("degree_name"))
            if degree_name:
                candidates.append(
                    {
                        "name": degree_name,
                        "level": _normalize_level(degree_info.get("level")),
                        "study_duration_years": degree_info.get("duration_years"),
                    }
                )

    return _deduplicate_candidates(candidates)


def _program_candidate_from_item(item: Any, level_hint: str | None) -> dict | None:
    if isinstance(item, str):
        name = _as_string(item)
        if not name:
            return None
        return {"name": name, "level": level_hint or "Unknown"}

    if not isinstance(item, dict):
        return None

    name = (
        _as_string(item.get("name"))
        or _as_string(item.get("program_name"))
        or _as_string(item.get("major"))
    )
    if not name:
        return None

    level = _normalize_level(item.get("level") or item.get("degree") or level_hint)

    return {
        "name": name,
        "level": level,
        "discipline": _as_string(item.get("discipline")),
        "study_duration_years": item.get("study_duration_years")
        or item.get("duration_years"),
        "teaching_language": item.get("teaching_language") or item.get("language"),
        "study_profile": item.get("study_profile"),
        "pressure_profile": item.get("pressure_profile"),
        "career_outcomes": item.get("career_outcomes"),
        "training": item.get("training"),
        "admission_rules": item.get("admission_rules"),
    }


def _extract_admission_rules(raw_payload: dict, candidate: dict) -> dict:
    source = candidate.get("admission_rules")
    if not isinstance(source, dict):
        source = _safe_get(raw_payload, "admission_requirements")
    if not isinstance(source, dict):
        source = {}

    min_score = _to_float(
        source.get("min_score")
        or source.get("minimum_score")
        or candidate.get("min_score")
        or raw_payload.get("min_score")
    )

    certificate_types = _extract_str_list(
        source.get("certificate_types")
        or source.get("accepted_certificates")
        or raw_payload.get("certificate_types")
    )

    mandatory_subjects = _extract_str_list(
        source.get("mandatory_subjects")
        or source.get("required_subjects")
        or raw_payload.get("mandatory_subjects")
    )

    return {
        "min_score": min_score,
        "certificate_types": certificate_types,
        "mandatory_subjects": mandatory_subjects,
    }


def _extract_decision_profile(raw_payload: dict, candidate: dict) -> tuple[dict, bool]:
    study_profile = candidate.get("study_profile")
    if not isinstance(study_profile, dict):
        study_profile = raw_payload.get("study_profile")
    if not isinstance(study_profile, dict):
        study_profile = {}

    pressure_profile = candidate.get("pressure_profile")
    if not isinstance(pressure_profile, dict):
        pressure_profile = raw_payload.get("pressure_profile")
    if not isinstance(pressure_profile, dict):
        pressure_profile = {}

    training_payload = _extract_training_payload(raw_payload, candidate)
    career_payload = _extract_career_payload(raw_payload, candidate)
    fit_payload = _extract_student_fit_payload(raw_payload, candidate)

    profile = {
        "theoretical_intensity": _to_numeric(study_profile.get("theoretical_intensity")),
        "practical_intensity": _to_numeric(study_profile.get("practical_intensity")),
        "technology_dependency": _to_numeric(
            study_profile.get("technology_dependency")
            or study_profile.get("digital_dependency")
            or study_profile.get("simulation_dependency")
        ),
        "project_dependency": _to_numeric(study_profile.get("project_dependency")),
        "group_work_dependency": _to_numeric(study_profile.get("group_work_dependency")),
        "research_orientation": _to_numeric(
            study_profile.get("research_orientation")
            or study_profile.get("research_exposure")
        ),
        "creative_intensity": _to_numeric(study_profile.get("creative_intensity")),
        "portfolio_dependency": _to_numeric(study_profile.get("portfolio_dependency")),
        "workload_level": _to_numeric(pressure_profile.get("workload_level")),
        "deadline_pressure": _to_numeric(
            pressure_profile.get("deadline_pressure")
            or pressure_profile.get("exam_pressure")
            or pressure_profile.get("clinical_evaluation_pressure")
        ),
        "evaluation_style": _as_string(pressure_profile.get("evaluation_style"))
        or "unknown",
        "failure_risk": _to_numeric(pressure_profile.get("failure_risk")),
        "training": {
            "mandatory_training": _to_bool(training_payload.get("mandatory_training")),
            "industry_training": _to_bool(
                training_payload.get("industry_training")
                if "industry_training" in training_payload
                else training_payload.get("clinical_training")
            ),
            "training_style": _extract_training_style(training_payload),
            "industry_alignment": _to_numeric(
                training_payload.get("industry_alignment")
                or training_payload.get("industry_partnership_strength")
            ),
        },
        "career_outcomes": {
            "common_roles": _extract_str_list(
                career_payload.get("common_roles")
                or career_payload.get("entry_roles")
                or career_payload.get("career_roles")
                or career_payload.get("primary_career_paths")
            ),
            "employment_sectors": _extract_str_list(
                career_payload.get("employment_sectors")
            ),
            "employability_level": _to_numeric(
                career_payload.get("employability_level")
                or career_payload.get("career_growth_potential")
            ),
            "international_mobility": _to_numeric(
                career_payload.get("international_mobility")
                or career_payload.get("international_employability")
            ),
        },
        "student_fit_model": {
            "best_for": _extract_str_list(fit_payload.get("best_for")),
            "less_suitable_for": _extract_str_list(
                fit_payload.get("less_suitable_for")
                or fit_payload.get("not_suitable_for")
            ),
        },
    }

    structured_profile = bool(study_profile) or bool(pressure_profile)
    return profile, structured_profile


def _extract_training_payload(raw_payload: dict, candidate: dict) -> dict:
    candidate_training = candidate.get("training")
    if isinstance(candidate_training, dict):
        return candidate_training

    for key in (
        "training_and_practice",
        "training_and_industry",
        "training_and_industry_exposure",
        "training_and_fieldwork",
        "training_and_industry_engagement",
        "training",
    ):
        value = raw_payload.get(key)
        if isinstance(value, dict):
            return value

    return {}


def _extract_career_payload(raw_payload: dict, candidate: dict) -> dict:
    candidate_career = candidate.get("career_outcomes")
    if isinstance(candidate_career, dict):
        return candidate_career

    value = raw_payload.get("career_outcomes")
    if isinstance(value, dict):
        return value

    return {}


def _extract_student_fit_payload(raw_payload: dict, candidate: dict) -> dict:
    value = candidate.get("student_fit_model")
    if isinstance(value, dict):
        return value

    value = raw_payload.get("student_fit_model")
    if isinstance(value, dict):
        return value

    return {}


def _set_program_system_flags(*, program: dict, structured_profile_present: bool) -> None:
    admission = program["admission_rules"]
    profile = program["decision_profile"]

    has_admission = bool(
        admission.get("min_score") is not None
        or admission.get("certificate_types")
        or admission.get("mandatory_subjects")
    )

    numeric_profile_values = [
        profile.get("theoretical_intensity"),
        profile.get("practical_intensity"),
        profile.get("technology_dependency"),
        profile.get("project_dependency"),
        profile.get("group_work_dependency"),
        profile.get("research_orientation"),
        profile.get("creative_intensity"),
        profile.get("portfolio_dependency"),
        profile.get("workload_level"),
        profile.get("deadline_pressure"),
        profile.get("failure_risk"),
        profile["training"].get("industry_alignment"),
        profile["career_outcomes"].get("employability_level"),
        profile["career_outcomes"].get("international_mobility"),
    ]
    has_numeric_profile = any(value is not None for value in numeric_profile_values)

    decision_ready = bool(has_admission and (has_numeric_profile or structured_profile_present))

    core_numeric_for_comparison = [
        profile.get("workload_level"),
        profile.get("deadline_pressure"),
        profile.get("theoretical_intensity"),
        profile.get("practical_intensity"),
    ]
    comparison_aux = [
        profile["training"].get("industry_alignment"),
        profile["career_outcomes"].get("employability_level"),
        profile["career_outcomes"].get("international_mobility"),
    ]

    supports_cross_comparison = bool(
        all(value is not None for value in core_numeric_for_comparison)
        and any(value is not None for value in comparison_aux)
    )

    completeness_ratio = _program_completeness_ratio(program)
    if completeness_ratio >= 0.65:
        data_completeness = "high"
    elif completeness_ratio >= 0.35:
        data_completeness = "medium"
    else:
        data_completeness = "low"

    program["system_flags"] = {
        "decision_ready": decision_ready,
        "data_completeness": data_completeness,
        "supports_cross_college_comparison": supports_cross_comparison,
    }


def _resolve_graph_program_level(
    *,
    program_node: dict,
    relationships: list[dict],
    node_by_id: dict[str, dict],
) -> str:
    program_id = _as_string(program_node.get("id"))
    for relationship in relationships:
        if relationship.get("type") != "HAS_DEGREE":
            continue
        if _as_string(relationship.get("from")) != program_id:
            continue

        degree_id = _as_string(relationship.get("to"))
        degree_node = node_by_id.get(degree_id)
        if not degree_node:
            continue

        properties = degree_node.get("properties", {})
        if isinstance(properties, dict):
            level = _normalize_level(properties.get("level") or properties.get("name"))
            if level:
                return level

    return "Unknown"


def _extract_graph_context(raw_payload: Any) -> dict | None:
    if not isinstance(raw_payload, dict):
        return None

    nodes = raw_payload.get("nodes")
    relationships = raw_payload.get("relationships")
    if not isinstance(nodes, list) or not isinstance(relationships, list):
        return None

    node_by_id: dict[str, dict] = {}
    campus_node = None
    college_node = None
    program_nodes: list[dict] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_id = _as_string(node.get("id"))
        if node_id:
            node_by_id[node_id] = node

        label = _as_string(node.get("label"))
        if label == "Campus" and campus_node is None:
            campus_node = node
        elif label == "College" and college_node is None:
            college_node = node
        elif label == "Program":
            program_nodes.append(node)

    return {
        "campus": campus_node,
        "college": college_node,
        "program_nodes": program_nodes,
        "relationships": [r for r in relationships if isinstance(r, dict)],
        "node_by_id": node_by_id,
    }


def _extract_last_updated(raw_payload: Any) -> str:
    if isinstance(raw_payload, dict):
        source = raw_payload.get("source")
        if isinstance(source, dict):
            value = _non_empty_string(source.get("last_updated"))
            if value:
                return value

    keys = {
        "last_updated",
        "updated_at",
        "updated_on",
        "update_date",
        "last_modified",
    }

    for key, value in _walk_key_values(raw_payload):
        if key in keys:
            normalized = _non_empty_string(value)
            if normalized:
                return normalized

    return ""


def _walk_key_values(payload: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key), value
            yield from _walk_key_values(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk_key_values(item)


def _deduplicate_candidates(candidates: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for candidate in candidates:
        name = _as_string(candidate.get("name"))
        level = _normalize_level(candidate.get("level"))
        if not name:
            continue

        key = (name.lower(), level.lower())
        if key in seen:
            continue

        seen.add(key)
        candidate["name"] = name
        candidate["level"] = level
        deduped.append(candidate)

    return deduped


def _extract_training_style(training_payload: dict) -> str:
    direct_style = _as_string(training_payload.get("training_style"))
    if direct_style:
        return direct_style

    description = _as_string(training_payload.get("description"))
    if description:
        return description

    for key in ("training_model", "training_methods"):
        value = training_payload.get(key)
        if isinstance(value, list):
            parts = [_as_string(item) for item in value]
            parts = [part for part in parts if part]
            if parts:
                return ", ".join(parts)

    return "unknown"


def _program_completeness_ratio(program: dict) -> float:
    profile = program["decision_profile"]

    fields = [
        program.get("name"),
        None if str(program.get("level", "")).lower() == "unknown" else program.get("level"),
        None
        if str(program.get("discipline", "")).lower() == "unknown"
        else program.get("discipline"),
        program.get("duration_years"),
        None
        if str(program.get("teaching_language", "")).lower() == "unknown"
        else program.get("teaching_language"),
        program["admission_rules"].get("min_score"),
        program["admission_rules"].get("certificate_types"),
        program["admission_rules"].get("mandatory_subjects"),
        profile.get("theoretical_intensity"),
        profile.get("practical_intensity"),
        profile.get("technology_dependency"),
        profile.get("project_dependency"),
        profile.get("group_work_dependency"),
        profile.get("research_orientation"),
        profile.get("creative_intensity"),
        profile.get("portfolio_dependency"),
        profile.get("workload_level"),
        profile.get("deadline_pressure"),
        None if profile.get("evaluation_style") == "unknown" else profile.get("evaluation_style"),
        profile.get("failure_risk"),
        profile["training"].get("mandatory_training"),
        profile["training"].get("industry_training"),
        None
        if profile["training"].get("training_style") == "unknown"
        else profile["training"].get("training_style"),
        profile["training"].get("industry_alignment"),
        profile["career_outcomes"].get("common_roles"),
        profile["career_outcomes"].get("employment_sectors"),
        profile["career_outcomes"].get("employability_level"),
        profile["career_outcomes"].get("international_mobility"),
        profile["student_fit_model"].get("best_for"),
        profile["student_fit_model"].get("less_suitable_for"),
    ]

    filled = sum(1 for field in fields if _is_filled(field))
    return filled / len(fields)


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in {"", "unknown", "n/a", "null"}
    if isinstance(value, list):
        return len(value) > 0
    return True


def _safe_get(payload: Any, *keys: str) -> Any:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_str_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
                return _extract_str_list(parsed)
            except json.JSONDecodeError:
                pass
        return [stripped]

    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            text = _as_string(item)
            if text:
                output.append(text)
        return output

    if isinstance(value, dict):
        output: list[str] = []
        for item in value.values():
            output.extend(_extract_str_list(item))
        return output

    return []


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "mandatory", "required"}:
            return True
        if normalized in {"false", "no", "0", "none", "not_required"}:
            return False

    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+", value)
        if match:
            return int(match.group())
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace("%", "")
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _to_numeric(value: Any) -> float | None:
    numeric = _to_float(value)
    if numeric is not None:
        return numeric

    text = _non_empty_string(value)
    if not text:
        return None

    normalized = (
        text.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("+", "_")
    )
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return QUALITATIVE_TO_NUMERIC.get(normalized)


def _normalize_level(value: Any) -> str:
    text = _non_empty_string(value)
    if not text:
        return "Unknown"

    lowered = text.lower()

    if any(token in lowered for token in ("undergraduate", "bachelor", "bsc", "ba")):
        return "Undergraduate"
    if any(token in lowered for token in ("postgraduate", "master", "msc", "ma", "phd")):
        return "Postgraduate"
    if "certificate" in lowered or "professional" in lowered:
        return "Professional"

    return text


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    return slug


def _safe_filename_token(value: str) -> str:
    safe = re.sub(r"[<>:\\\"/|?*]+", "_", value).strip()
    return safe or "normalized"


def _as_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _non_empty_string(value: Any) -> str:
    text = _as_string(value)
    return text if text else ""
