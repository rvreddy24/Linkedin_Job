"""Jobicy free remote job feed adapter."""

from typing import List
from engine.sources.base import BaseSourceAdapter
from engine.models import NormalizedListing
from engine.filters import compute_fingerprint, is_agency_suspect
from engine.config import HUNT_CONFIG


class JobicyAdapter(BaseSourceAdapter):
    source_name = "jobicy"

    def fetch(self) -> List[NormalizedListing]:
        url = "https://jobicy.com/api/v2/remote-jobs"
        data = self._http_get(url)
        if not data or not isinstance(data, dict):
            return []

        jobs = data.get("jobs", [])
        agency_hints = HUNT_CONFIG.get("agency_name_hints", [])
        listings: List[NormalizedListing] = []

        for job in jobs:
            native_id = str(job.get("id") or "")
            title = str(job.get("jobTitle") or "")
            company = str(job.get("companyName") or "")
            geo = str(job.get("jobGeo") or "")
            job_url = str(job.get("url") or "")
            desc = str(job.get("jobDescription") or "")
            posted_at = str(job.get("pubDate") or "")
            job_type = str(job.get("jobType") or "")

            listing = NormalizedListing(
                listing_id=f"jobicy:{native_id}",
                fingerprint=compute_fingerprint(company, title),
                source=self.source_name,
                title=title,
                company=company,
                location=geo,
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
