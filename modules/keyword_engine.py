import re
from docx import Document

STOP_WORDS = {
    # ── Articles, conjunctions, prepositions ─────────────────────────────
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "this", "that", "these", "those", "it", "its", "you", "your", "we",
    "our", "they", "their", "he", "she", "his", "her", "who", "which",
    "what", "when", "where", "how", "why", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "than", "too", "very",
    "just", "about", "up", "out", "if", "into", "through", "during",
    "before", "after", "above", "below", "between", "while", "although",
    "not", "no", "nor", "so", "yet", "either", "neither", "whether",
    "us", "them", "him", "me", "my", "i",

    # ── Generic job posting language ─────────────────────────────────────
    "work", "experience", "team", "company", "role", "position", "job",
    "candidate", "looking", "seeking", "join", "help", "build", "grow",
    "support", "supporting", "ensure", "enable", "create", "creating",
    "develop", "developing", "development", "implement", "implementing",
    "implementation", "define", "collaborate", "collaborating", "communicate",
    "across", "within", "including", "well", "also", "must", "required",
    "preferred", "plus", "bonus", "ability", "strong", "excellent",
    "great", "good", "best", "new", "make", "use", "years", "year",
    "time", "key", "high", "large", "complex", "multiple", "day", "days",
    "week", "weeks", "month", "months", "number", "per", "own", "take",
    "get", "set", "see", "way", "working", "based", "related",
    "responsible", "responsibilities", "following",
    "degree", "bachelor", "master", "equivalent",
    "like", "love", "passionate", "excited", "motivated", "opportunity",
    "environment", "culture", "mission", "vision", "values", "impact",
    "fast", "paced", "dynamic", "innovative", "collaborative", "inclusive",
    "diverse", "world", "industry", "cutting", "edge", "proven",
    # ── Generic qualifier / descriptor words (not skill signals) ─────────
    "knowledge", "familiarity", "understanding", "awareness", "exposure",
    "helpful", "desired", "ideal", "ideally", "someone",
    "skills", "ability", "abilities", "expertise", "proficiency",
    "background", "history", "track", "record", "demonstrate",
    # ── Section header words that bleed into keyword extraction ───────────
    # These are section markers (used in REQUIRED_SECTION_MARKERS /
    # PREFERRED_SECTION_MARKERS) so they should never appear as ATS keywords.
    "requirements", "qualifications", "responsibilities",
    # ── Generic action/ownership words that bleed everywhere ─────────────
    "open", "opening", "monitor", "monitoring", "ownership", "deliver",
    "delivery", "deliverable", "deliverables", "initiative", "initiatives",
    "execution", "execute", "launch", "launching", "hours", "alongside",
    "partner", "partnering", "intake", "align", "alignment",
    "core", "owns", "driven", "driving",
    # NOTE: "drive", "drive", "lead", "leading", "manage", "managing",
    # "management", "product", "technical", "digital", "strategic" are
    # intentionally NOT in STOP_WORDS — they are meaningful ATS signals.

    # ── Generic seniority / title words (too broad to be ATS signal) ─────
    "senior", "junior", "associate", "principal", "staff",
    "engineer", "coordinator", "recruiter", "contractor",
    "consultant", "advisor", "general", "global",

    # ── Work style / location (not recruiter keyword filters) ─────────────
    "remote", "onsite", "hybrid", "office", "location", "worldwide",
    "globally", "distributed", "local", "travel", "relocate",

    # ── Job board UI / navigation text ───────────────────────────────────
    "apply", "applying", "applied", "application", "applications",
    "click", "submit", "find", "search", "browse", "view",
    "learn", "read", "show", "details", "visit",
    "hiring", "hire", "posted", "listing", "listings",
    "opening", "openings", "vacancy", "vacancies", "requisition",
    "interview", "interviewing", "cover", "letter", "portfolio",
    "salary", "compensation", "equity", "benefits", "pto", "vacation",
    "health", "dental", "vision", "insurance", "retirement",
    "full", "time", "part", "permanent", "temporary",
    "freelance", "hourly", "annual", "range", "pay",

    # ── Known job board names that bleed into posting text ───────────────
    "jobgether", "linkedin", "indeed", "glassdoor", "ziprecruiter",
    "monster", "wellfound", "builtin", "greenhouse", "lever", "ashby",
    "workday", "icims", "jobvite", "smartrecruiters", "taleo",

    # ── Short noise tokens ────────────────────────────────────────────────
    "wrs", "llc", "inc", "ltd", "corp", "etc", "via", "ref", "req",
    # ── HTML / metadata artifacts ─────────────────────────────────────────
    "nbsp", "middot", "amp", "href", "class", "span", "div", "alt", "src",
    "type", "name", "value", "label", "item", "list",
    # NOTE: "title" and "titles" are excluded from STOP_WORDS because
    # they appear in resume/JD context meaningfully (e.g. "job titles").
    # ── Generic employment metadata ───────────────────────────────────────
    "employment", "full-time", "part-time", "contract",
    "status", "category", "department", "city", "state",
    "country", "zip", "code", "date", "updated", "active",
    "ago", "today", "yesterday", "here", "now",
    "salaries", "similar", "jobs", "reviews", "ratings",
    "interviews", "questions", "photos", "overview",
}

