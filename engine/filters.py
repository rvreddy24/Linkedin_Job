"""Normalization, US location filtering, fingerprinting, and keyword prefilters."""

import re
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from engine.models import NormalizedListing

# Regex for non-US indicators
NON_US_PATTERN = re.compile(
    r"\b(london|bengaluru|bangalore|uk|united kingdom|india|germany|deutschland|singapore|berlin|munich|münchen|frankfurt|darmstadt|hamburg|cologne|köln|stuttgart|paris|france|canada|toronto|vancouver|australia|sydney|melbourne|netherlands|amsterdam|europe|emea|latam|apac|brazil|mexico|poland|spain|madrid|barcelona|ireland|dublin|japan|tokyo|switzerland|zurich|austria|vienna)\b",
    re.IGNORECASE,
)

# DACH / German anti-discrimination legal markers (m/f/d, m/w/d...)
DACH_PATTERN = re.compile(
    r"\b\(?(m/f/d|m/w/d|d/m/w|m/w/x|f/m/d)\)?\b",
    re.IGNORECASE,
)

# Regex for US location indicators
US_PATTERN = re.compile(
    r"\b(united states|usa|u\.s\.a?|u\.s\.|\b[A-Z]{2}\b\s+remote|us-remote|remote,\s*us|remote\s*\(us\)|us\s+only|anywhere\s+in\s+the\s+us)\b",
    re.IGNORECASE,
)

# Two-letter US state postal abbreviations
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
}


def norm(s: str) -> str:
    """Normalize string: lowercase, replace & with 'and', alphanumeric words only."""
    if not s:
        return ""
    text = str(s).lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def company_key(s: str) -> str:
    """Normalize company name and strip common legal suffixes."""
    normalized = norm(s)
    cleaned = re.sub(
        r"\b(pvt|private|ltd|limited|inc|llc|llp|gmbh|plc|corp|corporation)\b",
        "",
        normalized,
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def compute_fingerprint(company: str, title: str) -> str:
    """Compute deduplication fingerprint: companyKey(company) + '|' + norm(title)."""
    return f"{company_key(company)}|{norm(title)}"


def is_agency_suspect(company: str, title: str, agency_hints: List[str]) -> bool:
    """Check if employer is suspect recruiter or staffing agency."""
    combined = f"{company} {title}".lower()
    for hint in agency_hints:
        if hint.lower() in combined:
            return True
    return False


def is_us_listing(country: str, location: str, remote: bool, title: str = "") -> bool:
    """
    US keep rule:
    country in {US, USA, United States, ''} AND
    (location matches US patterns OR country==US OR (remote==true and matches US)).
    Drop if clearly non-US (e.g. London, Germany, Munich, m/f/d, Bengaluru).
    """
    if title and DACH_PATTERN.search(title):
        return False

    norm_country = str(country or "").strip().upper()
    norm_loc = str(location or "").strip()

    if DACH_PATTERN.search(norm_loc):
        return False

    # Immediate drop if country is clearly non-US (e.g., GB, UK, IN, DE, CA, AU, etc.)
    if norm_country and norm_country not in {"US", "USA", "UNITED STATES"}:
        return False

    # Check for obvious non-US locations in the string
    if NON_US_PATTERN.search(norm_loc):
        return False

    # Positive US indicators
    if norm_country in {"US", "USA", "UNITED STATES"}:
        return True

    if US_PATTERN.search(norm_loc):
        return True

    # Check for State patterns like "Austin, TX" or "New York, NY"
    state_match = re.search(r",\s*([A-Za-z]{2})\b", norm_loc)
    if state_match and state_match.group(1).upper() in US_STATES:
        return True

    # Remote cases
    if remote:
        lower_loc = norm_loc.lower()
        if not norm_loc or lower_loc in {"remote", "us-remote", "remote, us", "remote (us)"}:
            return True
        if US_PATTERN.search(norm_loc):
            return True
        # If location specifies worldwide or global, keep only if US is explicitly allowed
        if "worldwide" in lower_loc or "global" in lower_loc or "anywhere" in lower_loc:
            return bool(US_PATTERN.search(norm_loc))
        # If it explicitly mentions "remote" and is not marked with non-US indicators
        if "remote" in lower_loc and not NON_US_PATTERN.search(norm_loc):
            return True

    return False


def keyword_prefilter(
    title: str,
    description: str,
    keywords_include: List[str],
    keywords_exclude_title: List[str],
) -> bool:
    """
    Keep if title or description contains any keywords_include (case-insensitive).
    Drop if title matches keywords_exclude_title unless an include keyword also hits.
    Drop empty titles.
    """
    if not title or not title.strip():
        return False

    title_lower = title.lower()
    desc_lower = description.lower() if description else ""

    # Check includes
    has_include = False
    for kw in keywords_include:
        kw_l = kw.lower()
        if kw_l in title_lower or kw_l in desc_lower:
            has_include = True
            break

    if not has_include:
        return False

    # Check excludes on title
    has_exclude = False
    for ex in keywords_exclude_title:
        if ex.lower() in title_lower:
            has_exclude = True
            break

    if has_exclude:
        # Check if an include keyword is in the TITLE itself to override
        title_has_include = any(kw.lower() in title_lower for kw in keywords_include)
        if not title_has_include:
            return False

    return True


def deduplicate_listings(
    listings: List[NormalizedListing],
    seen_listing_ids: set,
    seen_fingerprints: set,
) -> Tuple[List[NormalizedListing], int]:
    """
    Drop incoming rows that match either seen listing_id or seen fingerprint.
    Returns (unique_listings, duplicates_dropped_count).
    """
    unique_items: List[NormalizedListing] = []
    dropped_count = 0

    for item in listings:
        if item.listing_id in seen_listing_ids or item.fingerprint in seen_fingerprints:
            dropped_count += 1
            continue

        seen_listing_ids.add(item.listing_id)
        seen_fingerprints.add(item.fingerprint)
        unique_items.append(item)

    return unique_items, dropped_count


def parse_posted_datetime(posted_at: str) -> Optional[datetime]:
    """Parse ISO format, unix timestamps, and common date formats to UTC datetime."""
    if not posted_at:
        return None

    # Unix epoch timestamp (seconds or milliseconds)
    try:
        ts = float(posted_at)
        if ts > 1e11:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, OSError):
        pass

    # ISO 8601 strings
    cleaned = str(posted_at).replace("Z", "+00:00").strip()
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Common string patterns
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ):
        try:
            dt = datetime.strptime(posted_at, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    return None


def is_posted_within_hours(posted_at: str, max_hours: int = 24, now: Optional[datetime] = None) -> bool:
    """Check if a posting was published within max_hours (defaults to 24 hours)."""
    dt = parse_posted_datetime(posted_at)
    if not dt:
        return False

    if now is None:
        now = datetime.now(timezone.utc)

    age_seconds = (now - dt).total_seconds()
    # Allow up to 1h future drift for server clock disparities, and max_hours in past
    return -3600 <= age_seconds <= (max_hours * 3600)
