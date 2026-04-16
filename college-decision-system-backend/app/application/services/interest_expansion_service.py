import re
import unicodedata

from thefuzz import process, fuzz


class InterestExpansionService:
    """Service to normalize, expand, and fuzz-match student interests into canonical categories."""
    
    SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
        "ai": ("ai", "artificial intelligence", "machine learning", "intelligent systems", "data science"),
        "business": ("business", "management", "finance", "marketing", "accounting", "economics", "entrepreneurship", "supply chain", "logistics", "trade"),
        "engineering": ("engineering", "architecture", "mechanical", "electrical", "electronics", "communications", "construction", "industrial", "chemical", "biomedical", "aerospace", "petroleum", "marine engineering", "computer engineering"),
        "cybersecurity": ("cybersecurity", "cyber security", "information security", "network security"),
        "software": ("software", "computer science", "information systems", "programming"),
        "healthcare": ("healthcare", "medicine", "pharmacy", "dentistry", "clinical", "medical"),
        "design": ("design", "art", "fashion", "interior", "graphic", "visual art"),
        "law": ("law", "legal", "policy"),
        "language": ("language", "translation", "media", "communication"),
        "logistics": ("logistics", "transport", "maritime", "supply chain", "trade"),
    }

    PROFILE_FIELDS: dict[str, tuple[str, ...]] = {
        "ai": ("ai_focus", "data_focus", "software_focus", "programming_intensity"),
        "business": ("business_focus", "finance_focus", "management_exposure", "entrepreneurship_focus"),
        "engineering": ("math_intensity", "physics_intensity", "hardware_focus", "energy_sector_focus"),
        "cybersecurity": ("security_focus", "software_focus", "programming_intensity"),
        "software": ("software_focus", "programming_intensity", "data_focus"),
        "healthcare": ("healthcare_focus", "biology_focus", "lab_intensity"),
        "design": ("design_creativity", "creativity_design_focus"),
        "law": ("law_policy_focus",),
        "language": ("language_communication_focus",),
        "logistics": ("logistics_focus", "international_trade_focus", "transport_operations_focus", "maritime_focus"),
    }

    PROFILE_ONLY_CAPS: dict[str, float] = {
        "ai": 0.55,
        "business": 0.65,
        "engineering": 0.35,
        "cybersecurity": 0.55,
        "software": 0.6,
        "healthcare": 0.55,
        "design": 0.55,
        "law": 0.55,
        "language": 0.55,
        "logistics": 0.65,
    }
    
    def __init__(self):
        self.canonical_map = {
            alias: canonical
            for canonical, aliases in self.SEARCH_ALIASES.items()
            for alias in aliases
        }
        self.all_known_aliases = list(self.canonical_map.keys())

    def normalize_text(self, value: str | None) -> str:
        """Standardize text strictly into ascii lowercase alphamumeric and spaces."""
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        text = ascii_text.lower()
        text = text.replace("&", " and ")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def canonicalize(self, normalized_interest: str) -> str | None:
        """Use fuzzy matching to determine the closest academic category for user input."""
        if not normalized_interest:
            return None
            
        # 1. Exact direct match
        if normalized_interest in self.canonical_map:
            return self.canonical_map[normalized_interest]
            
        # 2. Token subset match (like original logic)
        interest_tokens = set(normalized_interest.split())
        for alias, canonical in self.canonical_map.items():
            alias_tokens = set(alias.split())
            if alias_tokens and interest_tokens and (
                alias_tokens.issubset(interest_tokens) or interest_tokens.issubset(alias_tokens)
            ):
                return canonical
                
        # 3. Fuzzy match fallback
        # If a user types "artifical intelgence", `thefuzz` catches it against "artificial intelligence"
        match = process.extractOne(normalized_interest, self.all_known_aliases, scorer=fuzz.token_sort_ratio, score_cutoff=75)
        if match:
            best_alias = match[0]
            return self.canonical_map[best_alias]
            
        return None

    def expand(self, normalized_interest: str) -> tuple[str, ...]:
        """Expand an interest into its academic siblings and parent categories."""
        if not normalized_interest:
            return ()
            
        canonical = self.canonicalize(normalized_interest)
        terms = {normalized_interest}
        if canonical:
            terms.add(canonical)
            terms.update(self.SEARCH_ALIASES.get(canonical, (canonical,)))
        return tuple(sorted(terms))

    def get_profile_fields(self, canonical_interest: str) -> tuple[str, ...]:
        return self.PROFILE_FIELDS.get(canonical_interest, ())

    def get_profile_cap(self, canonical_interest: str) -> float:
        return self.PROFILE_ONLY_CAPS.get(canonical_interest, 0.6)

    def fuzzy_score_against_text(self, term: str, searchable_text: str, searchable_tokens: set[str]) -> float:
        """Score a single expanded term against the program's searchable text."""
        term_tokens = term.split()
        if not term_tokens:
            return 0.0

        if len(term_tokens) == 1:
            return 1.0 if term_tokens[0] in searchable_tokens else 0.0

        if term in searchable_text:
            return 1.0

        # Exact token overlap (legacy behavior)
        overlap = len(set(term_tokens) & searchable_tokens) / len(term_tokens)
        if overlap >= 0.5:
            return round(overlap, 4)
            
        # Partial fuzzy ratio for multi-word elements that almost hit
        fz_score = fuzz.partial_ratio(term, searchable_text)
        if fz_score >= 85:
            return round(fz_score / 100.0, 4)
            
        return 0.0