# ── Universal multi-word technical terms to preserve ──────────────────────────
# User-specific domain terms belong in config.json → custom_keywords, not here.
MULTI_WORD_TERMS = [
    # Product discipline
    "product strategy", "product roadmap", "product management", "product manager",
    "product-led growth", "product led growth", "product marketing",
    "technical product manager", "platform product manager", "senior product manager",
    "program management", "program manager",
    # Data / analysis
    "data pipeline", "data migration", "data platform", "data integrity",
    "data management", "data governance", "data driven", "data-driven",
    "root cause analysis", "competitive analysis", "market analysis",
    "a/b testing", "ab testing", "multivariate testing",
    # APIs / platforms
    "api platform", "api development", "rest api", "graphql api",
    "api integration", "api gateway", "api design",
    # Engineering practices
    "agile methodology", "agile development", "scrum framework",
    "sprint planning", "backlog management", "backlog grooming",
    "continuous integration", "continuous delivery", "ci/cd",
    "service level", "service level agreement", "observability",
    # Customer / GTM
    "customer success", "customer experience", "customer journey",
    "client success", "client experience",
    "go-to-market", "go to market",
    "customer lifecycle", "customer retention", "customer acquisition",
    # Strategy / planning
    "strategic planning", "strategic initiatives", "digital transformation",
    "cross-functional", "cross functional",
    "stakeholder management", "vendor management",
    "executive reporting", "executive alignment",
    "budget management", "resource management",
    # ML / AI
    "machine learning", "artificial intelligence", "natural language",
    "natural language processing", "large language model",
    # Multi-word certifications / methodologies
    "project management", "change management",
    "multi-stakeholder", "multi stakeholder",
]

# ── Synonym groups ─────────────────────────────────────────────────────────────
# Each group is a list; the FIRST element is the canonical form.
# Both JD and resume keywords are mapped to canonical before comparison,
# so "APIs" in a JD matches "API" on a resume.
SYNONYM_GROUPS = [
    # Plurals / abbreviation variants
    ["api", "apis"],
    ["kpi", "kpis"],
    ["okr", "okrs"],
    ["sql", "structured query language"],
    ["crm", "customer relationship management"],
    ["saas", "software as a service"],
    ["b2b", "business to business", "business-to-business"],
    ["b2c", "business to consumer", "business-to-consumer"],
    ["ux", "user experience"],
    ["ui", "user interface"],
    ["ml", "machine learning"],
    ["ai", "artificial intelligence"],
    ["llm", "large language model"],
    ["nlp", "natural language processing"],
    ["roi", "return on investment"],
    ["mrr", "monthly recurring revenue"],
    ["arr", "annual recurring revenue"],
    ["nps", "net promoter score"],
    ["csat", "customer satisfaction"],
    ["ltv", "lifetime value", "customer lifetime value"],
    ["cac", "customer acquisition cost"],
    ["dau", "daily active users"],
    ["mau", "monthly active users"],
    ["gtm", "go-to-market", "go to market"],
    ["cx", "customer experience"],
    # Title variants
    ["platform product manager", "platform pm", "product manager platform", "pm platform"],
    ["technical product manager", "technical pm", "tpm"],
    # Phrase variants
    ["a/b testing", "ab testing", "a-b testing", "split testing"],
    ["customer success", "client success"],
    ["customer experience", "client experience"],
    ["product management", "product mgmt"],
    ["program management", "programme management"],
    ["stakeholder management", "stakeholder engagement"],
    ["agile", "agile methodology", "agile development"],
    ["scrum", "scrum framework"],
    ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment"],
]

