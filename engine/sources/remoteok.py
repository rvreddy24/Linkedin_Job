"""RemoteOK free job feed adapter."""

from typing import List
from engine.sources.base import BaseSourceAdapter
from engine.models import NormalizedListing
from engine.filters import compute_fingerprint, is_agency_suspect
from engine.config import HUNT_CONFIG


class RemoteOKAdapter(BaseSourceAdapter):
    source_name = "remoteok"

    def fetch(self) -> List[NormalizedListing]:
        url = "https://remoteok.com/api"
        data = self._http_get(url)
        if not data or not isinstance(data, list):
            return []

        agency_hints = HUNT_CONFIG.get("agency_name_hints", [])
        listings: List[NormalizedListing] = []

        for item in data:
            if not isinstance(item, dict):
                continue
            # RemoteOK includes legal notice as first element without 'id' or with 'legal' key
            if "id" not in item or "position" not in item:
                continue

            native_id = str(item.get("id") or "")
            title = str(item.get("position") or "")
            company = str(item.get("company") or "")
            loc = str(item.get("location") or "")
            job_url = str(item.get("url") or "")
            desc = str(item.get("description") or "")
            posted_at = str(item.get("date") or "")

            listing = NormalizedListing(
                listing_id=f"remoteok:{native_id}",
                fingerprint=compute_fingerprint(company, title),
                source=self.source_name,
                title=title,
                company=company,
                location=loc,
                country="",
                remote=True,
                posted_at=posted_at,
                url=job_url,
                description=desc,
                agency_suspect=is_agency_suspect(company, title, agency_hints),
            )
            listings.append(listing)

        return listings
