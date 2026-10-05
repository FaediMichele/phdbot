import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from phd_searcher.pipeline.progress import Progress
from phd_searcher.service.schedule_service import ScheduleService
from phd_searcher.thermal import ThermalConfig, ThermalGuard, read_cpu_sensors


def ready_guard():
    guard = ThermalGuard(ThermalConfig(enabled=True, hot_seconds=10, cool_seconds=10))
    for t in (0, 5, 10):
        guard.observe({"cpu": 70}, t)
    assert not guard.blocked_at(10)
    return guard


def test_sustained_heat_and_cooling_hysteresis():
    g = ready_guard()
    g.observe({"cpu": 97}, 15)
    g.observe({"cpu": 97}, 20)
    assert not g.blocked_at(20)
    g.observe({"cpu": 97}, 25)
    assert g.blocked_at(25)
    g.observe({"cpu": 90}, 30)
    assert g.blocked_at(30)
    g.observe({"cpu": 80}, 35)
    g.observe({"cpu": 80}, 40)
    assert g.blocked_at(40)
    g.observe({"cpu": 80}, 45)
    assert not g.blocked_at(45)


def test_brief_heat_and_interrupted_cooldown_do_not_accumulate():
    g = ready_guard()
    g.observe({"cpu": 96}, 15)
    g.observe({"cpu": 90}, 20)
    g.observe({"cpu": 96}, 25)
    assert not g.blocked_at(25)
    g.observe({"cpu": 103}, 30)
    assert g.blocked_at(30)  # emergency threshold skips the hot-duration delay
    g.observe({"cpu": 80}, 35)
    g.observe({"cpu": 86}, 40)
    g.observe({"cpu": 80}, 45)
    assert g.blocked_at(45)


def test_restart_stale_and_lost_sensor_fail_closed():
    g = ThermalGuard(ThermalConfig(enabled=True, cool_seconds=10))
    assert g.blocked_at(0)
    g.observe({"cpu": 90}, 0)
    assert g.blocked_at(0)  # restart cannot bypass a previous cooldown
    g = ready_guard()
    assert g.blocked_at(26)
    g.observe({"cpu": 70}, 30)
    assert g.blocked_at(30)
    g.unavailable("read failed")
    assert g.blocked_at(31)
    assert not g.sensors
    g.observe({"cpu": 70}, 35)
    g.observe({"cpu": 70}, 40)
    g.observe({"cpu": 70}, 45)
    assert not g.blocked_at(45)


def test_sampling_gap_cannot_count_as_sustained_cooling():
    g = ThermalGuard(ThermalConfig(enabled=True))
    g.observe({"cpu": 70}, 0)
    g.observe({"cpu": 70}, 100)
    assert g.blocked_at(100)


def test_throttle_only_releases_after_uninterrupted_cooling():
    g = ready_guard()
    for t in range(15, 50, 5):
        g.observe({"cpu": 92}, t)
    assert g.throttle_requested
    assert not g.blocked_at(45)
    g.observe({"cpu": 80}, 50)
    g.observe({"cpu": 88}, 55)
    g.observe({"cpu": 80}, 60)
    g.observe({"cpu": 80}, 65)
    assert g.throttle_requested
    g.observe({"cpu": 80}, 70)
    assert not g.throttle_requested


def test_critical_event_always_notifies_even_during_pause(tmp_path):
    g = ThermalGuard(ThermalConfig(enabled=True, notify_pauses=False, event_dir=tmp_path))
    g.context = {"run_id": 42, "stage": "schema"}
    g.emit("pause", reason="cooling")
    g.observe({"cpu": 103}, 0)
    g.observe({"cpu": 104}, 5)
    events = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    assert len(events) == 2
    assert all(e["run_id"] == 42 and e["pipeline_terminal"] is False for e in events)
    assert [e["notify"] for e in events if e["kind"] == "pause"] == [False]
    assert [e["notify"] for e in events if e["kind"] == "critical"] == [True]
    g.observe({"cpu": 90}, 10)
    g.observe({"cpu": 103}, 15)
    assert len(list(tmp_path.glob("thermal-critical-*.json"))) == 2