# Build the base synonym map at module load time.
# Maps every variant → canonical form.
_BASE_SYNONYM_MAP: dict[str, str] = {}
for _group in SYNONYM_GROUPS:
    _canonical = _group[0]
    for _variant in _group:
        _BASE_SYNONYM_MAP[_variant.lower()] = _canonical


REQUIRED_SECTION_MARKERS = [
    "requirements", "required", "must have", "must-have",
    "qualifications", "what you need", "you have", "you bring",
    "what we need", "minimum qualifications", "basic qualifications",
    "you will need", "we are looking for",
]

PREFERRED_SECTION_MARKERS = [
    "preferred", "nice to have", "nice-to-have", "bonus",
    "plus if you", "ideally", "great to have", "desired",
    "what would be great",
]


# ── Synonym helpers ────────────────────────────────────────────────────────────

def _build_synonym_map(custom_synonyms=None):
    """
    Merge the built-in synonym map with user-provided custom_synonyms.
    custom_synonyms: list of lists (same format as SYNONYM_GROUPS).
    Returns a dict mapping variant → canonical.
    """
    syn_map = dict(_BASE_SYNONYM_MAP)
    if custom_synonyms:
        for group in custom_synonyms:
            if not group:
                continue
            canonical = group[0].lower()
            for variant in group:
                syn_map[variant.lower()] = canonical
    return syn_map


def _canonicalize(term, syn_map):
    """Map a term to its canonical form if a synonym mapping exists."""
    return syn_map.get(term.lower(), term.lower())


def _canonicalize_set(terms, syn_map):
    """Canonicalize every term in a set, returning a new set."""
    return {_canonicalize(t, syn_map) for t in terms}


def _get_multi_word_terms(custom_keywords=None):
    """
    Return the full list of multi-word terms to match.
    Appends custom_keywords (user config) to the universal MULTI_WORD_TERMS.
    Only includes entries that contain a space (i.e., are actually multi-word).
    """
    terms = list(MULTI_WORD_TERMS)
    if custom_keywords:
        for kw in custom_keywords:
            kw_lower = kw.lower().strip()
            if " " in kw_lower and kw_lower not in terms:
                terms.append(kw_lower)
    return terms


# ── Tokenization / extraction ──────────────────────────────────────────────────

