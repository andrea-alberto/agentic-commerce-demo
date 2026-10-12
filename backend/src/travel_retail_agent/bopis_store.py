# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Unified BOPIS (Buy Online, Pick-up In Store) Engine & Order Store."""

from datetime import datetime, timezone, timedelta
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("travel_retail_agent.bopis")

DEFAULT_PROJECT_ID = "agentic-comm-mi-devfest-2026"
ORDERS_COLLECTION = "bopis_orders"


class BopisOrderStore:
    """Multi-channel BOPIS Order Storage with Firestore persistence and local fail-safe."""

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or DEFAULT_PROJECT_ID
        self._local_cache: dict[str, dict[str, Any]] = {}
        self._data_file = Path(__file__).parent / "data" / "bopis_orders.json"
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        self._firestore_client = None
        self._firestore_enabled = False

        self._load_local_cache()
        self._init_firestore()

        # Seed with initial demo orders if empty
        if not self._local_cache:
            self._seed_sample_orders()

    def _init_firestore(self):
        """Attempt to connect to Google Cloud Firestore."""
        try:
            from google.cloud import firestore
            self._firestore_client = firestore.Client(project=self.project_id)
            # Test simple call
            _ = list(self._firestore_client.collection(ORDERS_COLLECTION).limit(1).stream())
            self._firestore_enabled = True
            logger.info("Firestore collegato con successo sul progetto '%s'!", self.project_id)
            self._sync_from_firestore()
        except Exception as e:
            self._firestore_enabled = False
            self._firestore_client = None
            logger.warning(
                "Firestore non attivo o credenziali non configurate (fallback locale attivo): %s", e
            )

    def _sync_from_firestore(self):
        """Sync remote orders from Firestore into memory."""
        if not self._firestore_enabled or not self._firestore_client:
            return
        try:
            docs = self._firestore_client.collection(ORDERS_COLLECTION).stream()
            count = 0
            for doc in docs:
                data = doc.to_dict()
                if "order_id" in data:
                    self._local_cache[data["order_id"]] = data
                    count += 1
            if count > 0:
                self._save_local_cache()
                logger.info("Sincronizzati %d ordini da Firestore.", count)
        except Exception as e:
            logger.error("Errore sync da Firestore: %s", e)

    def _backfill_order_timing(self, o: dict[str, Any]) -> dict[str, Any]:
        """Ensure placed_at_display, requested_delivery_display, and lead_time_minutes are present."""
        now_dt = datetime.now().astimezone()
        today_str = now_dt.strftime("%d/%m/%Y")
        if not o.get("placed_at_display"):
            try:
                dt = datetime.fromisoformat(o["created_at"])
                o["placed_at_display"] = dt.strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                o["placed_at_display"] = now_dt.strftime("%d/%m/%Y %H:%M:%S")

        if not o.get("requested_delivery_display") or "min" in o.get("requested_delivery_display", "").lower():
            fld = o.get("fulfillment_details", {})
            time_val = fld.get("delivery_time") or fld.get("service_time") or fld.get("slot_start")
            if not time_val and fld.get("window") and "min" not in fld.get("window", "").lower():
                time_val = fld.get("window")
            if not time_val:
                try:
                    dt_base = datetime.fromisoformat(o.get("created_at", ""))
                except Exception:
                    dt_base = now_dt
                lead = o.get("lead_time_minutes") or 5
                time_val = (dt_base + timedelta(minutes=lead)).strftime("%H:%M")
            o["requested_delivery_display"] = f"{today_str} {time_val}"

        if "lead_time_minutes" not in o or o["lead_time_minutes"] is None:
            fl_type = o.get("fulfillment_type")
            if fl_type == "in_seat_train":
                o["lead_time_minutes"] = 35
            elif fl_type == "pickup_locker":
                o["lead_time_minutes"] = 30
            else:
                o["lead_time_minutes"] = 5
        return o

    def _load_local_cache(self):
        """Load local JSON cache if present."""
        if self._data_file.exists():
            try:
                with self._data_file.open("r", encoding="utf-8") as f:
                    orders = json.load(f)
                    for o in orders:
                        self._local_cache[o["order_id"]] = self._backfill_order_timing(o)
            except Exception as e:
                logger.warning("Impossibile caricare cache ordini locale: %s", e)

    def _save_local_cache(self):
        """Save local JSON cache."""
        try:
            with self._data_file.open("w", encoding="utf-8") as f:
                json.dump(list(self._local_cache.values()), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Errore salvataggio file ordini locale: %s", e)

    def _seed_sample_orders(self):
        """Seed initial orders across channels to showcase the multi-channel capability."""
        now = datetime.now().astimezone()
        today_str = now.strftime("%d/%m/%Y")
        samples = [
            {
                "order_id": "ORD-MI-9540A",
                "created_at": (now - timedelta(minutes=12)).isoformat(),
                "updated_at": (now - timedelta(minutes=5)).isoformat(),
                "placed_at_display": (now - timedelta(minutes=12)).strftime("%d/%m/%Y %H:%M:%S"),
                "requested_delivery_display": f"{today_str} {(now + timedelta(minutes=18)).strftime('%H:%M')}",
                "lead_time_minutes": 30,
                "channel_source": "ucp_direct_a2a",
                "channel_label": "Demo 1: UCP Direct A2A",
                "status": "preparing",
                "fulfillment_type": "in_seat_train",
                "fulfillment_details": {
                    "train_number": "Frecciarossa 9540",
                    "platform": "Binario 14",
                    "carriage": "Carrozza 4",
                    "seat": "12D",
                    "delivery_time": (now + timedelta(minutes=18)).strftime("%H:%M"),
                    "window": f"{(now + timedelta(minutes=18)).strftime('%H:%M')} - {(now + timedelta(minutes=19)).strftime('%H:%M')}",
                    "delivery_fee_cents": 650,
                    "target_minutes_left": 18,
                },
                "items": [
                    {
                        "id": "PANIN-004",
                        "title": "Ciabatta con Crudo di Parma DOP e Mozzarella",
                        "quantity": 1,
                        "price_cents": 850,
                        "image_url": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=500&q=80",
                    },
                    {
                        "id": "BEV-001",
                        "title": "Caffè Espresso Selezione 100% Arabica",
                        "quantity": 1,
                        "price_cents": 150,
                        "image_url": "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=500&q=80",
                    },
                ],
                "totals": {
                    "subtotal_cents": 1000,
                    "delivery_fee_cents": 650,
                    "total_cents": 1650,
                    "currency": "EUR",
                },
                "buyer": {
                    "name": "Marco Rossi",
                    "email": "marco.rossi@example.it",
                },
                "ap2_verification": {
                    "verified": True,
                    "mandate_type": "ap2_cart_mandate",
                    "credential_manager": "LocalCredentialManager",
                    "token_id": "tok_lcm_passkey_9540",
                },
            },
            {
                "order_id": "ORD-MI-LOCK1",
                "created_at": (now - timedelta(minutes=25)).isoformat(),
                "updated_at": (now - timedelta(minutes=2)).isoformat(),
                "placed_at_display": (now - timedelta(minutes=25)).strftime("%d/%m/%Y %H:%M:%S"),
                "requested_delivery_display": f"{today_str} {(now + timedelta(minutes=10)).strftime('%H:%M')} - {(now + timedelta(minutes=20)).strftime('%H:%M')}",
                "lead_time_minutes": 35,
                "channel_source": "web_mcp",
                "channel_label": "Demo 2: Web MCP",
                "status": "ready_for_pickup",
                "fulfillment_type": "pickup_locker",
                "fulfillment_details": {
                    "location": "Smart Locker Piano Interrato",
                    "box_number": "Box #14",
                    "pin_code": "8492",
                    "slot_start": (now + timedelta(minutes=10)).strftime("%H:%M"),
                    "slot_end": (now + timedelta(minutes=20)).strftime("%H:%M"),
                    "delivery_fee_cents": 0,
                    "target_minutes_left": 10,
                },
                "items": [
                    {
                        "id": "PANIN-001",
                        "title": "Focaccia Ligure Tradizionale all'Olio EVO",
                        "quantity": 2,
                        "price_cents": 650,
                        "image_url": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=500&q=80",
                    },
                    {
                        "id": "BEV-003",
                        "title": "Succo d'Arancia Rossa di Sicilia Bio 250ml",
                        "quantity": 1,
                        "price_cents": 350,
                        "image_url": "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=500&q=80",
                    },
                ],
                "totals": {
                    "subtotal_cents": 1650,
                    "delivery_fee_cents": 0,
                    "total_cents": 1650,
                    "currency": "EUR",
                },
                "buyer": {
                    "name": "Giulia Bianchi",
                    "email": "giulia.bianchi@example.it",
                },
                "ap2_verification": {
                    "verified": True,
                    "mandate_type": "ap2_cart_mandate",
                    "credential_manager": "LocalCredentialManager",
                    "token_id": "tok_lcm_passkey_lock1",
                },
            },
            {
                "order_id": "ORD-MI-TAB05",
                "created_at": (now - timedelta(minutes=8)).isoformat(),
                "updated_at": (now - timedelta(minutes=3)).isoformat(),
                "placed_at_display": (now - timedelta(minutes=8)).strftime("%d/%m/%Y %H:%M:%S"),
                "requested_delivery_display": f"{today_str} {(now + timedelta(minutes=5)).strftime('%H:%M')}",
                "lead_time_minutes": 13,
                "channel_source": "two_agent_a2a",
                "channel_label": "Demo 3: Two-Agent A2A M2M",
                "status": "preparing",
                "fulfillment_type": "dine_in_table",
                "fulfillment_details": {
                    "location": "Bistrot Binario 12",
                    "table_number": "Tavolo 5",
                    "service_time": (now + timedelta(minutes=5)).strftime("%H:%M"),
                    "window": "Finestra 5 min",
                    "delivery_fee_cents": 0,
                    "target_minutes_left": 5,
                },
                "items": [
                    {
                        "id": "DOLCE-001",
                        "title": "Brioche Artigianale al Pistacchio di Bronte",
                        "quantity": 1,
                        "price_cents": 280,
                        "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500&q=80",
                    },
                    {
                        "id": "BEV-002",
                        "title": "Cappuccino Italiano con Latte Fresco Intero",
                        "quantity": 1,
                        "price_cents": 200,
                        "image_url": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=500&q=80",
                    },
                ],
                "totals": {
                    "subtotal_cents": 480,
                    "delivery_fee_cents": 0,
                    "total_cents": 480,
                    "currency": "EUR",
                },
                "buyer": {
                    "name": "Alessandro Verdi",
                    "email": "alessandro.verdi@example.it",
                },
                "ap2_verification": {
                    "verified": True,
                    "mandate_type": "ap2_cart_mandate",
                    "credential_manager": "LocalCredentialManager",
                    "token_id": "tok_lcm_passkey_tab05",
                },
            },
        ]

        for s in samples:
            self._local_cache[s["order_id"]] = s
        self._save_local_cache()

    def record_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Record or update a BOPIS order."""
        order_id = order_data["order_id"]
        now_dt = datetime.now().astimezone()
        now_iso = now_dt.isoformat()
        if "created_at" not in order_data:
            order_data["created_at"] = now_iso
        order_data["updated_at"] = now_iso

        if "placed_at_display" not in order_data:
            try:
                dt = datetime.fromisoformat(order_data["created_at"])
                order_data["placed_at_display"] = dt.strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                order_data["placed_at_display"] = now_dt.strftime("%d/%m/%Y %H:%M:%S")

        if "requested_delivery_display" not in order_data or "min" in order_data.get("requested_delivery_display", "").lower():
            fld = order_data.get("fulfillment_details", {})
            time_val = fld.get("delivery_time") or fld.get("service_time") or fld.get("slot_start")
            if not time_val and fld.get("window") and "min" not in fld.get("window", "").lower():
                time_val = fld.get("window")
            if not time_val:
                try:
                    dt_base = datetime.fromisoformat(order_data.get("created_at", ""))
                except Exception:
                    dt_base = now_dt
                lead = order_data.get("lead_time_minutes") or 5
                time_val = (dt_base + timedelta(minutes=lead)).strftime("%H:%M")
            date_prefix = now_dt.strftime("%d/%m/%Y")
            order_data["requested_delivery_display"] = f"{date_prefix} {time_val}"

        self._local_cache[order_id] = order_data
        self._save_local_cache()

        # If Firestore is active, write document
        if self._firestore_enabled and self._firestore_client:
            try:
                self._firestore_client.collection(ORDERS_COLLECTION).document(order_id).set(order_data)
                logger.info("Ordine %s salvato su Firestore.", order_id)
            except Exception as e:
                logger.error("Errore salvataggio ordine %s su Firestore: %s", order_id, e)

        return order_data

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        o = self._local_cache.get(order_id)
        return self._backfill_order_timing(o) if o else None

    def get_all_orders(self, max_age_hours: int | None = None) -> list[dict[str, Any]]:
        # Return sorted by updated_at descending
        now_dt = datetime.now().astimezone()
        orders = [self._backfill_order_timing(o) for o in self._local_cache.values()]

        if max_age_hours is not None:
            cutoff = now_dt - timedelta(hours=max_age_hours)
            filtered = []
            for o in orders:
                ts = o.get("created_at") or o.get("updated_at")
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt < cutoff:
                            continue
                    except Exception:
                        pass
                filtered.append(o)
            orders = filtered

        orders.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return orders

    def get_orders_for_buyer(self, buyer_email: str) -> list[dict[str, Any]]:
        """Restituisce solo gli ordini associati all'email del buyer specificato (Modalità 1: Matching per Email)."""
        target_email = buyer_email.strip().lower()
        orders = [self._backfill_order_timing(o) for o in self._local_cache.values()]
        matched = []
        for o in orders:
            buyer = o.get("buyer") or {}
            b_email = (buyer.get("email") or o.get("buyer_email") or "").strip().lower()
            if b_email and b_email == target_email:
                matched.append(o)
        matched.sort(key=lambda x: x.get("updated_at", "") or x.get("created_at", ""), reverse=True)
        return matched

    def update_order_status(self, order_id: str, new_status: str) -> dict[str, Any] | None:
        order = self._local_cache.get(order_id)
        if not order:
            return None
        order["status"] = new_status
        order["updated_at"] = datetime.now().astimezone().isoformat()
        self._local_cache[order_id] = order
        self._save_local_cache()

        if self._firestore_enabled and self._firestore_client:
            try:
                self._firestore_client.collection(ORDERS_COLLECTION).document(order_id).update({
                    "status": new_status,
                    "updated_at": order["updated_at"],
                })
            except Exception as e:
                logger.error("Errore aggiornamento stato ordine %s su Firestore: %s", order_id, e)

        return order

    def get_stats(self) -> dict[str, Any]:
        orders = list(self._local_cache.values())
        stats = {
            "total_orders": len(orders),
            "preparing": sum(1 for o in orders if o.get("status") == "preparing"),
            "ready_for_pickup": sum(1 for o in orders if o.get("status") == "ready_for_pickup"),
            "completed": sum(1 for o in orders if o.get("status") == "completed"),
            "by_channel": {},
            "by_fulfillment": {},
        }
        for o in orders:
            ch = o.get("channel_source", "unknown")
            stats["by_channel"][ch] = stats["by_channel"].get(ch, 0) + 1
            fl = o.get("fulfillment_type", "unknown")
            stats["by_fulfillment"][fl] = stats["by_fulfillment"].get(fl, 0) + 1
        return stats


# Global Singleton
bopis_store = BopisOrderStore()
