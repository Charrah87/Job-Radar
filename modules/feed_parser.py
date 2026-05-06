import feedparser
import requests
from urllib.parse import urlparse, parse_qs, unquote
from html import unescape
import re

# Path segments that indicate editorial / non-job content
_NON_JOB_PATH_SEGMENTS = {
    "news", "blog", "article", "articles", "press", "press-release",
    "press-releases", "research", "insights", "whitepaper", "whitepapers",
    "resources", "events", "webinar", "podcast", "newsletter",
    "announcement", "announcements", "story", "stories", "post", "posts",
    "opinion", "media", "publication", "publications",
}


def _is_non_job_url(url, blocked_domains=None):
    """
    Return True if the URL looks like editorial content rather than a job posting.

    Checks (in order):
      1. Domain matches a blocked_domains entry from config.json
      2. Path starts with /@ — user profile pages (e.g. himalayas.app/@username)
      3. Any path segment matches known editorial patterns (/news/, /blog/, etc.)
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.lower()

        # 1. Explicit domain blocklist
        if blocked_domains:
            for domain in blocked_domains:
                if domain.lower() in hostname:
                    return True

        # 2. User profile pattern (/@username)
        if path.startswith("/@"):
            return True

        # 3. Editorial path segment check
        for part in path.split("/"):
            part_clean = part.split("?")[0].split("#")[0]
            if part_clean in _NON_JOB_PATH_SEGMENTS:
                return True

    except Exception:
        pass
    return False


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_JSON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_rss_bytes(url, timeout=20):
    """
    Pre-fetch RSS content with requests so we get proper redirect following,
    cookie handling, and browser-like headers — then hand the bytes to
    feedparser for XML parsing.  Returns None on any failure.
    """
    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception:
        pass
    return None


def _fetch_json(url, timeout=20):
    """Fetch a JSON API endpoint. Returns parsed dict/list or None."""
    try:
        resp = requests.get(url, headers=_JSON_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def extract_real_url(raw_url):
    """Extract the actual job URL from Google's redirect wrapper.

    Google Search uses ?q=  but Google Alerts RSS uses ?url= — check both.
    """
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url)
        params = parse_qs(parsed.query)
        for key in ("q", "url"):
            if key in params:
                return unquote(params[key][0])
    except Exception:
        pass
    return raw_url


def detect_ats(url, ats_domains):
    """Detect ATS platform name from URL."""
    for domain, name in ats_domains.items():
        if domain in url:
            return name
    return "Unknown"


def extract_company_from_url(url, ats):
    """Best-effort company name extraction from ATS URL structure."""
    try:
        parts = urlparse(url).path.strip("/").split("/")
        if ats in ("Greenhouse",) and len(parts) >= 1:
            return parts[0].replace("-", " ").title()
        if ats in ("Lever", "Ashby") and len(parts) >= 1:
            return parts[0].replace("-", " ").title()
        if ats == "Workday":
            hostname = urlparse(url).hostname or ""
            company = hostname.split(".")[0]
            return company.replace("-", " ").title()
    except Exception:
        pass
    return ""


# Known job board / aggregator names — don't treat these as company names
_BOARD_NAMES = {
    "jobgether", "remoteleaf", "linkedin", "indeed", "glassdoor", "ziprecruiter",
    "monster", "wellfound", "builtin", "simplyhired", "careerbuilder", "dice",
    "flexjobs", "remoteok", "weworkremotely", "otta", "getwork", "jooble",
    "joblist", "talent", "talentcom", "betterteam", "snagajob", "lensa",
    "remotive", "arbeitnow", "jobicy",
}

# Words that appear after " - " but are modifiers, not company names
_SUFFIX_NOISE = {
    "remote", "hybrid", "onsite", "contract", "full-time", "part-time",
    "us", "usa", "global", "worldwide", "anywhere", "urgent",
}


def extract_company_from_title(raw_title):
    """
    Extract company name from common RSS title formats:
      "Job Title at Company Name"
      "Job Title - Company Name"
    Returns "" if nothing useful found.
    """
    text = re.sub(r"<[^>]+>", "", raw_title).strip()

    # Pattern: "… at Company Name [optional trailing modifier]"
    m = re.search(r"\bat\s+([A-Z][^\|\-–\n]+?)(?:\s*[-–|].*)?$", text)
    if m:
        candidate = m.group(1).strip().rstrip("–-| ").strip()
        if (candidate.lower() not in _SUFFIX_NOISE
                and candidate.lower() not in _BOARD_NAMES
                and len(candidate) > 1):
            return candidate

    # Pattern: "Job Title - Company Name" (last segment after final " - ")
    if " - " in text:
        parts = text.rsplit(" - ", 1)
        candidate = parts[-1].strip()
        if (candidate.lower() not in _SUFFIX_NOISE
                and candidate.lower() not in _BOARD_NAMES
                and not re.match(r"^\d", candidate)
                and len(candidate) > 2):
            return candidate

    return ""


def clean_title(raw_title):
    """Strip HTML tags, decode entities, and remove trailing company suffix."""
    title = re.sub(r"<[^>]+>", "", raw_title).strip()
    title = unescape(title)
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        title = parts[0].strip()
    return title


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "").strip()


# ── JSON API parsers ──────────────────────────────────────────────────────────

def _parse_remotive(data, label, ats_domains):
    """Parse Remotive API response: {jobs: [{url, title, company_name, ...}]}"""
    results = []
    for job in data.get("jobs", []):
        url = job.get("url", "").strip()
        if not url:
            continue
        title = _strip_html(job.get("title", ""))
        company = job.get("company_name", "")
        summary = _strip_html(job.get("description", ""))[:800]
        ats = detect_ats(url, ats_domains)
        results.append({
            "feed_label": label,
            "url": url,
            "ats": ats,
            "title": title,
            "company": company,
            "summary": summary,
        })
    return results


def _parse_arbeitnow(data, label, ats_domains):
    """Parse Arbeitnow API response: {data: [{url, title, company_name, ...}]}"""
    results = []
    for job in data.get("data", []):
        url = job.get("url", "").strip()
        if not url:
            continue
        # Only keep remote jobs
        if not job.get("remote", False):
            continue
        title = _strip_html(job.get("title", ""))
        company = job.get("company_name", "")
        summary = _strip_html(job.get("description", ""))[:800]
        ats = detect_ats(url, ats_domains)
        results.append({
            "feed_label": label,
            "url": url,
            "ats": ats,
            "title": title,
            "company": company,
            "summary": summary,
        })
    return results


# ── Main fetch function ───────────────────────────────────────────────────────

def fetch_feeds(config):
    """
    Fetch all configured feeds (RSS/Atom or JSON API).
    Feed config entries may include a "type" field:
      - omitted / "rss"       → standard RSS/Atom via feedparser
      - "remotive_api"        → Remotive JSON API
      - "arbeitnow_api"       → Arbeitnow JSON API
    Returns a list of raw job dicts ready for processing.
    """
    ats_domains     = config.get("ats_domains", {})
    blocked_domains = config.get("blocked_domains", [])
    results = []

    for feed_cfg in config.get("rss_feeds", []):
        label    = feed_cfg.get("label", "")
        feed_url = feed_cfg.get("url", "")
        ftype    = feed_cfg.get("type", "rss")
        if not feed_url:
            continue

        # ── JSON API feeds ────────────────────────────────────────────────
        if ftype == "remotive_api":
            data = _fetch_json(feed_url)
            if data:
                results.extend(_parse_remotive(data, label, ats_domains))
            continue

        if ftype == "arbeitnow_api":
            data = _fetch_json(feed_url)
            if data:
                results.extend(_parse_arbeitnow(data, label, ats_domains))
            continue

        # ── RSS / Atom feeds ──────────────────────────────────────────────
        try:
            content = _fetch_rss_bytes(feed_url)
            if content:
                feed = feedparser.parse(content)
            else:
                feed = feedparser.parse(feed_url)
        except Exception:
            continue

        for entry in feed.entries:
            raw_link = entry.get("link", "")
            real_url = extract_real_url(raw_link)
            if not real_url:
                continue

            # Drop editorial content and profile pages before any further processing
            if _is_non_job_url(real_url, blocked_domains):
                continue

            raw_title = entry.get("title", "")
            ats = detect_ats(real_url, ats_domains)

            company = extract_company_from_url(real_url, ats)
            if not company:
                company = extract_company_from_title(raw_title)

            title   = clean_title(raw_title)
            summary = _strip_html(entry.get("summary", ""))

            results.append({
                "feed_label": label,
                "url": real_url,
                "ats": ats,
                "title": title,
                "company": company,
                "summary": summary,
            })

    return results
