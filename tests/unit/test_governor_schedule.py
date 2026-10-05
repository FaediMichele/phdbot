import json
from datetime import UTC, datetime, timedelta

import pytest

from phd_searcher.service.governor_admission import governor_block_reason
from phd_searcher.typedef.pipeline import PipelineStartBody
from phd_searcher.typedef.schedule import GovernorPlan, ScheduleCreate
from tests.unit.test_schedule import _pipeline_job, _PipelineRecorder, _RecordingScheduleService


def plan() -> dict[str, object]:
    return {
        "cwd": "/project",
        "objective": "collect missing evidence",
        "expected_result": "bounded receipt",
        "estimated_seconds": 7200,
        "estimate_basis": "recent comparable runs around 2 hours",
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "approved": True,
        "requires_codex": False,
        "provider_routes_verified": True,
    }


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    state = {
        "updated_at": datetime.now(UTC).timestamp(),
        "enabled": True,
        "mode": "PARK",
        "manual_park": False,
        "park": {"reason": "dynamic safety reserve"},
        "pilot_projects": ["/project"],
    }
    p.write_text(json.dumps(state))
    monkeypatch.setenv("PHDBOT_GOVERNOR_STATE_FILE", str(p))
    return p, state


def test_two_hour_job_not_rejected_when_reset_is_imminent(state_file):
    p, s = state_file
    s["limits"] = {"five_hour": {"resets_at": datetime.now(UTC).timestamp() + 60}}
    p.write_text(json.dumps(s))
    assert governor_block_reason(plan()) is None


@pytest.mark.parametrize(
    "change",
    [
        {"manual_park": True},
        {"updated_at": 0},
        {"enabled": False},
        {"mode": "ERROR"},
        {"park": {"reason": "hook failure"}},
        {"pilot_projects": []},
    ],
)
def test_unsafe_governor_states_block(state_file, change):
    p, s = state_file
    s.update(change)
    p.write_text(json.dumps(s))
    assert governor_block_reason(plan())


def test_missing_and_corrupt_state_block(state_file):
    p, _ = state_file
    p.write_text("bad")
    assert governor_block_reason(plan())
    p.unlink()
    assert governor_block_reason(plan())


class Recorder(_RecordingScheduleService):
    async def _defer_governor(self, job_id, reason):
        self.deferred = (job_id, reason)


@pytest.mark.asyncio
async def test_gate_is_checked_at_dispatch_not_enqueue(state_file):
    p, s = state_file
    j = _pipeline_job()
    j.payload["_governor_plan"] = plan()
    s["manual_park"] = True
    p.write_text(json.dumps(s))
    pipeline = _PipelineRecorder()
    service = Recorder(j, pipeline)
    await service._dispatch(j.id)
    assert not pipeline.calls
    assert service.deferred
    s["manual_park"] = False
    p.write_text(json.dumps(s))
    await service._dispatch(j.id)
    assert len(pipeline.calls) == 1
    assert service.running == (11, 73)
    assert "_governor_plan" not in pipeline.calls[0][2]


@pytest.mark.asyncio
async def test_second_useful_job_waits_for_existing_pipeline(state_file):
    j = _pipeline_job()
    j.payload["_governor_plan"] = plan()
    pipeline = _PipelineRecorder("pipeline already running")
    service = Recorder(j, pipeline)
    await service._dispatch(j.id)
    assert service.deferred
    assert service.failed is None


def test_plan_is_visible_and_old_jobs_remain_compatible():
    j = _pipeline_job()
    j.payload["_governor_plan"] = plan()
    assert _RecordingScheduleService._view(j).governor_plan.estimated_seconds == 7200
    body = ScheduleCreate(
        target="pipeline",
        run_at=datetime.now(UTC) + timedelta(minutes=1),
        pipeline=PipelineStartBody(stages=["index"]),
        governor_plan=GovernorPlan.model_validate(plan()),
    )
    assert body.governor_plan.estimate_basis


def test_optional_valet_wake_root_survives_schedule_roundtrip():
    j = _pipeline_job()
    wake_plan = {**plan(), "valet_wake_root_id": "root-exact"}
    j.payload["_governor_plan"] = wake_plan
    assert _RecordingScheduleService._view(j).governor_plan.valet_wake_root_id == "root-exact"
    assert GovernorPlan.model_validate(plan()).valet_wake_root_id is None
