"""Paired frozen-input comparison against PHDBOT's already optimized baseline."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from phd_searcher.ddw import schema_probe as probe
from phd_searcher.ddw.worker import digest, encoded, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--live-baseline", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bundle = probe.read_bundle(args.manifest)
    # Local run uses the actual current production helper, not a reimplementation.
    # Hosted run uses the exact frozen source functions with recorded provenance.
    if args.live_baseline:
        from phd_searcher.pipeline.schema_gen import _validated_reusable_schema
        probe._validated_reusable_schema = _validated_reusable_schema
    baseline_times = []
    for _ in range(3):
        started = time.perf_counter()
        baseline = [probe.offline_probe(case) for case in bundle["cases"]]
        baseline_times.append(time.perf_counter() - started)
    write_json(args.output / "baseline.json", baseline)
    observations = {}
    remote_results = []
    for jobs in (1, 2):
        result_path = args.output / f"ddw-{jobs}.json"
        if result_path.exists():
            raise ValueError("use a fresh experiment output directory")
        started = time.perf_counter()
        subprocess.run([sys.executable, "-m", "phd_searcher.ddw.schema_probe", str(args.manifest),
                        str(result_path), "--jobs", str(jobs)], check=True, timeout=90)
        end_to_end = time.perf_counter() - started
        started = time.perf_counter()
        receipt = json.loads(result_path.read_bytes())
        assert receipt["work_key"] == digest(args.manifest.read_bytes())
        assert digest(encoded(receipt["results"])) == receipt["results_sha256"]
        # Equality includes all extracted fields and exact prepared model input.
        assert receipt["results"] == baseline
        remote_results = receipt["results"]
        verify_seconds = time.perf_counter() - started
        observations[str(jobs)] = {"end_to_end_seconds": end_to_end, "worker_seconds": receipt["elapsed_seconds"],
                                   "verification_seconds": verify_seconds, "result_bytes": result_path.stat().st_size,
                                   "result_gzip_bytes": len(gzip.compress(result_path.read_bytes()))}
    expected = json.loads((args.manifest.parent / "audit.json").read_bytes())
    correctness = []
    for result in baseline:
        audit = expected[result["id"]]
        pairs = [{"title": item.get("title"), "url": item.get("url")} for item in result["items"]]
        correct = pairs == audit["expected_pairs"] if "expected_pairs" in audit else None
        correctness.append({"id": result["id"], "decision": result["decision"], "items": len(pairs),
                            "audited_extraction_matches": correct, "audit_scope": audit["scope"]})
    input_raw = args.manifest.read_bytes() + b"".join((args.manifest.parent / c["snapshot"]).read_bytes() for c in bundle["cases"])
    distribution = dict(Counter(r["decision"] for r in baseline))
    result = {"version": 1, "source_commit": os.environ.get("DDW_SOURCE_COMMIT", "local"),
              "baseline_commit": bundle["baseline_commit"], "baseline_mode": "current-helper" if args.live_baseline else "frozen-exact-helper",
              "cases": len(baseline), "concordance": len(baseline), "distribution": distribution,
              "additional_reuses": sum(b["decision"] != "reused" and d["decision"] == "reused" for b, d in zip(baseline, remote_results, strict=True)),
              "additional_model_generations_avoided": sum(b["decision"] == "generation_candidate" and d["decision"] != "generation_candidate" for b, d in zip(baseline, remote_results, strict=True)),
              "model_calls_executed": 0,
              "baseline_seconds": baseline_times, "baseline_median_seconds": statistics.median(baseline_times),
              "ddw": observations, "input_bytes": len(input_raw), "input_gzip_bytes": len(gzip.compress(input_raw)),
              "input_preparation_cases": sum(r["prepared_html"] is not None for r in baseline),
              "correctness": correctness, "python": platform.python_version(), "platform": platform.platform(),
              "limitations": ["historical selected cohort, not catalogue prevalence", "no end-to-end pipeline or GPU overlap measured",
                              "generation candidates conditional on rendering/ownership/due-state", "hash verification is not worker authentication"]}
    write_json(args.output / "summary.json", result)
    write_json(args.output / "checksums.json", {p.name: digest(p.read_bytes()) for p in args.output.glob("*.json") if p.name != "checksums.json"})
    print(json.dumps(result))


if __name__ == "__main__":
    main()