def _tokenize(text):
    """Lowercase, strip punctuation, split into words."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-\+\#\.]", " ", text)
    tokens = []
    for w in text.split():
        w = w.strip("-+#.")
        if len(w) <= 2:
            continue
        # Skip numeric noise: pure numbers, salary ranges (145k), employee ranges (11-50),
        # years (2004), IDs, or any token starting with a digit
        if w[0].isdigit():
            continue
        tokens.append(w)
    return tokens


def _extract_multi_word(text, multi_word_terms=None):
    """Find known multi-word technical terms in text."""
    terms = multi_word_terms if multi_word_terms is not None else MULTI_WORD_TERMS
    text_lower = text.lower()
    found = set()
    for term in terms:
        if term in text_lower:
            found.add(term)
    return found


def _component_words(multi_word_set):
    """
    Return the set of individual words that make up any matched multi-word term.
    These should not be extracted as standalone keywords — the multi-word form
    already captures the concept (e.g. don't add "management" and "stakeholder"
    separately when "stakeholder management" is already matched).
    """
    components = set()
    for term in multi_word_set:
        for part in re.split(r"[\s\-/]+", term):
            part = part.strip("()[]")
            if part and len(part) > 2:
                components.add(part.lower())
    return components


# ── Title scoring ──────────────────────────────────────────────────────────────

# Default title history — used for ATS title match scoring.
# Override by editing user_profile.titles in config.json.
_TITLE_HISTORY = [
    "senior product manager",
    "platform product manager",
    "technical product manager",
    "product manager",
]

# Weight map: how much each match quality contributes to title_score (0.0–1.0)
_TITLE_SCORE_MAP = {
    "exact":    1.00,   # e.g. "senior product manager" == "senior product manager"
    "close":    0.85,   # same function, minor modifier difference
    "adjacent": 0.60,   # same department (director → PM, PM → director)
    "weak":     0.35,   # loosely related (program manager, project manager)
    "none":     0.10,   # unrelated
}

def _score_ats_title(job_title, resume_canonical, syn_map):
    """
    Score how well the job title matches the user's known title history.
    Returns a float 0.0–1.0 for use in the ATS formula.

    resume_canonical: the canonicalized resume keyword set (unused here,
                      kept for signature consistency with future expansion).
    syn_map: synonym map (unused here, kept for consistency).
    """
    jt = job_title.lower().strip()
    if not jt:
        return 0.70  # No title provided — neutral

    # Exact match against any known title
    for known in _TITLE_HISTORY:
        if jt == known:
            return _TITLE_SCORE_MAP["exact"]

    # Strong signal words present
    pm_signal = bool(re.search(r"\bproduct\s+manager\b", jt))
    director_signal = bool(re.search(r"\bdirector\b", jt))
    vp_signal = bool(re.search(r"\bvice\s+president\b|\bvp\b", jt))
    program_signal = bool(re.search(r"\bprogram\s+manager\b", jt))
    project_signal = bool(re.search(r"\bproject\s+manager\b", jt))

    if pm_signal:
        return _TITLE_SCORE_MAP["close"]     # Any PM variant is a close match

    if director_signal or vp_signal:
        return _TITLE_SCORE_MAP["adjacent"]  # Leadership adjacency

    if program_signal or project_signal:
        return _TITLE_SCORE_MAP["weak"]      # Related but different function

    return _TITLE_SCORE_MAP["none"]


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_resume_keywords(resume_path, custom_keywords=None):
    """
    Read a .docx resume and extract a deduplicated keyword set.

    custom_keywords: list of strings from config.json → custom_keywords.
                     User-specific domain terms (e.g. "real estate", "proptech")
                     are added directly to the keyword set.
    Returns a sorted list of strings.
    """
    try:
        doc = Document(resume_path)
    except Exception:
        return []

    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    multi_word_terms = _get_multi_word_terms(custom_keywords)

    keywords = set()

    # Multi-word terms first (universal + user-defined)
    multi = _extract_multi_word(full_text, multi_word_terms)
    keywords |= multi

    # Don't re-extract component words of already-matched multi-word terms
    blocked = _component_words(multi)

    # Single meaningful tokens
    for word in _tokenize(full_text):
        if word not in STOP_WORDS and word not in blocked and len(word) > 2:
            keywords.add(word)

    # Add single-word custom_keywords directly (multi-word already handled above)
    if custom_keywords:
        for kw in custom_keywords:
            kw_lower = kw.lower().strip()
            if " " not in kw_lower and kw_lower:
                keywords.add(kw_lower)

    return sorted(keywords)


def extract_jd_keywords(posting_text, multi_word_terms=None):
    """
    Extract required and preferred keyword sets from a job description.

    multi_word_terms: pre-built list from _get_multi_word_terms(). If None,
                      uses MULTI_WORD_TERMS only.
    Returns dict with keys: required (set), preferred (set).
    """
    req_text, pref_text, _ = _split_jd_sections(posting_text)
    terms = multi_word_terms if multi_word_terms is not None else MULTI_WORD_TERMS

    def build_set(text):
        multi = _extract_multi_word(text, terms)
        # Don't re-extract the individual component words of matched multi-word terms.
        # "stakeholder management" is already captured — "stakeholder" and "management"
        # as standalone tokens would inflate the denominator and dilute the score.
        blocked = _component_words(multi)
        kw = set(multi)
        for word in _tokenize(text):
            if word not in STOP_WORDS and word not in blocked and len(word) > 2:
                kw.add(word)
        return kw

    return {
        "required": build_set(req_text),
        "preferred": build_set(pref_text),
    }


def score_ats(posting_text, resume_keywords, weights,
              job_title="", custom_keywords=None, custom_synonyms=None):
    """
    Calculate ATS keyword match score.

    job_title:        The job's title string, used for title match scoring.
    custom_keywords:  list from config.json → custom_keywords. Passed to
                      _get_multi_word_terms() so user domain terms are included
                      in JD extraction too.
    custom_synonyms:  list of lists from config.json → custom_synonyms. Merged
                      with built-in SYNONYM_GROUPS before comparison.

    Returns:
        ats_score (int 0-100)
        matched_keywords (list)
        missing_keywords (list, required-missing first)
    """
    syn_map = _build_synonym_map(custom_synonyms)
    multi_word_terms = _get_multi_word_terms(custom_keywords)

    # Canonicalize resume keyword set
    resume_canonical = _canonicalize_set(set(k.lower() for k in resume_keywords), syn_map)

    # Extract JD keywords using expanded multi-word terms
    jd = extract_jd_keywords(posting_text, multi_word_terms)

    # Canonicalize JD keyword sets
    required  = _canonicalize_set(jd["required"],  syn_map)
    preferred = _canonicalize_set(jd["preferred"], syn_map)

    req_matched  = required  & resume_canonical
    req_missing  = required  - resume_canonical
    pref_matched = preferred & resume_canonical
    pref_missing = preferred - resume_canonical

    req_score   = len(req_matched)  / len(required)  if required  else 1.0
    pref_score  = len(pref_matched) / len(preferred) if preferred else 1.0
    title_score = _score_ats_title(job_title, resume_canonical, syn_map)

    raw = (
        req_score   * weights.get("required_skills",  0.60)
        + pref_score  * weights.get("preferred_skills", 0.25)
        + title_score * weights.get("title_match",      0.15)
    )

    ats_score = min(round(raw * 100), 100)

    # Sort: required-missing first, then preferred-missing (no overlap)
    matched = sorted(req_matched | pref_matched)
    missing = sorted(req_missing) + sorted(pref_missing - req_missing)

    return {
        "ats_score":        ats_score,
        "matched_keywords": matched[:30],
        "missing_keywords": missing[:20],
    }


# ── Section splitter ───────────────────────────────────────────────────────────

def _split_jd_sections(posting_text):
    """
    Split the JD into required, preferred, and general sections.
    Returns (required_text, preferred_text, general_text).
    """
    lines = posting_text.split("\n")
    sections = {"required": [], "preferred": [], "general": []}
    current = "general"

    for line in lines:
        line_lower = line.lower().strip()
        if any(m in line_lower for m in REQUIRED_SECTION_MARKERS):
            current = "required"
        elif any(m in line_lower for m in PREFERRED_SECTION_MARKERS):
            current = "preferred"
        sections[current].append(line)

    # If nothing ended up in required, treat everything as required
    if not sections["required"]:
        sections["required"] = lines

    return (
        " ".join(sections["required"]),
        " ".join(sections["preferred"]),
        " ".join(sections["general"]),
    )


# ── Job filters ───────────────────────────────────────────────────────────────

# Non-US countries / regions — if explicitly referenced as the job location, skip
_NON_US_COUNTRY = re.compile(
    r"\b(serbia|belgrade|croatia|zagreb|romania|bucharest|"
    r"ukraine|kyiv|poland|warsaw|czech|prague|hungary|budapest|"
    r"united\s+kingdom|uk\b|england|scotland|wales|london|manchester|"
    r"germany|berlin|munich|hamburg|france|paris|lyon|"
    r"netherlands|amsterdam|spain|madrid|barcelona|"
    r"italy|rome|milan|portugal|lisbon|sweden|stockholm|"
    r"norway|oslo|denmark|copenhagen|finland|helsinki|"
    r"switzerland|zurich|austria|vienna|belgium|brussels|"
    r"australia|sydney|melbourne|brisbane|new\s+zealand|auckland|"
    r"canada|toronto|vancouver|montreal|ottawa|calgary|"
    r"india|bangalore|mumbai|delhi|hyderabad|"
    r"singapore|hong\s+kong|japan|tokyo|china|beijing|shanghai|"
    r"brazil|sao\s+paulo|mexico|argentina|colombia|chile|"
    r"israel|tel\s+aviv|south\s+africa|nigeria|kenya)\b",
    re.I,
)

# Signals that a non-US country name is being used as a JOB LOCATION
_LOCATION_CONTEXT = re.compile(
    r"(?:location|located\s+in|based\s+in|office\s+in|"
    r"headquartered\s+in|work\s+from|remote\s+(?:from|in|within|only)|"
    r"applicants?\s+(?:must|should)\s+be\s+(?:in|based|located)|"
    r"open\s+to\s+candidates?\s+in|"
    r"eligible\s+to\s+work\s+in)",
    re.I,
)

# Clear US signals — if present anywhere, treat as US job
_US_SIGNAL = re.compile(
    r"\b(united\s+states|usa\b|u\.s\.a\b|u\.s\.\b|"
    r"alabama|alaska|arizona|arkansas|california|colorado|"
    r"connecticut|delaware|florida|georgia|hawaii|idaho|"
    r"illinois|indiana|iowa|kansas|kentucky|louisiana|"
    r"maine|maryland|massachusetts|michigan|minnesota|"
    r"mississippi|missouri|montana|nebraska|nevada|"
    r"new\s+hampshire|new\s+jersey|new\s+mexico|new\s+york|"
    r"north\s+carolina|north\s+dakota|ohio|oklahoma|oregon|"
    r"pennsylvania|rhode\s+island|south\s+carolina|south\s+dakota|"
    r"tennessee|texas|utah|vermont|virginia|washington|"
    r"west\s+virginia|wisconsin|wyoming|"
    r"\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|"
    r"LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|"
    r"OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b)\b",
    re.I,
)

# Cybersecurity role titles / domains to exclude
_CYBER_TITLE = re.compile(
    r"\b(cyber\s*security|cybersec|information\s+security|infosec|"
    r"security\s+engineer|penetration\s+test|pen\s+test|"
    r"soc\s+analyst|threat\s+intel|vulnerability|"
    r"devsecops|siem|firewall|intrusion\s+detection|"
    r"ciso|chief\s+information\s+security)\b",
    re.I,
)

_DEGREE_WORDS = re.compile(
    r"\b(bachelor'?s?\s+degree|master'?s?\s+degree|"
    r"b\.s\b|b\.a\b|m\.s\b|m\.b\.a\b|\bmba\b|"
    r"4-year\s+degree|four.year\s+degree|"
    r"undergraduate\s+degree|college\s+degree|advanced\s+degree)\b",
    re.I,
)
_REQUIRE_WORDS = re.compile(
    r"\b(required|requires?|must\s+have|must-have|mandatory|"
    r"minimum\s+qualifications?|minimum\s+requirements?|minimum\s+education|"
    r"basic\s+qualifications?|essential|necessary)\b",
    re.I,
)
_DEGREE_EXEMPT = re.compile(
    r"\bor\s+(equivalent|relevant|comparable|related)\s+(work\s+)?experience\b"
    r"|\bor\s+equivalent\b"
    r"|\bor\s+(a\s+)?combination\s+of\s+education",
    re.I,
)


def _build_region_pattern(onsite_regions):
    """
    Build a regex from the user's configured onsite_regions list.
    Returns None if the list is empty (disables the location filter).
    """
    if not onsite_regions:
        return None
    escaped = [re.escape(r.strip()) for r in onsite_regions if r.strip()]
    if not escaped:
        return None
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.I)


def should_skip_job(title, posting_text, work_style="", job_filters=None):
    """
    Return (True, reason) if the job should be silently dropped, else (False, "").

    Filters applied in order:
      1. Cybersecurity roles — title match
      2. Degree hard-required — posting text, excluding "or equivalent experience"
      3. Non-US location — if require_us_only is True in job_filters
      4. Onsite/hybrid outside allowed regions — only if onsite_regions is configured

    job_filters: dict from config.json job_filters block. Keys:
      require_us_only (bool)  — drop jobs explicitly located outside the US
      allow_remote (bool)     — always accept remote roles
      onsite_regions (list)   — city/region names to accept for onsite/hybrid roles
                                leave empty to accept all onsite/hybrid locations
    """
    filters      = job_filters or {}
    require_us   = filters.get("require_us_only", True)
    allow_remote = filters.get("allow_remote", True)
    regions      = filters.get("onsite_regions", [])
    region_re    = _build_region_pattern(regions)

    combined = f"{title} {posting_text}"
    snippet  = posting_text if posting_text else ""

    # ── 1. Cybersecurity title filter ─────────────────────────────────────
    if _CYBER_TITLE.search(title):
        return True, "cybersecurity role"

    # ── 2. Degree required filter ─────────────────────────────────────────
    req_text, _, _ = _split_jd_sections(snippet)
    req_section_detected = any(m in req_text.lower() for m in REQUIRED_SECTION_MARKERS)

    for dm in _DEGREE_WORDS.finditer(req_text):
        w0 = max(0, dm.start() - 300)
        w1 = min(len(req_text), dm.end() + 300)
        window = req_text[w0:w1]
        if _DEGREE_EXEMPT.search(window):
            continue
        if req_section_detected or _REQUIRE_WORDS.search(window):
            return True, f"degree required ({dm.group(0).strip()})"

    # ── 3. Non-US location filter ─────────────────────────────────────────
    if require_us:
        for cm in _NON_US_COUNTRY.finditer(snippet):
            w0 = max(0, cm.start() - 200)
            w1 = min(len(snippet), cm.end() + 100)
            window = snippet[w0:w1]
            if _LOCATION_CONTEXT.search(window) and not _US_SIGNAL.search(window):
                return True, f"non-US location ({cm.group(0).strip()})"

    # ── 4. Onsite / hybrid outside configured regions ─────────────────────
    if region_re:
        effective_style = work_style or (
            "Remote"  if re.search(r"\bremote\b",       combined, re.I) else
            "Hybrid"  if re.search(r"\bhybrid\b",       combined, re.I) else
            "Onsite"  if re.search(r"\bon.?site\b|\bin.?office\b|\bin.?person\b", combined, re.I) else
            ""
        )
        if effective_style in ("Onsite", "Hybrid"):
            if allow_remote and re.search(r"\bremote\b", combined, re.I):
                pass  # Has remote option — let it through
            elif not region_re.search(combined):
                return True, f"outside configured regions ({effective_style})"

    return False, ""


def generate_recommendations(job_title, company, ats_score, missing_keywords, matched_keywords):
    """
    Generate a plain-language resume optimization list.
    Formatted for direct paste into an LLM alongside the resume.
    """
    lines = [
        f"Resume optimization — {job_title} at {company}",
        f"Current ATS score: {ats_score}% — target: 85%+",
        "",
        f"Keywords matched ({len(matched_keywords)}): {', '.join(matched_keywords[:15])}{'...' if len(matched_keywords) > 15 else ''}",
        "",
        f"Keywords missing from your resume ({len(missing_keywords)}):",
    ]

    for i, kw in enumerate(missing_keywords, 1):
        lines.append(
            f"  {i}. \"{kw}\" — add to Skills section or rephrase a relevant bullet to include it naturally"
        )

    lines += [
        "",
        "─" * 60,
        "Instructions for your LLM:",
        "Paste this list above along with your current resume and say:",
        "",
        "  'Update my resume to include the missing keywords listed above,",
        "   only where they are naturally supported by my actual experience.",
        "   Do not add new bullets, metrics, tools, or accomplishments.",
        "   Same facts — better keyword alignment only.'",
        "",
        "Rules:",
        "  - No fabrication",
        "  - No new bullets or metrics not in the original",
        "  - Rephrase existing bullets only",
        "  - Skills section additions are fine if the skill is real",
    ]

    return "\n".join(lines)
