# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Simulated AP2 (Agentic Payments Protocol) Mandate Token Generator & Verifier.
Implements Google AP2 Intent & Cart Mandates with FIDO2/TPM simulated signatures.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

# Simulated HMAC secret for local demo authorization (override via AP2_SHARED_SECRET_KEY)
SHARED_SECRET_KEY = os.getenv("AP2_SHARED_SECRET_KEY", "mock_ap2_secret_key_demo").encode("utf-8")


def create_ap2_mandate(
    order_id: str,
    buyer_email: str,
    max_amount_cents: int,
    mandate_type: str = "ap2_cart_mandate",
    credential_manager: str = "LocalCredentialManager",
) -> Dict[str, Any]:
    """Generate an AP2 cryptographic delegation mandate."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "AP2-SD-JWT"}
    payload = {
        "iss": "https://identity.google.com/ap2/lcm",
        "sub": buyer_email,
        "aud": "https://merchant.milanocentrale.it",
        "order_id": order_id,
        "mandate_type": mandate_type,
        "credential_manager": credential_manager,
        "max_amount_cents": max_amount_cents,
        "iat": now,
        "exp": now + 3600,
        "jti": f"tok_ap2_{order_id.lower()}_{now}",
    }

    hdr_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    pay_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(SHARED_SECRET_KEY, f"{hdr_b64}.{pay_b64}".encode(), hashlib.sha256).hexdigest()

    token_jwt = f"{hdr_b64}.{pay_b64}.{sig[:32]}"

    return {
        "verified": True,
        "mandate_type": mandate_type,
        "credential_manager": credential_manager,
        "token_id": payload["jti"],
        "token_jwt": token_jwt,
        "max_amount_cents": max_amount_cents,
        "signature_scheme": "FIDO2_Passkey_P256",
    }


def verify_ap2_mandate(token_dict: Dict[str, Any], total_cents: int) -> bool:
    """Verify mandate validity and spending limit."""
    if not token_dict or not token_dict.get("verified"):
        return False
    max_cents = token_dict.get("max_amount_cents", 0)
    if total_cents > max_cents:
        return False
    return True
