"""CPU thermal backpressure for local pipeline work; never changes hardware limits."""

from __future__ import annotations

import asyncio
import json
import logging
import math
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from time import monotonic
from typing import Self
from uuid import uuid4

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOGGER = logging.getLogger(__name__)
_CPU_DRIVERS = {"k10temp", "coretemp", "zenpower"}


class ThermalConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PHDBOT_THERMAL_", extra="ignore")

    enabled: bool = False
    pause_c: float = Field(default=95, gt=0, le=110, allow_inf_nan=False)
    resume_c: float = Field(default=85, gt=0, le=110, allow_inf_nan=False)
    critical_c: float = Field(default=102, gt=0, le=110, allow_inf_nan=False)
    hot_seconds: float = Field(default=60, ge=0, le=600, allow_inf_nan=False)
    cool_seconds: float = Field(default=30, ge=0, le=600, allow_inf_nan=False)
    sample_seconds: float = Field(default=5, ge=1, le=30, allow_inf_nan=False)
    event_dir: Path | None = None
    notify_pauses: bool = True
    throttle_c: float = Field(default=90, gt=0, le=110, allow_inf_nan=False)
    throttle_seconds: float = Field(default=30, ge=0, le=600, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_thresholds(self) -> Self:
        if not self.resume_c < self.throttle_c < self.pause_c <= self.critical_c:
            raise ValueError("thermal thresholds must satisfy resume_c < throttle_c < pause_c <= critical_c")
        return self


def read_cpu_sensors(root: Path = Path("/sys/class/hwmon")) -> dict[str, float]:
    """Use labelled kernel hwmon CPU sensors, ignoring disks and GPU sensors.

    Re-discover paths each time: hwmon numbers may change after a reboot.
    A failed read of a recognised CPU sensor fails closed rather than treating
    it as a cool reading. No package installation or privileged writes needed.
    """
    values: dict[str, float] = {}
    for hwmon in root.glob("hwmon*"):
        try:
            driver = (hwmon / "name").read_text().strip()
        except OSError:
            continue
        if driver not in _CPU_DRIVERS:
            continue
        for sensor in hwmon.glob("temp*_input"):
            label_file = sensor.with_name(sensor.name.replace("_input", "_label"))
            label = label_file.read_text().strip() if label_file.exists() else sensor.stem
            value = float(sensor.read_text()) / 1000
            if not math.isfinite(value) or not 0 < value < 150:
                raise ValueError(f"invalid CPU sensor reading: {driver}/{label}")
            values[f"{hwmon.name}/{driver}/{label}"] = value
    if not values:
        raise ValueError("no supported CPU temperature sensor available")
    return values


class ThermalGuard:
    def __init__(self, config: ThermalConfig) -> None:
        self.config = config
        # After restart require a fresh, sustained cool interval. This prevents
        # restart from bypassing a cooldown whose history was lost.
        self.paused = config.enabled
        self.reason = "awaiting_sensor" if config.enabled else "disabled"
        self.sensors: dict[str, float] = {}
        self.error: str | None = None
        self.sampled_at: str | None = None
        self.last_sample: float | None = None
        self.hot_since: float | None = None
        self.cool_since: float | None = None
        self._task: asyncio.Task[None] | None = None
        self.warm_since: float | None = None
        self.throttle_cool_since: float | None = None
        self.throttle_requested = False
        self._critical_latched = False
        self.context: dict[str, object] = {}
        self.event_error: str | None = None

    def emit(self, kind: str, **details: object) -> None:
        """A completed observation, never a fabricated terminal pipeline result."""
        record = {
            "status": "done", "kind": kind, "observation_only": True,
            "pipeline_terminal": False, "at": datetime.now(UTC).isoformat(),
            "cpu_c": max(self.sensors.values(), default=None),
            "notify": kind == "critical" or (kind == "pause" and self.config.notify_pauses),
            **self.context, **details,
        }
        _LOGGER.warning("thermal event: %s", json.dumps(record))
        if self.config.event_dir is None:
            return
        try:
            directory = self.config.event_dir
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / f"thermal-{kind}-{uuid4().hex}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(record, ensure_ascii=False))
            temporary.replace(target)
            self.event_error = None
        except OSError as exc:
            self.event_error = str(exc)
            _LOGGER.error("thermal event persistence failed: %s", exc)

    def observe(self, values: dict[str, float], now: float) -> None:
        """Pure time-based hysteresis, also used by deterministic tests."""
        if not values or any(not math.isfinite(v) or not 0 < v < 150 for v in values.values()):
            self.unavailable("invalid or missing CPU temperature")
            return
        if self.last_sample is not None and now - self.last_sample > self.config.sample_seconds * 3:
            self.paused = True
            self.hot_since = self.cool_since = None
            self.warm_since = self.throttle_cool_since = None
        self.last_sample = now
        self.sampled_at = datetime.now(UTC).isoformat()
        self.sensors = dict(values)
        self.error = None
        temperature = max(values.values())
        if temperature >= self.config.critical_c and not self._critical_latched:
            self._critical_latched = True
            self.emit("critical", action="pause requested at next safe boundary")
        elif temperature < self.config.pause_c:
            self._critical_latched = False
        if temperature >= self.config.throttle_c:
            if self.warm_since is None:
                self.warm_since = now
            if now - self.warm_since >= self.config.throttle_seconds:
                self.throttle_requested = True
        else:
            self.warm_since = None
        if temperature >= self.config.pause_c:
            if self.hot_since is None:
                self.hot_since = now
        else:
            self.hot_since = None
        if temperature >= self.config.critical_c or (
            self.hot_since is not None and now - self.hot_since >= self.config.hot_seconds
        ):
            self.paused = True
        if self.paused:
            self.reason = "cooling"
            if temperature <= self.config.resume_c:
                if self.cool_since is None:
                    self.cool_since = now
                if now - self.cool_since >= self.config.cool_seconds:
                    self.paused = False
                    self.throttle_requested = False
                    self.reason = "ready"
            else:
                self.cool_since = None
        else:
            self.cool_since = None
            self.reason = "hot_pending" if self.hot_since is not None else "ready"
        if self.paused:
            self.throttle_requested = True
        if temperature <= self.config.resume_c:
            # A throttle-only episode also needs a stable cool interval.
            if self.throttle_requested:
                if self.throttle_cool_since is None:
                    self.throttle_cool_since = now
                if now - self.throttle_cool_since >= self.config.cool_seconds:
                    self.throttle_requested = False
        else:
            self.throttle_cool_since = None

    def unavailable(self, error: str) -> None:
        self.paused = True
        self.reason = "sensor_unavailable"
        self.error = error
        self.sensors = {}
        self.hot_since = self.cool_since = None
        self.warm_since = self.throttle_cool_since = None

    def blocked_at(self, now: float) -> bool:
        if not self.config.enabled:
            return False
        if self.last_sample is None or now - self.last_sample > self.config.sample_seconds * 3:
            self.paused = True
            self.hot_since = self.cool_since = None
            self.warm_since = self.throttle_cool_since = None
            if self.reason != "sensor_unavailable":
                self.reason = "sensor_stale" if self.last_sample is not None else "awaiting_sensor"
        return self.paused

    @property
    def blocked(self) -> bool:
        return self.blocked_at(monotonic())

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.config.enabled,
            "blocked": self.blocked,
            "reason": self.reason,
            "cpu_c": max(self.sensors.values(), default=None),
            "sensors": dict(self.sensors),
            "sampled_at": self.sampled_at,
            "error": self.error,
            "event_error": self.event_error,
            "throttle_requested": self.throttle_requested or self.blocked,
            "config": self.config.model_dump(mode="json"),
            "scope": "CPU only; GPU temperature is not monitored",
        }

    async def start(self) -> None:
        if self.config.enabled and (self._task is None or self._task.done()):
            self._task = asyncio.create_task(self._watch(), name="phdbot-thermal")

    async def shutdown(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _watch(self) -> None:
        while True:
            previous = self.reason
            try:
                values = await asyncio.to_thread(read_cpu_sensors)
                self.observe(values, monotonic())
            except (OSError, ValueError) as exc:
                self.unavailable(str(exc))
            if self.reason != previous:
                _LOGGER.warning("thermal guard: %s CPU=%s", self.reason, max(self.sensors.values(), default=None))
            await asyncio.sleep(self.config.sample_seconds)


@lru_cache(maxsize=1)
def get_thermal_guard() -> ThermalGuard:
    return ThermalGuard(ThermalConfig())
