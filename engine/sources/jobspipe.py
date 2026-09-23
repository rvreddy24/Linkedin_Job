"""JobsPipe API source adapter."""

from typing import List, Tuple
from engine.sources.base import BaseSourceAdapter
from engine.models import NormalizedListing
from engine.filters import compute_fingerprint, is_agency_suspect
from engine.config import JOBSPIPE_API_KEY, HUNT_CONFIG


class JobsPipeAdapter(BaseSourceAdapter):
    source_name = "jobspipe"

    def __init__(self, api_key: str = JOBSPIPE_API_KEY):
        self.api_key = api_key
        self.last_credits_spent = 0
        self.last_total_results = 0

    def fetch(self) -> List[NormalizedListing]:
        if not self.api_key or not self.api_key.startswith("jp_"):
            print("[jobspipe] No valid JOBSPIPE_API_KEY found. Skipping JobsPipe search.")
            return []

        url = "https://api.jobspipe.dev/v1/jobs/search"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        queries = HUNT_CONFIG.get("jobspipe_queries", [["Forward Deployed Engineer", "AI Solutions Engineer", "GenAI Engineer"]])
        limit = HUNT_CONFIG.get("jobspipe_limit", 25)
        posted_days = HUNT_CONFIG.get("posted_within_days", 1)
        agency_hints = HUNT_CONFIG.get("agency_name_hints", [])

        listings: List[NormalizedListing] = []

        for q_list in queries:
            payload = {
                "job_title_or": q_list,
                "job_country_code_or": ["US"],
                "posted_at_max_age_days": posted_days,
                "limit": limit,
                "include_total_results": True,
            }

            resp = self._http_post(url, json_data=payload, headers=headers)
            if not resp:
                continue

            metadata = resp.get("metadata", {})
            self.last_credits_spent += metadata.get("credits_charged", 0)
            self.last_total_results = max(self.last_total_results, metadata.get("total_results", 0))

            items = resp.get("data", [])
            for item in items:
                native_id = str(item.get("id") or "")
                title = str(item.get("job_title") or "")
                company = str(item.get("company") or "")
                location = str(item.get("location") or "")
                country = str(item.get("country_code") or "US")
                remote = bool(item.get("remote", False))
                posted_at = str(item.get("date_posted") or "")
                job_url = str(item.get("source_url") or "")
                desc = str(item.get("description") or "")

                listing = NormalizedListing(
                    listing_id=f"jobspipe:{native_id}",
                    fingerprint=compute_fingerprint(company, title),
                    source=self.source_name,
                    title=title,
                    company=company,
                    location=location,
                    country=country,
                    remote=remote,
                    posted_at=posted_at,
                    url=job_url,
                    description=desc,
                    agency_suspect=is_agency_suspect(company, title, agency_hints),
                )
                listings.append(listing)

        return listings
