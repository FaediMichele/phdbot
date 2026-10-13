"""Offline tests of confidential delivery and fail-closed assignment checks."""
# ruff: noqa: PT009, PT027

import base64
import copy
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ddw"))
import evidence_experiment as experiment  # noqa: E402


class EvidenceDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        cls.public = cls.key.public_key().public_bytes(serialization.Encoding.PEM,
                                                       serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.private = cls.key.private_bytes(serialization.Encoding.PEM,
                                            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        cls.context = {"work": "fixture"}

    def test_confidential_roundtrip(self):
        payload = {"text": "SENSITIVE FIXTURE person@example.org", "receipt": {"state": "partial"}}
        envelope = experiment.seal(payload, self.public, self.context)
        self.assertNotIn(payload["text"], json.dumps(envelope))
        self.assertNotIn("PRIVATE KEY", json.dumps(envelope))
        self.assertEqual(experiment.unseal(envelope, self.private, self.context), payload)

    def test_tampered_ciphertext_is_rejected(self):
        envelope = experiment.seal({"text": "private"}, self.public, self.context)
        cipher = bytearray(base64.b64decode(envelope["ciphertext"]))
        cipher[-1] ^= 1
        envelope["ciphertext"] = base64.b64encode(cipher).decode()
        with self.assertRaises(InvalidTag):
            experiment.unseal(envelope, self.private, self.context)

    def test_changed_context_is_rejected(self):
        envelope = experiment.seal({"text": "private"}, self.public, self.context)
        with self.assertRaisesRegex(ValueError, "identity"):
            experiment.unseal(envelope, self.private, {"work": "another-assignment"})

    def test_decompression_is_bounded(self):
        envelope = experiment.seal({"text": "x" * 100}, self.public, self.context)
        with patch("phd_searcher.ddw.delivery.MAX_PLAIN", 32), self.assertRaisesRegex(ValueError, "limit"):
            experiment.unseal(envelope, self.private, self.context)

    def test_policy_change_prevents_any_html_request(self):
        manifest = json.loads((ROOT / "tools/ddw/evidence-task.json").read_bytes())
        with patch.object(experiment, "policy", return_value={"allowed": True, "sha256": "changed"}):
            _, blocked = experiment.check_policies(manifest)
        self.assertEqual(blocked, frozenset(manifest["task"]["allowed_hosts"]))
        manifest["task"]["expires_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(experiment.worker, "run_page", side_effect=AssertionError("HTML request")), \
                patch.object(experiment.worker.time, "sleep"):
            _, receipt = experiment.worker.run(manifest["task"], Path(directory), network=True, blocked_hosts=blocked)
        self.assertEqual(receipt["state"], "partial")
        self.assertTrue(all(p["error_type"] == "AccessPolicyBlocked" for p in receipt["pages"]))

    def test_one_blocked_host_does_not_stall_other_assigned_host(self):
        task = json.loads((ROOT / "tools/ddw/evidence-task.json").read_bytes())["task"]
        task["expires_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(experiment.worker, "run_page", return_value={"state": "error", "error_type": "AllowedProbe"}) as page, \
                patch.object(experiment.worker.time, "sleep"):
            _, receipt = experiment.worker.run(task, Path(directory), network=True,
                                               blocked_hosts=frozenset({"jobs.nottingham.ac.uk"}))
        self.assertEqual(page.call_count, 3)
        self.assertEqual(sum(p["error_type"] == "AccessPolicyBlocked" for p in receipt["pages"]), 2)

    def test_manifest_rejects_recipient_and_task_substitution(self):
        original = json.loads((ROOT / "tools/ddw/evidence-task.json").read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            recipient = Path(directory) / "recipient.pem"
            recipient.write_bytes(self.public)
            original["recipient_sha256"] = experiment.worker.digest(self.public)
            path.write_text(json.dumps(original))
            experiment.read_manifest(path, recipient, check_expiry=False)
            altered = copy.deepcopy(original)
            altered["task"]["pages"][0]["url"] += "?changed=1"
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, "assignment"):
                experiment.read_manifest(path, recipient, check_expiry=False)


if __name__ == "__main__":
    unittest.main()


def test_central_assignment_produces_signed_encrypted_delivery(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from phd_searcher.ddw import delivery, worker
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    signer = ed25519.Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    signing = signer.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    signing_public = signer.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    html = "<main><h1>Synthetic opportunity</h1></main>"
    schema = {"baseSelector": "main", "fields": [{"name": "title", "selector": "h1", "type": "text"}]}
    task = {"version": 1, "cycle": "signed-test", "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "timeout_seconds": 2, "allowed_hosts": ["example.test"], "pages": [{"url": "https://example.test/job",
            "html": html, "html_sha256": worker.digest(html.encode()), "schema": schema,
            "schema_sha256": worker.digest(worker.encoded(schema))}]}
    context = {"operation": "ddw-evidence-v1", "assignment_id": "signed-test", "attempt": 1,
               "task_sha256": worker.digest(worker.encoded(task)), "recipient_sha256": worker.digest(public),
               "source_commit": "a" * 40}
    manifest = {"version": 1, "operation": "ddw-evidence-v1", "context": context, "task": task,
                "task_sha256": context["task_sha256"], "recipient_sha256": context["recipient_sha256"]}
    monkeypatch.setenv("DDW_SOURCE_COMMIT", "a" * 40)
    monkeypatch.setattr(experiment, "check_policies", lambda _: ([], frozenset()))
    summary = experiment.execute(manifest, public, tmp_path / "delivery", signing)
    assert summary["state"] == "complete"
    encrypted = (tmp_path / "delivery/evidence.sealed.json").read_bytes()
    assert html.encode() not in encrypted
    payload = delivery.unseal(delivery.authenticate(encrypted, signing_public), private, context)
    assert payload["task"] == task
    assert payload["receipt"]["attempt"] == 1
