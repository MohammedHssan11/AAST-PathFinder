import json
import os
from typing import Any, Dict, List


BASE_DIR = r"C:\Users\mh978\Downloads\college-decision\normalized_college_v2"

TARGET_FILES = [
    "College_of_Management_and_Technology_Dokki.normalized.v2.json",
    "College_of_International_Transport_and_Logistics.normalized.v2.json",
    "College_of_International_Transport_and_Logistics_Abukir.normalized.v2.json",
    "College_of_International_Transport_and_Logistics_Dokki.normalized.v2.json",
    "College_of_International_Transport_and_Logistics_El_Alamein.normalized.v2.json",
]

LOGISTICS_MAJORS = [
    "Logistics and Supply Chain Management",
    "Transport Logistics Management",
    "International Trade Logistics",
    "Energy and Petroleum Logistics Management",
]

LOGISTICS_FACILITIES = [
    "Logistics simulation labs",
    "Supply chain analytics labs",
    "Transport planning labs",
    "Case study classrooms",
    "Industry training partnerships",
    "Business incubators",
]

ADMISSION_CERTS = [
    "Egyptian Thanaweya Amma",
    "IGCSE",
    "American Diploma",
    "Arab High School Certificates",
]

LOGISTICS_ROLES = [
    "Supply Chain Analyst",
    "Logistics Planner",
    "Freight Forwarding Specialist",
    "Procurement Analyst",
    "Transport Operations Manager",
    "Trade Compliance Analyst",
    "Warehouse Operations Manager",
]


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


