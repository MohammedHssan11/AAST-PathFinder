import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


BASE_DIR = r"C:\Users\mh978\Downloads\college-decision\normalized_college_v2"

ALLOWED_ENTITY_TYPES = {"college", "program", "department", "branch"}

REQUIRED_PROGRAM_FIELDS = [
    "decision_profile",
    "career_paths",
    "employment_outlook",
    "best_fit_traits",
    "avoid_if",
    "summary",
    "program_family",
    "close_alternatives",
    "differentiation_notes",
]

ESSENTIAL_METRICS = [
    "math_intensity",
    "programming_intensity",
    "design_creativity",
    "ai_focus",
    "data_focus",
    "software_focus",
    "security_focus",
    "business_focus",
]


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


def level_from_score(score: float) -> int:
    if score >= 0.67:
        return 3
    if score >= 0.50:
        return 2
    return 1


def label_from_level(level: int) -> str:
    return {1: "weak", 2: "medium", 3: "strong"}.get(level, "medium")


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


def flatten_null_empty(data: Any, path: str = "") -> Tuple[List[str], List[str]]:
    nulls: List[str] = []
    empties: List[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{path}.{k}" if path else k
            n, e = flatten_null_empty(v, p)
            nulls.extend(n)
            empties.extend(e)
    elif isinstance(data, list):
        if len(data) == 0:
            empties.append(path)
        else:
            for i, v in enumerate(data):
                n, e = flatten_null_empty(v, f"{path}[{i}]")
                nulls.extend(n)
                empties.extend(e)
    else:
        if data is None:
            nulls.append(path)
        elif isinstance(data, str) and data.strip() == "":
            empties.append(path)
    return nulls, empties


def infer_family(name: str) -> str:
    low = (name or "").lower()
    if any(k in low for k in ["cyber", "security"]):
        return "CYBERSEC_FAMILY"
    if any(k in low for k in ["artificial intelligence", "intelligent systems", "machine learning"]):
        return "AI_FAMILY"
    if any(k in low for k in ["data science", "data", "analytics"]):
        return "DATA_FAMILY"
    if any(k in low for k in ["software"]):
        return "SOFTWARE_FAMILY"
    if any(k in low for k in ["computer science", "computer"]):
        return "CS_FAMILY"
    if any(k in low for k in ["information systems", "information system"]):
        return "IS_FAMILY"
    if any(k in low for k in ["business", "management", "marketing"]):
        return "BUSINESS_FAMILY"
    if any(k in low for k in ["finance", "accounting"]):
        return "FINANCE_FAMILY"
    if any(k in low for k in ["logistics", "transport", "supply chain"]):
        return "LOGISTICS_FAMILY"
    if any(k in low for k in ["maritime", "marine"]):
        return "MARITIME_FAMILY"
    if any(k in low for k in ["law", "legal"]):
        return "LAW_POLICY_FAMILY"
    if any(k in low for k in ["medicine", "medical", "dental", "dentistry", "pharmacy"]):
        return "HEALTHCARE_FAMILY"
    if any(k in low for k in ["art", "design", "graphics", "multimedia"]):
        return "DESIGN_FAMILY"
    if any(k in low for k in ["engineering"]):
        return "ENGINEERING_FAMILY"
    return "GENERAL_FAMILY"


def default_metrics_for_program(name: str) -> Dict[str, float]:
    low = (name or "").lower()
    base = {
        "math_intensity": 0.55,
        "programming_intensity": 0.50,
        "design_creativity": 0.45,
        "ai_focus": 0.50,
        "data_focus": 0.50,
        "software_focus": 0.50,
        "security_focus": 0.45,
        "business_focus": 0.50,
    }
    if "computer science" in low:
        base.update(
            {
                "math_intensity": 0.82,
                "programming_intensity": 0.90,
                "design_creativity": 0.40,
                "ai_focus": 0.60,
                "data_focus": 0.65,
                "software_focus": 0.90,
                "security_focus": 0.55,
                "business_focus": 0.40,
            }
        )
    elif any(k in low for k in ["artificial intelligence", "intelligent systems", "machine learning"]):
        base.update(
            {
                "math_intensity": 0.90,
                "programming_intensity": 0.90,
                "design_creativity": 0.45,
                "ai_focus": 0.92,
                "data_focus": 0.78,
                "software_focus": 0.70,
                "security_focus": 0.45,
                "business_focus": 0.38,
            }
        )
    elif any(k in low for k in ["data science", "analytics"]):
        base.update(
            {
                "math_intensity": 0.82,
                "programming_intensity": 0.78,
                "design_creativity": 0.38,
                "ai_focus": 0.72,
                "data_focus": 0.92,
                "software_focus": 0.62,
                "security_focus": 0.40,
                "business_focus": 0.52,
            }
        )
    elif "information systems" in low:
        base.update(
            {
                "math_intensity": 0.62,
                "programming_intensity": 0.68,
                "design_creativity": 0.36,
                "ai_focus": 0.50,
                "data_focus": 0.64,
                "software_focus": 0.62,
                "security_focus": 0.48,
                "business_focus": 0.80,
            }
        )
    elif any(k in low for k in ["cyber", "security"]):
        base.update(
            {
                "math_intensity": 0.68,
                "programming_intensity": 0.78,
                "design_creativity": 0.30,
                "ai_focus": 0.46,
                "data_focus": 0.50,
                "software_focus": 0.72,
                "security_focus": 0.90,
                "business_focus": 0.42,
            }
        )
    elif "software" in low:
        base.update(
            {
                "math_intensity": 0.70,
                "programming_intensity": 0.90,
                "design_creativity": 0.40,
                "ai_focus": 0.52,
                "data_focus": 0.56,
                "software_focus": 0.92,
                "security_focus": 0.55,
                "business_focus": 0.42,
            }
        )
    elif any(k in low for k in ["business", "management", "marketing"]):
        base.update(
            {
                "math_intensity": 0.55,
                "programming_intensity": 0.45,
                "design_creativity": 0.44,
                "ai_focus": 0.38,
                "data_focus": 0.52,
                "software_focus": 0.40,
                "security_focus": 0.30,
                "business_focus": 0.90,
            }
        )
    elif any(k in low for k in ["finance", "accounting"]):
        base.update(
            {
                "math_intensity": 0.62,
                "programming_intensity": 0.46,
                "design_creativity": 0.30,
                "ai_focus": 0.42,
                "data_focus": 0.62,
                "software_focus": 0.45,
                "security_focus": 0.34,
                "business_focus": 0.76,
            }
        )
    return base


def default_roles_for_program(name: str, family: str) -> List[str]:
    low = (name or "").lower()
    if "computer science" in low or family in {"CS_FAMILY", "SOFTWARE_FAMILY"}:
        return ["Software Engineer", "Backend Engineer", "DevOps Engineer", "Cloud Engineer"]
    if family == "AI_FAMILY":
        return ["AI Engineer", "Machine Learning Engineer", "Data Scientist", "MLOps Engineer"]
    if family == "DATA_FAMILY":
        return ["Data Scientist", "Data Analyst", "Business Intelligence Engineer", "Data Engineer"]
    if family == "CYBERSEC_FAMILY":
        return ["Cybersecurity Analyst", "SOC Analyst", "Security Engineer", "Penetration Tester"]
    if family == "IS_FAMILY":
        return ["Business Analyst", "Systems Analyst", "ERP Specialist", "Product Analyst"]
    if family == "BUSINESS_FAMILY":
        return ["Business Analyst", "Operations Analyst", "Management Trainee", "Marketing Specialist"]
    if family == "FINANCE_FAMILY":
        return ["Financial Analyst", "Accountant", "Audit Associate", "Risk Analyst"]
    if family == "LOGISTICS_FAMILY":
        return ["Supply Chain Analyst", "Logistics Coordinator", "Operations Planner", "Procurement Analyst"]
    if family == "LAW_POLICY_FAMILY":
        return ["Legal Analyst", "Compliance Analyst", "Legal Research Assistant", "Corporate Legal Coordinator"]
    if family == "HEALTHCARE_FAMILY":
        return ["Clinical Practitioner", "Healthcare Quality Specialist", "Medical Research Assistant", "Hospital Operations Coordinator"]
    if family == "DESIGN_FAMILY":
        return ["UI/UX Designer", "Graphic Designer", "Multimedia Designer", "Digital Content Designer"]
    if family == "ENGINEERING_FAMILY":
        return ["Design Engineer", "Project Engineer", "Field Engineer", "Maintenance Engineer"]
    return ["Specialist Role", "Analyst Role", "Coordinator Role", "Graduate Trainee"]


def default_outlook(family: str) -> Dict[str, Dict[str, Any]]:
    mapping = {
        "CS_FAMILY": (0.76, 0.72),
        "SOFTWARE_FAMILY": (0.78, 0.74),
        "AI_FAMILY": (0.75, 0.78),
        "DATA_FAMILY": (0.72, 0.74),
        "CYBERSEC_FAMILY": (0.78, 0.76),
        "IS_FAMILY": (0.68, 0.60),
        "BUSINESS_FAMILY": (0.64, 0.58),
        "FINANCE_FAMILY": (0.66, 0.60),
        "LOGISTICS_FAMILY": (0.66, 0.62),
        "LAW_POLICY_FAMILY": (0.58, 0.50),
        "HEALTHCARE_FAMILY": (0.74, 0.58),
        "DESIGN_FAMILY": (0.56, 0.52),
        "ENGINEERING_FAMILY": (0.68, 0.62),
        "GENERAL_FAMILY": (0.56, 0.50),
    }
    eg_score, int_score = mapping.get(family, mapping["GENERAL_FAMILY"])
    eg_level = level_from_score(eg_score)
    int_level = level_from_score(int_score)
    return {
        "egypt_market": {"level": eg_level, "label": label_from_level(eg_level), "score": round(eg_score, 2)},
        "international_market": {"level": int_level, "label": label_from_level(int_level), "score": round(int_score, 2)},
    }


def normalize_market(market: Any, fallback_level: int = 2, fallback_score: float = 0.58) -> Dict[str, Any]:
    if not isinstance(market, dict):
        level = fallback_level
        score = fallback_score
        return {"level": level, "label": label_from_level(level), "score": round(clamp(score), 2)}

    level = market.get("level")
    score = market.get("score")
    label = market.get("label")

    if isinstance(score, str):
        try:
            score = float(score)
        except Exception:
            score = None

    if level not in [1, 2, 3]:
        if isinstance(score, (int, float)):
            level = level_from_score(float(score))
        else:
            level = fallback_level

    if not isinstance(score, (int, float)):
        score = fallback_score if level == fallback_level else {1: 0.40, 2: 0.58, 3: 0.75}[level]

    score = round(clamp(float(score)), 2)
    if label not in ["weak", "medium", "strong"]:
        label = label_from_level(level)

    return {"level": int(level), "label": str(label), "score": score}


def fit_traits_from_profile(dp: Dict[str, Any]) -> List[str]:
    traits: List[str] = []
    if float(dp.get("math_intensity", 0.5)) >= 0.7:
        traits.append("Comfortable with quantitative and analytical coursework")
    if float(dp.get("programming_intensity", 0.5)) >= 0.7:
        traits.append("Interested in coding and technical problem-solving")
    if float(dp.get("design_creativity", 0.5)) >= 0.7:
        traits.append("Enjoys creative ideation and design-driven tasks")
    if float(dp.get("business_focus", 0.5)) >= 0.7:
        traits.append("Prefers strategy, operations, and business decision contexts")
    if float(dp.get("security_focus", 0.5)) >= 0.7:
        traits.append("Interested in risk mitigation and secure systems thinking")
    if not traits:
        traits.append("Open to mixed theory-practice learning environments")
    return traits[:4]


def avoid_traits_from_profile(dp: Dict[str, Any]) -> List[str]:
    avoid: List[str] = []
    if float(dp.get("math_intensity", 0.5)) >= 0.75:
        avoid.append("You strongly prefer minimal mathematics")
    if float(dp.get("programming_intensity", 0.5)) >= 0.75:
        avoid.append("You want a non-technical day-to-day workload")
    if float(dp.get("business_focus", 0.5)) >= 0.75:
        avoid.append("You dislike case-driven or business-oriented projects")
    if float(dp.get("security_focus", 0.5)) >= 0.75:
        avoid.append("You are not interested in compliance and security operations")
    if not avoid:
        avoid.append("You want a very narrow, single-discipline curriculum")
    return avoid[:4]


def enforce_range(
    dp: Dict[str, Any],
    metric: str,
    lo: float,
    hi: float,
    path: str,
    logs: List[Dict[str, Any]],
    issue: str,
    reason: str,
) -> None:
    old = dp.get(metric)
    if not isinstance(old, (int, float)):
        return
    new = round(clamp(float(old), lo, hi), 2)
    if new != old:
        dp[metric] = new
        log_change(logs, issue, f"{path}.{metric}", old, new, reason)


def logical_consistency_adjustments(name: str, dp: Dict[str, Any], path: str, logs: List[Dict[str, Any]]) -> None:
    low = (name or "").lower()
    if "computer science" in low:
        enforce_range(
            dp,
            "math_intensity",
            0.75,
            0.90,
            path,
            logs,
            "Unrealistic Computer Science math intensity",
            "Computer Science should typically remain within the expected range.",
        )
        enforce_range(
            dp,
            "programming_intensity",
            0.85,
            0.95,
            path,
            logs,
            "Unrealistic Computer Science programming intensity",
            "Computer Science should typically remain within the expected range.",
        )
    if any(k in low for k in ["artificial intelligence", "intelligent systems", "machine learning"]):
        enforce_range(
            dp,
            "math_intensity",
            0.85,
            0.95,
            path,
            logs,
            "Unrealistic AI math intensity",
            "AI programs are expected to have high math intensity.",
        )
        enforce_range(
            dp,
            "ai_focus",
            0.85,
            1.00,
            path,
            logs,
            "Unrealistic AI focus",
            "AI programs are expected to show high AI focus.",
        )
    if "information systems" in low:
        enforce_range(
            dp,
            "business_focus",
            0.70,
            0.90,
            path,
            logs,
            "Unrealistic Information Systems business focus",
            "Information Systems should keep strong business orientation.",
        )
        enforce_range(
            dp,
            "programming_intensity",
            0.60,
            0.75,
            path,
            logs,
            "Unrealistic Information Systems programming intensity",
            "Information Systems programming intensity should be moderate.",
        )
    if any(k in low for k in ["cyber", "security"]):
        enforce_range(
            dp,
            "security_focus",
            0.85,
            1.00,
            path,
            logs,
            "Unrealistic Cybersecurity security focus",
            "Cybersecurity programs should maintain very high security focus.",
        )
        enforce_range(
            dp,
            "programming_intensity",
            0.70,
            0.85,
            path,
            logs,
            "Unrealistic Cybersecurity programming intensity",
            "Cybersecurity programming intensity is expected in a high-moderate range.",
        )


def validate_entity_type(data: Dict[str, Any], logs: List[Dict[str, Any]], detected: List[str]) -> None:
    entity = data.get("entity")
    if not isinstance(entity, dict):
        old = entity
        data["entity"] = {"entity_type": "college", "college_id": None, "college_name": None}
        log_change(
            logs,
            "Missing/invalid entity section",
            "entity",
            old,
            data["entity"],
            "Created valid entity object with conservative defaults.",
        )
        detected.append("entity section was missing or malformed.")
        return
    et = entity.get("entity_type")
    if et not in ALLOWED_ENTITY_TYPES:
        branch = dget(data, "official_data.location.branch")
        new_type = "branch" if not is_empty(branch) else "college"
        log_change(
            logs,
            "Inconsistent entity_type",
            "entity.entity_type",
            et,
            new_type,
            "Entity type corrected to valid schema enum based on location branch presence.",
        )
        entity["entity_type"] = new_type
        detected.append(f"entity.entity_type invalid -> corrected to {new_type}.")


def complete_program_profile(
    program: Dict[str, Any],
    idx: int,
    all_names: List[str],
    logs: List[Dict[str, Any]],
    detected: List[str],
) -> None:
    base_path = f"decision_support.program_profiles[{idx}]"
    name = str(program.get("program_name") or f"Program {idx + 1}")
    if "program_name" not in program or is_empty(program.get("program_name")):
        old = program.get("program_name")
        program["program_name"] = name
        log_change(
            logs,
            "Missing program_name",
            f"{base_path}.program_name",
            old,
            name,
            "Added fallback program name for schema consistency.",
        )
        detected.append(f"{base_path} missing program_name.")

    # Ensure required fields exist
    for f in REQUIRED_PROGRAM_FIELDS:
        if f not in program:
            old = None
            if f == "decision_profile":
                new = {}
            elif f in {"career_paths", "best_fit_traits", "avoid_if", "close_alternatives", "differentiation_notes"}:
                new = []
            elif f == "employment_outlook":
                new = {}
            elif f == "summary":
                new = ""
            elif f == "program_family":
                new = infer_family(name)
            else:
                new = None
            program[f] = new
            log_change(
                logs,
                f"Missing required program field: {f}",
                f"{base_path}.{f}",
                old,
                new,
                "Added missing required field for program completeness.",
            )
            detected.append(f"{base_path}.{f} was missing.")

    # program_family normalization
    inferred_family = infer_family(name)
    if not isinstance(program.get("program_family"), str) or is_empty(program.get("program_family")):
        old = program.get("program_family")
        program["program_family"] = inferred_family
        log_change(
            logs,
            "Missing/invalid program_family",
            f"{base_path}.program_family",
            old,
            inferred_family,
            "Inferred program family from program_name.",
        )
    # decision_profile and essential metrics
    dp = program.get("decision_profile")
    if not isinstance(dp, dict):
        old = dp
        dp = {}
        program["decision_profile"] = dp
        log_change(
            logs,
            "Invalid decision_profile structure",
            f"{base_path}.decision_profile",
            old,
            dp,
            "Replaced with object to satisfy schema.",
        )
        detected.append(f"{base_path}.decision_profile invalid structure.")

    defaults = default_metrics_for_program(name)
    for metric, default_val in defaults.items():
        if metric not in dp or not isinstance(dp.get(metric), (int, float)):
            old = dp.get(metric)
            dp[metric] = round(default_val, 2)
            log_change(
                logs,
                f"Missing/non-numeric metric: {metric}",
                f"{base_path}.decision_profile.{metric}",
                old,
                dp[metric],
                "Filled using conservative program-specific heuristic default.",
            )
            detected.append(f"{base_path}.decision_profile.{metric} missing or invalid.")

    # Clamp all numeric decision_profile values
    for k, v in list(dp.items()):
        if isinstance(v, (int, float)):
            nv = round(clamp(float(v), 0.0, 1.0), 2)
            if nv != v:
                dp[k] = nv
                log_change(
                    logs,
                    "Out-of-range decision_profile value",
                    f"{base_path}.decision_profile.{k}",
                    v,
                    nv,
                    "Metrics must remain in [0,1].",
                )
                detected.append(f"{base_path}.decision_profile.{k} had out-of-range value.")

    # Logical consistency for core programs
    logical_consistency_adjustments(name, dp, f"{base_path}.decision_profile", logs)

    # career_paths
    roles = program.get("career_paths")
    family = program.get("program_family") or inferred_family
    defaults_roles = default_roles_for_program(name, family)
    if not isinstance(roles, list):
        old = roles
        roles = []
        program["career_paths"] = roles
        log_change(
            logs,
            "Invalid career_paths type",
            f"{base_path}.career_paths",
            old,
            roles,
            "career_paths must be an array.",
        )
    normalized_roles = [str(r).strip() for r in roles if isinstance(r, str) and r.strip()]
    if len(normalized_roles) < 4:
        for r in defaults_roles:
            if r not in normalized_roles:
                normalized_roles.append(r)
            if len(normalized_roles) >= 4:
                break
    normalized_roles = uniq(normalized_roles)
    if normalized_roles != roles:
        old = roles
        program["career_paths"] = normalized_roles
        log_change(
            logs,
            "Incomplete career_paths",
            f"{base_path}.career_paths",
            old,
            normalized_roles,
            "Expanded with realistic role outcomes for program relevance.",
        )
        detected.append(f"{base_path}.career_paths expanded for realism/completeness.")

    # employment_outlook
    eo = program.get("employment_outlook")
    if not isinstance(eo, dict):
        old = eo
        eo = {}
        program["employment_outlook"] = eo
        log_change(
            logs,
            "Invalid employment_outlook type",
            f"{base_path}.employment_outlook",
            old,
            eo,
            "employment_outlook must be an object.",
        )

    fallback = default_outlook(family)
    old_eg = eo.get("egypt_market")
    old_int = eo.get("international_market")
    eo["egypt_market"] = normalize_market(old_eg, fallback["egypt_market"]["level"], fallback["egypt_market"]["score"])
    eo["international_market"] = normalize_market(
        old_int, fallback["international_market"]["level"], fallback["international_market"]["score"]
    )
    if eo["egypt_market"] != old_eg:
        log_change(
            logs,
            "Normalized Egypt employment_outlook market",
            f"{base_path}.employment_outlook.egypt_market",
            old_eg,
            eo["egypt_market"],
            "Ensured required {level,label,score} structure and valid ranges.",
        )
    if eo["international_market"] != old_int:
        log_change(
            logs,
            "Normalized international employment_outlook market",
            f"{base_path}.employment_outlook.international_market",
            old_int,
            eo["international_market"],
            "Ensured required {level,label,score} structure and valid ranges.",
        )

    # best_fit_traits
    bft = program.get("best_fit_traits")
    if not isinstance(bft, list) or len([x for x in bft if isinstance(x, str) and x.strip()]) == 0:
        old = bft
        new = fit_traits_from_profile(dp)
        program["best_fit_traits"] = new
        log_change(
            logs,
            "Missing/empty best_fit_traits",
            f"{base_path}.best_fit_traits",
            old,
            new,
            "Generated realistic student fit traits from decision profile.",
        )
        detected.append(f"{base_path}.best_fit_traits populated.")

    # avoid_if
    av = program.get("avoid_if")
    if not isinstance(av, list) or len([x for x in av if isinstance(x, str) and x.strip()]) == 0:
        old = av
        new = avoid_traits_from_profile(dp)
        program["avoid_if"] = new
        log_change(
            logs,
            "Missing/empty avoid_if",
            f"{base_path}.avoid_if",
            old,
            new,
            "Generated realistic mismatch indicators from profile intensities.",
        )
        detected.append(f"{base_path}.avoid_if populated.")

    # summary
    if not isinstance(program.get("summary"), str) or program.get("summary").strip() == "":
        old = program.get("summary")
        new = f"Heuristic profile for {name} emphasizing the strongest academic and career-alignment dimensions."
        program["summary"] = new
        log_change(
            logs,
            "Missing/empty summary",
            f"{base_path}.summary",
            old,
            new,
            "Added concise program summary for explainability.",
        )
        detected.append(f"{base_path}.summary populated.")

    # close alternatives and differentiation notes
    alt = program.get("close_alternatives")
    if not isinstance(alt, list):
        old = alt
        alt = []
        program["close_alternatives"] = alt
        log_change(
            logs,
            "Invalid close_alternatives type",
            f"{base_path}.close_alternatives",
            old,
            alt,
            "close_alternatives must be an array.",
        )
    if len([x for x in alt if isinstance(x, str) and x.strip()]) == 0:
        inferred = [n for n in all_names if n != name][:2]
        old = alt
        program["close_alternatives"] = inferred
        log_change(
            logs,
            "Missing close_alternatives",
            f"{base_path}.close_alternatives",
            old,
            inferred,
            "Filled with nearest available program names within same file context.",
        )

    dn = program.get("differentiation_notes")
    if not isinstance(dn, list):
        old = dn
        dn = []
        program["differentiation_notes"] = dn
        log_change(
            logs,
            "Invalid differentiation_notes type",
            f"{base_path}.differentiation_notes",
            old,
            dn,
            "differentiation_notes must be an array.",
        )
    if len([x for x in program["differentiation_notes"] if isinstance(x, str) and x.strip()]) == 0:
        notes = []
        for alt_name in program.get("close_alternatives", [])[:2]:
            if isinstance(alt_name, str) and alt_name.strip():
                notes.append(
                    f"Compared with {alt_name}, this program has a different focus mix across math, programming, and domain emphasis."
                )
        if not notes:
            notes = ["Focus pattern is distinct relative to other available options in this file."]
        old = dn
        program["differentiation_notes"] = notes
        log_change(
            logs,
            "Missing differentiation_notes",
            f"{base_path}.differentiation_notes",
            old,
            notes,
            "Added short differentiators based on heuristic profile contrast.",
        )


def process_file(path: str) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    detected: List[str] = []
    logs: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        detected.append("Root JSON is not an object; no repair applied.")
        return detected, logs, data

    nulls, empties = flatten_null_empty(data)
    if nulls:
        detected.append(f"Null fields detected: {len(nulls)} (examples: {', '.join(nulls[:8])}).")
    if empties:
        detected.append(f"Empty fields/arrays detected: {len(empties)} (examples: {', '.join(empties[:8])}).")

    validate_entity_type(data, logs, detected)

    ds = data.get("decision_support")
    if not isinstance(ds, dict):
        old = ds
        ds = {"program_profiles": []}
        data["decision_support"] = ds
        log_change(
            logs,
            "Missing/invalid decision_support",
            "decision_support",
            old,
            ds,
            "Created decision_support container for program-level repairs.",
        )
        detected.append("decision_support missing or invalid.")

    profiles = ds.get("program_profiles")
    if not isinstance(profiles, list):
        old = profiles
        profiles = []
        ds["program_profiles"] = profiles
        log_change(
            logs,
            "Invalid program_profiles type",
            "decision_support.program_profiles",
            old,
            profiles,
            "program_profiles must be an array.",
        )
        detected.append("decision_support.program_profiles invalid.")

    if len(profiles) == 0:
        fallback_name = dget(data, "entity.college_name") or dget(data, "source.source_file_name") or "Program"
        fallback = {
            "program_name": str(fallback_name),
            "decision_profile": default_metrics_for_program(str(fallback_name)),
            "career_paths": default_roles_for_program(str(fallback_name), infer_family(str(fallback_name))),
            "employment_outlook": default_outlook(infer_family(str(fallback_name))),
            "best_fit_traits": ["Open to interdisciplinary learning and structured progression"],
            "avoid_if": ["You require a highly specialized track from year one"],
            "summary": f"Heuristic fallback program profile for {fallback_name}.",
            "program_family": infer_family(str(fallback_name)),
            "close_alternatives": [],
            "differentiation_notes": ["Fallback profile created due to missing program entries."],
        }
        profiles.append(fallback)
        log_change(
            logs,
            "Missing program profiles",
            "decision_support.program_profiles",
            [],
            profiles,
            "Added one conservative fallback program profile for completeness.",
        )
        detected.append("No program_profiles found; added fallback profile.")

    all_names = []
    for i, p in enumerate(profiles):
        if isinstance(p, dict):
            all_names.append(str(p.get("program_name") or f"Program {i + 1}"))
        else:
            all_names.append(f"Program {i + 1}")

    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            old = p
            p = {}
            profiles[i] = p
            log_change(
                logs,
                "Non-object program profile entry",
                f"decision_support.program_profiles[{i}]",
                old,
                p,
                "Converted to object for field-level repair.",
            )
            detected.append(f"program_profiles[{i}] was not an object.")
        complete_program_profile(p, i, all_names, logs, detected)

    # Refresh quality_check missing_fields based on official_data only
    quality = data.get("quality_check")
    if not isinstance(quality, dict):
        old = quality
        quality = {}
        data["quality_check"] = quality
        log_change(
            logs,
            "Missing/invalid quality_check",
            "quality_check",
            old,
            quality,
            "Created quality_check object to keep audit consistency.",
        )
    official = data.get("official_data", {})
    off_nulls, off_empties = flatten_null_empty(official, "official_data")
    missing_fields = uniq(off_nulls + off_empties)
    old_missing = quality.get("missing_fields")
    quality["missing_fields"] = missing_fields
    if old_missing != missing_fields:
        log_change(
            logs,
            "Stale/missing quality_check.missing_fields",
            "quality_check.missing_fields",
            old_missing,
            missing_fields,
            "Recomputed from current official_data null/empty paths.",
        )

    # Add uncertainty note if heavy repair
    if len(logs) > 0:
        notes = ensure_list(quality.get("notes"))
        repair_note = "Decision-support fields were repaired heuristically; official_data remained source-grounded."
        if repair_note not in notes:
            notes.append(repair_note)
        quality["notes"] = notes

    # Keep inferred traceability for heuristic corrections
    trace = data.get("traceability")
    if not isinstance(trace, dict):
        trace = {"supported_facts": [], "inferred_items": []}
        data["traceability"] = trace
    inferred = ensure_list(trace.get("inferred_items"))
    inferred_item = {
        "item": "decision_support.program_profiles",
        "basis": "Program profile audit/repair applied for completeness, consistency, and realistic heuristic calibration.",
    }
    if inferred_item not in inferred:
        inferred.append(inferred_item)
    trace["inferred_items"] = inferred

    return detected, logs, data


def make_report(file_name: str, detected: List[str], logs: List[Dict[str, Any]], corrected: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"FILE: {file_name}")
    lines.append(f"TIMESTAMP_UTC: {iso_now()}")
    lines.append("")
    lines.append("1. Detected issues")
    if detected:
        for d in uniq(detected):
            lines.append(f"- {d}")
    else:
        lines.append("- No major structural issues detected.")
    lines.append("")
    lines.append("2. Detailed repair log")
    if logs:
        for row in logs:
            lines.append("")
            lines.append(f"Issue:\n{row['Issue']}")
            lines.append(f"Field:\n{row['Field']}")
            lines.append(f"Old Value:\n{json.dumps(row['Old Value'], ensure_ascii=False)}")
            lines.append(f"New Value:\n{json.dumps(row['New Value'], ensure_ascii=False)}")
            lines.append(f"Reason:\n{row['Reason']}")
    else:
        lines.append("- No value changes were required.")
    lines.append("")
    lines.append("3. Final corrected JSON file")
    lines.append(json.dumps(corrected, ensure_ascii=False, indent=2))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    files = sorted([f for f in os.listdir(BASE_DIR) if f.lower().endswith(".normalized.v2.json")])
    for file_name in files:
        path = os.path.join(BASE_DIR, file_name)
        detected, logs, corrected = process_file(path)
        write_json_atomic(path, corrected)
        report_name = f"{os.path.splitext(file_name)[0]}.audit_repair_report.txt"
        report_path = os.path.join(BASE_DIR, report_name)
        write_text_atomic(report_path, make_report(file_name, detected, logs, corrected))
        print(f"REPAIR CHECKPOINT: completed_file={file_name} | status=done", flush=True)


if __name__ == "__main__":
    main()
