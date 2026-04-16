import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


BASE_DIR = r"C:\Users\mh978\Downloads\college-decision\normalized_college_v2"

DEFAULT_OVERVIEW_SHORT = (
    "A leading engineering college within AASTMT offering internationally accredited engineering programs "
    "with strong emphasis on applied training and industry collaboration."
)
DEFAULT_OVERVIEW_STATUS = (
    "Active undergraduate and postgraduate engineering programs with international accreditation and "
    "industry partnerships."
)

DEFAULT_CERTIFICATES = [
    "Thanaweia Amma",
    "IGCSE",
    "American Diploma",
    "IB",
    "German Abitur",
    "French Baccalaureate",
]

REQUIRED_FACILITIES = [
    "Engineering Laboratories",
    "Computer Labs",
    "Workshops",
    "Research Centers",
    "Student Activities",
    "Campus Infrastructure",
    "Library",
]

GENERIC_ENGINEERING_ROLES = {
    "Design Engineer",
    "Project Engineer",
    "Field Engineer",
    "Maintenance Engineer",
    "Operations Engineer",
    "Graduate Trainee",
    "Engineering Specialist",
    "Specialist Role",
    "Analyst Role",
    "Coordinator Role",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x).strip()
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


def log_change(
    logs: List[Dict[str, Any]],
    issue: str,
    field: str,
    old_value: Any,
    new_value: Any,
    reason: str,
) -> None:
    if old_value == new_value:
        return
    logs.append(
        {
            "Issue": issue,
            "Field": field,
            "Old Value": old_value,
            "New Value": new_value,
            "Reason": reason,
        }
    )


def is_engineering_file(data: Dict[str, Any]) -> bool:
    source_file = str(dget(data, "source.source_file_name") or "").lower()
    if source_file in {"fees.json", "tuition_fees_2025_2026.json"}:
        return False

    college_name = str(dget(data, "entity.college_name") or "").lower()
    programs = " | ".join(
        [
            str(p.get("program_name") or "").lower()
            for p in ensure_list(dget(data, "decision_support.program_profiles"))
            if isinstance(p, dict)
        ]
    )
    blob = f"{college_name} | {programs}"
    keywords = [
        "engineering",
        "architect",
        "mechanical",
        "electrical",
        "construction",
        "civil",
        "marine engineering",
        "electronics and communications",
        "computer engineering",
    ]
    return any(k in blob for k in keywords)


def career_map(program_name: str) -> List[str]:
    low = (program_name or "").lower()
    if "architect" in low:
        return ["Architect", "Urban Designer", "BIM Engineer", "Architectural Consultant", "Sustainability Architect"]
    if "computer engineering" in low:
        return ["Software Engineer", "Embedded Systems Engineer", "AI Engineer", "Machine Learning Engineer", "Cloud Engineer"]
    if "mechanical" in low:
        return [
            "Mechanical Design Engineer",
            "Automation Engineer",
            "Robotics Engineer",
            "Manufacturing Engineer",
            "Maintenance Engineer",
        ]
    if "civil" in low or "construction" in low or "buildings engineering" in low:
        return ["Structural Engineer", "Site Engineer", "Project Engineer", "Construction Manager", "Infrastructure Engineer"]
    if "electrical" in low or "electronics and communications" in low:
        return ["Power Systems Engineer", "Control Systems Engineer", "Automation Engineer", "Electrical Design Engineer"]
    return []


def set_profile_metric(
    dp: Dict[str, Any],
    metric: str,
    new_value: float,
    base_path: str,
    logs: List[Dict[str, Any]],
    issue: str,
    reason: str,
) -> None:
    old = dp.get(metric)
    if old != new_value:
        dp[metric] = round(clamp(new_value), 2)
        log_change(logs, issue, f"{base_path}.{metric}", old, dp[metric], reason)


