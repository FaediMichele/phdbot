"""Bounded confidential delivery shared by worker and central admission."""
from __future__ import annotations

import base64
import gzip
import io
import json
import os
from typing import Any, cast

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from phd_searcher.ddw import worker

MAX_PLAIN = 8_000_000
MAX_ENVELOPE = 12_000_000

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



def signer_public_key(pem: bytes) -> ed25519.Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError("invalid_signer_key")
    return key


def sign(envelope: dict[str, Any], private_pem: bytes) -> dict[str, Any]:
    key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise ValueError("invalid_signer_key")
    return {"version": 1, "envelope": envelope,
            "signature": base64.b64encode(key.sign(worker.encoded(envelope))).decode()}


def authenticate(signed: bytes, public_pem: bytes) -> dict[str, Any]:
    if len(signed) > MAX_ENVELOPE:
        raise ValueError("delivery_limit")
    value = json.loads(signed)
    if set(value) != {"version", "envelope", "signature"} or value["version"] != 1:
        raise ValueError("invalid_signed_delivery")
    signer_public_key(public_pem).verify(base64.b64decode(value["signature"], validate=True),
                                         worker.encoded(value["envelope"]))
    return cast(dict[str, Any], value["envelope"])
