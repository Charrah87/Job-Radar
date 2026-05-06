import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 12

# ── Aggregator detection ──────────────────────────────────────────────────────
_AGGREGATOR_DOMAINS = {
    "theladders.com", "linkedin.com", "indeed.com", "glassdoor.com",
    "ziprecruiter.com", "monster.com", "wellfound.com", "builtin.com",
    "simplyhired.com", "careerbuilder.com", "dice.com", "flexjobs.com",
    "remoteok.com", "weworkremotely.com", "otta.com", "getwork.com",
    "jooble.org", "jobgether.com", "remoteleaf.com", "lensa.com",
    "snagajob.com", "talent.com", "joblist.com", "dailyremote.com",
}

# Domains to skip when scanning pages for outbound company links
_SKIP_DOMAINS = _AGGREGATOR_DOMAINS | {
    "google.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "apple.com", "microsoft.com", "cloudflare.com",
    "duckduckgo.com", "bing.com",
}

# Sites that require a login to view content — skip page fetching entirely
_NO_FETCH_DOMAINS = {"linkedin.com"}


def is_aggregator_url(url):
    """Return True if the URL is from a job board aggregator rather than a direct ATS."""
    try:
        hostname = urlparse(url).hostname or ""
        return any(d in hostname for d in _AGGREGATOR_DOMAINS)
    except Exception:
        return False


def _ddg_first_result(query):
    """
    Search DuckDuckGo HTML and return the first result URL.
    Returns "" on failure or no results.
    """
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", class_="result__a"):
            href = a.get("href", "")
            if not href:
                continue
            # DDG wraps real URLs: //duckduckgo.com/l/?uddg=ENCODED_URL&...
            if href.startswith("//"):
                href = "https:" + href
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
            if href.startswith("http"):
                return href
    except Exception:
        pass
    return ""


def _extract_company_link_from_aggregator(soup, company_name):
    """
    Scan an aggregator page's outbound links for the company's own website.
    Returns the scheme+hostname of the first matching external link, or "".
    """
    if not soup:
        return ""

    company_slug = re.sub(r"[^a-z0-9]", "", (company_name or "").lower())

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            continue
        try:
            parsed = urlparse(href)
            hostname = parsed.hostname or ""
        except Exception:
            continue

        if any(d in hostname for d in _SKIP_DOMAINS):
            continue

        # Match if company name appears in the domain (e.g. "kalepa.com" for "Kalepa")
        host_clean = re.sub(r"[^a-z0-9]", "", hostname.lower())
        if company_slug and len(company_slug) > 2 and company_slug in host_clean:
            return f"{parsed.scheme}://{hostname}"

    return ""


def _find_ats_url_in_aggregator(soup, ats_domains):
    """
    Scan an aggregator page's links for a direct ATS posting URL.
    Returns the first ATS URL found, or "" if none.
    """
    if not soup:
        return ""
    ats_domain_list = list(ats_domains.keys())
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            continue
        try:
            hostname = urlparse(href).hostname or ""
            if any(d in hostname for d in ats_domain_list):
                return href
        except Exception:
            continue
    return ""


def resolve_aggregator_url(url, ats_domains):
    """
    For aggregator URLs, attempt to find the direct ATS posting URL
    embedded in the page. Returns the ATS URL if found, else the original URL.
    Skips resolution entirely for sites behind login walls (e.g. LinkedIn).
    """
    if not is_aggregator_url(url):
        return url
    try:
        hostname = urlparse(url).hostname or ""
        if any(d in hostname for d in _NO_FETCH_DOMAINS):
            return url
    except Exception:
        pass
    soup = _get_soup(url)
    ats_url = _find_ats_url_in_aggregator(soup, ats_domains)
    return ats_url if ats_url else url


def _find_linkedin_page(company_name):
    """
    Search DuckDuckGo for the company's LinkedIn page.
    Returns a normalized linkedin.com/company/slug URL or "".
    """
    if not company_name:
        return ""
    raw = _ddg_first_result(f'site:linkedin.com/company "{company_name}"')
    if not raw:
        return ""
    # Normalize: strip trailing paths/params beyond the company slug
    m = re.search(r"(https://(?:www\.)?linkedin\.com/company/[^/?#\s]+)", raw)
    return m.group(1) if m else ""


def _get_soup(url):
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None


def _clean_text(text):
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def fetch_job_text(url, ats, fallback=""):
    """
    Fetch full job description text from the ATS careers page.
    Falls back to the RSS snippet if scraping fails or returns too little.
    """
    soup = _get_soup(url)
    if not soup:
        return fallback

    text = ""

    if ats == "Greenhouse":
        content = (
            soup.find(id="content")
            or soup.find("div", class_=re.compile(r"job-post|posting", re.I))
            or soup.find("main")
        )
        if content:
            text = _clean_text(content.get_text(separator=" "))

    elif ats == "Lever":
        content = (
            soup.find("div", class_=re.compile(r"posting-page|content-wrapper", re.I))
            or soup.find("main")
        )
        if content:
            text = _clean_text(content.get_text(separator=" "))

    elif ats == "Ashby":
        # Ashby is often JS-rendered; try main content, fall back to snippet
        content = (
            soup.find("main")
            or soup.find("div", class_=re.compile(r"job|posting|description", re.I))
        )
        if content:
            text = _clean_text(content.get_text(separator=" "))

    elif ats == "Workday":
        content = (
            soup.find("div", class_=re.compile(r"job-description|gwt-Label", re.I))
            or soup.find("main")
        )
        if content:
            text = _clean_text(content.get_text(separator=" "))

    else:
        body = soup.find("body")
        if body:
            text = _clean_text(body.get_text(separator=" "))[:4000]

    # If we got very little text, use fallback
    if len(text) < 200:
        return fallback or text

    return text