def test_event_write_failure_does_not_disable_guard(tmp_path):
    file = tmp_path / "not-a-directory"
    file.write_text("occupied")
    g = ThermalGuard(ThermalConfig(enabled=True, event_dir=file))
    g.observe({"cpu": 103}, 0)
    assert g.blocked_at(0)
    assert g.event_error


def test_sensor_loss_resets_throttle_history():
    g = ready_guard()
    g.observe({"cpu": 92}, 15)
    g.unavailable("missing")
    assert g.warm_since is None
    assert g.throttle_cool_since is None


def test_disabled_guard_and_invalid_config():
    assert not ThermalGuard(ThermalConfig(enabled=False)).blocked_at(100)
    with pytest.raises(ValueError, match="thermal thresholds"):
        ThermalConfig(resume_c=99, pause_c=95)


def test_cpu_sensor_discovery_ignores_gpu_disks_and_rejects_invalid(tmp_path):
    for number, driver, value in ((1, "k10temp", "97000"), (9, "coretemp", "98000"), (3, "nvme", "110000"), (4, "amdgpu", "100000")):
        p = tmp_path / f"hwmon{number}"
        p.mkdir()
        (p / "name").write_text(driver)
        (p / "temp1_input").write_text(value)
    assert max(read_cpu_sensors(tmp_path).values()) == 98
    (tmp_path / "hwmon1" / "temp1_input").write_text("nan")
    with pytest.raises(ValueError, match="invalid CPU sensor"):
        read_cpu_sensors(tmp_path)


@pytest.mark.asyncio
async def test_wait_preserves_progress_and_reacts_to_operator_stop(monkeypatch):
    guard = ThermalGuard(ThermalConfig(enabled=True))
    monkeypatch.setattr("phd_searcher.pipeline.progress.get_thermal_guard", lambda: guard)
    monkeypatch.setattr(guard, "start", AsyncMock())
    progress = Progress()
    progress.current = "institution"
    progress.done = 2
    progress._checkpoint = {"last_id": 42}
    labels = []

    async def persist():
        labels.append(progress.current)
        if str(progress.current).startswith("Pausa termica"):
            progress.should_stop = True

    monkeypatch.setattr(progress, "_persist", persist)
    await progress.wait_for_temperature()
    assert progress.should_stop
    assert progress.current == "institution"
    assert progress.done == 2
    assert progress._checkpoint["last_id"] == 42
    assert len(labels) == 2


@pytest.mark.asyncio
async def test_wait_automatically_continues_same_unit(monkeypatch):
    guard = ThermalGuard(ThermalConfig(enabled=True))
    monkeypatch.setattr("phd_searcher.pipeline.progress.get_thermal_guard", lambda: guard)
    monkeypatch.setattr(guard, "start", AsyncMock())
    progress = Progress()
    progress.current = "source"

    async def cool(_delay):
        guard.config.enabled = False  # deterministic release, no real hardware or wait

    monkeypatch.setattr(asyncio, "sleep", cool)
    await progress.wait_for_temperature()
    assert progress.current == "source"
    assert progress.done == 0
    assert not progress.should_stop
    assert progress._checkpoint["performance"]["thermal_wait"]["calls"] == 1


@pytest.mark.asyncio
async def test_scheduler_reconciles_but_does_not_claim_hot_jobs(monkeypatch):
    guard = ThermalGuard(ThermalConfig(enabled=True))
    monkeypatch.setattr("phd_searcher.service.schedule_service.get_thermal_guard", lambda: guard)
    service = object.__new__(ScheduleService)
    service._reconcile_running = AsyncMock()
    service._claim_due = AsyncMock()
    await service.tick()
    service._reconcile_running.assert_awaited_once()
    service._claim_due.assert_not_awaited()
