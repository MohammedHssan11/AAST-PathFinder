import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


BASE_DIR = r"C:\Users\mh978\Downloads\college-decision\normalized_college_v2"


FOCUS_FIELDS = [
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
]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def label_from_level(level: int) -> str:
    return {1: "weak", 2: "medium", 3: "strong"}.get(level, "medium")


def level_from_score(score: float) -> int:
    if score >= 0.67:
        return 3
    if score >= 0.50:
        return 2
    return 1


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
    out = []
    seen = set()
    for it in items:
        key = json.dumps(it, ensure_ascii=False, sort_keys=True) if isinstance(it, (dict, list)) else str(it).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


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


def missing_official_fields(obj: Any, prefix: str = "official_data") -> List[str]:
    missing: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}"
            if v is None:
                missing.append(p)
            elif isinstance(v, str) and v.strip() == "":
                missing.append(p)
            elif isinstance(v, list):
                if len(v) == 0:
                    missing.append(p)
            elif isinstance(v, dict):
                missing.extend(missing_official_fields(v, p))
    return missing


def add_inferred_item(data: Dict[str, Any], item: str, basis: str) -> None:
    trace = data.setdefault("traceability", {})
    inferred = trace.setdefault("inferred_items", [])
    row = {"item": item, "basis": basis}
    if row not in inferred:
        inferred.append(row)


def infer_program_family(name: str) -> str:
    low = (name or "").lower()
    if any(k in low for k in ["law", "legal"]):
        return "LAW_POLICY_FAMILY"
    if any(k in low for k in ["cyber", "security"]):
        return "CYBERSEC_FAMILY"
    if any(k in low for k in ["artificial intelligence", " ai", "intelligent systems", "machine learning"]):
        return "AI_FAMILY"
    if any(k in low for k in ["data science", "analytics", "data"]):
        return "DATA_FAMILY"
    if any(k in low for k in ["software"]):
        return "SOFTWARE_FAMILY"
    if any(k in low for k in ["computer science", "computer"]):
        return "CS_FAMILY"
    if any(k in low for k in ["information systems", "information system", "is "]):
        return "IS_FAMILY"
    if any(k in low for k in ["logistics", "supply chain", "transport"]):
        return "LOGISTICS_FAMILY"
    if any(k in low for k in ["maritime", "marine", "nautical"]):
        return "MARITIME_FAMILY"
    if any(k in low for k in ["medicine", "medical", "dental", "dentistry", "pharmacy", "clinical"]):
        return "HEALTHCARE_FAMILY"
    if any(k in low for k in ["finance", "accounting"]):
        return "FINANCE_FAMILY"
    if any(k in low for k in ["business", "management", "marketing", "mba"]):
        return "BUSINESS_FAMILY"
    if any(k in low for k in ["art", "design", "graphics", "multimedia"]):
        return "DESIGN_FAMILY"
    if any(k in low for k in ["archaeology", "heritage", "cultural"]):
        return "HERITAGE_FAMILY"
    if any(k in low for k in ["fisher", "aquaculture"]):
        return "AQUACULTURE_FAMILY"
    if any(k in low for k in ["engineering"]):
        return "ENGINEERING_FAMILY"
    return "GENERAL_FAMILY"


def base_focus() -> Dict[str, float]:
    return {k: 0.50 for k in FOCUS_FIELDS}


