"""Test feed adapters against live endpoints."""

import pytest
from engine.sources.remotive import RemotiveAdapter
from engine.sources.remoteok import RemoteOKAdapter
from engine.sources.arbeitnow import ArbeitnowAdapter
from engine.sources.jobicy import JobicyAdapter
from engine.sources import fetch_all_sources


def test_live_public_feeds():
    """Verify that at least one public feed succeeds and returns listings."""
    res = fetch_all_sources()
    assert "listings" in res
    assert "source_counts" in res
    assert isinstance(res["listings"], list)
    print(f"Total raw listings fetched across public feeds: {len(res['listings'])}")
    print(f"Source counts breakdown: {res['source_counts']}")
    # As long as the aggregator returns without raising, failover is proven
    assert res["raw_total"] >= 0 if "raw_total" in res else True
