"""Normalization, US location filtering, fingerprinting, and keyword prefilters."""

import re
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from engine.models import NormalizedListing

# Comprehensive regex for non-US indicators (cities, countries, regions, timezones)
NON_US_PATTERN = re.compile(
    r"\b("
    r"london|manchester|birmingham|edinburgh|glasgow|bristol|leeds|cambridge\s*,\s*uk|oxford\s*,\s*uk|"
    r"uk|united kingdom|great britain|england|scotland|wales|ireland|dublin|belfast|"
    r"india|bengaluru|bangalore|hyderabad|pune|mumbai|delhi|new delhi|noida|gurugram|gurgaon|chennai|kolkata|"
    r"germany|deutschland|berlin|munich|münchen|frankfurt|darmstadt|hamburg|cologne|köln|stuttgart|düsseldorf|leipzig|"
    r"singapore|malaysia|kuala lumpur|indonesia|jakarta|philippines|manila|vietnam|ho chi minh|hanoi|thailand|bangkok|"
    r"paris|lyon|marseille|france|spain|madrid|barcelona|valencia|italy|rome|milan|naples|"
    r"canada|toronto|vancouver|montreal|ottawa|calgary|edmonton|waterloo|quebec|ontario|british columbia|"
    r"australia|sydney|melbourne|brisbane|perth|adelaide|new zealand|auckland|wellington|"
    r"netherlands|amsterdam|rotterdam|utrecht|hague|switzerland|zurich|geneva|basel|austria|vienna|"
    r"sweden|stockholm|gothenburg|norway|oslo|denmark|copenhagen|finland|helsinki|"
    r"poland|warsaw|krakow|wroclaw|czech|prague|brno|romania|bucharest|cluj|portugal|lisbon|porto|"
    r"greece|athens|belgium|brussels|hungary|budapest|bulgaria|sofia|ukraine|kyiv|"
    r"japan|tokyo|osaka|kyoto|korea|seoul|china|beijing|shanghai|shenzhen|taiwan|taipei|hong kong|"
    r"brazil|são paulo|sao paulo|rio de janeiro|mexico|mexico city|guadalajara|monterrey|argentina|buenos aires|colombia|bogota|chile|santiago|"
    r"israel|tel aviv|jerusalem|uae|dubai|abu dhabi|saudi arabia|riyadh|egypt|cairo|nigeria|lagos|kenya|nairobi|south africa|cape town|johannesburg|"
    r"europe|european|emea|latam|apac|asia|middle east|oceania|africa|"
    r"worldwide|global|anywhere\s+in\s+the\s+world|worldwide\s+remote|"
    r"cet|cest|gmt|bst|ist|eet|eest|aest|awst|acst|nzst|westeurope|easteurope"
    r")\b",
    re.IGNORECASE,
)

# DACH / German anti-discrimination legal markers (m/f/d, m/w/d...)
DACH_PATTERN = re.compile(
    r"\b\(?(m/f/d|m/w/d|d/m/w|m/w/x|f/m/d)\)?\b",
    re.IGNORECASE,
)

# Regex for positive US indicators in location strings
US_PATTERN = re.compile(
    r"(?:"
    r"\b(united states|usa|u\.s\.a?|u\.s\.|"
    r"us-remote|remote,\s*us|remote\s*-\s*us|remote\s+us|us\s+only|us-only|"
    r"us\s+based|us-based|based\s+in\s+the\s+us|anywhere\s+in\s+the\s+us|"
    r"authorized\s+to\s+work\s+in\s+the\s+us|us\s+citizens?|green\s+card|"
    r"\b[A-Z]{2}\b\s+remote)\b|"
    r"remote\s*\(\s*us\s*\)|\(\s*us\s*\)|\b(?:us|usa)\b"
    r")",
    re.IGNORECASE,
)

# Regex for positive US indicators in job descriptions (avoiding pronoun 'us')
US_DESC_PATTERN = re.compile(
    r"\b("
    r"united states|usa|u\.s\.|us-remote|remote,\s*us|remote\s*\(us\)|"
    r"us\s+only|us-based|based\s+in\s+the\s+us|anywhere\s+in\s+the\s+us|"
    r"authorized\s+to\s+work\s+in\s+the\s+us|us\s+citizens?|green\s+card|"
    r"eligible\s+to\s+work\s+in\s+the\s+united\s+states"
    r")\b",
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

# Full US state names
US_STATES_FULL = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
    "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
    "new york", "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia"
}

# Major US tech cities
US_TECH_CITIES = {
    "san francisco", "san jose", "sunnyvale", "mountain view", "palo alto", "santa clara",
    "cupertino", "menlo park", "redwood city", "oakland", "berkeley", "bay area", "sf bay area", "silicon valley",
    "los angeles", "san diego", "seattle", "bellevue", "redmond", "austin", "dallas", "houston",
    "san antonio", "fort worth", "new york", "new york city", "nyc", "manhattan", "brooklyn",
    "boston", "cambridge", "chicago", "atlanta", "denver", "boulder", "salt lake city", "portland",
    "miami", "raleigh", "durham", "charlotte", "philadelphia", "pittsburgh", "washington dc", "dc metro",
    "phoenix", "scottsdale", "minneapolis"
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


def is_us_listing(
    country: str,
    location: str,
    remote: bool,
    title: str = "",
    description: str = "",
) -> bool:
    """
    Strict USA-Only location gatekeeper.
    Every listing (remote, hybrid, or on-site) must be strictly confirmed in the US.
    Immediate drop if:
      - Country is explicitly non-US.
      - Title, location, or country matches non-US countries, foreign cities, timezones (CET, BST), or DACH markers.
      - Vague remote roles (e.g. 'Worldwide' or plain 'Remote') with NO verified US residency requirement.
    """
    # 1. German/DACH legal markers (m/f/d) in title or location
    if title and DACH_PATTERN.search(title):
        return False
    if location and DACH_PATTERN.search(location):
        return False

    norm_country = str(country or "").strip().upper()
    norm_loc = str(location or "").strip()
    lower_loc = norm_loc.lower()

    # 2. Drop if country is explicitly non-US
    if norm_country and norm_country not in {"US", "USA", "UNITED STATES"}:
        return False

    # 3. Drop if title or location mentions non-US cities, countries, or regions
    if NON_US_PATTERN.search(norm_loc):
        return False
    if title and NON_US_PATTERN.search(title):
        return False

    # 4. Check for positive US indicators
    has_positive_us = False

    if norm_country in {"US", "USA", "UNITED STATES"}:
        has_positive_us = True
    elif US_PATTERN.search(norm_loc):
        has_positive_us = True
    elif re.search(r",\s*([A-Za-z]{2})\b", norm_loc) and re.search(r",\s*([A-Za-z]{2})\b", norm_loc).group(1).upper() in US_STATES:
        has_positive_us = True
    elif any(st in lower_loc for st in US_STATES_FULL):
        has_positive_us = True
    elif any(city in lower_loc for city in US_TECH_CITIES):
        has_positive_us = True

    # 5. Remote and Hybrid enforcement
    if has_positive_us:
        return True

    # If role is marked remote or hybrid, only allow if description explicitly confirms US presence
    if remote and description:
        if DACH_PATTERN.search(description):
            return False
        if US_DESC_PATTERN.search(description):
            return True

    # Otherwise (e.g. unverified 'Remote', 'Worldwide', or non-US location) -> Drop!
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
