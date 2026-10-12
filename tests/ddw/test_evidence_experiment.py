"""Offline tests of confidential delivery and fail-closed assignment checks."""
# ruff: noqa: PT009, PT027

import base64
import copy
import json
import sys
import tempfile
import unittest
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
        with patch.object(experiment, "MAX_PLAIN", 32), self.assertRaisesRegex(ValueError, "limit"):
            experiment.unseal(envelope, self.private, self.context)

    def test_policy_change_prevents_any_html_request(self):
        manifest = json.loads((ROOT / "tools/ddw/evidence-task.json").read_bytes())
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(experiment, "policy", return_value={"allowed": True, "sha256": "changed"}), \
                patch.object(experiment.worker, "run", side_effect=AssertionError("HTML request")), \
                self.assertRaisesRegex(ValueError, "policy"):
            experiment.execute(manifest, self.public, Path(directory) / "result")

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
