"""One approved HTML canary; public output contains measurements, never bodies."""

from __future__ import annotations

import argparse
import base64
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.utils import preprocess_html_for_schema

from phd_searcher.ddw import worker

AGENT = "PHDBOT-DDW-experiment/1"
APPROVED_URLS = {
    "https://jobs.fbk.eu/",
    "https://recruitingapp-5034.de.umantis.com/Jobs/2?lang=eng",
    "https://jobs.ait.ac.at/Jobs",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: object, fp: object, code: int, msg: str,
                         headers: object, newurl: str) -> None:
        return None


def read_manifest(path: Path) -> dict[str, Any]:
    manifest = cast(dict[str, Any], json.loads(path.read_bytes()))
    if (manifest["version"] != 1 or manifest["authorization"] != "html-canary-20261012"
            or {p["url"] for p in manifest["pages"]} != APPROVED_URLS
            or len(manifest["pages"]) != 3):
        raise ValueError("unapproved_canary_scope")
    if datetime.now(UTC) >= datetime.fromisoformat(manifest["expires_at"]):
        raise ValueError("expired_canary")
    return manifest


def policy(url: str) -> dict[str, Any]:
    robots_url = f"https://{urlsplit(url).hostname}/robots.txt"
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.perf_counter()
    try:
        with opener.open(Request(robots_url, headers={"User-Agent": AGENT,
                         "Accept-Encoding": "identity"}), timeout=10) as response:
            raw = response.read(64_001)
            if response.status != 200 or len(raw) > 64_000:
                raise ValueError("robots_limit_or_status")
        parser = RobotFileParser()
        parser.parse(raw.decode("utf-8", errors="replace").splitlines())
        allowed = parser.can_fetch(AGENT, url)
        return {"robots_url": robots_url, "observed_at": worker.now(), "allowed": allowed,
                "sha256": worker.digest(raw), "bytes": len(raw),
                "seconds": time.perf_counter() - started}
    except (HTTPError, OSError, ValueError) as exc:
        return {"robots_url": robots_url, "observed_at": worker.now(), "allowed": False,
                "error_type": type(exc).__name__, "seconds": time.perf_counter() - started}


def detail_routes(url: str, items: list[dict[str, str]]) -> list[str]:
    # Technical evidence candidates, never an opening/eligibility verdict.
    routes = set()
    for item in items:
        link = urljoin(url, item.get("url", ""))
        parsed = urlsplit(link)
        if (item.get("title", "").strip() and item.get("url") and parsed.scheme == "https"
                and parsed.hostname == urlsplit(url).hostname and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment
                and not any(p in parsed.path.lower() for p in ("checklogin", "/application/", "/login"))):
            routes.add(link)
    return sorted(routes)


def compare(data: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    raw = base64.b64decode(data["body_base64"], validate=True)
    started = time.perf_counter()
    baseline = JsonCssExtractionStrategy(schema).extract(data["url"], raw.decode("utf-8", errors="replace"))
    baseline_seconds = time.perf_counter() - started
    started = time.perf_counter()
    direct = worker.extract(raw, schema)
    ddw_seconds = time.perf_counter() - started
    started = time.perf_counter()
    prepared = preprocess_html_for_schema(html_content=raw.decode("utf-8", errors="replace"),
                                         text_threshold=2000, attr_value_threshold=500)
    prepared = prepared[:500_000]
    preparation_seconds = time.perf_counter() - started
    # No extracted strings, full HTML, headers or model inputs in public output.
    routes = detail_routes(data["url"], direct)
    return {"body_sha256": worker.digest(raw), "body_bytes": len(raw),
            "items_sha256": worker.digest(worker.encoded(data["items"])),
            "item_count": len(data["items"]), "usable_detail_routes": len(routes),
            "public_detail_urls": routes,
            "same_byte_agreement": baseline == direct == data["items"],
            "baseline_extract_seconds": baseline_seconds, "ddw_extract_seconds": ddw_seconds,
            "diagnostic_preparation_seconds": preparation_seconds,
            "prepared_bytes": len(prepared.encode()), "prepared_sha256": worker.digest(prepared.encode()),
            "observed_at": data["observed_at"]}


def execute(manifest: dict[str, Any], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    policies = [policy(p["url"]) for p in manifest["pages"]]
    if not all(p["allowed"] for p in policies):
        summary: dict[str, Any] = {"state": "policy_blocked", "policies": policies}
        worker.write_json(output / "html-canary.json", summary)
        return summary
    task = {"version": 1, "cycle": manifest["authorization"], "expires_at": manifest["expires_at"],
            "timeout_seconds": 10, "allowed_hosts": [urlsplit(p["url"]).hostname for p in manifest["pages"]],
            "pages": [{k: p[k] for k in ("url", "schema", "schema_sha256")} for p in manifest["pages"]]}
    worker.validate(task)
    # Raw responses exist only in private/ephemeral temporary storage. Never upload it.
    with tempfile.TemporaryDirectory(prefix="phdbot-html-canary-") as temporary:
        acquisition_started = time.perf_counter()
        directory, receipt = worker.run(task, Path(temporary), network=True)
        acquisition_seconds = time.perf_counter() - acquisition_started
        verification_started = time.perf_counter()
        worker.verify(directory, receipt["work_key"])
        verification_seconds = time.perf_counter() - verification_started
        pages = []
        for entry, source in zip(receipt["pages"], manifest["pages"], strict=True):
            page = {"id": source["id"], "url": source["url"], "state": entry["state"],
                    "schema_sha256": source["schema_sha256"]}
            if entry["state"] == "ok":
                data = json.loads((directory / f"page-{entry['index']}.json").read_bytes())["data"]
                page.update(compare(data, source["schema"]))
            else:
                page["error_type"] = entry.get("error_type", "Unprocessed")
            pages.append(page)
        summary = {"version": 1, "authorization": manifest["authorization"],
                   "source_commit": os.environ.get("DDW_SOURCE_COMMIT", "local-uncommitted"),
                   "build_id": worker.build_id(), "work_key": receipt["work_key"],
                   "assignment_sha256": worker.digest(worker.encoded(task)),
                   "state": receipt["state"], "started_at": receipt["started_at"],
                   "finished_at": receipt["finished_at"], "measured_at": worker.now(),
                   "acquisition_seconds": acquisition_seconds, "verification_seconds": verification_seconds,
                   "total_seconds": time.perf_counter() - started, "policies": policies, "pages": pages,
                   "request_budget": {"robots": 3, "assigned_html": 3, "retry": 0, "redirect": 0},
                   "full_html_exported": False, "llm_calls": 0, "llm_calls_avoided": 0}
        worker.write_json(output / "html-canary.json", summary)
        worker.write_json(output / "checksums.json", {"html-canary.json": worker.digest(worker.encoded(summary))})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("this approved canary requires explicit --allow-network")
    summary = execute(read_manifest(args.manifest), args.output)
    print(json.dumps({"state": summary["state"], "output": str(args.output)}))
    # A handled partial result is evidence; policy denial or disagreement is failure.
    good = [p for p in summary.get("pages", []) if p["state"] == "ok"]
    raise SystemExit(0 if good and all(p["same_byte_agreement"] for p in good) else 2)


if __name__ == "__main__":
    main()
