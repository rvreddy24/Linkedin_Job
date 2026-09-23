"""Data models for Auto Bot LinkedIn Job."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class NormalizedListing(BaseModel):
    listing_id: str
    fingerprint: str
    source: str
    title: str
    company: str
    location: str = ""
    country: str = ""
    remote: bool = False
    employment_type: str = ""
    posted_at: str = ""
    url: str
    description: str = ""
    agency_suspect: bool = False


class ScoringResult(BaseModel):
    type: Literal["DIRECT_GIG", "BUY_SIGNAL", "IGNORE"] = "IGNORE"
    score: int = Field(default=0, ge=0, le=100)
    band: Literal["low", "medium", "high"] = "low"
    one_line_fit: str = ""
    angle: str = ""
    approach_role: str = ""
    asks_for: str = ""
    concern: str = ""
    agency_post: bool = False
    keep: bool = False


class PipelineItem(BaseModel):
    listing_id: str
    fingerprint: str
    run_at: str
    type: str
    score: int
    band: str
    company: str
    title: str
    location: str
    country: str
    source: str
    url: str
    one_line_fit: str
    angle: str
    approach_role: str
    asks_for: str
    concern: str
    agency_post: bool
    status: Literal["new", "drafted", "opened", "contact_sent", "cooldown", "dead"] = "new"
    draft: str = ""
    last_touch_at: Optional[str] = None


class TouchRecord(BaseModel):
    touched_at: str
    company_key: str
    listing_id: str
    action: Literal["draft", "open", "contact"]
    preview: str = ""