def extract_company_website(soup, company_name):
    """Try to find the company's main website from the posting page."""
    if not soup:
        return ""
    # Look for links that mention the company or are external
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "greenhouse" not in href and "lever" not in href \
                and "ashby" not in href and "workday" not in href and "google" not in href:
            if company_name and company_name.lower().split()[0] in href.lower():
                return href
    return ""


def extract_company_description(soup, ats):
    """Extract the 'About the company' section from the posting."""
    if not soup:
        return ""
    about_patterns = re.compile(r"about\s+(us|the\s+company|company)", re.I)
    for tag in soup.find_all(["h2", "h3", "h4", "strong"]):
        if about_patterns.search(tag.get_text()):
            sibling = tag.find_next_sibling()
            if sibling:
                return _clean_text(sibling.get_text())[:400]
    return ""


def extract_job_details(text):
    """
    Extract salary range, location, and work style from posting text.
    Returns dict with keys: salary, location, work_style.
    """
    details = {"salary": "", "location": "", "work_style": ""}
    if not text:
        return details

    # ── Work style ────────────────────────────────────────────────────────
    t = text.lower()
    if re.search(r"\bhybrid\b", t):
        details["work_style"] = "Hybrid"
    elif re.search(r"\bfully\s+remote\b|\b100%\s+remote\b", t):
        details["work_style"] = "Remote"
    elif re.search(r"\bremote\b", t):
        details["work_style"] = "Remote"
    elif re.search(r"\bon.?site\b|\bin.?office\b|\bin.?person\b", t):
        details["work_style"] = "Onsite"

    # ── Salary ────────────────────────────────────────────────────────────
    # Matches: $120,000 - $160,000 / $120k-$160k / $120,000/yr / etc.
    salary_match = re.search(
        r"\$([\d,]+[kK]?)\s*(?:[-–to]+\s*\$([\d,]+[kK]?))?(?:\s*(?:per\s+year|\/yr|\/year|annually))?",
        text,
        re.I,
    )
    if salary_match:
        lo = salary_match.group(1).replace(",", "")
        hi = salary_match.group(2)
        if hi:
            hi = hi.replace(",", "")
            details["salary"] = f"${lo}–${hi}"
        else:
            details["salary"] = f"${lo}"

    # ── Location ─────────────────────────────────────────────────────────
    # Look for "Location: City, ST" or "City, State" near the top of the text
    loc_match = re.search(
        r"(?:location|based\s+in|office\s+in)[:\s]+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)",
        text, re.I
    )
    if loc_match:
        loc = loc_match.group(1).strip().rstrip(".")
        if len(loc) < 60:
            details["location"] = loc

    return details


def extract_contact_from_text(text):
    """Extract hiring manager or recruiter contact info from posting text."""
    contact = {"name": "", "title": "", "email": ""}
    if not text:
        return contact

    # Email
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    if emails:
        contact["email"] = emails[0]

    # Name + title patterns like "Contact: Jane Smith, Head of Recruiting"
    name_pattern = re.search(
        r"(?:contact|recruiter|reach out to|hiring manager)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
        text, re.I
    )
    if name_pattern:
        contact["name"] = name_pattern.group(1)

    return contact


def check_url_alive(url):
    """
    Return True if the URL is still live, False if it returns 404 or 410.
    Defaults to True on network errors — a connection failure is not the same
    as a posting being taken down, so we avoid falsely expiring jobs.
    """
    try:
        resp = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
        return resp.status_code not in (404, 410)
    except Exception:
        return True  # Network hiccup — don't expire


def fetch_company_info(url, ats, company_name, posting_text):
    """
    Build the company_info dict.

    Website resolution order:
      1. For aggregator/unknown URLs — scrape the page for an outbound company link,
         then fall back to a DuckDuckGo search.
      2. For direct ATS URLs (Greenhouse, Lever, etc.) — scan the posting page for
         an outbound company link using the existing extractor.
      3. Last resort: guess https://www.{slug}.com

    LinkedIn is resolved via DuckDuckGo for all jobs where the company name is known.
    """
    soup = _get_soup(url)
    description = extract_company_description(soup, ats) if soup else ""
    website = ""

    if is_aggregator_url(url) or ats == "Unknown":
        # Try to find the real company link embedded in the aggregator page
        if soup:
            website = _extract_company_link_from_aggregator(soup, company_name)
        # Fall back to DDG search
        if not website and company_name:
            website = _ddg_first_result(f'"{company_name}" company official website')
    else:
        # Direct ATS page — use existing outbound-link extractor
        website = extract_company_website(soup, company_name) if soup else ""

    # Last resort: guess from company name slug
    if not website and company_name:
        slug = company_name.lower().replace(" ", "")
        website = f"https://www.{slug}.com"

    # LinkedIn — search for all jobs where we have a company name
    linkedin = _find_linkedin_page(company_name)

    return {
        "description": description,
        "website": website,
        "linkedin": linkedin,
    }
