"""Summarize an existing catalogue wave from a read-only database snapshot.

Use with scripts/capture_catalog_waves.py (or an equivalent snapshot).
This command never schedules pipelines, contacts Ollama, or changes the index.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def _duration(job: dict[str, Any]) -> float | None:
    started, finished = job.get("started_at"), job.get("finished_at")
    if not started or not finished:
        return None
    return max(0.0, (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds())


def _schedule_ids(plan: dict[str, Any]) -> set[int]:
    ids: list[int] = []
    for entry in plan["jobs"].values():
        if entry.get("status") == "accepted":
            ids.extend(entry["schedule_ids"])
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("wave plan has no accepted jobs or repeats a schedule ID")
    return set(ids)


def _institution_groups(plan: dict[str, Any]) -> dict[int, str]:
    groups: dict[int, str] = {}
    for entry in plan["jobs"].values():
        if entry.get("status") != "accepted" or not entry.get("groups"):
            continue
        if len(entry["ids"]) != len(entry["groups"]):
            raise ValueError("wave plan has mismatched group labels")
        # Expansion responses sort institution IDs; request order may differ.
        groups.update(zip(entry["ids"], entry["groups"], strict=True))
    return groups


def summarize(snapshot: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    ids = _schedule_ids(plan)
    group_labels = _institution_groups(plan)
    jobs = [job for job in snapshot["jobs"] if job["id"] in ids]
    if len(jobs) != len(ids):
        raise ValueError(f"snapshot is missing {len(ids) - len(jobs)} wave schedules")
    if {job["id"] for job in jobs} != ids:
        raise ValueError("snapshot repeats schedules or omits wave members")
    states = Counter(job["state"] for job in jobs)
    terminal = [job for job in jobs if job["state"] in {"done", "failed", "cancelled"}]
    active = [job for job in jobs if job["state"] in {"scheduled", "starting", "running", "waiting_pipeline"}]
    durations = [elapsed for job in terminal if (elapsed := _duration(job)) is not None]
    recent = sorted(terminal, key=lambda job: job.get("finished_at") or "")[-100:]
    recent_durations = [elapsed for job in recent if (elapsed := _duration(job)) is not None]
    central = statistics.mean(recent_durations) if len(recent_durations) >= 10 else (
        statistics.mean(durations) if durations else None
    )
    admitted_ids = {int(job["institution_id"]) for job in jobs if job.get("institution_id")}
    terminal_ids = {int(job["institution_id"]) for job in terminal if job.get("institution_id")}
    sources = [row for row in snapshot["sources"] if row["university_id"] in terminal_ids]
    outcomes = [row for row in snapshot["outcomes"] if row["university_id"] in terminal_ids]
    source_counts = Counter(row["university_id"] for row in sources)
    markers: defaultdict[int, int] = defaultdict(int)
    routing_reasons: Counter[str] = Counter()
    for row in outcomes:
        markers[row["university_id"]] += row["current_indexed_markers"]
        if row.get("routing_reason"):
            routing_reasons[row["routing_reason"]] += row["rows"]
    result: dict[str, Any] = {
        "wave": plan["objective"],
        "captured_at": snapshot["captured_at"],
        "as_of": snapshot.get("as_of"),
        "total": len(ids),
        "states": dict(sorted(states.items())),
        "terminal": len(terminal),
        "remaining": len(active),
        "running_ids": sorted(job["id"] for job in jobs if job["state"] == "running"),
        "failed": [
            {"schedule_id": job["id"], "run_id": job.get("pipeline_run_id"), "error": job.get("error")}
            for job in jobs if job["state"] == "failed"
        ],
        "timing_seconds": {
            "all_mean": round(statistics.mean(durations), 1) if durations else None,
            "all_median": round(statistics.median(durations), 1) if durations else None,
            "recent_100_mean": round(statistics.mean(recent_durations), 1) if recent_durations else None,
            "recent_100_median": round(statistics.median(recent_durations), 1) if recent_durations else None,
            "remaining_central_seconds": round(len(active) * central) if central is not None else None,
            "remaining_central_hours": round(len(active) * central / 3600, 2) if central is not None else None,
        },
        "discovery_status": dict(Counter(job["discovery_status"] for job in terminal)),
        "sources": {
            "total": len(sources),
            "institutions_with_sources": len(source_counts),
            "institutions_without_sources": len(terminal_ids - source_counts.keys()),
            "by_institution_count": dict(sorted(Counter(source_counts.get(id_, 0) for id_ in terminal_ids).items())),
            "quality_status": dict(Counter(row["quality_status"] for row in sources)),
            "schema_status": dict(Counter(row["schema_status"] for row in sources)),
            "quality_reasons": dict(Counter(
                row["quality_reason"] for row in sources if row.get("quality_reason")
            ).most_common(10)),
            "top_hosts": dict(Counter(
                urlsplit(row["url"]).hostname or "invalid_url" for row in sources
            ).most_common(15)),
            "adapters": dict(Counter(row.get("adapter") or "html" for row in sources)),
        },
        "positions": {
            "all_rows": sum(row["rows"] for row in outcomes),
            "current_indexed_markers": sum(row["current_indexed_markers"] for row in outcomes),
            "institutions_with_current_indexed_markers": sum(bool(markers[id_]) for id_ in terminal_ids),
            "types": dict(Counter({
                kind: sum(row["rows"] for row in outcomes if row["position_type"] == kind)
                for kind in {row["position_type"] for row in outcomes}
            })),
            "routing_reasons": dict(routing_reasons.most_common(10)),
        },
        "schema_checkpoint": {
            key: sum((job.get("schema") or {}).get(key, 0) for job in terminal)
            for key in ("processed", "reused", "generated")
        },
        "admitted_institutions": len(admitted_ids),
    }
    if group_labels:
        group_result: dict[str, dict[str, Any]] = {}
        for group in sorted(set(group_labels.values())):
            group_jobs = [job for job in jobs if group_labels.get(int(job["institution_id"])) == group]
            group_terminal = [job for job in group_jobs if job["state"] in {"done", "failed", "cancelled"}]
            group_ids = {int(job["institution_id"]) for job in group_terminal if job.get("institution_id")}
            group_times = [elapsed for job in group_terminal if (elapsed := _duration(job)) is not None]
            group_result[group] = {
                "total": len(group_jobs),
                "terminal": len(group_terminal),
                "states": dict(Counter(job["state"] for job in group_jobs)),
                "mean_seconds": round(statistics.mean(group_times), 1) if group_times else None,
                "institutions_with_sources": len(group_ids & source_counts.keys()),
                "institutions_with_current_indexed_markers": sum(bool(markers[id_]) for id_ in group_ids),
                "current_indexed_markers": sum(markers[id_] for id_ in group_ids),
            }
        result["groups"] = group_result
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.snapshot.read_text()), json.loads(args.plan.read_text()))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
