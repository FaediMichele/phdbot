import copy
import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts import thermal_cpu_trial as trial


def setup_trial(tmp_path, monkeypatch, state="applying", current=0):
    now = datetime(2026, 10, 5, tzinfo=UTC)
    record = {"container_id": "a" * 64, "original_nano_cpus": 0,
              "target_nano_cpus": 4_000_000_000, "completion_event": "wave-cpu-test",
              "created_at": now.isoformat(), "expires_at": (now + timedelta(hours=2)).isoformat(),
              "state": state}
    actual = {"Id": "a" * 64, "HostConfig": {"NanoCpus": current},
              "Config": {"Labels": {"com.docker.compose.project": "phdbot", "com.docker.compose.service": "ollama"}}}
    path = tmp_path / "lease.json"
    trial.save(path, record)
    calls = []
    monkeypatch.setattr(trial, "inspect", lambda _: copy.deepcopy(actual))

    def update(container, limit):
        calls.append((container, limit))
        actual["HostConfig"]["NanoCpus"] = limit

    monkeypatch.setattr(trial, "update", update)
    return path, now, actual, calls


def test_apply_then_expire_restores_and_never_reapplies(tmp_path, monkeypatch):
    path, now, actual, calls = setup_trial(tmp_path, monkeypatch)
    assert trial.advance(path, tmp_path, now=now)["state"] == "active"
    assert actual["HostConfig"]["NanoCpus"] == 4_000_000_000
    assert trial.advance(path, tmp_path, now=now + timedelta(hours=3))["state"] == "restored"
    trial.advance(path, tmp_path, now=now + timedelta(hours=4))
    assert [c[1] for c in calls] == [4_000_000_000, 0]


def test_crash_after_docker_apply_does_not_repeat_mutation(tmp_path, monkeypatch):
    path, now, _, calls = setup_trial(tmp_path, monkeypatch, current=4_000_000_000)
    assert trial.advance(path, tmp_path, now=now)["state"] == "active"
    assert calls == []


def test_expired_unapplied_lease_never_applies(tmp_path, monkeypatch):
    path, now, _, calls = setup_trial(tmp_path, monkeypatch)
    assert trial.advance(path, tmp_path, now=now + timedelta(hours=3))["state"] == "restored"
    assert calls == []


def test_completed_wave_restores_early(tmp_path, monkeypatch):
    path, now, _, calls = setup_trial(tmp_path, monkeypatch, state="active", current=4_000_000_000)
    receipt = tmp_path / "var/valet-events/wave-cpu-test.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"kind": "wave_terminal", "status": "done",
                                   "jobs": [{"state": "done", "finished_at": now.isoformat()}]}))
    assert trial.advance(path, tmp_path, now=now)["state"] == "restored"
    assert [c[1] for c in calls] == [0]


@pytest.mark.parametrize("current", [0, 2_000_000_000])
def test_operator_change_is_preserved(tmp_path, monkeypatch, current):
    path, now, actual, calls = setup_trial(tmp_path, monkeypatch, state="active", current=current)
    assert trial.advance(path, tmp_path, now=now)["state"] == "conflict"
    assert actual["HostConfig"]["NanoCpus"] == current
    assert calls == []


def test_wrong_container_identity_is_rejected(tmp_path, monkeypatch):
    path, now, actual, calls = setup_trial(tmp_path, monkeypatch)
    actual["Id"] = "b" * 64
    with pytest.raises(ValueError, match="original"):
        trial.advance(path, tmp_path, now=now)
    assert calls == []


def test_restore_interruption_retries_original_budget(tmp_path, monkeypatch):
    path, now, actual, calls = setup_trial(tmp_path, monkeypatch, state="restoring", current=4_000_000_000)
    assert trial.advance(path, tmp_path, now=now)["state"] == "restored"
    assert actual["HostConfig"]["NanoCpus"] == 0
    assert len(calls) == 1


def test_invalid_expiry_or_budget_rejected(tmp_path, monkeypatch):
    path, now, _, calls = setup_trial(tmp_path, monkeypatch)
    data = json.loads(path.read_text())
    data["expires_at"] = (now + timedelta(days=1)).isoformat()
    trial.save(path, data)
    with pytest.raises(ValueError, match="six hours"):
        trial.advance(path, tmp_path, now=now)
    assert calls == []
