"""Remotive free job feed adapter."""

from typing import List
from engine.sources.base import BaseSourceAdapter
from engine.models import NormalizedListing
from engine.filters import compute_fingerprint, is_agency_suspect
from engine.config import HUNT_CONFIG


class RemotiveAdapter(BaseSourceAdapter):
    source_name = "remotive"

    def fetch(self) -> List[NormalizedListing]:
        url = "https://remotive.com/api/remote-jobs"
        data = self._http_get(url)
        if not data or not isinstance(data, dict):
            return []

        jobs = data.get("jobs", [])
        agency_hints = HUNT_CONFIG.get("agency_name_hints", [])
        listings: List[NormalizedListing] = []

        for job in jobs:
            native_id = str(job.get("id") or "")
            title = str(job.get("title") or "")
            company = str(job.get("company_name") or "")
            loc = str(job.get("candidate_required_location") or "")
            job_url = str(job.get("url") or "")
            desc = str(job.get("description") or "")
            posted_at = str(job.get("publication_date") or "")
            job_type = str(job.get("job_type") or "")

            listing = NormalizedListing(
                listing_id=f"remotive:{native_id}",
                fingerprint=compute_fingerprint(company, title),
                source=self.source_name,
                title=title,
                company=company,
                location=loc,
                country="",
                remote=True,
                employment_type=job_type,
                posted_at=posted_at,
                url=job_url,
                description=desc,
                agency_suspect=is_agency_suspect(company, title, agency_hints),
            )
            listings.append(listing)

        return listings
