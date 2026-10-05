import json
import subprocess

from scripts import thermal_event_bridge as bridge


def receipt(tmp_path, kind="critical", notify=False):
    path = tmp_path / "exports/thermal-events/thermal-critical-test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": "done", "kind": kind, "notify": notify,
                                "observation_only": True, "pipeline_terminal": False, "cpu_c": 103}))
    return path


def test_critical_delivered_once_and_retry_does_not_repeat_desktop(tmp_path, monkeypatch):
    receipt(tmp_path)
    desktop = []
    calls = []
    monkeypatch.setattr(bridge, "notify_desktop", desktop.append)

    def fail(*args):
        calls.append(args)
        raise subprocess.TimeoutExpired("test", 1)

    monkeypatch.setattr(bridge, "publish_valet", fail)
    assert bridge.drain(tmp_path, tmp_path, tmp_path) == 1
    monkeypatch.setattr(bridge, "publish_valet", lambda *a: calls.append(a))
    assert bridge.drain(tmp_path, tmp_path, tmp_path) == 0
    assert bridge.drain(tmp_path, tmp_path, tmp_path) == 0
    assert len(desktop) == 1
    assert len(calls) == 2


def test_routine_pause_can_be_log_only(tmp_path, monkeypatch):
    receipt(tmp_path, kind="pause", notify=False)
    calls = []
    monkeypatch.setattr(bridge, "notify_desktop", calls.append)
    monkeypatch.setattr(bridge, "publish_valet", lambda *a: calls.append(a))
    assert bridge.drain(tmp_path, tmp_path, tmp_path) == 0
    assert calls == []


def test_pipeline_terminal_record_is_not_a_thermal_event(tmp_path, monkeypatch):
    p = receipt(tmp_path)
    p.write_text(json.dumps({"status": "done", "kind": "critical", "pipeline_terminal": True}))
    calls = []
    monkeypatch.setattr(bridge, "notify_desktop", calls.append)
    assert bridge.drain(tmp_path, tmp_path, tmp_path) == 1
    assert calls == []
