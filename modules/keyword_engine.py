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
    "drive", "manage", "managed", "managing", "management", "lead", "leading",
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
    # ── Generic action/ownership words that bleed everywhere ─────────────
    "open", "opening", "monitor", "monitoring", "ownership", "deliver",
    "delivery", "deliverable", "deliverables", "initiative", "initiatives",
    "execution", "execute", "launch", "launching", "hours", "alongside",
    "partner", "partnering", "ownership", "intake", "align", "alignment",
    "core", "own", "owns", "drive", "driven", "driving",

    # ── Generic seniority / title words (too broad to be ATS signal) ─────
    "senior", "junior", "associate", "principal", "staff",
    "manager", "director", "engineer", "analyst", "specialist",
    "coordinator", "recruiter", "contractor", "consultant", "advisor",
    "technical", "product", "digital", "global", "strategic", "general",

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
    "title", "titles", "type", "name", "value", "label", "item", "list",
    # ── Generic employment metadata ───────────────────────────────────────
    "employment", "full-time", "part-time", "contract", "permanent",
    "status", "category", "department", "location", "city", "state",
    "country", "zip", "code", "date", "posted", "updated", "active",
    "ago", "today", "yesterday", "apply", "click", "here", "now",
    "salaries", "salary", "similar", "jobs", "reviews", "ratings",
    "benefits", "interviews", "questions", "photos", "overview",
}

# Known multi-word technical terms to preserve
MULTI_WORD_TERMS = [
    "product strategy", "product roadmap", "product management", "product manager",
    "technical product manager", "platform product manager", "senior product manager",
    "root cause analysis", "executive reporting", "vendor management",
    "budget management", "stakeholder management", "multi-stakeholder",
    "data pipeline", "data migration", "data platform", "data integrity",
    "api platform", "api development", "rest api", "graphql api",
    "cross-functional", "go-to-market", "product-led growth",
    "machine learning", "artificial intelligence", "natural language",
    "real estate", "proptech", "mls integration", "listing data",
    "agile methodology", "scrum framework", "sprint planning",
    "customer success", "customer experience", "client success",
    "p95 latency", "service level", "observability",
]

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
        # years (2004), IDs (6748), or any token starting with a digit
        if w[0].isdigit():
            continue
        tokens.append(w)
    return tokens


def _extract_multi_word(text):
    """Find known multi-word technical terms in text."""
    text_lower = text.lower()
    found = set()
    for term in MULTI_WORD_TERMS:
        if term in text_lower:
            found.add(term)
    return found


def extract_resume_keywords(resume_path):
    """
    Read a .docx resume and extract a deduplicated keyword set.
    Returns a sorted list of strings.
    """
    try:
        doc = Document(resume_path)
    except Exception:
        return []

    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    keywords = set()

    # Multi-word terms first
    keywords |= _extract_multi_word(full_text)

    # Single meaningful tokens
    for word in _tokenize(full_text):
        if word not in STOP_WORDS and len(word) > 2:
            keywords.add(word)

    return sorted(keywords)


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


def extract_jd_keywords(posting_text):
    """
    Extract required and preferred keyword sets from a job description.
    Returns dict with keys: required (set), preferred (set).
    """
    req_text, pref_text, gen_text = _split_jd_sections(posting_text)

    def build_set(text):
        kw = set()
        kw |= _extract_multi_word(text)
        for word in _tokenize(text):
            if word not in STOP_WORDS and len(word) > 2:
                kw.add(word)
        return kw

    return {
        "required": build_set(req_text),
        "preferred": build_set(pref_text),
    }


def score_ats(posting_text, resume_keywords, weights):
    """
    Calculate ATS keyword match score.

    Returns:
        ats_score (int 0-100)
        matched_keywords (list)
        missing_keywords (list, required-missing first)
    """
    resume_set = set(k.lower() for k in resume_keywords)
    jd = extract_jd_keywords(posting_text)

    required = jd["required"]
    preferred = jd["preferred"]

    req_matched = required & resume_set
    req_missing = required - resume_set

    pref_matched = preferred & resume_set
    pref_missing = preferred - resume_set

    req_score = len(req_matched) / len(required) if required else 1.0
    pref_score = len(pref_matched) / len(preferred) if preferred else 1.0
    title_score = 0.80  # Baseline; fit_scorer handles title comparison

    raw = (
        req_score * weights.get("required_skills", 0.60)
        + pref_score * weights.get("preferred_skills", 0.25)
        + title_score * weights.get("title_match", 0.15)
    )

    ats_score = min(round(raw * 100), 100)

    # Sort: required-missing first, then preferred-missing
    matched = sorted(req_matched | pref_matched)
    missing = sorted(req_missing) + sorted(pref_missing - req_missing)

    return {
        "ats_score": ats_score,
        "matched_keywords": matched[:30],
        "missing_keywords": missing[:20],
    }


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
    # Escape each region name and join with OR
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
    filters       = job_filters or {}
    require_us    = filters.get("require_us_only", True)
    allow_remote  = filters.get("allow_remote", True)
    regions       = filters.get("onsite_regions", [])
    region_re     = _build_region_pattern(regions)

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
    # Only applies if the user has set onsite_regions in config.
    # If onsite_regions is empty, all onsite/hybrid locations are accepted.
    if region_re:
        effective_style = work_style or (
            "Remote"  if re.search(r"\bremote\b", combined, re.I) else
            "Hybrid"  if re.search(r"\bhybrid\b", combined, re.I) else
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
