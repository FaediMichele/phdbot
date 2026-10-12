"""Standalone unittest suite: no PHDBOT settings, database, models or network."""
# ruff: noqa: PT009, PT027
# Keep the standalone standard-library runner independent from PHDBOT pytest plugins.

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from phd_searcher.ddw import worker as w

ORIGINAL_POPEN = subprocess.Popen

def task():
    schema = {"baseSelector": ".job", "fields": [
        {"name": "title", "type": "text", "selector": "a"},
        {"name": "url", "type": "attribute", "selector": "a", "attribute": "href"},
    ]}
    html = '<article class="job"><a href="/position/1">Synthetic PhD position</a></article>'
    return {"version": 1, "cycle": "fixture-cycle-1", "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "timeout_seconds": 5, "allowed_hosts": ["example.org"], "pages": [{
                "url": "https://example.org/jobs", "schema": schema, "schema_sha256": w.digest(w.encoded(schema)),
                "html": html, "html_sha256": w.digest(html.encode()),
            }]}


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_real_child_and_idempotent_replay(self):
        job = task()
        directory, receipt = w.run(job, self.root)
        self.assertEqual(receipt["state"], "complete")
        with patch.object(w, "run_page", side_effect=AssertionError("must not rerun")):
            self.assertEqual(w.run(job, self.root), (directory, receipt))
        data = json.loads((directory / "page-0.json").read_bytes())["data"]
        self.assertEqual(data["items"], [{"title": "Synthetic PhD position", "url": "/position/1"}])

    def test_real_child_timeout(self):
        job = task()
        job["timeout_seconds"] = 0.05
        # An actual subprocess exceeding its deadline is killed/reaped.
        with patch.object(w.subprocess, "Popen", wraps=lambda *a, **kw: ORIGINAL_POPEN(
                [sys.executable, "-c", "import time; time.sleep(10)"], **kw)):
            _, receipt = w.run(job, self.root)
        self.assertEqual(receipt["pages"][0]["state"], "timeout")
        self.assertEqual(receipt["state"], "partial")

    def test_interruption_and_explicit_next_attempt(self):
        job = task()
        with patch.object(w, "run_page", side_effect=KeyboardInterrupt):
            directory, first = w.run(job, self.root)
        self.assertEqual(first["state"], "interrupted")
        self.assertEqual(w.verify(directory, first["work_key"]), first)
        _, second = w.run(job, self.root, attempt=2)
        self.assertEqual(second["work_key"], first["work_key"])
        self.assertEqual(second["state"], "complete")
        self.assertEqual(json.loads((directory / "receipt.json").read_bytes()), first)

    def test_partial_preserves_successful_page(self):
        job = task()
        bad = copy.deepcopy(job["pages"][0])
        bad.update(url="https://example.org/empty", html="<p>No matching elements</p>")
        bad["html_sha256"] = w.digest(bad["html"].encode())
        job["pages"].append(bad)
        directory, receipt = w.run(job, self.root)
        self.assertEqual(receipt["state"], "partial")
        self.assertEqual([p["state"] for p in receipt["pages"]], ["ok", "error"])
        self.assertTrue((directory / "page-0.json").exists())

    def test_expired_does_not_execute(self):
        job = task()
        job["expires_at"] = "2000-01-01T00:00:00+00:00"
        with patch.object(w, "run_page", side_effect=AssertionError("expired")):
            _, receipt = w.run(job, self.root)
        self.assertEqual(receipt["state"], "expired")

    def test_network_disabled_by_default(self):
        job = task()
        del job["pages"][0]["html"]
        del job["pages"][0]["html_sha256"]
        with patch.object(w, "fetch", side_effect=AssertionError("network")), self.assertRaisesRegex(ValueError, "network_disabled"):
            w.page_result(job, 0, False)

    def test_rejects_tampered_results(self):
        directory, receipt = w.run(task(), self.root)
        (directory / "page-0.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "result_hash_mismatch"):
            w.verify(directory, receipt["work_key"])

    def test_different_cycle_changes_work_identity(self):
        first = task()
        second = copy.deepcopy(first)
        second["cycle"] = "next-refresh"
        self.assertNotEqual(w.digest(w.encoded(first)), w.digest(w.encoded(second)))

    def test_bad_contracts(self):
        mutations = [lambda j: j.update(version=2), lambda j: j.update(timeout_seconds=100),
                     lambda j: j["pages"].append(copy.deepcopy(j["pages"][0])),
                     lambda j: j["pages"][0].update(schema_sha256="bad"),
                     lambda j: j["pages"][0].update(url="file:///etc/passwd"),
                     lambda j: j["pages"][0].update(url="https://user:password@example.org/jobs")]
        for mutate in mutations:
            job = task()
            mutate(job)
            with self.subTest(job=job), self.assertRaises(ValueError):
                w.validate(job)

    def test_unsupported_schema_is_not_approximated(self):
        job = task()
        schema = job["pages"][0]["schema"]
        schema["fields"][0]["type"] = "regex"
        job["pages"][0]["schema_sha256"] = w.digest(w.encoded(schema))
        with self.assertRaisesRegex(ValueError, "unsupported_field"):
            w.validate(job)

    def test_private_or_mixed_dns_is_rejected_before_connect(self):
        for ips in (["127.0.0.1"], ["93.184.216.34", "10.0.0.1"], ["::1"]):
            answers = [(2, 1, 6, "", (ip, 443)) for ip in ips]
            with patch.object(w.socket, "getaddrinfo", return_value=answers), \
                    patch.object(w.socket, "create_connection", side_effect=AssertionError("connect")), \
                    self.assertRaisesRegex(ValueError, "non_public_address"):
                w.fetch("https://example.org/jobs", ["example.org"], 1)

    def test_pinned_https_rejects_redirect_and_oversize(self):
        from unittest.mock import MagicMock
        for status, body, reason in [(302, b"", "http_302"), (200, b"x" * (w.MAX_BYTES + 1), "body_limit")]:
            connection = MagicMock()
            response = connection.getresponse.return_value
            response.status = status
            response.getheader.side_effect = lambda key, default=None: {"Content-Type": "text/html"}.get(key, default)
            response.read.return_value = body
            with patch.object(w.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]), \
                    patch.object(w.socket, "create_connection") as connect, \
                    patch.object(w.ssl, "create_default_context"), \
                    patch.object(w.http.client, "HTTPSConnection", return_value=connection), \
                    self.assertRaisesRegex(ValueError, reason):
                w.fetch("https://example.org/jobs", ["example.org"], 1)
            connect.assert_called_once_with(("93.184.216.34", 443), timeout=1)


    def test_different_attempt_cannot_overlap(self):
        job = task()
        claim = self.root / w.digest(w.encoded(job)) / "active"
        claim.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "already_claimed"):
            w.run(job, self.root, attempt=2)

    def test_unfinished_receipt_is_not_reclaimed(self):
        job = task()
        directory = self.root / w.digest(w.encoded(job)) / "1"
        directory.mkdir(parents=True)
        w.write_json(directory / "task.json", job)
        w.write_json(directory / "receipt.json", {"version": 1, "work_key": w.digest(w.encoded(job)), "state": "running"})
        with self.assertRaisesRegex(ValueError, "unfinished_receipt"):
            w.run(job, self.root)

    def test_interruption_reaps_inflight_child(self):
        job = task()
        task_path = self.root / "task.json"
        w.write_json(task_path, job)
        from unittest.mock import MagicMock
        process = MagicMock()
        process.wait.side_effect = [KeyboardInterrupt, 0]
        process.poll.return_value = None
        with patch.object(w.subprocess, "Popen", return_value=process), self.assertRaises(KeyboardInterrupt):
            w.run_page(task_path, 0, self.root / "output.json", False, 1)
        process.kill.assert_called_once()

    def test_tampered_completion_claim_rejected(self):
        job = task()
        job["expires_at"] = "2000-01-01T00:00:00+00:00"
        directory, receipt = w.run(job, self.root)
        receipt["state"] = "complete"
        w.write_json(directory / "receipt.json", receipt)
        with self.assertRaisesRegex(ValueError, "false_completion"):
            w.verify(directory, receipt["work_key"])
