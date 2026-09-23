"""Arbeitnow job feed adapter."""

from typing import List
from engine.sources.base import BaseSourceAdapter
from engine.models import NormalizedListing
from engine.filters import compute_fingerprint, is_agency_suspect
from engine.config import HUNT_CONFIG


class ArbeitnowAdapter(BaseSourceAdapter):
    source_name = "arbeitnow"

    def fetch(self) -> List[NormalizedListing]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        data = self._http_get(url)
        if not data or not isinstance(data, dict):
            return []

        jobs = data.get("data", [])
        agency_hints = HUNT_CONFIG.get("agency_name_hints", [])
        listings: List[NormalizedListing] = []

        for job in jobs:
            slug = str(job.get("slug") or "")
            native_id = slug or str(job.get("url") or "")
            title = str(job.get("title") or "")
            company = str(job.get("company_name") or "")
            loc = str(job.get("location") or "")
            job_url = str(job.get("url") or "")
            desc = str(job.get("description") or "")
            posted_at = str(job.get("created_at") or "")
            remote = bool(job.get("remote", False))

            # Arbeitnow is a German job board. Mark country as DE unless location explicitly specifies US
            is_explicit_us = any(term in loc.lower() for term in ["united states", "usa", "us-remote", "remote, us"])
            country_val = "US" if is_explicit_us else "DE"

            listing = NormalizedListing(
                listing_id=f"arbeitnow:{native_id}",
                fingerprint=compute_fingerprint(company, title),
                source=self.source_name,
                title=title,
                company=company,
                location=loc,
                country=country_val,
                remote=remote,
                posted_at=posted_at,
                url=job_url,
                description=desc,
                agency_suspect=is_agency_suspect(company, title, agency_hints),
            )
            listings.append(listing)

        return listings
