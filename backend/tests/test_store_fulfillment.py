# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Unit tests for RetailStore fulfillment options, counter pickup vs table service."""

import json
from pathlib import Path
import unittest

from travel_retail_agent.store import RetailStore, UcpMetadata


class TestStoreFulfillment(unittest.TestCase):
    """Test suite for RetailStore fulfillment logic."""

    def setUp(self):
        self.store = RetailStore()
        ucp_path = Path(__file__).parent.parent / "src" / "travel_retail_agent" / "data" / "ucp.json"
        with open(ucp_path, "r", encoding="utf-8") as f:
            raw_meta = json.load(f)
            self.metadata = UcpMetadata.model_validate(raw_meta["ucp"])

        # Create a fresh checkout with an item
        self.checkout = self.store.add_to_checkout(self.metadata, "PANIN-004", 1)

    def test_default_service_is_counter(self):
        """Calling set_table_service without explicit table number must default to Al Banco."""
        co = self.store.set_table_service(self.checkout.id, service_time="16:30")
        method = co.fulfillment.root.methods[0]
        opt = next(o for o in method.groups[0].options if o.id == "pickup_express")

        self.assertEqual(opt.title, "Ritiro al Banco (Bistrot Binario 12)")
        self.assertIn("Ritiro al banco confermato (Al Banco)", opt.description)
        dest = method.destinations[0].root
        self.assertIn("Al Banco (Ritiro al Banco:", dest.extended_address)

    def test_counter_variants_normalization(self):
        """All variations of counter requests must normalize to 'Al Banco'."""
        variants = [
            "Al Banco",
            "al banco",
            "banco",
            "bancone",
            "al bancone",
            "consegna al bancone",
            "ritiro al bancone",
            "desk al banco",
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                co = self.store.set_table_service(
                    self.checkout.id,
                    table_number=variant,
                    service_time="16:30",
                )
                method = co.fulfillment.root.methods[0]
                opt = next(o for o in method.groups[0].options if o.id == "pickup_express")

                self.assertEqual(
                    opt.title,
                    "Ritiro al Banco (Bistrot Binario 12)",
                    f"Variant '{variant}' did not yield counter title",
                )
                self.assertIn(
                    "Ritiro al banco confermato (Al Banco)",
                    opt.description,
                    f"Variant '{variant}' description still mentioned table service",
                )
                self.assertNotIn(
                    "Tavolo",
                    opt.description,
                    f"Variant '{variant}' should not mention Tavolo",
                )
                dest = method.destinations[0].root
                self.assertIn("Al Banco (Ritiro al Banco:", dest.extended_address)

    def test_table_service_preservation(self):
        """Specifying an actual table number must produce 'Servizio al Tavolo'."""
        tables = [
            ("Tavolo 5", "Tavolo 5"),
            ("tavolo 1", "Tavolo 1"),
            ("3", "Tavolo 3"),
            ("12", "Tavolo 12"),
        ]
        for input_tbl, expected_label in tables:
            with self.subTest(input_tbl=input_tbl):
                co = self.store.set_table_service(
                    self.checkout.id,
                    table_number=input_tbl,
                    service_time="16:35",
                )
                method = co.fulfillment.root.methods[0]
                opt = next(o for o in method.groups[0].options if o.id == "pickup_express")

                self.assertIn("Servizio al Tavolo", opt.title)
                self.assertIn(f"Servizio al tavolo confermato ({expected_label})", opt.description)
                dest = method.destinations[0].root
                self.assertIn(f"{expected_label} (Servizio al Tavolo:", dest.extended_address)

    def test_totals_fulfillment_label(self):
        """Fulfillment row in checkout totals must adapt between counter and table."""
        # 1. Al Banco
        co_banco = self.store.set_table_service(self.checkout.id, table_number="Al Banco")
        fl_total_banco = next(t for t in co_banco.totals if t.type == "fulfillment")
        self.assertEqual(fl_total_banco.display_text, "Ritiro al Banco (Bistrot Binario 12)")

        # 2. Tavolo 5
        co_table = self.store.set_table_service(self.checkout.id, table_number="Tavolo 5")
        fl_total_table = next(t for t in co_table.totals if t.type == "fulfillment")
        self.assertIn("Servizio al Tavolo", fl_total_table.display_text)

    def test_train_delivery_carriage_and_time(self):
        """Train delivery must parse delivery_time and normalize carriage without duplicating 'Carrozza'."""
        co_train = self.store.set_train_delivery(
            self.checkout.id,
            train_number="Frecciarossa 9540",
            carriage="Carrozza 4",
            seat="12D",
            delivery_time="19:45",
            platform="Binario 14",
        )
        method = co_train.fulfillment.root.methods[0]
        opt = next(o for o in method.groups[0].options if o.id == "in_seat_train")
        dest = method.destinations[0].root

        # Assert delivery time in earliest_fulfillment_time and description
        self.assertEqual(opt.earliest_fulfillment_time.strftime("%H:%M"), "19:45")
        self.assertIn("19:45", opt.description)
        self.assertIn("19:46", opt.description)

        # Assert no double Carrozza
        self.assertIn("Carrozza 4", opt.description)
        self.assertNotIn("Carrozza Carrozza", opt.description)
        self.assertIn("Carrozza 4", dest.extended_address)
        self.assertNotIn("Carrozza Carrozza", dest.extended_address)


if __name__ == "__main__":
    unittest.main()
