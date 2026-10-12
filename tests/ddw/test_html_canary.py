"""Scope, privacy and benchmark/production separation; all tests are offline."""
# ruff: noqa: PT009, PT027

import base64
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "ddw"))
import html_canary as canary  # noqa: E402


class CanaryTests(unittest.TestCase):
    def test_scope_and_expiry_are_enforced(self):
        manifest = json.loads((ROOT / "tools/ddw/html-canary.json").read_bytes())
        manifest["expires_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(manifest))
            self.assertEqual(len(canary.read_manifest(path)["pages"]), 3)
            manifest["pages"][0]["url"] = "https://unapproved.example/"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "scope"):
                canary.read_manifest(path)
            manifest["pages"][0]["url"] = "https://jobs.fbk.eu/"
            manifest["expires_at"] = "2020-01-01T00:00:00+00:00"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "expired"):
                canary.read_manifest(path)

    def test_policy_denial_never_fetches_pages(self):
        manifest = json.loads((ROOT / "tools/ddw/html-canary.json").read_bytes())
        with tempfile.TemporaryDirectory() as temporary, patch.object(canary, "policy", return_value={"allowed": False}), \
                patch.object(canary.worker, "run", side_effect=AssertionError("page fetch")):
            result = canary.execute(manifest, Path(temporary) / "public")
        self.assertEqual(result["state"], "policy_blocked")

    def test_summary_never_exports_content_or_contact_data(self):
        raw = b'<article><h2>PRIVATE TEST TITLE</h2><a href="/job/1">Apply</a><p>person@example.org</p></article>'
        schema = {"name": "test", "baseSelector": "article", "fields": [
            {"name": "title", "selector": "h2", "type": "text"},
            {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"}]}
        items = canary.worker.extract(raw, schema)
        result = canary.compare({"url": "https://example.org/jobs", "body_base64": base64.b64encode(raw).decode(),
                                 "items": items, "observed_at": "fixture"}, schema)
        serialized = json.dumps(result)
        for forbidden in ("PRIVATE TEST TITLE", "person@example.org", "body_base64", "<article>"):
            self.assertNotIn(forbidden, serialized)
        self.assertTrue(result["same_byte_agreement"])
        self.assertEqual(result["usable_detail_routes"], 1)

    def test_login_and_query_routes_are_not_ready_evidence(self):
        items = [{"title": "Job", "url": "/Vacancies/490/Application/CheckLogin/2"},
                 {"title": "Job", "url": "/detail?session=123"},
                 {"title": "Job", "url": "/Vacancies/490/Description/2"}]
        self.assertEqual(canary.detail_routes("https://example.org/jobs", items),
                         ["https://example.org/Vacancies/490/Description/2"])

    def test_portable_archive_excludes_frozen_benchmark(self):
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run([sys.executable, str(ROOT / "tools/ddw/experiment.py"), temporary],
                           check=True, capture_output=True, timeout=15)
            with zipfile.ZipFile(Path(temporary) / "worker.zip") as archive:
                names = archive.namelist()
                self.assertEqual(len(names), 7)
                self.assertFalse(any("reference" in n or "schema_probe" in n for n in names))

    def test_production_never_imports_frozen_baseline(self):
        for path in (ROOT / "src/phd_searcher").rglob("*.py"):
            if "ddw" not in path.parts:
                text = path.read_text()
                self.assertNotIn("phd_searcher.ddw.reference", text, str(path))
                self.assertNotIn("phd_searcher.ddw.schema_probe", text, str(path))
        worker_source = (ROOT / "src/phd_searcher/ddw/worker.py").read_text()
        self.assertIn("from phd_searcher.pipeline.schema_quality import", worker_source)
        self.assertNotIn("reference", worker_source)


if __name__ == "__main__":
    unittest.main()