def ensure_overview(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    overview = dget(data, "official_data.overview")
    if not isinstance(overview, dict):
        old = overview
        data.setdefault("official_data", {})["overview"] = {}
        overview = data["official_data"]["overview"]
        log_change(
            logs,
            "Missing/invalid overview object",
            "official_data.overview",
            old,
            overview,
            "Created overview object to hold required academic description fields.",
        )
        issues.append("overview object missing or invalid.")

    if is_empty(overview.get("short_description")):
        old = overview.get("short_description")
        overview["short_description"] = DEFAULT_OVERVIEW_SHORT
        log_change(
            logs,
            "Missing overview.short_description",
            "official_data.overview.short_description",
            old,
            overview["short_description"],
            "Filled concise engineering college description as requested.",
        )
        issues.append("overview.short_description was null/empty.")

    if is_empty(overview.get("current_status")):
        old = overview.get("current_status")
        overview["current_status"] = DEFAULT_OVERVIEW_STATUS
        log_change(
            logs,
            "Missing overview.current_status",
            "official_data.overview.current_status",
            old,
            overview["current_status"],
            "Filled concise current-status statement as requested.",
        )
        issues.append("overview.current_status was null/empty.")


def ensure_admission(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    admission = dget(data, "official_data.admission_requirements")
    if not isinstance(admission, dict):
        old = admission
        data.setdefault("official_data", {})["admission_requirements"] = {}
        admission = data["official_data"]["admission_requirements"]
        log_change(
            logs,
            "Missing/invalid admission_requirements object",
            "official_data.admission_requirements",
            old,
            admission,
            "Created admission_requirements object for required defaults.",
        )
        issues.append("admission_requirements object missing or invalid.")

    if is_empty(admission.get("accepted_certificates")):
        old = admission.get("accepted_certificates")
        admission["accepted_certificates"] = list(DEFAULT_CERTIFICATES)
        log_change(
            logs,
            "Missing accepted_certificates",
            "official_data.admission_requirements.accepted_certificates",
            old,
            admission["accepted_certificates"],
            "Filled requested realistic admission certificate set.",
        )
        issues.append("admission accepted_certificates empty/null.")

    if admission.get("entry_exams_required") is None:
        old = admission.get("entry_exams_required")
        admission["entry_exams_required"] = True
        log_change(
            logs,
            "Null entry_exams_required",
            "official_data.admission_requirements.entry_exams_required",
            old,
            True,
            "Set required default to true as requested.",
        )
        issues.append("entry_exams_required was null.")

    if admission.get("medical_fitness_required") is None:
        old = admission.get("medical_fitness_required")
        admission["medical_fitness_required"] = True
        log_change(
            logs,
            "Null medical_fitness_required",
            "official_data.admission_requirements.medical_fitness_required",
            old,
            True,
            "Set required default to true as requested.",
        )
        issues.append("medical_fitness_required was null.")

    if admission.get("age_limit") is None:
        old = admission.get("age_limit")
        admission["age_limit"] = 22
        log_change(
            logs,
            "Null age_limit",
            "official_data.admission_requirements.age_limit",
            old,
            22,
            "Set requested standard admission age limit.",
        )
        issues.append("age_limit was null.")


def ensure_regulations(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    regs = dget(data, "official_data.student_regulations")
    if not isinstance(regs, dict):
        old = regs
        data.setdefault("official_data", {})["student_regulations"] = {}
        regs = data["official_data"]["student_regulations"]
        log_change(
            logs,
            "Missing/invalid student_regulations object",
            "official_data.student_regulations",
            old,
            regs,
            "Created student_regulations object for required defaults.",
        )
        issues.append("student_regulations object missing or invalid.")

    defaults = {
        "add_course_deadline_week": 2,
        "withdraw_deadline_week": 14,
        "max_absence_percent": 15,
    }
    for key, val in defaults.items():
        if regs.get(key) is None:
            old = regs.get(key)
            regs[key] = val
            log_change(
                logs,
                f"Null {key}",
                f"official_data.student_regulations.{key}",
                old,
                val,
                "Set typical AASTMT regulation default as requested.",
            )
            issues.append(f"student_regulations.{key} was null.")


def ensure_facilities(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    facilities = dget(data, "official_data.facilities_and_resources")
    if not isinstance(facilities, list):
        old = facilities
        data.setdefault("official_data", {})["facilities_and_resources"] = []
        facilities = data["official_data"]["facilities_and_resources"]
        log_change(
            logs,
            "Invalid facilities_and_resources type",
            "official_data.facilities_and_resources",
            old,
            facilities,
            "Converted facilities_and_resources to list.",
        )
        issues.append("facilities_and_resources invalid type.")

    old = list(facilities)
    text_set = {str(x).strip().lower() for x in facilities if isinstance(x, str)}
    for req in REQUIRED_FACILITIES:
        if req.lower() not in text_set:
            facilities.append(req)
    facilities = uniq([f for f in facilities if isinstance(f, str) and f.strip()])
    data["official_data"]["facilities_and_resources"] = facilities
    if facilities != old:
        log_change(
            logs,
            "Missing required facilities",
            "official_data.facilities_and_resources",
            old,
            facilities,
            "Ensured baseline engineering facilities list is present.",
        )
        if len(old) == 0:
            issues.append("facilities_and_resources was empty.")


def ensure_program_profile_repairs(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    profiles = dget(data, "decision_support.program_profiles")
    if not isinstance(profiles, list):
        return

    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            continue
        base_path = f"decision_support.program_profiles[{i}]"
        name = str(p.get("program_name") or f"Program {i + 1}")
        dp = p.get("decision_profile")
        if not isinstance(dp, dict):
            old = dp
            dp = {}
            p["decision_profile"] = dp
            log_change(
                logs,
                "Missing/invalid decision_profile",
                f"{base_path}.decision_profile",
                old,
                dp,
                "Created decision_profile object for metric repairs.",
            )
            issues.append(f"{base_path}.decision_profile missing/invalid.")

        # Clamp all numeric metrics to [0,1]
        for k, v in list(dp.items()):
            if isinstance(v, (int, float)):
                nv = round(clamp(float(v)), 2)
                if nv != v:
                    dp[k] = nv
                    log_change(
                        logs,
                        "Out-of-range decision metric",
                        f"{base_path}.decision_profile.{k}",
                        v,
                        nv,
                        "Decision profile metrics must be within [0,1].",
                    )
                    issues.append(f"{base_path}.decision_profile.{k} had out-of-range value.")

        low = name.lower()

        # Step 7 targeted realism fixes
        if "architect" in low:
            if not (0.85 <= float(dp.get("design_creativity", -1)) <= 0.95):
                set_profile_metric(
                    dp,
                    "design_creativity",
                    0.90,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic architecture design_creativity",
                    "Architecture should have high design creativity.",
                )
                issues.append(f"{base_path} architecture design_creativity adjusted.")
            if not (0.60 <= float(dp.get("math_intensity", -1)) <= 0.70):
                set_profile_metric(
                    dp,
                    "math_intensity",
                    0.65,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic architecture math_intensity",
                    "Architecture math intensity should be moderate.",
                )
                issues.append(f"{base_path} architecture math_intensity adjusted.")
            if not (0.30 <= float(dp.get("programming_intensity", -1)) <= 0.45):
                set_profile_metric(
                    dp,
                    "programming_intensity",
                    0.40,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic architecture programming_intensity",
                    "Architecture programming intensity should be low-moderate.",
                )
                issues.append(f"{base_path} architecture programming_intensity adjusted.")

        if "computer engineering" in low:
            if not (0.82 <= float(dp.get("math_intensity", -1)) <= 0.88):
                set_profile_metric(
                    dp,
                    "math_intensity",
                    0.85,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic computer engineering math_intensity",
                    "Computer engineering math intensity should be high.",
                )
                issues.append(f"{base_path} computer engineering math_intensity adjusted.")
            if not (0.90 <= float(dp.get("programming_intensity", -1)) <= 0.95):
                set_profile_metric(
                    dp,
                    "programming_intensity",
                    0.92,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic computer engineering programming_intensity",
                    "Computer engineering programming intensity should be very high.",
                )
                issues.append(f"{base_path} computer engineering programming_intensity adjusted.")
            if not (0.65 <= float(dp.get("ai_focus", -1)) <= 0.80):
                set_profile_metric(
                    dp,
                    "ai_focus",
                    0.72,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic computer engineering ai_focus",
                    "Computer engineering AI focus should be moderate-high.",
                )
                issues.append(f"{base_path} computer engineering ai_focus adjusted.")
            if float(dp.get("software_focus", -1)) < 0.90:
                set_profile_metric(
                    dp,
                    "software_focus",
                    0.92,
                    f"{base_path}.decision_profile",
                    logs,
                    "Unrealistic computer engineering software_focus",
                    "Computer engineering software focus should be at least 0.90.",
                )
                issues.append(f"{base_path} computer engineering software_focus adjusted.")

        if "mechanical" in low:
            if float(dp.get("physics_intensity", -1)) != 0.85:
                set_profile_metric(
                    dp,
                    "physics_intensity",
                    0.85,
                    f"{base_path}.decision_profile",
                    logs,
                    "Mechanical physics_intensity mismatch",
                    "Mechanical profile calibrated to realistic physics intensity.",
                )
                issues.append(f"{base_path} mechanical physics_intensity adjusted.")
            if float(dp.get("math_intensity", -1)) != 0.80:
                set_profile_metric(
                    dp,
                    "math_intensity",
                    0.80,
                    f"{base_path}.decision_profile",
                    logs,
                    "Mechanical math_intensity mismatch",
                    "Mechanical profile calibrated to realistic math intensity.",
                )
                issues.append(f"{base_path} mechanical math_intensity adjusted.")
            if float(dp.get("hardware_focus", -1)) < 0.80:
                set_profile_metric(
                    dp,
                    "hardware_focus",
                    0.82,
                    f"{base_path}.decision_profile",
                    logs,
                    "Mechanical hardware_focus too low",
                    "Mechanical profile should emphasize hardware orientation.",
                )
                issues.append(f"{base_path} mechanical hardware_focus adjusted.")

        if "electrical" in low or "electronics and communications" in low:
            if float(dp.get("math_intensity", -1)) != 0.85:
                set_profile_metric(
                    dp,
                    "math_intensity",
                    0.85,
                    f"{base_path}.decision_profile",
                    logs,
                    "Electrical math_intensity mismatch",
                    "Electrical profile calibrated to realistic math intensity.",
                )
                issues.append(f"{base_path} electrical math_intensity adjusted.")
            if float(dp.get("physics_intensity", -1)) != 0.90:
                set_profile_metric(
                    dp,
                    "physics_intensity",
                    0.90,
                    f"{base_path}.decision_profile",
                    logs,
                    "Electrical physics_intensity mismatch",
                    "Electrical profile calibrated to realistic physics intensity.",
                )
                issues.append(f"{base_path} electrical physics_intensity adjusted.")
            if float(dp.get("hardware_focus", -1)) != 0.85:
                set_profile_metric(
                    dp,
                    "hardware_focus",
                    0.85,
                    f"{base_path}.decision_profile",
                    logs,
                    "Electrical hardware_focus mismatch",
                    "Electrical profile calibrated to realistic hardware focus.",
                )
                issues.append(f"{base_path} electrical hardware_focus adjusted.")

        # Career path specificity
        mapped = career_map(name)
        if mapped:
            old_roles = ensure_list(p.get("career_paths"))
            old_clean = [r for r in old_roles if isinstance(r, str)]
            generic_count = sum(1 for r in old_clean if r in GENERIC_ENGINEERING_ROLES)
            if generic_count > 0 or len(old_clean) < 4 or set(old_clean) != set(mapped):
                p["career_paths"] = mapped
                log_change(
                    logs,
                    "Generic/weak engineering career paths",
                    f"{base_path}.career_paths",
                    old_roles,
                    mapped,
                    "Replaced with program-specific career outcomes.",
                )
                issues.append(f"{base_path}.career_paths made program-specific.")


def apply_campus_college_level_metrics(data: Dict[str, Any], issues: List[str], logs: List[Dict[str, Any]]) -> None:
    clp = dget(data, "decision_support.college_level_profile")
    if not isinstance(clp, dict):
        return
    city = str(dget(data, "official_data.location.city") or "").lower()
    branch = str(dget(data, "official_data.location.branch") or "").lower()
    loc = f"{city} | {branch}"

    if "smart village" in loc:
        metrics = {
            "campus_life_score": 0.78,
            "city_opportunity_score": 0.90,
            "industry_exposure": 0.88,
            "cost_of_living_score": 0.42,
        }
    elif "alamein" in loc:
        metrics = {
            "campus_life_score": 0.85,
            "city_opportunity_score": 0.55,
            "industry_exposure": 0.58,
            "cost_of_living_score": 0.60,
        }
    elif "south valley" in loc:
        metrics = {
            "campus_life_score": 0.70,
            "city_opportunity_score": 0.40,
            "industry_exposure": 0.45,
            "cost_of_living_score": 0.72,
        }
    elif any(k in loc for k in ["heliopolis", "cairo", "giza", "dokki"]):
        metrics = {
            "campus_life_score": 0.74,
            "city_opportunity_score": 0.88,
            "industry_exposure": 0.84,
            "cost_of_living_score": 0.45,
        }
    elif any(k in loc for k in ["alexandria", "abu qir", "abukir", "miami"]):
        metrics = {
            "campus_life_score": 0.76,
            "city_opportunity_score": 0.72,
            "industry_exposure": 0.74,
            "cost_of_living_score": 0.58,
        }
    elif "latakia" in loc:
        metrics = {
            "campus_life_score": 0.72,
            "city_opportunity_score": 0.58,
            "industry_exposure": 0.52,
            "cost_of_living_score": 0.56,
        }
    else:
        metrics = {
            "campus_life_score": 0.72,
            "city_opportunity_score": 0.62,
            "industry_exposure": 0.62,
            "cost_of_living_score": 0.55,
        }

    for key, val in metrics.items():
        old = clp.get(key)
        if old != val:
            clp[key] = val
            log_change(
                logs,
                f"Missing/adjusted campus metric: {key}",
                f"decision_support.college_level_profile.{key}",
                old,
                val,
                "Added campus decision metric using provided campus-range guidance.",
            )
            if old is None:
                issues.append(f"college_level_profile.{key} was missing.")


def make_report(file_name: str, issues: List[str], logs: List[Dict[str, Any]], corrected: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"FILE: {file_name}")
    lines.append(f"TIMESTAMP_UTC: {iso_now()}")
    lines.append("")
    lines.append("1. Issues detected")
    if issues:
        for i in uniq(issues):
            lines.append(f"- {i}")
    else:
        lines.append("- No significant issues detected.")
    lines.append("")
    lines.append("2. Repair log")
    if logs:
        for row in logs:
            lines.append("")
            lines.append(f"Issue:\n{row['Issue']}")
            lines.append(f"Field:\n{row['Field']}")
            lines.append(f"Old Value:\n{json.dumps(row['Old Value'], ensure_ascii=False)}")
            lines.append(f"New Value:\n{json.dumps(row['New Value'], ensure_ascii=False)}")
            lines.append(f"Reason:\n{row['Reason']}")
    else:
        lines.append("- No direct modifications were needed.")
    lines.append("")
    lines.append("3. Final corrected JSON file")
    lines.append(json.dumps(corrected, ensure_ascii=False, indent=2))
    lines.append("")
    return "\n".join(lines)


def process_file(path: str) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues: List[str] = []
    logs: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        issues.append("Root JSON is not object; skipped.")
        return issues, logs, data

    # Step 1 audit-driven repairs
    ensure_overview(data, issues, logs)
    ensure_admission(data, issues, logs)
    ensure_regulations(data, issues, logs)
    ensure_facilities(data, issues, logs)
    ensure_program_profile_repairs(data, issues, logs)
    apply_campus_college_level_metrics(data, issues, logs)

    # Keep quality_check note
    quality = data.setdefault("quality_check", {})
    notes = ensure_list(quality.get("notes"))
    note = "Engineering-file targeted audit/repair applied for overview, admission, regulations, facilities, careers, and decision profile realism."
    if note not in notes:
        notes.append(note)
    quality["notes"] = notes

    return issues, logs, data


def main() -> None:
    files = sorted([f for f in os.listdir(BASE_DIR) if f.lower().endswith(".normalized.v2.json")])
    for file_name in files:
        path = os.path.join(BASE_DIR, file_name)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not is_engineering_file(data):
            continue

        issues, logs, corrected = process_file(path)
        write_json_atomic(path, corrected)
        report_name = f"{os.path.splitext(file_name)[0]}.engineering_audit_repair_report.txt"
        report_path = os.path.join(BASE_DIR, report_name)
        write_text_atomic(report_path, make_report(file_name, issues, logs, corrected))
        print(f"ENGINEERING REPAIR CHECKPOINT: completed_file={file_name} | status=done", flush=True)


if __name__ == "__main__":
    main()
