#!/usr/bin/env python3
"""Observe all IDs of explicitly registered waves; never launches project work."""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen

try:
    from scripts.thermal_event_bridge import atomic_json, publish_valet
except ModuleNotFoundError:
    from thermal_event_bridge import atomic_json, publish_valet


def terminal_receipt(ids: list[int], jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """An arbitrary terminal job is never a barrier for the rest of its wave."""
    if not ids or len(set(ids)) != len(ids) or any(type(i) is not int or i < 1 for i in ids):
        raise ValueError("wave requires unique positive schedule IDs")
    by_id = {job["id"]: job for job in jobs}
    if any(i not in by_id for i in ids):
        return None
    selected = [by_id[i] for i in ids]
    if any(job["state"] not in {"done", "failed", "cancelled"} for job in selected):
        return None
    if any(not job.get("finished_at") for job in selected):
        return None
    if any(job["state"] == "done" and not job.get("pipeline_run_id") for job in selected):
        raise ValueError("completed schedule missing pipeline identity")
    return {
        "status": "done" if all(job["state"] == "done" for job in selected) else "failed",
        "kind": "wave_terminal", "schedule_ids": ids,
        "jobs": [{key: job.get(key) for key in ("id", "state", "pipeline_run_id", "finished_at", "error")}
                 for job in selected],
    }


def check(project: Path, api: str, base: Path, runtime: Path) -> None:
    directory = project / "var/wave-watches"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "bridge.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for manifest in directory.glob("wave-*.json"):
            if manifest.is_symlink() or manifest.stat().st_size > 65536:
                raise ValueError("invalid wave registration")
            config = json.loads(manifest.read_text())
            if config.get("delivered"):
                continue
            binding = json.loads((base / "project-events/pairings.json").read_text())["sources"]["phdbot"]
            if config.get("valet_wake_root_id") != binding.get("thread_id"):
                raise ValueError("registered wave does not match the paired root")
            event_id = config["event_id"]
            if not re.fullmatch(r"wave-[a-zA-Z0-9_-]{1,90}", event_id):
                raise ValueError("invalid wave event ID")
            target = project / "var/valet-events" / f"{event_id}.json"
            if not target.exists():
                ids = config["schedule_ids"]
                # Individual GETs avoid a truncated global schedules listing.
                # The registered cohort is bounded; already delivered waves cost no HTTP requests.
                if not isinstance(ids, list) or not 1 <= len(ids) <= 100:
                    raise ValueError("wave observer supports 1-100 exact IDs")
                jobs = []
                for schedule_id in ids:
                    if type(schedule_id) is not int or schedule_id < 1:
                        raise ValueError("invalid schedule ID")
                    with urlopen(f"{api.rstrip('/')}/v1/schedules/{schedule_id}", timeout=5) as response:
                        job = json.load(response)
                    if job.get("id") != schedule_id:
                        raise ValueError("schedule identity mismatch")
                    jobs.append(job)
                record = terminal_receipt(ids, jobs)
                if record is None:
                    continue
                record["observed_at"] = datetime.now(UTC).isoformat()
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_json(target, record)
            else:
                record = json.loads(target.read_text())
                if record.get("schedule_ids") != config["schedule_ids"] or record.get("kind") != "wave_terminal":
                    raise ValueError("wave receipt identity changed; inspect before delivery")
            publish_valet(target, project, base, runtime, outcome=record["status"])
            config["delivered"] = True
            atomic_json(manifest, config)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8003")
    parser.add_argument("--base", type=Path, default=Path.home() / ".local/share/codex-governor-app")
    parser.add_argument("--runtime", type=Path, default=Path.home() / ".local/lib/codex-governor-app")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    check(args.project.resolve(), args.api, args.base, args.runtime)


if __name__ == "__main__":
    main()
