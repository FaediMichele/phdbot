"""Bounded activation of already imported registry institutions."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from phd_searcher.typedef.schedule import GovernorPlan, ScheduleView


class ExpansionCandidate(BaseModel):
    id: int
    name: str
    country: str
    website_url: str
    catalog_tier: str


class ExpansionPreview(BaseModel):
    total: int
    catalog_only: int
    with_sources: int
    with_positions: int
    with_indexed_markers: int
    candidates: list[ExpansionCandidate]


class ExpansionCreate(BaseModel):
    institution_ids: list[int] = Field(min_length=1, max_length=10)
    max_sources: int = Field(default=3, ge=1, le=5)
    max_pages: int = Field(default=3, ge=1, le=5)
    governor_plan: GovernorPlan | None = None

    @field_validator("institution_ids")
    @classmethod
    def unique_positive_ids(cls, value: list[int]) -> list[int]:
        if any(identifier <= 0 for identifier in value) or len(set(value)) != len(value):
            raise ValueError("institution IDs must be positive and distinct")
        return value


class ExpansionQueued(BaseModel):
    state: Literal["queued"] = "queued"
    schedules: list[ScheduleView]
