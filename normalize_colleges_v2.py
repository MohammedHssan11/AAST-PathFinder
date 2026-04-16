import json
import os
import re
from datetime import datetime, timezone

INPUT_DIR = r"C:\Users\mh978\Downloads\college-decision\colleges"
OUTPUT_DIR = r"C:\Users\mh978\Downloads\college-decision\normalized_college_v2"
PROGRESS_PATH = os.path.join(OUTPUT_DIR, "_progress.json")

WEEK_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
}

INTENSITY = {
    "very_high": 0.85,
    "high": 0.75,
    "medium_high": 0.65,
    "medium": 0.55,
    "low_medium": 0.45,
    "low": 0.35,
}


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def ensure_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def uniq(items):
    out = []
    seen = set()
    for x in items:
        key = json.dumps(x, sort_keys=True, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def dget(data, path):
    cur = data
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def first(data, paths):
    for p in paths:
        v = dget(data, p)
        if not empty(v):
            return v, p
    return None, None


def to_text(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    if isinstance(v, list):
        parts = [to_text(x) for x in v]
        return "; ".join([p for p in parts if p]) or None
    if isinstance(v, dict):
        parts = []
        for k, x in v.items():
            t = to_text(x)
            if t:
                parts.append(f"{k}: {t}")
        return "; ".join(parts) or None
    return str(v)


def flatten_text(data, prefix=""):
    out = []
    if isinstance(data, dict):
        for k, v in data.items():
            np = f"{prefix}.{k}" if prefix else k
            out.extend(flatten_text(v, np))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            out.extend(flatten_text(v, f"{prefix}[{i}]"))
    elif isinstance(data, str):
        t = data.strip()
        if t:
            out.append((prefix, t))
    return out


def dedupe_raw_text(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None, False
    txt = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    paras = [p.strip() for p in re.split(r"\n\s*\n+", txt) if p.strip()]
    seen = set()
    out = []
    dup = False
    for p in paras:
        k = re.sub(r"\s+", " ", p).strip().lower()
        if k in seen:
            dup = True
            continue
        seen.add(k)
        out.append(p)
    cleaned = "\n\n".join(out[:8]).strip()
    if len(cleaned) > 2800:
        cleaned = cleaned[:2800].rsplit(" ", 1)[0].strip()
    return cleaned or None, dup


def parse_week(text, mode):
    if not text:
        return None
    low = text.lower()
    pat = r"(?:\d{1,2}|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth)\s+week"
    for m in re.finditer(pat, low):
        tok = m.group(0).split()[0]
        pos = m.start()
        window = low[max(0, pos - 120) : pos]
        if mode == "add" and "add" in window:
            return int(tok) if tok.isdigit() else WEEK_WORDS.get(tok)
        if mode == "withdraw" and "withdraw" in window:
            return int(tok) if tok.isdigit() else WEEK_WORDS.get(tok)
    return None


def parse_absence(text):
    if not text:
        return None
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", text)
    return float(m.group(1)) if m else None


def parse_age(text):
    if not text:
        return None
    m = re.search(r"age[^.]{0,80}?(?:not exceed|max|maximum)\s*(\d{1,2})", text, re.I)
    return int(m.group(1)) if m else None


def score(v):
    if isinstance(v, (int, float)):
        return max(0.0, min(1.0, float(v)))
    if isinstance(v, str):
        return INTENSITY.get(v.strip().lower().replace(" ", "_"))
    return None


def level(s):
    if s is None:
        return None
    return 3 if s >= 0.67 else (2 if s >= 0.50 else 1)


def template(src_name):
    return {
        "schema_version": "college_normalized_v2",
        "source": {"source_file_name": src_name, "input_path": INPUT_DIR, "generated_at": iso_now()},
        "entity": {"entity_type": "college", "college_id": None, "college_name": None},
        "official_data": {
            "location": {"city": None, "country": None, "branch": None},
            "establishment": {"year_established": None, "parent_institution": None},
            "overview": {"short_description": None, "current_status": None, "future_prospectus": None},
            "degrees_programs": {"undergraduate": [], "postgraduate": [], "professional_certificates": []},
            "accreditation": {"national": [], "international": []},
            "admission_requirements": {"accepted_certificates": [], "entry_exams_required": None, "medical_fitness_required": None, "age_limit": None, "other_conditions": []},
            "student_regulations": {"add_course_deadline_week": None, "withdraw_deadline_week": None, "max_absence_percent": None, "postponement_policy": None, "readmission_policy": None, "special_conditions": []},
            "training_and_practice": {"mandatory_training": None, "industry_training": None, "field_or_sea_training": None, "description": None},
            "international_mobility": {"available": None, "mobility_types": [], "regions": [], "partner_bodies": [], "evidence_based_notes": []},
            "research_and_innovation": {"research_focus": None, "industry_projects": None},
            "facilities_and_resources": [],
            "industry_and_external_relations": [],
            "vision_mission": {"vision": None, "mission": None},
            "leadership": [],
        },
        "decision_support": {
            "heuristic_basis_note": "Decision-support values are heuristic estimates, not official university facts.",
            "college_level_profile": {
                "theoretical_depth": None,
                "math_intensity": None,
                "practical_intensity": None,
                "field_work_intensity": None,
                "research_orientation": None,
                "career_flexibility": None,
                "egypt_employability": {"level": None, "score": None},
                "international_employability": {"level": None, "score": None},
                "international_mobility_strength": {"level": None, "score": None},
            },
            "program_profiles": [],
        },
        "text_artifacts": {"cleaned_summary_text": None},
        "traceability": {"supported_facts": [], "inferred_items": []},
        "quality_check": {"duplicate_content_removed": False, "missing_fields": [], "uncertain_items": [], "notes": []},
    }


def add_fact(lst, field, source):
    row = {"field": field, "source_path": source}
    if row not in lst:
        lst.append(row)


def graph_ctx(data):
    if not isinstance(data, dict):
        return {}
    nodes = data.get("nodes")
    rels = data.get("relationships")
    if not isinstance(nodes, list) or not isinstance(rels, list):
        return {}
    by_label = {}
    by_id = {}
    for n in nodes:
        if not isinstance(n, dict):
            continue
        lbl = str(n.get("label", "")).strip()
        by_label.setdefault(lbl, []).append(n)
        nid = n.get("id")
        if nid:
            by_id[nid] = n
    return {"by_label": by_label, "by_id": by_id, "rels": rels}


def node_name(node):
    if not isinstance(node, dict):
        return None
    p = node.get("properties", {})
    if isinstance(p, dict) and isinstance(p.get("name"), str) and p.get("name").strip():
        return p.get("name").strip()
    return None


def classify_accr(items):
    nat, intl = [], []
    for x in items:
        t = to_text(x)
        if not t:
            continue
        low = t.lower()
        if any(k in low for k in ["egypt", "supreme council", "scu", "national"]):
            nat.append(x)
        elif any(k in low for k in ["abet", "british", "riba", "imeche", "iet", "ice", "istructe", "iht", "international", "cac", "eac"]):
            intl.append(x)
        else:
            nat.append(x)
    return uniq(nat), uniq(intl)


def extract_program_names(data, g, fallback_name):
    names = []
    for key in ["programs", "departments_programs", "academic_programs", "departments"]:
        v = data.get(key)
        if isinstance(v, list):
            for it in v:
                if isinstance(it, str) and it.strip():
                    names.append(it.strip())
                elif isinstance(it, dict):
                    for nk in ["name", "program_name", "degree", "track"]:
                        nv = it.get(nk)
                        if isinstance(nv, str) and nv.strip():
                            names.append(nv.strip())
                            break
    dp = data.get("degrees_programs")
    if isinstance(dp, dict):
        for k in ["undergraduate", "postgraduate"]:
            for it in ensure_list(dp.get(k)):
                if isinstance(it, str) and it.strip():
                    names.append(it.strip())
                elif isinstance(it, dict):
                    n = it.get("name") or it.get("degree") or it.get("track")
                    if isinstance(n, str) and n.strip():
                        names.append(n.strip())
    for n in g.get("by_label", {}).get("Program", []):
        nm = node_name(n)
        if nm:
            names.append(nm)
    names = uniq([n for n in names if n])
    return names or [fallback_name]


def infer_entity_type(data, g):
    if isinstance(data.get("entity_type"), str) and data.get("entity_type") in ["college", "program", "department", "branch"]:
        return data.get("entity_type")
    if "branch" in data or isinstance(data.get("campus"), dict):
        return "branch"
    if "tuition_fees" in data:
        return "program"
    if g.get("by_label", {}).get("Program") and not g.get("by_label", {}).get("College"):
        return "program"
    return "college"


def extract_official(data, out, src_name):
    g = graph_ctx(data)
    off = out["official_data"]
    facts = out["traceability"]["supported_facts"]
    uncertain = out["quality_check"]["uncertain_items"]

    out["entity"]["entity_type"] = infer_entity_type(data, g)
    if "tuition_fees" in data:
        uncertain.append("entity_type_set_to_program_for_fee_dataset")

    cid, p = first(data, ["college_id", "college.college_id", "college.id"])
    if cid is None and g.get("by_label", {}).get("College"):
        cid = g["by_label"]["College"][0].get("id")
        p = "nodes[label=College][0].id"
    if not empty(cid):
        out["entity"]["college_id"] = cid
        add_fact(facts, "entity.college_id", p or "source")

    cname, p = first(data, ["college_name", "college.name"])
    if cname is None and g.get("by_label", {}).get("College"):
        cname = node_name(g["by_label"]["College"][0])
        p = "nodes[label=College][0].properties.name"
    if not empty(cname):
        out["entity"]["college_name"] = cname
        add_fact(facts, "entity.college_name", p or "source")

    city, p = first(data, ["location.city", "campus.city"])
    country, p2 = first(data, ["location.country", "campus.country"])
    branch, p3 = first(data, ["location.branch", "branch", "location.area", "campus.name"])
    if g.get("by_label", {}).get("Campus"):
        campus = g["by_label"]["Campus"][0]
        city = city or dget(campus, "properties.city")
        country = country or dget(campus, "properties.country")
        branch = branch or node_name(campus)
    if not empty(city):
        off["location"]["city"] = city
        add_fact(facts, "official_data.location.city", p or "campus/nodes")
    if not empty(country):
        off["location"]["country"] = country
        add_fact(facts, "official_data.location.country", p2 or "campus/nodes")
    if not empty(branch):
        off["location"]["branch"] = branch
        add_fact(facts, "official_data.location.branch", p3 or "campus/nodes")

    y, p = first(data, ["establishment.year_established", "college.established_year"])
    if y is None and g.get("by_label", {}).get("College"):
        y = dget(g["by_label"]["College"][0], "properties.established_year")
        p = "nodes[label=College][0].properties.established_year"
    if isinstance(y, str) and y.strip().isdigit():
        y = int(y.strip())
    if not empty(y):
        off["establishment"]["year_established"] = y
        add_fact(facts, "official_data.establishment.year_established", p or "source")
    parent, p = first(data, ["establishment.parent_institution", "parent_institution", "college.parent_institution"])
    if not empty(parent):
        off["establishment"]["parent_institution"] = parent
        add_fact(facts, "official_data.establishment.parent_institution", p or "source")

    sdesc, p = first(data, ["overview.short_description", "college.description", "college_identity.description", "description", "positioning", "overview"])
    if sdesc is None and g.get("by_label", {}).get("College"):
        sdesc = dget(g["by_label"]["College"][0], "properties.description")
        p = "nodes[label=College][0].properties.description"
    if isinstance(sdesc, dict):
        sdesc = to_text(sdesc)
    if not empty(sdesc):
        off["overview"]["short_description"] = sdesc
        add_fact(facts, "official_data.overview.short_description", p or "source")
    cur, p = first(data, ["overview.current_status", "current_status"])
    fut, p2 = first(data, ["overview.future_prospectus", "future_prospectus", "extra_sections.Current Status and Future Prospectus"])
    if not empty(cur):
        off["overview"]["current_status"] = cur
        add_fact(facts, "official_data.overview.current_status", p or "source")
    if not empty(fut):
        off["overview"]["future_prospectus"] = fut
        add_fact(facts, "official_data.overview.future_prospectus", p2 or "source")

    dp = data.get("degrees_programs")
    if isinstance(dp, dict):
        off["degrees_programs"]["undergraduate"] = uniq(ensure_list(dp.get("undergraduate")))
        off["degrees_programs"]["postgraduate"] = uniq(ensure_list(dp.get("postgraduate")))
        off["degrees_programs"]["professional_certificates"] = uniq(ensure_list(dp.get("professional_certificates")))
        for k in ["undergraduate", "postgraduate", "professional_certificates"]:
            if off["degrees_programs"][k]:
                add_fact(facts, f"official_data.degrees_programs.{k}", f"degrees_programs.{k}")
    if not off["degrees_programs"]["undergraduate"]:
        names = extract_program_names(data, g, out["entity"]["college_name"] or src_name.replace(".json", ""))
        if names:
            off["degrees_programs"]["undergraduate"] = names
            add_fact(facts, "official_data.degrees_programs.undergraduate", "programs/departments/nodes")
    if empty(off["degrees_programs"]["professional_certificates"]) and not empty(data.get("professional_certificates")):
        off["degrees_programs"]["professional_certificates"] = uniq(ensure_list(data.get("professional_certificates")))
        add_fact(facts, "official_data.degrees_programs.professional_certificates", "professional_certificates")

    accr = data.get("accreditation")
    nat, intl = [], []
    if isinstance(accr, dict):
        nat += ensure_list(accr.get("national"))
        intl += ensure_list(accr.get("international"))
    elif not empty(accr):
        n, i = classify_accr(ensure_list(accr))
        nat += n
        intl += i
    if not empty(data.get("accreditations")):
        n, i = classify_accr(ensure_list(data.get("accreditations")))
        nat += n
        intl += i
    for rel in g.get("rels", []):
        if str(rel.get("type", "")).upper() == "ACCREDITED_BY":
            n = g.get("by_id", {}).get(rel.get("to"))
            nm = node_name(n)
            if nm:
                nn, ii = classify_accr([nm])
                nat += nn
                intl += ii
    off["accreditation"]["national"] = uniq([x for x in nat if not empty(x)])
    off["accreditation"]["international"] = uniq([x for x in intl if not empty(x)])
    if off["accreditation"]["national"]:
        add_fact(facts, "official_data.accreditation.national", "accreditation/accreditations")
    if off["accreditation"]["international"]:
        add_fact(facts, "official_data.accreditation.international", "accreditation/accreditations")

    raw = data.get("raw_text")
    cleaned, dup = dedupe_raw_text(raw if isinstance(raw, str) else "")
    out["text_artifacts"]["cleaned_summary_text"] = cleaned
    out["quality_check"]["duplicate_content_removed"] = dup
    if cleaned:
        add_fact(facts, "text_artifacts.cleaned_summary_text", "raw_text")

    src_adm = data.get("admission_requirements")
    adm = off["admission_requirements"]
    if isinstance(src_adm, dict):
        for k in ["accepted_certificates", "entry_exams_required", "medical_fitness_required", "age_limit", "other_conditions"]:
            v = src_adm.get(k)
            if k in ["accepted_certificates", "other_conditions"]:
                v = uniq(ensure_list(v))
            if not empty(v):
                adm[k] = v
                add_fact(facts, f"official_data.admission_requirements.{k}", f"admission_requirements.{k}")
    blob = to_text([raw, data.get("student_regulations"), data.get("special_conditions")]) or ""
    if not adm["entry_exams_required"] and "entry exam" in blob.lower():
        adm["entry_exams_required"] = True
        add_fact(facts, "official_data.admission_requirements.entry_exams_required", "raw_text")
    if adm["medical_fitness_required"] is None and "medical fitness" in blob.lower():
        adm["medical_fitness_required"] = True
        add_fact(facts, "official_data.admission_requirements.medical_fitness_required", "raw_text")
    if adm["age_limit"] is None:
        a = parse_age(blob)
        if a is not None:
            adm["age_limit"] = a
            add_fact(facts, "official_data.admission_requirements.age_limit", "raw_text")
    cert_hits = []
    cert_map = [
        ("thanaweia amma", "Thanaweia Amma"),
        ("american high school diploma", "American High School Diploma"),
        ("igcse/gcse/gce", "IGCSE/GCSE/GCE"),
        ("french baccalaureate", "French Baccalaureate"),
        ("german abitur", "German Abitur"),
        ("international baccalaureate", "International Baccalaureate"),
    ]
    for needle, label in cert_map:
        if needle in blob.lower():
            cert_hits.append(label)
    if empty(adm["accepted_certificates"]) and cert_hits:
        adm["accepted_certificates"] = uniq(cert_hits)
        add_fact(facts, "official_data.admission_requirements.accepted_certificates", "raw_text")

    regs = off["student_regulations"]
    src_regs = data.get("student_regulations")
    if isinstance(src_regs, dict):
        if not empty(src_regs.get("postponement_policy")):
            regs["postponement_policy"] = src_regs.get("postponement_policy")
            add_fact(facts, "official_data.student_regulations.postponement_policy", "student_regulations.postponement_policy")
        if not empty(src_regs.get("readmission_policy")):
            regs["readmission_policy"] = src_regs.get("readmission_policy")
            add_fact(facts, "official_data.student_regulations.readmission_policy", "student_regulations.readmission_policy")
        if not empty(src_regs.get("special_conditions")):
            regs["special_conditions"] = uniq(ensure_list(src_regs.get("special_conditions")))
            add_fact(facts, "official_data.student_regulations.special_conditions", "student_regulations.special_conditions")
        if regs["max_absence_percent"] is None:
            ma = parse_absence(to_text(src_regs.get("attendance_policy")) or "")
            if ma is not None:
                regs["max_absence_percent"] = ma
                add_fact(facts, "official_data.student_regulations.max_absence_percent", "student_regulations.attendance_policy")
    if regs["add_course_deadline_week"] is None:
        regs["add_course_deadline_week"] = parse_week(blob, "add")
        if regs["add_course_deadline_week"] is not None:
            add_fact(facts, "official_data.student_regulations.add_course_deadline_week", "raw_text")
    if regs["withdraw_deadline_week"] is None:
        regs["withdraw_deadline_week"] = parse_week(blob, "withdraw")
        if regs["withdraw_deadline_week"] is not None:
            add_fact(facts, "official_data.student_regulations.withdraw_deadline_week", "raw_text")
    if regs["max_absence_percent"] is None:
        ma = parse_absence(blob)
        if ma is not None:
            regs["max_absence_percent"] = ma
            add_fact(facts, "official_data.student_regulations.max_absence_percent", "raw_text")

    t_src = None
    for key in ["training_and_practice", "training_and_fieldwork", "training_and_industry", "training_and_industry_exposure"]:
        if not empty(data.get(key)):
            t_src = key
            break
    tr = off["training_and_practice"]
    if t_src:
        tv = data.get(t_src)
        if isinstance(tv, dict):
            if not empty(tv.get("mandatory_training")):
                tr["mandatory_training"] = tv.get("mandatory_training")
                add_fact(facts, "official_data.training_and_practice.mandatory_training", f"{t_src}.mandatory_training")
            if not empty(tv.get("industry_training")):
                tr["industry_training"] = tv.get("industry_training")
                add_fact(facts, "official_data.training_and_practice.industry_training", f"{t_src}.industry_training")
            if "field_or_sea_training" in tv and not empty(tv.get("field_or_sea_training")):
                tr["field_or_sea_training"] = tv.get("field_or_sea_training")
                add_fact(facts, "official_data.training_and_practice.field_or_sea_training", f"{t_src}.field_or_sea_training")
            if "sea_or_field_training" in tv and not empty(tv.get("sea_or_field_training")):
                tr["field_or_sea_training"] = tv.get("sea_or_field_training")
                add_fact(facts, "official_data.training_and_practice.field_or_sea_training", f"{t_src}.sea_or_field_training")
            d = tv.get("description")
            if empty(d):
                d = to_text(tv)
            if not empty(d):
                tr["description"] = d
                add_fact(facts, "official_data.training_and_practice.description", t_src)
        else:
            tx = to_text(tv)
            if tx:
                tr["description"] = tx
                add_fact(facts, "official_data.training_and_practice.description", t_src)

    mob = off["international_mobility"]
    txt = flatten_text(data)
    hits = []
    mtypes = []
    partners = []
    for path, t in txt:
        low = t.lower()
        lpath = path.lower()
        if any(k in low or k in lpath for k in ["exchange", "dual degree", "international_partners", "international exposure", "international affiliations"]):
            hits.append(f"{path}: {t[:160]}")
        if "exchange" in low or "exchange" in lpath:
            mtypes.append("student_exchange")
        if "dual degree" in low:
            mtypes.append("dual_degree")
        if "international exposure" in low or "international exposure" in lpath:
            mtypes.append("international_exposure")
        if "international_partners" in lpath or "international partners" in low:
            mtypes.append("partner_universities")
    for key in ["international_partners", "partners", "partner_universities", "industry_and_international_relations", "industry_and_institutional_relations", "international_affiliations"]:
        for it in ensure_list(data.get(key)):
            tt = to_text(it)
            if tt and any(k in tt.lower() for k in ["universit", "exchange", "arab", "international", "uab", "uclan", "spain", "united kingdom"]):
                partners.append(tt)
    for rel in g.get("rels", []):
        if str(rel.get("type", "")).upper() == "HAS_PARTNER":
            n = g.get("by_id", {}).get(rel.get("to"))
            nm = node_name(n)
            if nm:
                partners.append(nm)
                hits.append(f"relationships.HAS_PARTNER: {nm}")
                mtypes.append("partner_universities")
    partners = uniq(partners)
    mtypes = uniq(mtypes)
    if hits or partners:
        mob["available"] = True
        mob["mobility_types"] = mtypes
        mob["partner_bodies"] = partners
        mob["evidence_based_notes"] = uniq(hits)[:6]
        add_fact(facts, "official_data.international_mobility.available", "mobility_evidence")
    else:
        mob["available"] = None
    regs_list = []
    for t in partners + mob["evidence_based_notes"]:
        low = t.lower()
        if "arab" in low:
            regs_list.append("Arab Countries")
        if "spain" in low:
            regs_list.append("Spain")
        if "united kingdom" in low:
            regs_list.append("United Kingdom")
    mob["regions"] = uniq(regs_list)

    rsrc = data.get("research_and_innovation")
    if empty(rsrc):
        rsrc = data.get("research_and_consulting")
    if isinstance(rsrc, dict):
        rf = rsrc.get("research_focus") or rsrc.get("focus")
        ip = rsrc.get("industry_projects") if "industry_projects" in rsrc else rsrc.get("consulting_projects")
        if empty(rf):
            rf = to_text(rsrc)
        if not empty(rf):
            off["research_and_innovation"]["research_focus"] = rf
            add_fact(facts, "official_data.research_and_innovation.research_focus", "research_and_innovation")
        if not empty(ip):
            off["research_and_innovation"]["industry_projects"] = ip
            add_fact(facts, "official_data.research_and_innovation.industry_projects", "research_and_innovation")
    elif not empty(rsrc):
        off["research_and_innovation"]["research_focus"] = to_text(rsrc)
        add_fact(facts, "official_data.research_and_innovation.research_focus", "research_and_innovation")

    fac = []
    for key in ["facilities_and_resources", "labs", "institutes_and_centers"]:
        fac += ensure_list(data.get(key))
    fac += ensure_list(dget(data, "college.labs"))
    for n in g.get("by_label", {}).get("Lab", []):
        nm = node_name(n)
        if nm:
            fac.append(nm)
    off["facilities_and_resources"] = uniq([x for x in fac if not empty(x)])
    if off["facilities_and_resources"]:
        add_fact(facts, "official_data.facilities_and_resources", "facilities/labs")

    ext = []
    for key in ["industry_and_international_relations", "industry_and_institutional_relations", "industry_partners", "partners", "international_partners"]:
        ext += ensure_list(data.get(key))
    ext += ensure_list(dget(data, "college.industry_partners"))
    for rel in g.get("rels", []):
        if str(rel.get("type", "")).upper() == "HAS_PARTNER":
            n = g.get("by_id", {}).get(rel.get("to"))
            nm = node_name(n)
            if nm:
                ext.append(nm)
    off["industry_and_external_relations"] = uniq([x for x in ext if not empty(x)])
    if off["industry_and_external_relations"]:
        add_fact(facts, "official_data.industry_and_external_relations", "partners/industry")

    v, p = first(data, ["vision_mission.vision", "college.vision", "vision"])
    m, p2 = first(data, ["vision_mission.mission", "college.mission", "mission"])
    if not empty(v):
        off["vision_mission"]["vision"] = v
        add_fact(facts, "official_data.vision_mission.vision", p or "source")
    if not empty(m):
        off["vision_mission"]["mission"] = m
        add_fact(facts, "official_data.vision_mission.mission", p2 or "source")

    leaders = []
    for key in ["leadership", "leadership_history", "current_dean", "dean_and_leadership", "administration", "governance", "extra_sections.Leadership", "college.administration"]:
        v = dget(data, key)
        if empty(v):
            continue
        if isinstance(v, list):
            leaders += v
        elif isinstance(v, dict):
            for k, x in v.items():
                tx = to_text(x)
                if tx:
                    leaders.append(f"{k}: {tx}")
        else:
            leaders.append(v)
    for n in g.get("by_label", {}).get("Person", []):
        nm = node_name(n)
        role = dget(n, "properties.role")
        if nm and role:
            leaders.append(f"{role}: {nm}")
        elif nm:
            leaders.append(nm)
    off["leadership"] = uniq([x for x in leaders if not empty(x)])
    if off["leadership"]:
        add_fact(facts, "official_data.leadership", "leadership sources")

    if src_name.lower() in ["fees.json", "tuition_fees_2025_2026.json"]:
        out["quality_check"]["notes"].append("Source is fee-focused dataset; many academic official fields are not applicable.")


def keyword_profile(name):
    low = (name or "").lower()
    p = {"theoretical": 0.55, "math": 0.5, "physics": 0.35, "programming": 0.35, "design": 0.4, "lab": 0.5, "field": 0.4, "management": 0.45, "workload": 0.55, "flex": 0.55}
    if any(k in low for k in ["computer", "software", "data", "ai", "cyber"]):
        p.update({"theoretical": 0.72, "math": 0.75, "physics": 0.45, "programming": 0.88, "lab": 0.72, "field": 0.3, "workload": 0.72, "flex": 0.72})
    elif any(k in low for k in ["engineering", "mechanical", "electrical", "marine", "construction"]):
        p.update({"theoretical": 0.75, "math": 0.8, "physics": 0.78, "programming": 0.5, "design": 0.58, "lab": 0.8, "field": 0.68, "workload": 0.78, "flex": 0.62})
    elif any(k in low for k in ["medicine", "dental", "dent", "pharmacy"]):
        p.update({"theoretical": 0.78, "math": 0.55, "programming": 0.2, "lab": 0.85, "field": 0.82, "workload": 0.82, "flex": 0.52})
    elif any(k in low for k in ["law"]):
        p.update({"theoretical": 0.8, "math": 0.28, "physics": 0.1, "programming": 0.1, "lab": 0.25, "field": 0.45, "management": 0.55, "workload": 0.68, "flex": 0.5})
    elif any(k in low for k in ["management", "business", "logistics", "transport"]):
        p.update({"theoretical": 0.62, "math": 0.55, "programming": 0.28, "field": 0.45, "management": 0.82, "workload": 0.62, "flex": 0.7})
    elif any(k in low for k in ["art", "design", "graphics", "multimedia"]):
        p.update({"theoretical": 0.5, "math": 0.3, "programming": 0.35, "design": 0.9, "lab": 0.55, "field": 0.42, "workload": 0.62})
    return p


def base_jobs(name):
    low = (name or "").lower()
    if any(k in low for k in ["computer", "software", "ai", "data", "cyber"]):
        return ["Software Engineer", "Data Analyst", "AI/ML Engineer", "Systems Specialist"], 0.72, 0.68
    if any(k in low for k in ["engineering", "mechanical", "electrical", "marine", "construction"]):
        return ["Design Engineer", "Field Engineer", "Operations Engineer", "Maintenance Engineer"], 0.68, 0.62
    if any(k in low for k in ["medicine", "dental", "dent", "pharmacy"]):
        return ["Clinical Practice", "Hospital/Clinic Roles", "Research Support", "Public Health Roles"], 0.74, 0.58
    if "law" in low:
        return ["Legal Practitioner", "Corporate Legal Advisor", "Compliance Specialist", "Judicial/Prosecution Track"], 0.58, 0.47
    if any(k in low for k in ["management", "business", "logistics", "transport"]):
        return ["Operations Specialist", "Supply Chain Analyst", "Business Development", "Management Trainee"], 0.64, 0.58
    if any(k in low for k in ["art", "design", "graphics", "multimedia"]):
        return ["Designer", "Creative Producer", "Visual Content Specialist", "Digital Media Roles"], 0.55, 0.5
    return [], 0.52, 0.45


def decision_support(data, out):
    inf = out["traceability"]["inferred_items"]
    names = extract_program_names(data, graph_ctx(data), out["entity"]["college_name"] or out["source"]["source_file_name"].replace(".json", ""))
    profiles = []
    for n in names:
        k = keyword_profile(n)
        jobs, eg, intl = base_jobs(n)
        pobj = None
        if isinstance(data.get("programs"), list):
            for p in data.get("programs"):
                if isinstance(p, dict) and str(p.get("name", "")).strip().lower() == n.lower():
                    pobj = p
                    break
        theo = score(dget(pobj or {}, "study_profile.theoretical_intensity")) or k["theoretical"]
        mathi = score(dget(pobj or {}, "study_profile.math_intensity")) or k["math"]
        progi = score(dget(pobj or {}, "study_profile.programming_intensity")) or k["programming"]
        labi = score(dget(pobj or {}, "study_profile.practical_intensity")) or k["lab"]
        work = score(dget(pobj or {}, "pressure_profile.workload_level")) or k["workload"]
        md = score(dget(pobj or {}, "career_outcomes.market_demand"))
        im = score(dget(pobj or {}, "career_outcomes.international_mobility"))
        if md is not None:
            eg = max(0.35, min(0.9, md))
            if im is None:
                intl = max(0.3, min(0.85, md - 0.05))
        if im is not None:
            intl = max(0.3, min(0.9, im))
        roles = jobs
        cr = dget(pobj or {}, "career_outcomes.common_roles")
        if isinstance(cr, list) and cr:
            roles = [x for x in cr if isinstance(x, str) and x.strip()]
        best = []
        avoid = []
        if theo >= 0.7:
            best.append("Enjoys analytical and theoretical reasoning")
        if mathi >= 0.7:
            best.append("Comfortable with mathematics-heavy coursework")
        if progi >= 0.7:
            best.append("Interested in coding/problem-solving work")
        if labi >= 0.7:
            best.append("Prefers practical or lab-oriented learning")
        if work >= 0.72:
            best.append("Can handle sustained high workload")
        if mathi >= 0.75:
            avoid.append("You want minimal mathematics")
        if progi >= 0.75:
            avoid.append("You prefer non-technical daily work")
        if k["field"] >= 0.7:
            avoid.append("You want no field/clinical exposure")
        if work >= 0.78:
            avoid.append("You prefer low academic pressure")
        profiles.append({
            "program_name": n,
            "decision_profile": {
                "theoretical_depth": round(theo, 2),
                "math_intensity": round(mathi, 2),
                "physics_intensity": round(k["physics"], 2),
                "programming_intensity": round(progi, 2),
                "design_creativity": round(k["design"], 2),
                "lab_intensity": round(labi, 2),
                "field_work_intensity": round(k["field"], 2),
                "management_exposure": round(k["management"], 2),
                "workload_difficulty": round(work, 2),
                "career_flexibility": round(k["flex"], 2),
            },
            "career_paths": uniq(roles),
            "employment_outlook": {"egypt_market": {"level": level(eg), "score": round(eg, 2)}, "international_market": {"level": level(intl), "score": round(intl, 2)}},
            "best_fit_traits": uniq(best)[:5],
            "avoid_if": uniq(avoid)[:4],
            "summary": f"Heuristic profile for {n} derived from available program indicators in the source file.",
        })
        inf.append({"item": f"decision_support.program_profiles[{n}]", "basis": "Heuristic profile from program title and available study/pressure/career fields."})
    out["decision_support"]["program_profiles"] = profiles

    def avg(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    c = out["decision_support"]["college_level_profile"]
    c["theoretical_depth"] = round(avg([p["decision_profile"]["theoretical_depth"] for p in profiles]), 2) if profiles else None
    c["math_intensity"] = round(avg([p["decision_profile"]["math_intensity"] for p in profiles]), 2) if profiles else None
    c["practical_intensity"] = round(avg([p["decision_profile"]["lab_intensity"] for p in profiles]), 2) if profiles else None
    c["field_work_intensity"] = round(avg([p["decision_profile"]["field_work_intensity"] for p in profiles]), 2) if profiles else None
    c["career_flexibility"] = round(avg([p["decision_profile"]["career_flexibility"] for p in profiles]), 2) if profiles else None
    research = out["official_data"]["research_and_innovation"]["research_focus"]
    c["research_orientation"] = round(0.62 if not empty(research) else 0.5, 2)
    eg = avg([p["employment_outlook"]["egypt_market"]["score"] for p in profiles])
    intl = avg([p["employment_outlook"]["international_market"]["score"] for p in profiles])
    if eg is not None:
        c["egypt_employability"] = {"level": level(eg), "score": round(eg, 2)}
    if intl is not None:
        c["international_employability"] = {"level": level(intl), "score": round(intl, 2)}
    ms = 0.58 if out["official_data"]["international_mobility"]["available"] is True else 0.42
    ms += min(0.2, len(out["official_data"]["international_mobility"]["partner_bodies"]) * 0.04)
    ms = min(ms, 0.85)
    c["international_mobility_strength"] = {"level": level(ms), "score": round(ms, 2)}
    inf.append({"item": "decision_support.college_level_profile", "basis": "Aggregated from heuristic program profiles and source mobility/research signals."})


def missing_fields(obj, prefix="official_data"):
    miss = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}"
            if v is None:
                miss.append(p)
            elif isinstance(v, str) and v.strip() == "":
                miss.append(p)
            elif isinstance(v, list):
                if len(v) == 0:
                    miss.append(p)
            elif isinstance(v, dict):
                miss.extend(missing_fields(v, p))
    return miss


def write_json(path, payload):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def process_one(path):
    src_name = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = {"raw_data": data}

    out = template(src_name)
    extract_official(data, out, src_name)
    decision_support(data, out)
    out["quality_check"]["missing_fields"] = uniq(missing_fields(out["official_data"]))
    out["quality_check"]["uncertain_items"] = uniq(out["quality_check"]["uncertain_items"])
    out["quality_check"]["notes"] = uniq(
        out["quality_check"]["notes"]
        + [
            "Official fields are extracted strictly from source-supported content.",
            "Decision-support fields are heuristic and separated from official_data.",
        ]
    )
    out["traceability"]["supported_facts"] = uniq(out["traceability"]["supported_facts"])
    out["traceability"]["inferred_items"] = uniq(out["traceability"]["inferred_items"])
    return out


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".json")])
    total = len(files)
    done = 0
    for i, name in enumerate(files):
        in_path = os.path.join(INPUT_DIR, name)
        out_name = f"{os.path.splitext(name)[0]}.normalized.v2.json"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        normalized = process_one(in_path)
        write_json(out_path, normalized)
        done += 1
        progress = {
            "last_completed_file": name,
            "next_file": files[i + 1] if i + 1 < total else None,
            "completed_count": done,
            "remaining_count": total - done,
            "timestamp": iso_now(),
        }
        write_json(PROGRESS_PATH, progress)
        print(f"CHECKPOINT: completed_file={name} | status=done", flush=True)


if __name__ == "__main__":
    try:
        main()
    except MemoryError:
        print("SAFE STOP: memory/context limit approaching.", flush=True)
        print("LAST_COMPLETED_FILE=unknown", flush=True)
        print("NEXT_FILE_TO_PROCESS=unknown", flush=True)
        print("REMAINING_FILES_ESTIMATE=unknown", flush=True)
