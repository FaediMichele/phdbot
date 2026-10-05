#!/usr/bin/env python3
"""Forward CPU observations to desktop and the existing, paired Valet outbox.

Run locally from a user timer. Never starts pipelines, changes quota, or copies
the private Valet credential into the API container. A receipt's ``done`` means
the observation was recorded; it does not mean its pipeline finished.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen

LOGGER = logging.getLogger(__name__)


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2))
    temporary.replace(path)


def read_event(path: Path, project: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.resolve().is_relative_to(project.resolve()):
        raise ValueError("thermal receipt must remain inside the project")
    if not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("invalid thermal receipt size or type")
    event = json.loads(path.read_text())
    if (not isinstance(event, dict) or event.get("status") != "done"
            or event.get("observation_only") is not True or event.get("pipeline_terminal") is not False
            or event.get("kind") not in {"critical", "pause", "pause_end"}):
        raise ValueError("not a completed thermal observation")
    return event


def should_notify(event: dict[str, Any]) -> bool:
    return event["kind"] == "critical" or (event["kind"] == "pause" and event.get("notify") is True)


def notify_desktop(event: dict[str, Any]) -> None:
    critical = event["kind"] == "critical"
    title = "PHDBOT: temperatura CPU critica" if critical else "PHDBOT: pausa termica"
    message = (f"CPU {event.get('cpu_c')} °C; run {event.get('run_id', 'nessuna')}. "
               + ("Richiesta pausa al prossimo punto sicuro." if critical else "Ripresa automatica dopo raffreddamento."))
    subprocess.run(["notify-send", "--app-name=PHDBOT", "--urgency=" + ("critical" if critical else "normal"),
                    title, message], check=True, timeout=10, capture_output=True)


def publish_valet(path: Path, project: Path, base: Path, runtime: Path, *, outcome: str = "done") -> None:
    # Refuse a stale pairing pointing to another checkout. project_events itself
    # verifies the private token, enrollment, bounded receipt and idempotent ID.
    binding = json.loads((base / "project-events/pairings.json").read_text())["sources"]["phdbot"]
    if Path(binding["cwd"]).resolve() != project.resolve():
        raise ValueError("Valet pairing does not match this project")
    subprocess.run([
        str(runtime / ".venv/bin/python"), str(runtime / "src/project_events.py"),
        "--base", str(base), "submit", "--source", "phdbot",
        "--token-file", str(base / "project-events/tokens/phdbot.key"),
        "--event-id", path.stem, "--outcome", outcome, "--receipt", str(path.resolve()),
    ], check=True, timeout=20, capture_output=True)


def drain(project: Path, base: Path, runtime: Path, *, desktop: bool = True) -> int:
    directory = project / "var/thermal"
    directory.mkdir(parents=True, exist_ok=True)
    errors = 0
    with (directory / "bridge.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = directory / "delivery.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        paths = sorted((project / "exports/thermal-events").glob("thermal-*.json"),
                       key=lambda p: (not p.name.startswith("thermal-critical-"), p.name))
        for path in paths:
            delivered = state.setdefault(path.stem, {})
            if delivered.get("complete"):
                continue
            try:
                event = read_event(path, project)
                if not should_notify(event):
                    delivered["complete"] = True
                    atomic_json(state_path, state)
                    continue
                # Desktop is independent from governor availability. A quota PARK
                # can delay the chat message but must not suppress local warning.
                for channel in ("desktop", "valet"):
                    if delivered.get(channel) or (channel == "desktop" and not desktop):
                        continue
                    try:
                        if channel == "desktop":
                            notify_desktop(event)
                        else:
                            publish_valet(path, project, base, runtime)
                        delivered[channel] = True
                        delivered.pop(channel + "_error", None)
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                        delivered[channel + "_error"] = type(exc).__name__
                        errors += 1
                        LOGGER.error("thermal delivery %s failed for %s: %s", channel, path.name, type(exc).__name__)
                    atomic_json(state_path, state)
                delivered["complete"] = bool(delivered.get("valet") and (delivered.get("desktop") or not desktop))
                atomic_json(state_path, state)
            except (OSError, ValueError, KeyError) as exc:
                errors += 1
                LOGGER.error("invalid thermal event %s: %s", path.name, type(exc).__name__)
        return errors


def sample(project: Path, api: str) -> None:
    """Low-cost temperature trace for comparing useful pipeline workloads."""
    with urlopen(api.rstrip("/") + "/v1/pipeline/thermal", timeout=5) as response:
        thermal = json.load(response)
    with urlopen(api.rstrip("/") + "/v1/pipeline/status", timeout=5) as response:
        pipeline = json.load(response)
    now = datetime.now(UTC)
    if pipeline.get("state") not in {"running", "stopping"} and not thermal.get("blocked"):
        return
    record = {"at": now.isoformat(), "thermal": thermal,
              "run_id": pipeline.get("run_id"), "state": pipeline.get("state"),
              "stage": pipeline.get("current_stage")}
    directory = project / "var/thermal"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"samples-{now:%Y%m%d}.jsonl").open("a") as output:
        output.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=Path.home() / ".local/share/codex-governor-app")
    parser.add_argument("--runtime", type=Path, default=Path.home() / ".local/lib/codex-governor-app")
    parser.add_argument("--api", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    errors = drain(args.project.resolve(), args.base, args.runtime)
    try:
        try:
            from scripts.thermal_cpu_trial import tick
        except ModuleNotFoundError:
            from thermal_cpu_trial import tick
        tick(args.project.resolve())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        LOGGER.error("CPU trial lease check failed: %s", type(exc).__name__)
        errors += 1
    try:
        sample(args.project.resolve(), args.api)
    except (OSError, ValueError) as exc:
        LOGGER.error("thermal sample unavailable: %s", type(exc).__name__)
        errors += 1
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
