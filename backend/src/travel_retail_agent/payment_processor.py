# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""UCP."""

import logging
from typing import Any
from a2a.types import Task, TaskState, TaskStatus
from ucp_sdk.models.schemas.shopping.types.payment_instrument import (
    PaymentInstrument,
)


class MockPaymentProcessor:
    """Mock Payment Processor simulating Merchant Agent to MPP Agent calls."""

    def process_payment(
        self, payment_data: PaymentInstrument, risk_data: Any | None = None
    ) -> Task:
        """Process the payment."""
        logging.info("=== AP2 MERCHANT PAYMENT PROCESSOR (MPP) ===")
        logging.info(
            "Ricevuto Payment Instrument: %s (id: %s)",
            getattr(payment_data.root, "type", "card"),
            getattr(payment_data.root, "id", ""),
        )
        if isinstance(risk_data, dict):
            ap2_id = risk_data.get("ap2_mandate_id", "N/A")
            dev_ver = risk_data.get("device_verification", "N/A")
            has_cart_jwt = bool(risk_data.get("cart_mandate_jwt"))
            has_pay_jwt = bool(risk_data.get("payment_mandate_jwt"))
            logging.info("Verifica Mandati AP2: ID=%s, Attestazione=%s", ap2_id, dev_ver)
            logging.info(
                "Firma Cart Mandate (SD-JWT): %s | Firma Payment Mandate (SD-JWT): %s",
                "Verificata ✅" if has_cart_jwt else "Simulata (mock)",
                "Verificata ✅" if has_pay_jwt else "Simulata (mock)",
            )
            logging.info("Autorizzazione AP2 completata con successo (Liability Shift: Issuer).")

        task = Task(
            context_id="a unique context id",
            id="a unique task id",
            status=TaskStatus(state=TaskState.completed),
        )
        return task
