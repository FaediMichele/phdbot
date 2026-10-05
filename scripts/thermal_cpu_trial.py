#!/usr/bin/env python3
"""Bounded CPU-budget lease for PHDBOT's Ollama container; never launches work.

The thermal notification timer calls tick(). A durable journal allows recovery
between Docker update and acknowledgement. Expiry restores the original budget
without depending on the API or an agent being available.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def save(path: Path, record: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    temporary.replace(path)


def inspect(container: str) -> dict[str, Any]:
    result = subprocess.run(["docker", "inspect", container], check=True, capture_output=True, text=True, timeout=10)
    return json.loads(result.stdout)[0]


def update(container: str, nano_cpus: int) -> None:
    subprocess.run(["docker", "update", "--cpus", str(nano_cpus / 1_000_000_000), container],
                   check=True, capture_output=True, timeout=10)


def validate(record: dict[str, Any]) -> None:
    if not re.fullmatch(r"[a-f0-9]{64}", record["container_id"]):
        raise ValueError("exact container identity required")
    if not re.fullmatch(r"wave-[a-zA-Z0-9_-]{1,90}", record["completion_event"]):
        raise ValueError("invalid completion event")
    for key in ("original_nano_cpus", "target_nano_cpus"):
        if type(record[key]) is not int or not 0 <= record[key] <= 16_000_000_000:
            raise ValueError("CPU budget outside experiment bounds")
    if record["target_nano_cpus"] < 1_000_000_000:
        raise ValueError("trial requires at least one CPU")
    if record["original_nano_cpus"] and record["target_nano_cpus"] >= record["original_nano_cpus"]:
        raise ValueError("trial must reduce the existing budget")
    created = datetime.fromisoformat(record["created_at"])
    expires = datetime.fromisoformat(record["expires_at"])
    if created.tzinfo is None or expires.tzinfo is None or not 0 < (expires - created).total_seconds() <= 21600:
        raise ValueError("lease must expire within six hours")


def completion_received(project: Path, event: str) -> bool:
    path = project / "var/valet-events" / (event + ".json")
    if not path.exists() or path.is_symlink() or path.stat().st_size > 65536:
        return False
    try:
        receipt = json.loads(path.read_text())
        jobs = receipt.get("jobs")
        return bool(receipt.get("kind") == "wave_terminal" and receipt.get("status") in {"done", "failed"}
                    and isinstance(jobs, list) and jobs
                    and all(isinstance(job, dict) and job.get("state") in {"done", "failed", "cancelled"}
                            and job.get("finished_at") for job in jobs))
    except (ValueError, AttributeError):
        return False


def advance(path: Path, project: Path, *, now: datetime) -> dict[str, Any]:
    record = json.loads(path.read_text())
    validate(record)
    if record["state"] in {"restored", "conflict"}:
        return record
    if record["state"] not in {"applying", "active", "restoring"}:
        raise ValueError("invalid lease state")
    actual = inspect(record["container_id"])
    labels = actual["Config"].get("Labels") or {}
    if (actual["Id"] != record["container_id"] or labels.get("com.docker.compose.project") != "phdbot"
            or labels.get("com.docker.compose.service") != "ollama"):
        raise ValueError("lease is restricted to the original PHDBOT Ollama container")
    config = actual["HostConfig"]
    current = config["NanoCpus"]
    original, target = record["original_nano_cpus"], record["target_nano_cpus"]
    # Never replace an operator's competing update, even during cleanup.
    if current not in {original, target} or config.get("CpuQuota", 0) or config.get("CpuPeriod", 0):
        record.update(state="conflict", reason="resource limits changed externally")
        save(path, record)
        return record
    expired = now >= datetime.fromisoformat(record["expires_at"])
    finished = False if expired else completion_received(project, record["completion_event"])
    restore = record["state"] == "restoring" or expired or finished
    if restore:
        record.update(state="restoring", restore_reason="completion" if finished else "expiry_or_manual")
        save(path, record)
        if current == target:
            update(record["container_id"], original)
        if inspect(record["container_id"])["HostConfig"]["NanoCpus"] != original:
            raise RuntimeError("CPU budget restoration not confirmed")
        record.update(state="restored", restored_at=now.isoformat())
    elif record["state"] == "applying":
        if current == original:
            update(record["container_id"], target)
        if inspect(record["container_id"])["HostConfig"]["NanoCpus"] != target:
            raise RuntimeError("CPU budget application not confirmed")
        record.update(state="active", applied_at=now.isoformat())
    elif current != target:
        record.update(state="conflict", reason="active budget changed externally")
    save(path, record)
    return record


def tick(project: Path) -> dict[str, Any] | None:
    directory = project / "var/thermal"
    path = directory / "cpu-trial.json"
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_size > 16384:
        raise ValueError("invalid CPU lease file")
    with (directory / "cpu-trial.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return advance(path, project, now=datetime.now(UTC))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(tick(args.project.resolve())))


if __name__ == "__main__":
    main()
