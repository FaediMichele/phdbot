"""Request and response types for persistent one-shot schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from phd_searcher.typedef.pipeline import PipelineStartBody

ScheduleTarget = Literal["pipeline", "macro"]
ScheduleState = Literal[
    "scheduled",
    "waiting_pipeline",
    "starting",
    "running",
    "done",
    "failed",
    "cancelled",
]


class GovernorPlan(BaseModel):
    """Agent-prepared useful work; estimate is not a reset-time cutoff."""

    model_config = ConfigDict(extra="forbid")
    cwd: str = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=2000)
    expected_result: str = Field(min_length=1, max_length=2000)
    estimated_seconds: int = Field(gt=0, le=604800)
    estimate_basis: str = Field(min_length=1, max_length=2000)
    expires_at: AwareDatetime
    approved: Literal[True]
    requires_codex: Literal[False]
    provider_routes_verified: Literal[True]
    valet_wake_root_id: str | None = Field(default=None, min_length=1, max_length=128)


class ScheduleCreate(BaseModel):
    """A local wall-clock time in the only supported deployment timezone."""

    target: ScheduleTarget
    run_at: datetime
    timezone: Literal["Europe/Rome"] = "Europe/Rome"
    pipeline: PipelineStartBody | None = None
    macro_id: int | None = Field(default=None, ge=1)
    governor_plan: GovernorPlan | None = None

    @model_validator(mode="after")
    def target_payload(self) -> Self:
        if self.target == "pipeline" and (self.pipeline is None or self.macro_id is not None):
            raise ValueError("pipeline schedules require pipeline parameters and no macro_id")
        if self.target == "macro" and (self.macro_id is None or self.pipeline is not None):
            raise ValueError("macro schedules require macro_id and no pipeline parameters")
        if self.governor_plan is not None and self.target != "pipeline":
            raise ValueError("governor plans currently support pipeline schedules only")
        return self


class ScheduleView(BaseModel):
    id: int
    target: ScheduleTarget
    state: ScheduleState
    run_at: datetime
    local_run_at: datetime
    timezone: Literal["Europe/Rome"]
    pipeline: PipelineStartBody | None = None
    macro_id: int | None = None
    pipeline_run_id: int | None = None
    macro_run_id: int | None = None
    governor_plan: GovernorPlan | None = None
    attempts: int = 0
    next_attempt_at: datetime | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
