import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


BASE_DIR = r"C:\Users\mh978\Downloads\college-decision\normalized_college_v2"
TARGET_FILES = [
    "CLC_MIAMI.normalized.v2.json",
    "CLC_SMART_VILLAGE.normalized.v2.json",
    "College_of_Archaeology_and_Cultural_Heritage_South_Valley.normalized.v2.json",
    "College_of_Art_and_Design.normalized.v2.json",
    "College_of_Fisheries_and_Aquaculture_Technology_AbuKir.normalized.v2.json",
]

DEFAULT_CERTIFICATES = [
    "Thanaweia Amma",
    "IGCSE",
    "American Diploma",
    "IB",
    "French Baccalaureate",
    "German Abitur",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def ensure_list(v: Any) -> List[Any]:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def uniq(items: List[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for x in items:
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def dget(data: Any, path: str) -> Any:
    cur = data
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def write_json_atomic(path: str, payload: Dict[str, Any]) -> None:
    temp = f"{path}.tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(temp, path)


def write_text_atomic(path: str, text: str) -> None:
    temp = f"{path}.tmp"
    with open(temp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temp, path)


def log_change(logs: List[Dict[str, Any]], issue: str, field: str, old: Any, new: Any, reason: str) -> None:
    if old == new:
        return
    logs.append(
        {
            "Issue": issue,
            "Field": field,
            "Old Value": old,
            "New Value": new,
            "Reason": reason,
        }
    )


def set_overview(data: Dict[str, Any], file_name: str, issues: List[str], logs: List[Dict[str, Any]]) -> None:
    overview = data.setdefault("official_data", {}).setdefault("overview", {})
    lc = file_name.lower()

    if "clc_" in lc:
        short = "A specialized academic college within AASTMT focusing on language studies, media production, and communication sciences."
        status = "Active undergraduate and postgraduate programs with practical media and communication training."
    elif "art_and_design" in lc:
        short = "A specialized AASTMT college delivering design-oriented education across visual arts, industrial design, and applied creative disciplines."
        status = "Active design programs with studio-based learning, project practice, and industry-linked creative training."
    elif "archaeology_and_cultural_heritage" in lc:
        short = "A specialized academic college focused on archaeology, heritage preservation, and cultural resource studies."
        status = "Active archaeology and heritage programs with fieldwork, conservation practice, and research training."
    elif "fisheries_and_aquaculture" in lc:
        short = "A specialized academic college focused on fisheries science, aquaculture technology, and marine resource management."
        status = "Active fisheries and aquaculture programs with laboratory and field-based practical training."
    else:
        short = "A specialized AASTMT academic college with applied learning pathways."
        status = "Active programs with practical and research-oriented training."

    if is_empty(overview.get("short_description")):
        old = overview.get("short_description")
        overview["short_description"] = short
        issues.append("overview.short_description was null/empty.")
        log_change(
            logs,
            "Missing overview.short_description",
            "official_data.overview.short_description",
            old,
            short,
            "Filled with concise realistic college description.",
        )
    if is_empty(overview.get("current_status")):
        old = overview.get("current_status")
        overview["current_status"] = status
        issues.append("overview.current_status was null/empty.")
        log_change(
            logs,
            "Missing overview.current_status",
            "official_data.overview.current_status",
            old,
            status,
            "Filled with concise realistic current status.",
        )


def set_admission(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    admission = data.setdefault("official_data", {}).setdefault("admission_requirements", {})
    if is_empty(admission.get("accepted_certificates")):
        old = admission.get("accepted_certificates")
        admission["accepted_certificates"] = list(DEFAULT_CERTIFICATES)
        issues.append("admission accepted_certificates empty/null.")
        log_change(
            logs,
            "Empty accepted_certificates",
            "official_data.admission_requirements.accepted_certificates",
            old,
            admission["accepted_certificates"],
            "Filled requested certificate list.",
        )
    if admission.get("entry_exams_required") is None:
        old = admission.get("entry_exams_required")
        admission["entry_exams_required"] = True
        issues.append("entry_exams_required was null.")
        log_change(
            logs,
            "Null entry_exams_required",
            "official_data.admission_requirements.entry_exams_required",
            old,
            True,
            "Set to true per repair policy.",
        )
    if admission.get("medical_fitness_required") is None:
        old = admission.get("medical_fitness_required")
        admission["medical_fitness_required"] = True
        issues.append("medical_fitness_required was null.")
        log_change(
            logs,
            "Null medical_fitness_required",
            "official_data.admission_requirements.medical_fitness_required",
            old,
            True,
            "Set to true per repair policy.",
        )
    if admission.get("age_limit") is None:
        old = admission.get("age_limit")
        admission["age_limit"] = 22
        issues.append("age_limit was null.")
        log_change(
            logs,
            "Null age_limit",
            "official_data.admission_requirements.age_limit",
            old,
            22,
            "Set to 22 per repair policy.",
        )


def ensure_facilities(data: Dict[str, Any], file_name: str, issues: List[str], logs: List[Dict[str, Any]]) -> None:
    facilities = data.setdefault("official_data", {}).setdefault("facilities_and_resources", [])
    if not isinstance(facilities, list):
        old = facilities
        facilities = []
        data["official_data"]["facilities_and_resources"] = facilities
        issues.append("facilities_and_resources had invalid type.")
        log_change(
            logs,
            "Invalid facilities_and_resources type",
            "official_data.facilities_and_resources",
            old,
            facilities,
            "Normalized to list type.",
        )

    lc = file_name.lower()
    required: List[str] = []
    if "clc_" in lc:
        required = ["TV studios", "Radio studios", "Editing labs", "Language labs", "Computer labs"]
    elif "art_and_design" in lc:
        required = ["Design studios", "Creative workshops", "Prototyping labs", "Digital design labs"]
    elif "fisheries_and_aquaculture" in lc:
        required = ["Aquaculture laboratories", "Marine biology labs", "Water quality labs", "Fish processing labs"]

    old = list(facilities)
    existing = {str(x).strip().lower() for x in facilities if isinstance(x, str)}
    for req in required:
        if req.lower() not in existing:
            facilities.append(req)
            existing.add(req.lower())
    facilities = uniq([x for x in facilities if isinstance(x, str) and x.strip()])
    data["official_data"]["facilities_and_resources"] = facilities
    if facilities != old:
        if len(old) == 0:
            issues.append("facilities_and_resources was empty.")
        else:
            issues.append("facilities_and_resources missed category-required infrastructure.")
        log_change(
            logs,
            "Facilities list repaired",
            "official_data.facilities_and_resources",
            old,
            facilities,
            "Ensured realistic category-specific infrastructure list.",
        )


def apply_media_profile(dp: Dict[str, Any], base: str, logs: List[Dict[str, Any]], issues: List[str], variant: str) -> None:
    # variant: translation/media/general
    if variant == "translation":
        targets = {"language_communication_focus": 0.93, "design_creativity": 0.72, "math_intensity": 0.25, "hardware_focus": 0.10}
    elif variant == "media":
        targets = {"language_communication_focus": 0.89, "design_creativity": 0.80, "math_intensity": 0.30, "hardware_focus": 0.15}
    else:
        targets = {"language_communication_focus": 0.88, "design_creativity": 0.75, "math_intensity": 0.30, "hardware_focus": 0.15}
    for k, v in targets.items():
        old = dp.get(k)
        if not isinstance(old, (int, float)) or old != v:
            dp[k] = v
            issues.append(f"{base}.{k} unrealistic or missing for media/communication profile.")
            log_change(
                logs,
                "Unrealistic media/communication decision profile value",
                f"{base}.{k}",
                old,
                v,
                "Adjusted to realistic range for media/communication programs.",
            )


def apply_design_profile(dp: Dict[str, Any], base: str, logs: List[Dict[str, Any]], issues: List[str]) -> None:
    targets = {"design_creativity": 0.94, "math_intensity": 0.32, "software_focus": 0.55}
    for k, v in targets.items():
        old = dp.get(k)
        if not isinstance(old, (int, float)) or old != v:
            dp[k] = v
            issues.append(f"{base}.{k} unrealistic or missing for design profile.")
            log_change(
                logs,
                "Unrealistic design-program decision profile value",
                f"{base}.{k}",
                old,
                v,
                "Adjusted to realistic design-program range.",
            )


def apply_archaeology_profile(dp: Dict[str, Any], base: str, logs: List[Dict[str, Any]], issues: List[str]) -> None:
    targets = {"research_orientation": 0.78, "field_work_intensity": 0.74}
    for k, v in targets.items():
        old = dp.get(k)
        if not isinstance(old, (int, float)) or old != v:
            dp[k] = v
            issues.append(f"{base}.{k} unrealistic or missing for archaeology profile.")
            log_change(
                logs,
                "Unrealistic archaeology decision profile value",
                f"{base}.{k}",
                old,
                v,
                "Adjusted to realistic archaeology range.",
            )


def apply_fisheries_profile(dp: Dict[str, Any], base: str, logs: List[Dict[str, Any]], issues: List[str]) -> None:
    targets = {"maritime_focus": 0.78, "field_work_intensity": 0.76, "biology_focus": 0.74}
    for k, v in targets.items():
        old = dp.get(k)
        if not isinstance(old, (int, float)) or old != v:
            dp[k] = v
            issues.append(f"{base}.{k} unrealistic or missing for fisheries profile.")
            log_change(
                logs,
                "Unrealistic fisheries decision profile value",
                f"{base}.{k}",
                old,
                v,
                "Adjusted to realistic fisheries range.",
            )


def update_programs(data: Dict[str, Any], file_name: str, issues: List[str], logs: List[Dict[str, Any]]) -> None:
    profiles = dget(data, "decision_support.program_profiles")
    if not isinstance(profiles, list):
        return
    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            continue
        name = str(p.get("program_name") or "")
        low = name.lower()
        base = f"decision_support.program_profiles[{i}].decision_profile"
        dp = p.setdefault("decision_profile", {})
        if not isinstance(dp, dict):
            old = dp
            dp = {}
            p["decision_profile"] = dp
            log_change(
                logs,
                "Invalid decision_profile object",
                f"decision_support.program_profiles[{i}].decision_profile",
                old,
                dp,
                "Normalized to object for repair operations.",
            )

        # Career path replacements
        mapped_roles: List[str] = []
        if "clc_" in file_name.lower():
            if any(k in low for k in ["translation", "linguistics", "english", "arabic"]):
                mapped_roles = ["Translator", "Localization Specialist", "Language Consultant", "Technical Translator"]
                apply_media_profile(dp, base, logs, issues, "translation")
            elif any(k in low for k in ["media", "radio", "tv", "film"]):
                mapped_roles = ["Journalist", "TV Producer", "Media Content Creator", "Broadcast Specialist", "Communication Consultant"]
                apply_media_profile(dp, base, logs, issues, "media")
            else:
                mapped_roles = ["Journalist", "Media Content Creator", "Communication Consultant", "Broadcast Specialist"]
                apply_media_profile(dp, base, logs, issues, "general")
        elif "archaeology_and_cultural_heritage" in file_name.lower():
            mapped_roles = ["Archaeologist", "Cultural Heritage Specialist", "Museum Curator", "Conservation Specialist", "Archaeological Researcher"]
            apply_archaeology_profile(dp, base, logs, issues)
        elif "art_and_design" in file_name.lower():
            apply_design_profile(dp, base, logs, issues)
            if "industrial" in low:
                mapped_roles = ["Industrial Designer", "Product Designer", "UX Designer", "Prototyping Specialist", "Design Consultant"]
            elif "graphic" in low:
                mapped_roles = ["Graphic Designer", "Visual Communication Designer", "UX Designer", "Brand Designer", "Motion Graphics Designer"]
            elif "fashion" in low:
                mapped_roles = ["Fashion Designer", "Apparel Product Developer", "Fashion Illustrator", "Textile Design Specialist", "Fashion Merchandising Specialist"]
            elif "interior" in low or "furniture" in low:
                mapped_roles = ["Interior Designer", "Furniture Designer", "Space Planner", "CAD Interior Specialist", "Exhibition Designer"]
            else:
                mapped_roles = ["Product Designer", "Graphic Designer", "UX Designer", "Creative Director", "Visual Artist"]
        elif "fisheries_and_aquaculture" in file_name.lower():
            mapped_roles = ["Aquaculture Specialist", "Fish Farm Manager", "Marine Resource Analyst", "Fish Processing Engineer", "Fisheries Policy Advisor"]
            apply_fisheries_profile(dp, base, logs, issues)

        # Replace generic careers when mapped exists
        if mapped_roles:
            old_roles = ensure_list(p.get("career_paths"))
            old_set = {str(r).strip().lower() for r in old_roles if isinstance(r, str)}
            generic_hits = {"specialist role", "analyst role", "coordinator role"} & old_set
            if generic_hits or len(old_roles) == 0 or old_set != {r.lower() for r in mapped_roles}:
                p["career_paths"] = mapped_roles
                issues.append(f"decision_support.program_profiles[{i}].career_paths generic/weak.")
                log_change(
                    logs,
                    "Generic or weak career paths",
                    f"decision_support.program_profiles[{i}].career_paths",
                    old_roles,
                    mapped_roles,
                    "Replaced with realistic program-specific roles.",
                )


def flatten_missing_official(data: Any, prefix: str = "official_data") -> List[str]:
    missing: List[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{prefix}.{k}"
            if v is None:
                missing.append(p)
            elif isinstance(v, str) and v.strip() == "":
                missing.append(p)
            elif isinstance(v, list):
                if len(v) == 0:
                    missing.append(p)
            elif isinstance(v, dict):
                missing.extend(flatten_missing_official(v, p))
    return missing


def finalize_quality(data: Dict[str, Any]) -> None:
    quality = data.setdefault("quality_check", {})
    official = data.get("official_data", {})
    quality["missing_fields"] = uniq(flatten_missing_official(official, "official_data"))
    notes = ensure_list(quality.get("notes"))
    note = "Batch-targeted repair applied for overview, admission, facilities, career paths, and decision-profile realism."
    if note not in notes:
        notes.append(note)
    quality["notes"] = notes


def process_file(file_name: str) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    path = os.path.join(BASE_DIR, file_name)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues: List[str] = []
    logs: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        issues.append("Root JSON is not object.")
        return issues, logs, data

    set_overview(data, file_name, issues, logs)
    set_admission(data, issues, logs)
    ensure_facilities(data, file_name, issues, logs)
    update_programs(data, file_name, issues, logs)
    finalize_quality(data)

    return uniq(issues), logs, data


def make_report(file_name: str, issues: List[str], corrected: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"FILE: {file_name}")
    lines.append(f"TIMESTAMP_UTC: {iso_now()}")
    lines.append("")
    lines.append("1) Issues detected")
    if issues:
        for issue in issues:
            lines.append(f"- {issue}")
    else:
        lines.append("- No major issues detected.")
    lines.append("")
    lines.append("3) Final corrected JSON")
    lines.append(json.dumps(corrected, ensure_ascii=False, indent=2))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    for file_name in TARGET_FILES:
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            print(f"SKIP: missing file={file_name}", flush=True)
            continue
        issues, logs, corrected = process_file(file_name)
        write_json_atomic(path, corrected)
        report_name = f"{os.path.splitext(file_name)[0]}.batch2_audit_repair_report.txt"
        report_path = os.path.join(BASE_DIR, report_name)
        write_text_atomic(report_path, make_report(file_name, issues, corrected))
        print(f"BATCH2 REPAIR CHECKPOINT: completed_file={file_name} | status=done", flush=True)


if __name__ == "__main__":
    main()
