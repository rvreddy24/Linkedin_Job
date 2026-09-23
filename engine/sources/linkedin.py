"""Native LinkedIn guest job search adapter (USA Only, past 24h)."""

import re
import urllib.parse
from datetime import datetime, timezone
from typing import List

from engine.sources.base import BaseSourceAdapter
from engine.models import NormalizedListing
from engine.filters import compute_fingerprint, is_agency_suspect
from engine.config import HUNT_CONFIG


class LinkedInAdapter(BaseSourceAdapter):
    source_name = "linkedin"

    def fetch(self) -> List[NormalizedListing]:
        """
        Fetch real-time LinkedIn job postings from the public LinkedIn search endpoint.
        Filters specifically for United States, posted within the last 24 hours.
        """
        search_queries = [
            "Forward Deployed Engineer",
            "Forward Deployed AI",
            "AI Solutions Engineer",
            "GenAI Engineer",
            "GenAI Solutions Engineer",
            "LLM Engineer",
            "AI Agent Engineer",
            "Applied AI Engineer",
            "Full Stack AI Engineer",
            "AI Systems Engineer",
            "AI Engineer Intern",
            "Machine Learning Intern",
            "Junior AI Engineer",
            "Entry Level AI Engineer",
            "New Grad Software Engineer",
        ]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        agency_hints = HUNT_CONFIG.get("agency_name_hints", [])
        listings: List[NormalizedListing] = []
        seen_ids = set()

        for query in search_queries:
            q_enc = urllib.parse.quote_plus(query)
            # geoId=103644278 is LinkedIn's entity ID for USA, f_TPR=r86400 is past 24 hours
            url = (
                f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
                f"keywords={q_enc}&location=United+States&geoId=103644278&f_TPR=r86400&start=0"
            )

            try:
                import requests
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code != 200 or not r.text:
                    continue
                resp_text = r.text
            except Exception as e:
                print(f"[linkedin] Request error for '{query}': {e}")
                continue

            cards = re.findall(r'<li[^>]*>(.*?)</li>', resp_text, re.DOTALL)
            for c in cards:
                title_m = re.search(r'<h3 class="base-search-card__title">\s*([^<]+?)\s*</h3>', c)
                comp_m = re.search(r'<h4 class="base-search-card__subtitle">\s*(?:<a[^>]*>)?\s*([^<]+?)\s*(?:</a>)?\s*</h4>', c)
                loc_m = re.search(r'<span class="job-search-card__location">\s*([^<]+?)\s*</span>', c)
                link_m = re.search(r'<a class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)
                date_m = re.search(r'<time[^>]*datetime="([^"]+)"', c)
                id_m = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', c)

                if not title_m or not (comp_m or link_m):
                    continue

                native_id = id_m.group(1) if id_m else ""
                if not native_id and link_m:
                    slug_match = re.search(r'-(\d+)$', link_m.group(1))
                    native_id = slug_match.group(1) if slug_match else link_m.group(1)

                if native_id in seen_ids:
                    continue
                seen_ids.add(native_id)

                title = title_m.group(1).strip()
                company = comp_m.group(1).strip() if comp_m else "Company on LinkedIn"
                location = loc_m.group(1).strip() if loc_m else "United States"
                job_url = link_m.group(1).strip() if link_m else f"https://www.linkedin.com/jobs/view/{native_id}"
                posted_at = date_m.group(1) if date_m else datetime.now(timezone.utc).isoformat()

                listing = NormalizedListing(
                    listing_id=f"linkedin:{native_id}",
                    fingerprint=compute_fingerprint(company, title),
                    source=self.source_name,
                    title=title,
                    company=company,
                    location=location,
                    country="US",
                    remote=True if "remote" in location.lower() else False,
                    posted_at=posted_at,
                    url=job_url,
                    description=f"{title} at {company}. Location: {location}. View posting directly on LinkedIn.",
                    agency_suspect=is_agency_suspect(company, title, agency_hints),
                )
                listings.append(listing)

        print(f"[linkedin] Fetched {len(listings)} fresh US job postings from LinkedIn (past 24h)")
        return listings
