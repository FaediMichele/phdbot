"""Wave reports must count persisted jobs and mark estimates as observed data."""

import pytest

from scripts.catalog_wave_report import summarize


def _job(job_id: int, state: str, seconds: int | None) -> dict[str, object]:
    return {
        "id": job_id,
        "state": state,
        "institution_id": str(job_id),
        "pipeline_run_id": job_id + 100 if seconds is not None else None,
        "started_at": "2026-10-01T00:00:00Z" if seconds is not None else None,
        "finished_at": f"2026-10-01T00:00:{seconds:02d}Z" if seconds is not None else None,
        "discovery_status": "done" if seconds is not None else "pending",
        "schema": {},
        "error": "source unreachable" if state == "failed" else None,
    }


def test_wave_report_counts_failures_remaining_and_observed_eta() -> None:
    snapshot = {
        "captured_at": "2026-10-01T01:00:00Z",
        "jobs": [_job(1, "done", 20), _job(2, "failed", 40), _job(3, "scheduled", None)],
        "sources": [{"university_id": 1, "quality_status": "healthy", "schema_status": "ok",
                     "quality_reason": None, "url": "https://example.org/jobs", "adapter": None}],
        "outcomes": [
            {"university_id": 1, "rows": 2, "current_indexed_markers": 1,
             "position_type": "phd", "routing_reason": "evidence:retry"}
        ],
    }
    plan = {"objective": "wave", "jobs": {"batch": {"status": "accepted", "schedule_ids": [1, 2, 3],
                                                      "ids": [2, 1, 3],
                                                      "groups": ["facility", "education", "facility"]}}}
    result = summarize(snapshot, plan)
    assert result["states"] == {"done": 1, "failed": 1, "scheduled": 1}
    assert result["remaining"] == 1
    assert result["timing_seconds"]["all_mean"] == 30.0
    assert result["timing_seconds"]["remaining_central_seconds"] == 30
    assert result["timing_seconds"]["remaining_central_hours"] == 0.01
    assert result["failed"][0]["schedule_id"] == 2
    assert result["positions"]["current_indexed_markers"] == 1
    assert result["sources"]["institutions_without_sources"] == 1
    assert result["positions"]["routing_reasons"] == {"evidence:retry": 2}
    assert result["groups"]["education"]["current_indexed_markers"] == 1
    assert result["groups"]["facility"]["current_indexed_markers"] == 0


def test_wave_report_rejects_missing_or_duplicate_schedule_ids() -> None:
    snapshot = {"captured_at": "2026-10-01T01:00:00Z", "jobs": [_job(1, "done", 20)], "sources": [], "outcomes": []}
    plan = {"objective": "wave", "jobs": {"batch": {"status": "accepted", "schedule_ids": [1, 2]}}}
    with pytest.raises(ValueError, match="missing 1"):
        summarize(snapshot, plan)
    plan["jobs"]["batch"]["schedule_ids"] = [1, 1]
    with pytest.raises(ValueError, match="repeats"):
        summarize(snapshot, plan)
