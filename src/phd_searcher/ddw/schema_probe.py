"""Offline schema-revalidation experiment, using the complete pinned validator.

No inference, browser, database or network operations. Input is a frozen bundle,
not an instruction to acquire data or alter PHDBOT state.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import socket
import time
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

# Crawl4AI imports LiteLLM; suppress its ancillary remote pricing-map request.
# This setting is confined to the experimental process, not production services.
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.utils import preprocess_html_for_schema

from phd_searcher.ddw.reference.bite_marker import bite_listing
from phd_searcher.ddw.reference.funding_sources import FUNDING_URLS, funding_items
from phd_searcher.ddw.reference.reuse import _schema_cache_key, _validated_reusable_schema
from phd_searcher.ddw.reference.source_validation import (
    listing_body_missing,
    page_state,
    staff_directory_evidence,
)
from phd_searcher.ddw.worker import digest, encoded, write_json


def read_bundle(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 2_000_000:
        raise ValueError("manifest_limit")
    bundle = json.loads(path.read_bytes())
    if bundle.get("version") != 1 or bundle.get("operation") != "schema-probe" or not 1 <= len(bundle["cases"]) <= 20:
        raise ValueError("unsupported_bundle")
    seen = set()
    for case in bundle["cases"]:
        if case["id"] in seen:
            raise ValueError("duplicate_case")
        seen.add(case["id"])
        snapshot = (path.parent / case["snapshot"]).resolve()
        if not snapshot.is_relative_to(path.parent.resolve()) or snapshot.stat().st_size > 1_000_000:
            raise ValueError("snapshot_boundary")
        raw = snapshot.read_bytes()
        if digest(raw) != case["snapshot_sha256"]:
            raise ValueError("snapshot_hash")
        for candidate in case["candidates"]:
            if digest(encoded(candidate["schema"])) != candidate["schema_sha256"]:
                raise ValueError("schema_hash")
            if _schema_cache_key(candidate["source_url"], candidate["kind"]) != _schema_cache_key(case["url"], case["kind"]):
                raise ValueError("cache_scope")
        case["html"] = raw.decode()
    return cast(dict[str, Any], bundle)


def probe(case: dict[str, Any]) -> dict[str, Any]:
    html = case["html"]
    marker = bite_listing(html) if case["official_owner"] else None
    state = page_state(html, case["http_status"])
    if state is None and not marker and listing_body_missing(html):
        state = "missing_content"
    if state is None and staff_directory_evidence(html):
        state = "staff_directory"
    result: dict[str, Any] = {"id": case["id"], "snapshot_sha256": case["snapshot_sha256"],
                              "decision": "deferred", "reason": state, "items": [],
                              "schema": None, "prepared_html": None}
    if state:
        return result
    if marker:
        result.update(decision="adapter", reason="bite", marker=marker)
        return result
    if case["url"] in FUNDING_URLS:
        try:
            items = funding_items(html, case["url"])
        except RuntimeError:
            result.update(reason="funding_adapter_failure")
        else:
            result.update(decision="adapter", reason="funding", items=items)
        return result
    schema = _validated_reusable_schema(html, [candidate["schema"] for candidate in case["candidates"]],
                                        expected_fields=case["expected_fields"])
    if schema is not None:
        result.update(decision="reused", schema=schema,
                      items=JsonCssExtractionStrategy(schema).extract(case["url"], html))
    else:
        # Match _generate_schema_with_tools' actual preparation parameters.
        compact = preprocess_html_for_schema(html_content=html, text_threshold=2000,
                                             attr_value_threshold=500, max_size=500_000)
        result.update(decision="generation_candidate", prepared_html=compact)
    return result


def offline_probe(case: dict[str, Any]) -> dict[str, Any]:
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("offline_probe")):
        return probe(case)


def implementation_id() -> str:
    parts = [Path(__file__).read_bytes(), version("crawl4ai").encode()]
    parts.extend(p.read_bytes() for p in sorted((Path(__file__).parent / "reference").glob("*.py")))
    return digest(b"\n".join(parts))


def execute(path: Path, output: Path, jobs: int = 1) -> dict[str, Any]:
    if jobs not in (1, 2):
        raise ValueError("worker_limit")
    bundle = read_bundle(path)
    identity = digest(path.read_bytes())
    if output.exists():
        saved = json.loads(output.read_bytes())
        if (saved["work_key"] != identity or digest(encoded(saved["results"])) != saved["results_sha256"]
                or saved["implementation_id"] != implementation_id()):
            raise ValueError("receipt_conflict_or_corruption")
        return cast(dict[str, Any], saved)
    start = time.perf_counter()
    # Covers accidental HTTP/model/DB connections through imported dependencies.
    if jobs == 1:
        results = [offline_probe(case) for case in bundle["cases"]]
    else:
        with ProcessPoolExecutor(max_workers=jobs, mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(offline_probe, bundle["cases"]))
    receipt = {"version": 1, "operation": "schema-probe", "work_key": identity, "state": "complete",
               "elapsed_seconds": time.perf_counter() - start, "results": results,
               "results_sha256": digest(encoded(results)), "model_calls_executed": 0,
               "implementation_id": implementation_id(), "jobs": jobs}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--jobs", type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    receipt = execute(args.manifest, args.output, args.jobs)
    print(json.dumps({key: receipt[key] for key in ("work_key", "state", "elapsed_seconds", "model_calls_executed")}))


if __name__ == "__main__":
    main()
