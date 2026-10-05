import pytest

from scripts.wave_event_bridge import terminal_receipt


def job(i, state="done"):
    return {"id": i, "state": state, "pipeline_run_id": i + 100,
            "finished_at": "2026-10-04T21:00:00Z" if state in {"done", "failed", "cancelled"} else None}


def test_last_schedule_done_does_not_mean_wave_done():
    assert terminal_receipt([1, 2], [job(1, "running"), job(2)]) is None
    assert terminal_receipt([1, 2], [job(2)]) is None
    assert terminal_receipt([1, 2], [job(1), job(2)])["status"] == "done"


def test_failed_or_cancelled_jobs_are_reported_only_when_wave_terminal():
    assert terminal_receipt([1, 2], [job(1, "failed"), job(2, "running")]) is None
    assert terminal_receipt([1, 2], [job(1, "failed"), job(2)])["status"] == "failed"
    assert terminal_receipt([1, 2], [job(1, "cancelled"), job(2)])["status"] == "failed"


def test_terminal_proof_requires_identity_timestamp_and_unique_ids():
    with pytest.raises(ValueError, match="unique"):
        terminal_receipt([1, 1], [job(1)])
    with pytest.raises(ValueError, match="identity"):
        terminal_receipt([1], [{**job(1), "pipeline_run_id": None}])
    assert terminal_receipt([1], [{**job(1), "finished_at": None}]) is None