def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def normalize_leadership(leadership: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not isinstance(leadership, list):
        return out

    for item in leadership:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            title = str(item.get("title") or item.get("role") or "").strip()
            period = str(item.get("period") or "").strip()
            if name or title or period:
                out.append({"name": name, "title": title, "period": period})
        elif isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            # Common pattern: "key: value"
            if ":" in text:
                left, right = text.split(":", 1)
                out.append({"name": right.strip(), "title": left.strip(), "period": ""})
            else:
                out.append({"name": text, "title": "", "period": ""})
    return out


def overview_defaults(file_name: str) -> Dict[str, str]:
    key = file_name.lower()
    if "management_and_technology_dokki" in key:
        return {
            "short_description": "A business-focused academic college at AASTMT Dokki offering management, finance, information systems, and logistics-oriented programs with practical learning pathways.",
            "current_status": "Active undergraduate business and management programs with applied projects and industry-connected learning activities.",
            "future_prospectus": "Expanding interdisciplinary business, digital commerce, and logistics education aligned with labor-market needs and innovation-driven entrepreneurship.",
        }
    if "international_transport_and_logistics_abukir" in key:
        return {
            "short_description": "A specialized college focused on international transport, logistics, and supply chain education with applied professional orientation at the Abu Kir branch.",
            "current_status": "Active logistics and transport-related academic programs supported by practical training and industry engagement.",
            "future_prospectus": "Strengthening regional and international logistics competencies through updated curricula, data-informed decision training, and industry partnerships.",
        }
    if "international_transport_and_logistics_dokki" in key:
        return {
            "short_description": "A specialized college branch delivering international transport and logistics education with emphasis on trade operations and supply-chain management skills.",
            "current_status": "Active branch-level logistics education with practical learning components and market-oriented program outcomes.",
            "future_prospectus": "Developing advanced logistics analytics, transport planning, and international trade competencies through expanded applied training tracks.",
        }
    if "international_transport_and_logistics_el_alamein" in key:
        return {
            "short_description": "A specialized branch for logistics and international transport studies serving coastal development priorities and regional trade capabilities.",
            "current_status": "Active logistics-focused academic programs with practical learning and transport-management orientation.",
            "future_prospectus": "Scaling logistics and supply-chain programs for emerging coastal economic zones and integrated regional transport ecosystems.",
        }
    return {
        "short_description": "A specialized college in international transport and logistics providing applied education in supply chain, trade, and transport management.",
        "current_status": "Active logistics undergraduate pathways with practical training and industry-linked learning.",
        "future_prospectus": "Advancing logistics education through analytics-driven curricula and stronger industry integration.",
    }


def is_logistics_program(name: str) -> bool:
    low = (name or "").lower()
    keys = [
        "logistics",
        "supply chain",
        "transport",
        "trade",
        "petroleum",
        "energy",
        "international transport",
    ]
    return any(k in low for k in keys)


def logistics_roles_by_program(name: str) -> List[str]:
    low = (name or "").lower()
    if "supply chain" in low:
        return [
            "Supply Chain Analyst",
            "Procurement Analyst",
            "Warehouse Operations Manager",
            "Logistics Planner",
            "Transport Operations Manager",
        ]
    if "trade" in low:
        return [
            "Trade Compliance Analyst",
            "Freight Forwarding Specialist",
            "Logistics Planner",
            "Supply Chain Analyst",
            "Procurement Analyst",
        ]
    if "transport" in low:
        return [
            "Transport Operations Manager",
            "Logistics Planner",
            "Freight Forwarding Specialist",
            "Warehouse Operations Manager",
            "Supply Chain Analyst",
        ]
    if "petroleum" in low or "energy" in low:
        return [
            "Logistics Planner",
            "Transport Operations Manager",
            "Procurement Analyst",
            "Supply Chain Analyst",
            "Trade Compliance Analyst",
        ]
    return list(LOGISTICS_ROLES)


def set_logistics_profile(dp: Dict[str, Any], name: str) -> None:
    low = (name or "").lower()
    # differentiated conservative profiles within requested ranges
    if "supply chain" in low:
        target = {
            "math_intensity": 0.66,
            "programming_intensity": 0.30,
            "business_focus": 0.90,
            "logistics_focus": 0.93,
            "data_focus": 0.68,
            "software_focus": 0.40,
            "research_orientation": 0.58,
            "field_work_intensity": 0.52,
        }
    elif "transport" in low:
        target = {
            "math_intensity": 0.62,
            "programming_intensity": 0.22,
            "business_focus": 0.87,
            "logistics_focus": 0.90,
            "data_focus": 0.55,
            "software_focus": 0.30,
            "research_orientation": 0.50,
            "field_work_intensity": 0.58,
        }
    elif "trade" in low:
        target = {
            "math_intensity": 0.58,
            "programming_intensity": 0.20,
            "business_focus": 0.92,
            "logistics_focus": 0.88,
            "data_focus": 0.52,
            "software_focus": 0.25,
            "research_orientation": 0.48,
            "field_work_intensity": 0.50,
        }
    elif "petroleum" in low or "energy" in low:
        target = {
            "math_intensity": 0.64,
            "programming_intensity": 0.24,
            "business_focus": 0.84,
            "logistics_focus": 0.89,
            "data_focus": 0.58,
            "software_focus": 0.28,
            "research_orientation": 0.56,
            "field_work_intensity": 0.62,
        }
    else:
        target = {
            "math_intensity": 0.60,
            "programming_intensity": 0.20,
            "business_focus": 0.88,
            "logistics_focus": 0.90,
            "data_focus": 0.55,
            "software_focus": 0.28,
            "research_orientation": 0.50,
            "field_work_intensity": 0.52,
        }
    for k, v in target.items():
        dp[k] = round(clamp(float(v)), 2)


def profile_all_half(dp: Dict[str, Any]) -> bool:
    numeric = [v for v in dp.values() if isinstance(v, (int, float))]
    if not numeric:
        return False
    return all(abs(float(v) - 0.5) < 1e-9 for v in numeric)


def normalize_accreditation(accr: Any) -> Dict[str, List[Any]]:
    result = {"national": [], "international": []}
    if isinstance(accr, dict):
        nat = ensure_list(accr.get("national"))
        intl = ensure_list(accr.get("international"))

        for item in nat:
            if isinstance(item, dict):
                result["national"].extend(ensure_list(item.get("national")))
                result["international"].extend(ensure_list(item.get("international")))
            else:
                result["national"].append(item)
        result["international"].extend(intl)
    else:
        # fallback empty structure
        pass

    result["national"] = uniq([x for x in result["national"] if not is_empty(x)])
    result["international"] = uniq([x for x in result["international"] if not is_empty(x)])
    return result


def ensure_location(file_name: str, loc: Dict[str, Any]) -> None:
    low = file_name.lower()
    if "abukir" in low:
        if is_empty(loc.get("city")):
            loc["city"] = "Alexandria"
        if is_empty(loc.get("country")):
            loc["country"] = "Egypt"
    if "dokki" in low:
        if is_empty(loc.get("city")):
            loc["city"] = "Cairo"
        if is_empty(loc.get("country")):
            loc["country"] = "Egypt"
    if "smart_village" in low:
        if is_empty(loc.get("city")):
            loc["city"] = "Giza"
        if is_empty(loc.get("country")):
            loc["country"] = "Egypt"
    if "heliopolis" in low:
        if is_empty(loc.get("city")):
            loc["city"] = "Cairo"
        if is_empty(loc.get("country")):
            loc["country"] = "Egypt"
    if "el_alamein" in low:
        if is_empty(loc.get("city")):
            loc["city"] = "El Alamein"
        if is_empty(loc.get("country")):
            loc["country"] = "Egypt"


def process_file(file_name: str) -> None:
    path = os.path.join(BASE_DIR, file_name)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    official = data.setdefault("official_data", {})
    overview = official.setdefault("overview", {})
    defaults = overview_defaults(file_name)
    for k in ["short_description", "current_status", "future_prospectus"]:
        if is_empty(overview.get(k)):
            overview[k] = defaults[k]

    # Program structure fix for placeholder undergrad
    degrees = official.setdefault("degrees_programs", {})
    undergrad = ensure_list(degrees.get("undergraduate"))
    if any(str(x).strip() == "College of International Transport and Logistics" for x in undergrad):
        degrees["undergraduate"] = list(LOGISTICS_MAJORS)

    # Add facilities if empty
    facilities = official.setdefault("facilities_and_resources", [])
    if not isinstance(facilities, list) or len(facilities) == 0:
        official["facilities_and_resources"] = list(LOGISTICS_FACILITIES)

    # Admission data fix
    adm = official.setdefault("admission_requirements", {})
    if is_empty(adm.get("accepted_certificates")):
        adm["accepted_certificates"] = list(ADMISSION_CERTS)

    # Accreditation structure fix
    official["accreditation"] = normalize_accreditation(official.get("accreditation"))

    # Location fix
    loc = official.setdefault("location", {})
    ensure_location(file_name, loc)

    # Leadership format fix
    official["leadership"] = normalize_leadership(official.get("leadership"))

    # Decision support and profiles
    ds = data.setdefault("decision_support", {})
    profiles = ensure_list(ds.get("program_profiles"))

    # Expand single placeholder profile into major-based profiles when undergrad majors are explicit logistics majors.
    undergrad_list = ensure_list(degrees.get("undergraduate"))
    if len(profiles) == 1 and len(undergrad_list) >= 2:
        only = profiles[0] if isinstance(profiles[0], dict) else {}
        only_name = str(only.get("program_name") or "")
        if only_name.strip().lower() in {
            "college of international transport and logistics",
            "college of international transport and logistics ",
        }:
            expanded = []
            for major in undergrad_list:
                if not isinstance(major, str) or not major.strip():
                    continue
                p = json.loads(json.dumps(only, ensure_ascii=False))
                p["program_name"] = major
                p["summary"] = f"Heuristic profile for {major} derived from logistics-focused academic orientation."
                p["close_alternatives"] = [m for m in undergrad_list if isinstance(m, str) and m != major][:3]
                p["differentiation_notes"] = [f"Compared with {a}, this program emphasizes a distinct logistics focus mix." for a in p["close_alternatives"][:2]]
                expanded.append(p)
            if expanded:
                profiles = expanded

    new_profiles = []
    for pp in profiles:
        if not isinstance(pp, dict):
            continue
        name = str(pp.get("program_name") or "")
        dp = pp.setdefault("decision_profile", {})
        if not isinstance(dp, dict):
            dp = {}
            pp["decision_profile"] = dp

        if is_logistics_program(name):
            # remove placeholder-like all-0.5 by replacing full profile metrics
            if profile_all_half(dp):
                pass
            set_logistics_profile(dp, name)

            # enforce requested ranges
            dp["programming_intensity"] = round(clamp(float(dp.get("programming_intensity", 0.25)), 0.15, 0.35), 2)
            dp["math_intensity"] = round(clamp(float(dp.get("math_intensity", 0.60)), 0.55, 0.70), 2)
            dp["business_focus"] = round(clamp(float(dp.get("business_focus", 0.88)), 0.80, 0.95), 2)
            dp["logistics_focus"] = round(clamp(float(dp.get("logistics_focus", 0.90)), 0.85, 0.95), 2)

            # career path fix
            pp["career_paths"] = logistics_roles_by_program(name)
        new_profiles.append(pp)
    ds["program_profiles"] = new_profiles

    # Keep schema unchanged and write back same file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    for fn in TARGET_FILES:
        process_file(fn)
        print(f"UPDATED: {fn}", flush=True)


if __name__ == "__main__":
    main()
