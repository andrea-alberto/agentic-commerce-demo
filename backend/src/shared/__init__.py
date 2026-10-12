# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Shared models, AP2 utilities, RFC 9421 helpers, and Station Rules
for Universal Commerce Protocol (UCP) Milano Centrale Ecosystem.
"""

from .models import (
    TravelerContext,
    TrainTicket,
    TravelerPreferences,
    AP2Delegation,
    UcpProduct,
    UcpCheckoutItem,
    UcpFulfillment,
    BopisOrder,
)
from .ap2_crypto import create_ap2_mandate, verify_ap2_mandate
from .rfc9421 import generate_rfc9421_signature, verify_rfc9421_signature
from .station_rules import (
    validate_station_constraints,
    TRAIN_DELIVERY_FEE_CENTS,
    MIN_LEAD_TIME_TRAIN_MINUTES,
    MIN_LEAD_TIME_LOCKER_MINUTES,
)

__all__ = [
    "TravelerContext",
    "TrainTicket",
    "TravelerPreferences",
    "AP2Delegation",
    "UcpProduct",
    "UcpCheckoutItem",
    "UcpFulfillment",
    "BopisOrder",
    "create_ap2_mandate",
    "verify_ap2_mandate",
    "generate_rfc9421_signature",
    "verify_rfc9421_signature",
    "validate_station_constraints",
    "TRAIN_DELIVERY_FEE_CENTS",
    "MIN_LEAD_TIME_TRAIN_MINUTES",
    "MIN_LEAD_TIME_LOCKER_MINUTES",
]
