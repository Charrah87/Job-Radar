import re

# ── Default domain term sets ──────────────────────────────────────────────
# These are used when scoring domain fit. You can extend these in the future
# by adding domain terms to config.json under user_profile.preferred_domains.

PROPTECH_TERMS = {
    "real estate", "proptech", "mls", "listings", "listing data",
    "title insurance", "escrow", "mortgage", "agents", "brokers",
}

SAAS_TERMS = {
    "saas", "api", "platform", "developer", "b2b", "integration",
    "integration platform", "data platform", "marketplace", "developer tools",
    "enterprise software", "cloud", "microservices", "webhook",
}

ADJACENT_TERMS = {
    "fintech", "hrtech", "martech", "edtech", "healthtech", "insurtech",
    "legaltech", "regtech", "payments", "e-commerce",
}

# ── Scoring helpers ───────────────────────────────────────────────────────

def score_title_match(jd_title, user_titles=None):
    """
    Score title relevance against the user's configured title history.
    user_titles: list of titles from config.json user_profile.titles (most to least senior).
    Returns 0–3.
    """
    t = jd_title.lower()

    # Check for exact or close match against user's own titles first
    if user_titles:
        for i, title in enumerate(user_titles):
            if title.lower() in t:
                # First title = best match, score decreases slightly for each subsequent
                return max(3.0 - (i * 0.3), 1.5)

    # Generic PM title scoring as fallback
    if "senior product manager" in t:
        return 3.0
    if "lead product manager" in t or "principal product manager" in t:
        return 2.5
    if "technical product manager" in t or "platform product manager" in t:
        return 2.5
    if re.search(r"\bplatform\s+pm\b", t) or re.search(r"\bpm\b.*\bplatform\b", t):
        return 2.5
    if "staff product manager" in t or "group product manager" in t:
        return 2.0
    if "product manager" in t and "associate" not in t:
        return 2.0
    if "associate product manager" in t:
        return 1.5
    if "product owner" in t or "senior product owner" in t:
        return 2.0
    if "director of product" in t or "head of product" in t or "vp of product" in t:
        return 1.5
    if "customer success manager" in t or "client success manager" in t:
        return 1.0
    if "technical account manager" in t or "technical customer success" in t:
        return 1.0
    if "program manager" in t:
        return 0.8
    return 0.3


def score_experience_level(posting_text, user_years=5):
    """
    Score years-of-experience match against the user's configured background.
    user_years: total years from config.json user_profile.years_experience.
    Returns 0–2.
    """
    text = posting_text.lower()

    patterns = [
        r"(\d+)\+?\s*(?:-\s*\d+)?\s*years?\s+of\s+(?:product\s+management|product\s+manager|pm\s+experience|product\s+experience)",
        r"(\d+)\+?\s*(?:-\s*\d+)?\s*years?\s+(?:of\s+)?(?:relevant\s+)?experience",
        r"minimum\s+(?:of\s+)?(\d+)\s+years?",
        r"at\s+least\s+(\d+)\s+years?",
    ]

    required_years = None
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            required_years = int(match.group(1))
            break

    if required_years is None:
        return 1.5  # Not stated — neutral

    if required_years <= user_years:
        return 2.0  # User meets or exceeds requirement
    if required_years <= user_years + 2:
        return 1.5  # Slight stretch
    if required_years <= user_years + 5:
        return 1.0  # Covered by total tenure
    return 0.5      # Requires significantly more experience


def score_domain_fit(posting_text, preferred_domains=None):
    """
    Score domain/industry alignment against user's preferred domains.
    preferred_domains: list from config.json user_profile.preferred_domains.
    Returns 0–1.
    """
    text = posting_text.lower()
    preferred = set(d.lower() for d in (preferred_domains or []))

    # PropTech / real estate
    if any(term in text for term in PROPTECH_TERMS):
        score = 1.0
        return score if "proptech" in preferred or "real estate" in preferred or not preferred else 0.7

    # SaaS / API / Platform
    if any(term in text for term in SAAS_TERMS):
        score = 0.8
        return score if any(d in preferred for d in ("saas", "api", "platform")) or not preferred else 0.6

    # Adjacent tech verticals
    if any(term in text for term in ADJACENT_TERMS):
        return 0.5

    return 0.2


def score_work_style(posting_text):
    """Score work style match against remote-first preference. Returns 0–1."""
    text = posting_text.lower()

    if any(p in text for p in ["fully remote", "remote-first", "100% remote", "all remote"]):
        return 1.0
    if "remote" in text and "hybrid" not in text and "in-office" not in text and "onsite" not in text:
        return 1.0
    if "hybrid" in text:
        return 0.7
    if any(p in text for p in ["in-office", "on-site", "onsite", "in office"]):
        return 0.2
    return 0.7  # Not stated — default to hybrid assumption


def score_skills_coverage(ats_score):
    """
    Convert ATS percentage score to fit-score skills factor.
    Returns 0–3.
    """
    pct = ats_score / 100.0
    if pct >= 0.80:
        return 3.0
    if pct >= 0.65:
        return 2.0
    if pct >= 0.45:
        return 1.5
    if pct >= 0.25:
        return 0.5
    return 0.0


def calculate_fit_score(job_title, posting_text, ats_score, user_profile=None):
    """
    Calculate holistic fit score (0–10).

    Factors:
      title_match       (0–3)  — compares job title against user_profile.titles
      skills_coverage   (0–3)  — derived from ats_score
      experience_level  (0–2)  — compares JD requirements against user_profile.years_experience
      domain_fit        (0–1)  — checks user_profile.preferred_domains
      work_style        (0–1)  — remote/hybrid/onsite preference

    user_profile is read from config.json. Defaults apply if not provided.
    """
    profile = user_profile or {}
    user_titles = profile.get("titles", [])
    user_years  = profile.get("years_experience", 5)
    preferred_domains = profile.get("preferred_domains", [])

    title_pts  = score_title_match(job_title, user_titles)
    skills_pts = score_skills_coverage(ats_score)
    exp_pts    = score_experience_level(posting_text, user_years)
    domain_pts = score_domain_fit(posting_text, preferred_domains)
    style_pts  = score_work_style(posting_text)

    total = title_pts + skills_pts + exp_pts + domain_pts + style_pts
    return min(round(total), 10)
