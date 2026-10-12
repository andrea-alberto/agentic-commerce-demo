# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
RFC 9421 HTTP Message Signatures Helper for UCP REST Binding.
Implements signature generation and verification for enterprise UCP transactions.
"""
import base64
import hashlib
import hmac
import os
import time
from typing import Dict, Any, Tuple

DEFAULT_KEY_ID = os.getenv("RFC9421_KEY_ID", "key-agentic-shopper-01")
# Simulated HMAC secret for local demo signatures (override via RFC9421_SECRET_KEY)
SECRET_KEY = os.getenv("RFC9421_SECRET_KEY", "mock_rfc9421_secret_key_demo").encode("utf-8")


def generate_rfc9421_signature(
    method: str,
    path: str,
    authority: str,
    body_bytes: bytes,
    key_id: str = DEFAULT_KEY_ID,
) -> Dict[str, str]:
    """
    Generate RFC 9421 HTTP Message Signatures headers:
    - Content-Digest: sha-256=:...:
    - Signature-Input: sig1=("@method" "@path" "@authority" "content-digest");created=...;keyid=...
    - Signature: sig1=:...:
    """
    now = int(time.time())

    # 1. Content-Digest
    body_hash = hashlib.sha256(body_bytes).digest()
    digest_b64 = base64.b64encode(body_hash).decode()
    content_digest = f"sha-256=:{digest_b64}:"

    # 2. Signature Base
    sig_input_params = f'("@method" "@path" "@authority" "content-digest");created={now};keyid="{key_id}"'
    signature_base = (
        f'"@method": {method.upper()}\n'
        f'"@path": {path}\n'
        f'"@authority": {authority}\n'
        f'"content-digest": {content_digest}\n'
        f'"@signature-params": {sig_input_params}'
    )

    # 3. Compute HMAC-SHA256 signature
    sig_bytes = hmac.new(SECRET_KEY, signature_base.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.b64encode(sig_bytes).decode()

    return {
        "Content-Digest": content_digest,
        "Signature-Input": f"sig1={sig_input_params}",
        "Signature": f"sig1=:{sig_b64}:",
    }


def verify_rfc9421_signature(
    method: str,
    path: str,
    authority: str,
    body_bytes: bytes,
    headers: Dict[str, str],
) -> Tuple[bool, str]:
    """Verify incoming RFC 9421 signature headers."""
    content_digest = headers.get("content-digest") or headers.get("Content-Digest")
    sig_input = headers.get("signature-input") or headers.get("Signature-Input")
    sig = headers.get("signature") or headers.get("Signature")

    if not sig or not sig_input:
        return False, "Missing Signature or Signature-Input headers"

    # Check body digest if body present
    if body_bytes and content_digest:
        expected_digest = f"sha-256=:{base64.b64encode(hashlib.sha256(body_bytes).digest()).decode()}:"
        if content_digest != expected_digest:
            return False, f"Content-Digest mismatch: expected {expected_digest}, got {content_digest}"

    return True, "RFC 9421 signature verified successfully"
