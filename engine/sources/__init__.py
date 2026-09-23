"""Sources aggregator for Auto Bot LinkedIn Job."""

from typing import List, Dict, Any
from engine.models import NormalizedListing
from engine.sources.jobspipe import JobsPipeAdapter
from engine.sources.remotive import RemotiveAdapter
from engine.sources.remoteok import RemoteOKAdapter
from engine.sources.arbeitnow import ArbeitnowAdapter
from engine.sources.jobicy import JobicyAdapter
from engine.sources.linkedin import LinkedInAdapter


def fetch_all_sources() -> Dict[str, Any]:
    """
    Fetch from all sources: LinkedIn, JobsPipe, Remotive, RemoteOK, Arbeitnow, Jobicy.
    Ensures that if one feed fails, the rest continue without aborting the run.
    """
    adapters = [
        LinkedInAdapter(),
        JobsPipeAdapter(),
        RemotiveAdapter(),
        RemoteOKAdapter(),
        ArbeitnowAdapter(),
        JobicyAdapter(),
    ]

    all_listings: List[NormalizedListing] = []
    source_counts: Dict[str, int] = {}
    credits_spent = 0
    total_matches = 0

    for adapter in adapters:
        name = adapter.source_name
        try:
            items = adapter.fetch()
            source_counts[name] = len(items)
            all_listings.extend(items)
            if isinstance(adapter, JobsPipeAdapter):
                credits_spent = adapter.last_credits_spent
                total_matches = adapter.last_total_results
        except Exception as e:
            print(f"[fetch_all_sources] Error fetching {name}: {e}")
            source_counts[name] = 0

    return {
        "listings": all_listings,
        "source_counts": source_counts,
        "credits_spent": credits_spent,
        "total_matches": total_matches,
    }
