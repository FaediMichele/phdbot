"""Bounded acquisition with encrypted file delivery; no canonical import."""

from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from html_canary import policy

from phd_searcher.ddw import worker

MAX_PLAIN = 8_000_000
MAX_ENVELOPE = 12_000_000


def read_manifest(path: Path, recipient: Path, *, check_expiry: bool = True) -> dict[str, Any]:
    manifest = cast(dict[str, Any], json.loads(path.read_bytes()))
    task = manifest["task"]
    worker.validate(task)
    if (manifest["version"] != 1 or manifest["operation"] != "private-evidence-canary"
            or not 1 <= len(task["pages"]) <= 10
            or worker.digest(worker.encoded(task)) != manifest["task_sha256"]
            or worker.digest(recipient.read_bytes()) != manifest["recipient_sha256"]
            or any("html" in page for page in task["pages"])):
        raise ValueError("invalid_evidence_assignment")
    if check_expiry and datetime.now(UTC) >= datetime.fromisoformat(task["expires_at"]):
        raise ValueError("expired_evidence_assignment")
    return manifest


def seal(payload: dict[str, Any], public_pem: bytes, context: dict[str, Any]) -> dict[str, Any]:
    raw = worker.encoded(payload)
    if len(raw) > MAX_PLAIN:
        raise ValueError("private_payload_limit")
    public_key = serialization.load_pem_public_key(public_pem)
    if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 3072:
        raise ValueError("invalid_recipient")
    key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
    aad = worker.encoded(context)
    cipher = AESGCM(key).encrypt(nonce, gzip.compress(raw), aad)
    wrapped = public_key.encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                                  algorithm=hashes.SHA256(), label=aad))
    return {"version": 1, "context": context, "nonce": base64.b64encode(nonce).decode(),
            "wrapped_key": base64.b64encode(wrapped).decode(), "ciphertext": base64.b64encode(cipher).decode()}


def unseal(envelope: dict[str, Any], private_pem: bytes, expected: dict[str, Any]) -> dict[str, Any]:
    if envelope["version"] != 1 or envelope["context"] != expected:
        raise ValueError("delivery_identity_mismatch")
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("invalid_private_key")
    aad = worker.encoded(expected)
    key = private_key.decrypt(base64.b64decode(envelope["wrapped_key"], validate=True),
                              padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                           algorithm=hashes.SHA256(), label=aad))
    compressed = AESGCM(key).decrypt(base64.b64decode(envelope["nonce"], validate=True),
                                     base64.b64decode(envelope["ciphertext"], validate=True), aad)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        raw = stream.read(MAX_PLAIN + 1)
    if len(raw) > MAX_PLAIN:
        raise ValueError("private_payload_limit")
    return cast(dict[str, Any], json.loads(raw))


def execute(manifest: dict[str, Any], public_pem: bytes, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    task = manifest["task"]
    policies = []
    # One robots read/host; every URL was prechecked against these exact bytes.
    # Changed policy fails closed instead of relying on a stale authorisation.
    for host, expected in manifest["robots_sha256"].items():
        url = next(page["url"] for page in task["pages"] if urlsplit(page["url"]).hostname == host)
        observed = policy(url)
        if not observed["allowed"] or observed.get("sha256") != expected:
            raise ValueError("policy_changed_or_denied")
        policies.append(observed)
    with tempfile.TemporaryDirectory(prefix="phdbot-private-evidence-") as temporary:
        acquisition_started = time.perf_counter()
        directory, receipt = worker.run(task, Path(temporary), network=True)
        acquisition_seconds = time.perf_counter() - acquisition_started
        verification_started = time.perf_counter()
        worker.verify(directory, manifest["task_sha256"])
        verification_seconds = time.perf_counter() - verification_started
        payload = {"task": task, "receipt": receipt,
                   "results": {str(entry["index"]): json.loads((directory / f"page-{entry['index']}.json").read_bytes())
                               for entry in receipt["pages"] if entry["state"] == "ok"}}
        context = {"operation": "private-evidence-canary", "task_sha256": manifest["task_sha256"],
                   "recipient_sha256": manifest["recipient_sha256"],
                   "source_commit": os.environ.get("DDW_SOURCE_COMMIT", "local-uncommitted")}
        seal_started = time.perf_counter()
        sealed = seal(payload, public_pem, context)
        sealing_seconds = time.perf_counter() - seal_started
        worker.write_json(output / "evidence.sealed.json", sealed)
        summary = {"version": 1, "context": context, "build_id": receipt["build_id"],
                   "state": receipt["state"], "started_at": receipt["started_at"],
                   "finished_at": receipt["finished_at"], "policies": policies,
                   "pages": receipt["pages"], "acquisition_seconds": acquisition_seconds,
                   "verification_seconds": verification_seconds, "sealing_seconds": sealing_seconds,
                   "elapsed_seconds": time.perf_counter() - started,
                   "private_json_bytes": len(worker.encoded(payload)),
                   "compressed_private_bytes": len(gzip.compress(worker.encoded(payload))),
                   "sealed_bytes": (output / "evidence.sealed.json").stat().st_size,
                   "html_request_limit": len(task["pages"]), "robots_request_limit": len(policies),
                   "retry_limit": 0, "plaintext_exported": False}
        worker.write_json(output / "summary.json", summary)
        worker.write_json(output / "checksums.json", {name: worker.digest((output / name).read_bytes())
                                                     for name in ("summary.json", "evidence.sealed.json")})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("recipient", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("explicit --allow-network required")
    result = execute(read_manifest(args.manifest, args.recipient), args.recipient.read_bytes(), args.output)
    print(json.dumps({"state": result["state"], "pages": result["pages"]}))
    raise SystemExit(0 if any(p["state"] == "ok" for p in result["pages"]) else 2)


if __name__ == "__main__":
    main()