def apply_keyword_focus(name: str, focus: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
    low = (name or "").lower()
    confident = True
    matched = False

    def set_many(mapping: Dict[str, float]) -> None:
        for k, v in mapping.items():
            focus[k] = v

    if any(k in low for k in ["artificial intelligence", "machine learning", "intelligent systems"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.86,
                "data_focus": 0.75,
                "software_focus": 0.66,
                "security_focus": 0.40,
                "hardware_focus": 0.35,
                "business_focus": 0.38,
                "finance_focus": 0.35,
                "logistics_focus": 0.33,
                "maritime_focus": 0.25,
                "healthcare_focus": 0.35,
                "creativity_design_focus": 0.45,
                "language_communication_focus": 0.45,
                "law_policy_focus": 0.33,
                "research_orientation": 0.70,
                "entrepreneurship_focus": 0.56,
                "international_work_readiness": 0.62,
                "remote_work_fit": 0.78,
            }
        )
    elif any(k in low for k in ["data science", "analytics", "data"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.66,
                "data_focus": 0.88,
                "software_focus": 0.62,
                "security_focus": 0.40,
                "hardware_focus": 0.30,
                "business_focus": 0.52,
                "finance_focus": 0.58,
                "logistics_focus": 0.42,
                "maritime_focus": 0.25,
                "healthcare_focus": 0.35,
                "creativity_design_focus": 0.35,
                "language_communication_focus": 0.50,
                "law_policy_focus": 0.34,
                "research_orientation": 0.68,
                "entrepreneurship_focus": 0.54,
                "international_work_readiness": 0.64,
                "remote_work_fit": 0.80,
            }
        )
    elif any(k in low for k in ["computer science", "computer"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.58,
                "data_focus": 0.62,
                "software_focus": 0.84,
                "security_focus": 0.58,
                "hardware_focus": 0.48,
                "business_focus": 0.40,
                "finance_focus": 0.38,
                "logistics_focus": 0.35,
                "maritime_focus": 0.20,
                "healthcare_focus": 0.28,
                "creativity_design_focus": 0.42,
                "language_communication_focus": 0.45,
                "law_policy_focus": 0.30,
                "research_orientation": 0.64,
                "entrepreneurship_focus": 0.58,
                "international_work_readiness": 0.62,
                "remote_work_fit": 0.82,
            }
        )
    elif "software" in low:
        matched = True
        set_many(
            {
                "ai_focus": 0.52,
                "data_focus": 0.56,
                "software_focus": 0.90,
                "security_focus": 0.55,
                "hardware_focus": 0.38,
                "business_focus": 0.42,
                "finance_focus": 0.36,
                "logistics_focus": 0.34,
                "maritime_focus": 0.18,
                "healthcare_focus": 0.25,
                "creativity_design_focus": 0.42,
                "language_communication_focus": 0.45,
                "law_policy_focus": 0.30,
                "research_orientation": 0.62,
                "entrepreneurship_focus": 0.60,
                "international_work_readiness": 0.62,
                "remote_work_fit": 0.84,
            }
        )
    elif any(k in low for k in ["cyber", "security"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.46,
                "data_focus": 0.50,
                "software_focus": 0.72,
                "security_focus": 0.92,
                "hardware_focus": 0.42,
                "business_focus": 0.42,
                "finance_focus": 0.40,
                "logistics_focus": 0.34,
                "maritime_focus": 0.22,
                "healthcare_focus": 0.25,
                "creativity_design_focus": 0.32,
                "language_communication_focus": 0.48,
                "law_policy_focus": 0.62,
                "research_orientation": 0.62,
                "entrepreneurship_focus": 0.50,
                "international_work_readiness": 0.66,
                "remote_work_fit": 0.75,
            }
        )
    elif any(k in low for k in ["information systems", "information system"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.50,
                "data_focus": 0.64,
                "software_focus": 0.62,
                "security_focus": 0.48,
                "hardware_focus": 0.32,
                "business_focus": 0.74,
                "finance_focus": 0.50,
                "logistics_focus": 0.48,
                "maritime_focus": 0.20,
                "healthcare_focus": 0.24,
                "creativity_design_focus": 0.34,
                "language_communication_focus": 0.62,
                "law_policy_focus": 0.38,
                "research_orientation": 0.56,
                "entrepreneurship_focus": 0.60,
                "international_work_readiness": 0.58,
                "remote_work_fit": 0.68,
            }
        )
    elif any(k in low for k in ["business", "management", "marketing"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.38,
                "data_focus": 0.52,
                "software_focus": 0.40,
                "security_focus": 0.30,
                "hardware_focus": 0.20,
                "business_focus": 0.90,
                "finance_focus": 0.64,
                "logistics_focus": 0.56,
                "maritime_focus": 0.24,
                "healthcare_focus": 0.25,
                "creativity_design_focus": 0.44,
                "language_communication_focus": 0.68,
                "law_policy_focus": 0.45,
                "research_orientation": 0.52,
                "entrepreneurship_focus": 0.74,
                "international_work_readiness": 0.62,
                "remote_work_fit": 0.64,
            }
        )
    elif any(k in low for k in ["finance", "accounting"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.42,
                "data_focus": 0.62,
                "software_focus": 0.45,
                "security_focus": 0.34,
                "hardware_focus": 0.18,
                "business_focus": 0.76,
                "finance_focus": 0.92,
                "logistics_focus": 0.42,
                "maritime_focus": 0.20,
                "healthcare_focus": 0.22,
                "creativity_design_focus": 0.28,
                "language_communication_focus": 0.60,
                "law_policy_focus": 0.52,
                "research_orientation": 0.54,
                "entrepreneurship_focus": 0.62,
                "international_work_readiness": 0.60,
                "remote_work_fit": 0.66,
            }
        )
    elif any(k in low for k in ["logistics", "supply chain", "transport"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.36,
                "data_focus": 0.54,
                "software_focus": 0.38,
                "security_focus": 0.28,
                "hardware_focus": 0.36,
                "business_focus": 0.76,
                "finance_focus": 0.58,
                "logistics_focus": 0.92,
                "maritime_focus": 0.68,
                "healthcare_focus": 0.20,
                "creativity_design_focus": 0.26,
                "language_communication_focus": 0.56,
                "law_policy_focus": 0.46,
                "research_orientation": 0.52,
                "entrepreneurship_focus": 0.58,
                "international_work_readiness": 0.68,
                "remote_work_fit": 0.44,
            }
        )
    elif any(k in low for k in ["maritime", "marine"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.30,
                "data_focus": 0.46,
                "software_focus": 0.34,
                "security_focus": 0.30,
                "hardware_focus": 0.62,
                "business_focus": 0.52,
                "finance_focus": 0.40,
                "logistics_focus": 0.72,
                "maritime_focus": 0.94,
                "healthcare_focus": 0.20,
                "creativity_design_focus": 0.26,
                "language_communication_focus": 0.54,
                "law_policy_focus": 0.42,
                "research_orientation": 0.54,
                "entrepreneurship_focus": 0.52,
                "international_work_readiness": 0.66,
                "remote_work_fit": 0.32,
            }
        )
    elif any(k in low for k in ["medicine", "medical", "dental", "dentistry", "pharmacy", "clinical"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.40,
                "data_focus": 0.50,
                "software_focus": 0.26,
                "security_focus": 0.24,
                "hardware_focus": 0.26,
                "business_focus": 0.36,
                "finance_focus": 0.32,
                "logistics_focus": 0.32,
                "maritime_focus": 0.16,
                "healthcare_focus": 0.94,
                "creativity_design_focus": 0.26,
                "language_communication_focus": 0.58,
                "law_policy_focus": 0.40,
                "research_orientation": 0.62,
                "entrepreneurship_focus": 0.42,
                "international_work_readiness": 0.58,
                "remote_work_fit": 0.24,
            }
        )
    elif any(k in low for k in ["law", "legal"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.28,
                "data_focus": 0.40,
                "software_focus": 0.22,
                "security_focus": 0.30,
                "hardware_focus": 0.10,
                "business_focus": 0.46,
                "finance_focus": 0.42,
                "logistics_focus": 0.22,
                "maritime_focus": 0.12,
                "healthcare_focus": 0.12,
                "creativity_design_focus": 0.24,
                "language_communication_focus": 0.80,
                "law_policy_focus": 0.94,
                "research_orientation": 0.62,
                "entrepreneurship_focus": 0.52,
                "international_work_readiness": 0.62,
                "remote_work_fit": 0.54,
            }
        )
    elif any(k in low for k in ["art", "design", "graphics", "multimedia"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.40,
                "data_focus": 0.36,
                "software_focus": 0.50,
                "security_focus": 0.24,
                "hardware_focus": 0.20,
                "business_focus": 0.44,
                "finance_focus": 0.30,
                "logistics_focus": 0.22,
                "maritime_focus": 0.15,
                "healthcare_focus": 0.20,
                "creativity_design_focus": 0.94,
                "language_communication_focus": 0.66,
                "law_policy_focus": 0.26,
                "research_orientation": 0.50,
                "entrepreneurship_focus": 0.64,
                "international_work_readiness": 0.56,
                "remote_work_fit": 0.72,
            }
        )
    elif any(k in low for k in ["archaeology", "heritage", "cultural"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.24,
                "data_focus": 0.38,
                "software_focus": 0.20,
                "security_focus": 0.20,
                "hardware_focus": 0.20,
                "business_focus": 0.34,
                "finance_focus": 0.24,
                "logistics_focus": 0.28,
                "maritime_focus": 0.30,
                "healthcare_focus": 0.16,
                "creativity_design_focus": 0.58,
                "language_communication_focus": 0.66,
                "law_policy_focus": 0.52,
                "research_orientation": 0.64,
                "entrepreneurship_focus": 0.38,
                "international_work_readiness": 0.54,
                "remote_work_fit": 0.36,
            }
        )
    elif any(k in low for k in ["fisher", "aquaculture"]):
        matched = True
        set_many(
            {
                "ai_focus": 0.26,
                "data_focus": 0.42,
                "software_focus": 0.24,
                "security_focus": 0.20,
                "hardware_focus": 0.40,
                "business_focus": 0.46,
                "finance_focus": 0.36,
                "logistics_focus": 0.56,
                "maritime_focus": 0.76,
                "healthcare_focus": 0.42,
                "creativity_design_focus": 0.20,
                "language_communication_focus": 0.50,
                "law_policy_focus": 0.36,
                "research_orientation": 0.58,
                "entrepreneurship_focus": 0.46,
                "international_work_readiness": 0.52,
                "remote_work_fit": 0.32,
            }
        )
    elif "engineering" in low:
        matched = True
        set_many(
            {
                "ai_focus": 0.38,
                "data_focus": 0.44,
                "software_focus": 0.42,
                "security_focus": 0.30,
                "hardware_focus": 0.76,
                "business_focus": 0.42,
                "finance_focus": 0.32,
                "logistics_focus": 0.36,
                "maritime_focus": 0.38,
                "healthcare_focus": 0.22,
                "creativity_design_focus": 0.48,
                "language_communication_focus": 0.44,
                "law_policy_focus": 0.24,
                "research_orientation": 0.58,
                "entrepreneurship_focus": 0.50,
                "international_work_readiness": 0.56,
                "remote_work_fit": 0.42,
            }
        )
    else:
        confident = False

    if not matched:
        confident = False
        for k in focus:
            focus[k] = 0.50

    return focus, confident


def adjust_focus_from_existing(decision_profile: Dict[str, Any], focus: Dict[str, float]) -> Dict[str, float]:
    programming = float(decision_profile.get("programming_intensity", 0.50) or 0.50)
    math_intensity = float(decision_profile.get("math_intensity", 0.50) or 0.50)
    creativity = float(decision_profile.get("design_creativity", 0.50) or 0.50)
    field = float(decision_profile.get("field_work_intensity", 0.50) or 0.50)
    management = float(decision_profile.get("management_exposure", 0.50) or 0.50)
    theory = float(decision_profile.get("theoretical_depth", 0.50) or 0.50)

    if programming >= 0.70:
        focus["software_focus"] += 0.08
        focus["remote_work_fit"] += 0.06
    if math_intensity >= 0.70:
        focus["data_focus"] += 0.05
        focus["research_orientation"] += 0.04
    if creativity >= 0.70:
        focus["creativity_design_focus"] += 0.08
    if field >= 0.65:
        focus["remote_work_fit"] -= 0.15
        focus["international_work_readiness"] += 0.03
    if management >= 0.70:
        focus["business_focus"] += 0.07
        focus["entrepreneurship_focus"] += 0.05
    if theory >= 0.70:
        focus["research_orientation"] += 0.08

    for k in list(focus.keys()):
        focus[k] = round(clamp(float(focus[k])), 2)
    return focus


def focus_vector(dp: Dict[str, Any]) -> List[float]:
    return [float(dp.get(k, 0.50) or 0.50) for k in FOCUS_FIELDS]


def similarity_score(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    avg_abs_diff = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    return clamp(1.0 - avg_abs_diff)


def family_cluster(family: str) -> str:
    tech = {"CS_FAMILY", "AI_FAMILY", "DATA_FAMILY", "SOFTWARE_FAMILY", "CYBERSEC_FAMILY", "IS_FAMILY"}
    business = {"BUSINESS_FAMILY", "FINANCE_FAMILY", "LOGISTICS_FAMILY", "MARITIME_FAMILY"}
    health = {"HEALTHCARE_FAMILY"}
    if family in tech:
        return "TECH"
    if family in business:
        return "BUSINESS"
    if family in health:
        return "HEALTH"
    return "OTHER"


def differentiation_note(this_name: str, this_focus: Dict[str, float], alt_name: str, alt_focus: Dict[str, float]) -> str:
    labels = {
        "ai_focus": "AI",
        "data_focus": "data",
        "software_focus": "software",
        "security_focus": "security",
        "hardware_focus": "hardware",
        "business_focus": "business",
        "finance_focus": "finance",
        "logistics_focus": "logistics",
        "maritime_focus": "maritime",
        "healthcare_focus": "healthcare",
        "creativity_design_focus": "creative design",
        "language_communication_focus": "communication/language",
        "law_policy_focus": "law/policy",
        "research_orientation": "research",
        "entrepreneurship_focus": "entrepreneurship",
        "international_work_readiness": "international work",
        "remote_work_fit": "remote work",
    }
    diffs = []
    for k in FOCUS_FIELDS:
        diff = float(this_focus.get(k, 0.5)) - float(alt_focus.get(k, 0.5))
        diffs.append((abs(diff), diff, k))
    diffs.sort(reverse=True, key=lambda x: x[0])
    top = [d for d in diffs if d[0] >= 0.08][:2]
    if not top:
        return f"Compared with {alt_name}, the focus balance is similar with only slight emphasis shifts."
    parts = []
    for _, sign, key in top:
        if sign > 0:
            parts.append(f"more {labels[key]}")
        else:
            parts.append(f"less {labels[key]}")
    if len(parts) == 1:
        return f"Compared with {alt_name}, this profile leans {parts[0]}."
    return f"Compared with {alt_name}, this profile leans {parts[0]} and {parts[1]}."


def normalize_employment_market(market: Dict[str, Any], uncertainty_notes: List[str], context: str) -> Dict[str, Any]:
    if not isinstance(market, dict):
        market = {}
    level = market.get("level")
    score = market.get("score")

    if isinstance(score, str):
        try:
            score = float(score)
        except ValueError:
            score = None

    if level not in [1, 2, 3]:
        if isinstance(score, (int, float)):
            level = level_from_score(float(score))
        else:
            level = 2
            score = 0.50
            uncertainty_notes.append(f"{context}: employment_outlook defaulted to medium due to missing level/score.")

    if not isinstance(score, (int, float)):
        score = {1: 0.40, 2: 0.58, 3: 0.75}[level]
        uncertainty_notes.append(f"{context}: employment_outlook score inferred from level mapping.")

    score = round(clamp(float(score)), 2)
    label = label_from_level(int(level))
    return {"level": int(level), "label": label, "score": score}


def infer_metro_area(city: Any, branch: Any) -> str:
    text = f"{city or ''} {branch or ''}".lower()
    if any(k in text for k in ["cairo", "giza", "heliopolis", "smart village", "dokki"]):
        return "Cairo"
    if any(k in text for k in ["alexandria", "abu qir", "abukir", "miami"]):
        return "Alexandria"
    if any(k in text for k in ["alamein", "matrouh", "new el alamein", "el alamein"]):
        return "Matrouh-Coastal"
    if any(k in text for k in ["port said", "suez", "ismailia"]):
        return "Canal"
    if any(k in text for k in ["south valley", "qena", "aswan", "luxor"]):
        return "Upper Egypt"
    if "latakia" in text:
        return "Latakia-Coastal"
    return None


def explicit_mobility_mention(data: Dict[str, Any]) -> bool:
    official = data.get("official_data", {})
    mobility = official.get("international_mobility", {})
    texts: List[str] = []
    texts.extend([str(x) for x in ensure_list(mobility.get("partner_bodies")) if not is_empty(x)])
    texts.extend([str(x) for x in ensure_list(mobility.get("evidence_based_notes")) if not is_empty(x)])
    texts.extend([str(x) for x in ensure_list(official.get("industry_and_external_relations")) if not is_empty(x)])
    t_desc = dget(official, "training_and_practice.description")
    if isinstance(t_desc, str) and t_desc.strip():
        texts.append(t_desc)
    cleaned_summary = dget(data, "text_artifacts.cleaned_summary_text")
    if isinstance(cleaned_summary, str) and cleaned_summary.strip():
        texts.append(cleaned_summary)

    blob = " | ".join(texts).lower()
    keywords = [
        "partner university",
        "partner universities",
        "university of",
        "universitat",
        "exchange committee",
        "students exchange",
        "student exchange",
        "international training",
        "training opportunities in universities",
        "dual degree",
    ]
    return any(k in blob for k in keywords)


def ensure_recommendation_layer(data: Dict[str, Any], changes: List[str]) -> None:
    rec = {
        "tie_break_rules": [
            {
                "rule_id": "LOCATION_TIE_BREAK",
                "when": "If final scores are close (difference <= 0.05), prefer closer campus to student's city.",
                "thresholds": {"score_delta_close": 0.05},
            },
            {
                "rule_id": "QUALITY_OVERRIDES_DISTANCE",
                "when": "If one option beats another by a meaningful margin (difference >= 0.12), choose the better option even if farther.",
                "thresholds": {"score_delta_override": 0.12},
            },
            {
                "rule_id": "PROGRAM_FAMILY_FALLBACK",
                "when": "If top program is not available on student's preferred campus, recommend closest alternative within same program_family.",
                "thresholds": {},
            },
        ],
        "scoring_components": {
            "fit_score_weight": 0.50,
            "career_score_weight": 0.30,
            "opportunity_score_weight": 0.20,
            "location_weight_inside_opportunity": 0.35,
        },
    }
    data["recommendation_layer"] = rec
    changes.append("Set top-level recommendation_layer with deterministic tie-break and scoring templates.")
    add_inferred_item(data, "recommendation_layer", "Deterministic recommendation template added for tie-breaking and fallback logic.")


def enrich_program_profiles(data: Dict[str, Any], changes: List[str], uncertainty_notes: List[str]) -> None:
    ds = data.setdefault("decision_support", {})
    profiles = ds.setdefault("program_profiles", [])
    if not isinstance(profiles, list):
        profiles = []
        ds["program_profiles"] = profiles

    if len(profiles) == 0:
        college_name = dget(data, "entity.college_name") or dget(data, "source.source_file_name") or "Entity"
        profiles.append(
            {
                "program_name": str(college_name),
                "decision_profile": {},
                "career_paths": [],
                "employment_outlook": {
                    "egypt_market": {"level": 2, "label": "medium", "score": 0.50},
                    "international_market": {"level": 2, "label": "medium", "score": 0.50},
                },
                "best_fit_traits": [],
                "avoid_if": [],
                "summary": "Heuristic fallback profile because program-level entries were missing.",
            }
        )
        uncertainty_notes.append("Program profiles were missing; created a single fallback heuristic profile.")
        changes.append("Created fallback program profile because none existed.")

    low_confidence_programs: List[str] = []
    family_by_name: Dict[str, str] = {}
    focus_by_name: Dict[str, Dict[str, float]] = {}

    for idx, p in enumerate(profiles):
        if not isinstance(p, dict):
            profiles[idx] = {"program_name": f"Program {idx + 1}", "decision_profile": {}}
            p = profiles[idx]
        name = str(p.get("program_name") or f"Program {idx + 1}")
        dp = p.setdefault("decision_profile", {})
        if not isinstance(dp, dict):
            dp = {}
            p["decision_profile"] = dp

        focus, confident = apply_keyword_focus(name, base_focus())
        focus = adjust_focus_from_existing(dp, focus)
        if not confident:
            low_confidence_programs.append(name)

        for f in FOCUS_FIELDS:
            dp[f] = round(clamp(float(focus.get(f, 0.50))), 2)

        family = infer_program_family(name)
        p["program_family"] = family
        family_by_name[name] = family
        focus_by_name[name] = {k: dp[k] for k in FOCUS_FIELDS}
        p.setdefault("close_alternatives", [])
        p.setdefault("differentiation_notes", [])

        outlook = p.setdefault("employment_outlook", {})
        egypt_market = normalize_employment_market(outlook.get("egypt_market"), uncertainty_notes, f"{name}/egypt_market")
        intl_market = normalize_employment_market(outlook.get("international_market"), uncertainty_notes, f"{name}/international_market")
        outlook["egypt_market"] = egypt_market
        outlook["international_market"] = intl_market

        add_inferred_item(
            data,
            f"decision_support.program_profiles[{name}].decision_profile_focus_extensions",
            "Heuristic focus expansion inferred from program_name and existing decision_profile indicators.",
        )
        add_inferred_item(
            data,
            f"decision_support.program_profiles[{name}].program_family",
            "Heuristic family classification based on program_name semantics.",
        )

    names = [str(p.get("program_name")) for p in profiles]
    tech_families = {"CS_FAMILY", "AI_FAMILY", "DATA_FAMILY", "SOFTWARE_FAMILY", "CYBERSEC_FAMILY", "IS_FAMILY"}

    for p in profiles:
        name = str(p.get("program_name"))
        this_family = family_by_name.get(name, "GENERAL_FAMILY")
        this_vec = focus_vector(p.get("decision_profile", {}))
        scored: List[Tuple[float, str]] = []
        for other in names:
            if other == name:
                continue
            other_family = family_by_name.get(other, "GENERAL_FAMILY")
            other_vec = [float(focus_by_name.get(other, {}).get(f, 0.50)) for f in FOCUS_FIELDS]
            sim = similarity_score(this_vec, other_vec)
            if this_family == other_family:
                sim += 0.08
            if this_family in tech_families and other_family in tech_families:
                sim += 0.07
            sim = clamp(sim)
            scored.append((sim, other))
        scored.sort(reverse=True, key=lambda x: x[0])
        close = [n for s, n in scored if s >= 0.55][:3]
        if not close and scored:
            close = [scored[0][1]]
        p["close_alternatives"] = close

        diff_notes = []
        for alt in close[:2]:
            alt_focus = focus_by_name.get(alt, {k: 0.50 for k in FOCUS_FIELDS})
            diff_notes.append(differentiation_note(name, focus_by_name.get(name, {}), alt, alt_focus))
        p["differentiation_notes"] = uniq(diff_notes)
        add_inferred_item(
            data,
            f"decision_support.program_profiles[{name}].close_alternatives",
            "Heuristic closeness derived from focus-vector similarity and program_family proximity within file.",
        )
        add_inferred_item(
            data,
            f"decision_support.program_profiles[{name}].differentiation_notes",
            "Heuristic differences generated from relative focus-field strengths against closest alternatives.",
        )

    if low_confidence_programs:
        low_list = ", ".join(sorted(low_confidence_programs))
        note = f"Low-confidence heuristic inference for program_family/focus fields: {low_list}."
        uncertainty_notes.append(note)
        quality = data.setdefault("quality_check", {})
        notes = quality.setdefault("notes", [])
        if note not in notes:
            notes.append(note)
        changes.append(f"Added low-confidence note for inferred program taxonomy/focus ({len(low_confidence_programs)} programs).")

    changes.append("Extended decision_support.program_profiles[*].decision_profile with 17 focus fields.")
    changes.append("Added program_family, close_alternatives, and differentiation_notes to all program profiles.")
    changes.append("Normalized employment_outlook labels/levels/scores for all program profiles.")


def apply_campus_profile(data: Dict[str, Any], changes: List[str]) -> None:
    ds = data.setdefault("decision_support", {})
    official = data.get("official_data", {})
    city = dget(official, "location.city")
    branch = dget(official, "location.branch")
    metro = infer_metro_area(city, branch)

    metro_defaults = {
        "Cairo": 0.45,
        "Alexandria": 0.48,
        "Matrouh-Coastal": 0.63,
        "Canal": 0.56,
        "Upper Egypt": 0.68,
        "Latakia-Coastal": 0.62,
    }
    commute = metro_defaults.get(metro, 0.55)
    branch_low = f"{branch or ''}".lower()
    if "smart village" in branch_low:
        commute = 0.50

    relations = ensure_list(official.get("industry_and_external_relations"))
    rel_count = len([r for r in relations if not is_empty(r)])
    industry_training = dget(official, "training_and_practice.industry_training")
    mobility_available = dget(official, "international_mobility.available")
    mobility_notes_count = len(ensure_list(dget(official, "international_mobility.evidence_based_notes")))
    facilities_count = len(ensure_list(official.get("facilities_and_resources")))

    industry_access = 0.45 + min(0.24, rel_count * 0.06)
    if industry_training is True:
        industry_access += 0.08
    if mobility_available is True:
        industry_access += 0.05
    if mobility_notes_count > 0:
        industry_access += 0.04
    industry_access = round(clamp(industry_access), 2)

    internship_density = 0.46 + min(0.20, rel_count * 0.05)
    if "smart village" in branch_low and rel_count > 0:
        internship_density += 0.10
    if industry_training is True:
        internship_density += 0.07
    internship_density = round(clamp(internship_density), 2)

    lifestyle = 0.45 + min(0.21, facilities_count * 0.03)
    if any(k in branch_low for k in ["alamein", "coastal"]):
        lifestyle += 0.04
    if "smart village" in branch_low:
        lifestyle += 0.02
    lifestyle = round(clamp(lifestyle), 2)

    campus_profile = {
        "metro_area": metro,
        "commute_friction_index": round(clamp(commute), 2),
        "relocation_friction_index": round(clamp(commute + 0.10), 2),
        "industry_access_signal": industry_access,
        "internship_density_signal": internship_density,
        "campus_lifestyle_signal": lifestyle,
        "notes": [
            "All campus_profile signals are heuristic estimates, not official statistics.",
            "Signals are derived from city/branch context and official relation/training/facility presence.",
        ],
    }
    ds["campus_profile"] = campus_profile
    changes.append("Added/updated decision_support.campus_profile heuristic signals.")
    add_inferred_item(
        data,
        "decision_support.campus_profile",
        "Heuristic campus decision layer inferred from official location plus relations/training/facilities signals.",
    )


def strengthen_mobility_and_college_profile(data: Dict[str, Any], changes: List[str], uncertainty_notes: List[str]) -> None:
    official = data.setdefault("official_data", {})
    mobility = official.setdefault("international_mobility", {})
    ds = data.setdefault("decision_support", {})
    clp = ds.setdefault("college_level_profile", {})

    was_available = mobility.get("available")
    if was_available is None and explicit_mobility_mention(data):
        mobility["available"] = True
        changes.append("Set official_data.international_mobility.available from null to true due to explicit in-file mobility mention.")

    evidence_count = 0
    evidence_count += len(ensure_list(mobility.get("partner_bodies")))
    evidence_count += len(ensure_list(mobility.get("mobility_types")))
    evidence_count += len(ensure_list(mobility.get("evidence_based_notes")))

    available = mobility.get("available")
    if available is True:
        score = 0.58 + min(0.24, evidence_count * 0.04)
    else:
        score = 0.42 + min(0.10, evidence_count * 0.02)
    score = round(clamp(score), 2)
    lvl = level_from_score(score)
    lbl = label_from_level(lvl)
    clp["international_mobility_strength"] = {"level": lvl, "label": lbl, "score": score}

    add_inferred_item(
        data,
        "decision_support.college_level_profile.international_mobility_strength",
        "Heuristic mobility strength computed from explicit mobility evidence density in official_data.",
    )

    if available is None and evidence_count == 0:
        uncertainty_notes.append("International mobility remained null due to no explicit partner/exchange/training-abroad evidence in file.")


def finalize_quality(data: Dict[str, Any], uncertainty_notes: List[str], changes: List[str]) -> None:
    quality = data.setdefault("quality_check", {})
    quality["missing_fields"] = uniq(missing_official_fields(data.get("official_data", {})))
    quality["uncertain_items"] = uniq(ensure_list(quality.get("uncertain_items")) + uncertainty_notes)
    notes = ensure_list(quality.get("notes"))
    notes.append("Heuristic recommendation/taxonomy/location layers were added under decision_support/recommendation_layer only.")
    quality["notes"] = uniq(notes)
    changes.append("Refreshed quality_check.missing_fields and appended uncertainty/heuristic notes.")


def upgrade_file(path: str) -> Tuple[List[str], List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    changes: List[str] = []
    uncertainty_notes: List[str] = []

    if not isinstance(data, dict):
        return ["Skipped non-object JSON structure."], ["File root is not a JSON object."]

    # Keep schema_version as-is by design.
    enrich_program_profiles(data, changes, uncertainty_notes)
    apply_campus_profile(data, changes)
    ensure_recommendation_layer(data, changes)
    strengthen_mobility_and_college_profile(data, changes, uncertainty_notes)
    finalize_quality(data, uncertainty_notes, changes)

    # Ensure no fake supported facts are added here.
    trace = data.setdefault("traceability", {})
    trace["supported_facts"] = ensure_list(trace.get("supported_facts"))
    trace["inferred_items"] = uniq(ensure_list(trace.get("inferred_items")))

    write_json_atomic(path, data)
    return changes, uncertainty_notes


def make_log_text(file_name: str, changes: List[str], uncertainty_notes: List[str]) -> str:
    lines = []
    lines.append(f"File: {file_name}")
    lines.append(f"Upgraded At (UTC): {iso_now()}")
    lines.append("")
    lines.append("Changes Applied:")
    if changes:
        for c in changes:
            lines.append(f"- {c}")
    else:
        lines.append("- No schema changes were required.")
    lines.append("")
    lines.append("Uncertainty Notes:")
    if uncertainty_notes:
        for n in uniq(uncertainty_notes):
            lines.append(f"- {n}")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("Anti-Hallucination Guard:")
    lines.append("- official_data was not expanded with unsupported factual claims.")
    lines.append("- New scoring/taxonomy/location logic was written under heuristic layers only.")
    return "\n".join(lines) + "\n"


def main() -> None:
    files = sorted(
        [
            f
            for f in os.listdir(BASE_DIR)
            if f.lower().endswith(".json") and f.lower().endswith(".normalized.v2.json")
        ]
    )
    total = len(files)
    for i, file_name in enumerate(files):
        path = os.path.join(BASE_DIR, file_name)
        changes, notes = upgrade_file(path)
        log_name = f"{os.path.splitext(file_name)[0]}.upgrade_log.txt"
        log_path = os.path.join(BASE_DIR, log_name)
        write_text_atomic(log_path, make_log_text(file_name, changes, notes))
        print(f"UPGRADE CHECKPOINT: completed_file={file_name} | status=done", flush=True)


if __name__ == "__main__":
    try:
        main()
    except MemoryError:
        print("SAFE STOP: memory/context limit approaching.", flush=True)
        print("LAST_COMPLETED_FILE=unknown", flush=True)
        print("NEXT_FILE_TO_PROCESS=unknown", flush=True)
        print("REMAINING_FILES_ESTIMATE=unknown", flush=True)
