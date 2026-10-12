# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Core Catalog & Store Service for Milano Centrale Travel Retail.

Agnostic business domain logic:
- Catalog loading & indexing from products.json
- Smart Relevance Ranking & Thermal Affinity (station rules)
- Shopping Cart management & BOPIS Order generation
"""

from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .bopis_store import bopis_store

logger = logging.getLogger("travel_retail_agent.catalog")

# Station Rules constants
MIN_LEAD_TIME_TRAIN_MINUTES = 30
MIN_LEAD_TIME_LOCKER_MINUTES = 30
TRAIN_DELIVERY_FEE_CENTS = 650

DATA_DIR = Path(__file__).parent / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"


class CatalogService:
    """Core in-memory catalog, ranking engine, and shopping cart service."""

    def __init__(self):
        self._products: dict[str, dict[str, Any]] = {}
        self._carts: dict[str, dict[str, Any]] = {}
        self._load_products()

    def _load_products(self):
        if PRODUCTS_FILE.exists():
            try:
                with PRODUCTS_FILE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        pid = item.get("productID")
                        if pid:
                            price_val = float(item.get("offers", {}).get("price", "0.0"))
                            price_cents = int(round(price_val * 100))
                            is_hot = any(
                                prop.get("name") == "temperature" and prop.get("value") == "hot"
                                for prop in item.get("additionalProperty", [])
                            ) or ("caldo" in item.get("name", "").lower())
                            
                            images = item.get("image", [])
                            img_url = images[0] if isinstance(images, list) and images else (images if isinstance(images, str) else "")

                            pickup_opts = [
                                {
                                    "id": "pickup",
                                    "title": "Ritiro Rapido al Banco Bistrot (Binario 12)",
                                    "price_cents": 0,
                                    "lead_time_minutes": 5,
                                    "description": "Pronto in 5 min al desk express del Bistrot",
                                }
                            ]
                            if not is_hot:
                                pickup_opts.append({
                                    "id": "pickup_locker",
                                    "title": "Smart Locker Stazione (Piano Interrato)",
                                    "price_cents": 0,
                                    "lead_time_minutes": 30,
                                    "description": "Ritiro contactless nello Smart Locker con PIN (solo per cibi freddi e tech)",
                                })

                            fulfillment_methods = [
                                {
                                    "type": "pickup",
                                    "description": "Ritiro in stazione (banco o locker)" if not is_hot else "Ritiro al banco (pronto in 5 min, idoneo per caldi)",
                                    "options": pickup_opts,
                                },
                                {
                                    "type": "shipping",
                                    "description": "Consegna al Posto a Bordo Treno (+€6.50)",
                                    "options": [
                                        {
                                            "id": "in_seat_train",
                                            "title": "Consegna al Posto Treno (Frecciarossa/Italo)",
                                            "price_cents": 650,
                                            "lead_time_minutes": 30,
                                            "description": "Consegna diretta alla carrozza/posto prima della partenza",
                                        }
                                    ],
                                },
                            ]

                            self._products[pid] = {
                                "id": pid,
                                "name": item.get("name"),
                                "price": price_val,
                                "price_cents": price_cents,
                                "currency": item.get("offers", {}).get("priceCurrency", "EUR"),
                                "description": item.get("description", ""),
                                "category": item.get("category", ""),
                                "is_hot": is_hot,
                                "image_url": img_url,
                                "packaging_type": item.get("packaging_type", "fresh_service" if "Food" in item.get("category", "") else "prepackaged"),
                                "net_weight_g": item.get("net_weight_g"),
                                "nutrition": item.get("nutrition"),
                                "processing_level": item.get("processing_level"),
                                "dietary_profile": item.get("dietary_profile"),
                                "coffee_profile": item.get("coffee_profile"),
                                "sustainability": item.get("sustainability"),
                                "travel_profile": item.get("travel_profile"),
                                "tech_specs": item.get("tech_specs"),
                                "fulfillment": {
                                    "methods": fulfillment_methods
                                },
                            }
            except Exception as e:
                logger.error("Errore caricamento prodotti nel CatalogService: %s", e)

    def get_all_products(self) -> list[dict[str, Any]]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Optional[dict[str, Any]]:
        return self._products.get(product_id)

    def search_products(self, query: str = "", category: str = "") -> list[dict[str, Any]]:
        """Smart Relevance Ranking & Thermal Affinity product search."""
        q = (query or "").strip().lower()
        cat = (category or "").strip().lower()

        stop_words = {
            "un", "uno", "una", "il", "lo", "la", "i", "gli", "le",
            "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
            "e", "ed", "o", "od", "al", "allo", "alla", "ai", "agli", "alle",
            "del", "dello", "della", "dei", "degli", "delle", "compatibile", "lo",
            # Action and conversational stopwords (e.g. 'aggiungi al carrello il panino vegano')
            "aggiungi", "aggiugi", "aggiungimi", "metti", "inserisci", "prendi", "prendimi", "dammi",
            "carrello", "nel", "nello", "nella", "nei", "negli", "nelle",
            "mostrami", "fammi", "vedere", "cerca", "trova", "vorrei", "favore"
        }
        raw_keywords = [
            w for w in q.replace(",", " ").replace(".", " ").replace(";", " ").split()
            if w not in stop_words and len(w) > 1
        ]

        wants_locker = any(w in q for w in ["locker", "smart locker", "armadietto", "interrato"])
        wants_cold = wants_locker or any(w in q for w in ["freddo", "fredda", "freddi", "fresco", "fresca", "cold"])
        wants_hot = any(w in q for w in ["caldo", "calda", "caldi", "fumante", "hot", "espresso", "cappuccino", "toast"])
        wants_vegan = any(w in q for w in ["vegan", "vegano", "vegana", "veg", "vegetale", "plant based"])
        wants_sandwich = any(w in q for w in ["panin", "sandwich", "ciabatt", "focaccia"])
        wants_juice = any(w in q for w in ["spremut", "aranc", "succo", "agrum"])

        scored_candidates: list[tuple[float, dict[str, Any]]] = []

        for p in self._products.values():
            name = p["name"].lower()
            desc = p["description"].lower()
            p_cat = p["category"].lower()
            is_hot = p.get("is_hot", False)
            diet_prof = p.get("dietary_profile") or {}
            diet_tags = [t.lower() for t in diet_prof.get("dietary_tags", [])]
            claims = [c.lower() for c in (p.get("nutrition") or {}).get("health_claims", [])]
            sust = p.get("sustainability") or {}
            origin = sust.get("origin", "").lower()
            coffee_prof = p.get("coffee_profile") or {}
            coffee_brew = coffee_prof.get("brewing_method", "").lower()
            coffee_notes = [n.lower() for n in coffee_prof.get("tasting_notes", [])]

            # Category filter if specified
            if cat and cat not in ["all", "tutti", "*"]:
                if cat in ["hot", "caldo", "caldi", "calda"] and not is_hot:
                    continue
                elif cat in ["cold", "freddo", "freddi", "fredda", "locker"] and (is_hot or "elettronica" in p_cat or "audio" in p_cat):
                    continue
                elif cat in ["tech", "elettronica"] and ("elettronica" not in p_cat and "audio" not in p_cat):
                    continue
                elif cat in ["bevande", "beverage", "drink", "drinks"] and ("bevande" not in p_cat and "caffe" not in p_cat and "caffetteria" not in p_cat):
                    continue
                elif cat in ["coffee", "caffetteria"] and ("caffe" not in p_cat and "caffetteria" not in p_cat):
                    continue
                elif cat in ["specialty", "caffe_specialty"] and not coffee_prof:
                    continue
                elif cat in ["sandwiches", "panini", "panino"] and ("panin" not in p_cat and "panin" not in name and "toast" not in name and "ciabatta" not in name and "focaccia" not in name):
                    continue
                elif cat in ["vegan", "vegano", "vegana"] and (not any("veg" in t for t in diet_tags) and "vegan" not in name and "vegano" not in name):
                    continue
                elif cat in ["gluten_free", "senza_glutine"] and (not any("glutine" in t for t in diet_tags) and "glutine" not in name and "aic" not in desc):
                    continue
                elif cat in ["lactose_free", "senza_lattosio"] and (not any("lattosio" in t for t in diet_tags) and "lattosio" not in desc):
                    continue
                elif cat in ["high_protein", "proteine"] and (not any("protein" in c for c in claims) and "protein" not in desc):
                    continue
                elif cat not in p_cat and cat not in ["all"]:
                    continue

            if not raw_keywords:
                # No search query: baseline score
                base_score = 10.0
                if cat in ["cold", "locker"] and not is_hot:
                    base_score += 10.0
                scored_candidates.append((base_score, p))
                continue

            score = 0.0

            # Direct exact phrase match
            if q in name:
                score += 50.0
            if q in desc:
                score += 25.0
            if "km 0" in q and ("km 0" in origin or "km 0" in desc):
                score += 40.0

            for kw in raw_keywords:
                stem = kw[:-1] if len(kw) > 4 and kw[-1] in "oiea" else kw
                if kw in name:
                    score += 35.0
                elif stem in name:
                    score += 20.0

                if kw in p_cat:
                    score += 20.0
                elif stem in p_cat:
                    score += 15.0

                if kw in desc:
                    score += 15.0
                elif stem in desc:
                    score += 10.0

                if kw in origin:
                    score += 20.0
                elif stem in origin:
                    score += 12.0

                # Dietary tags match
                if any(kw == t or stem == t or stem in t for t in diet_tags):
                    if wants_vegan and kw in ["vegan", "vegano", "veg"]:
                        if "vegan" in name or "vegano" in name:
                            score += 40.0
                        elif "vegan" in desc or "vegano" in desc:
                            score += 25.0
                        elif not is_hot and "food" in p_cat:
                            score += 15.0
                        else:
                            score += 2.0
                    else:
                        score += 8.0

                if any(kw in c for c in claims):
                    score += 6.0
                if kw in coffee_brew or any(kw in n for n in coffee_notes):
                    score += 8.0

            # Intent and Category affinities
            if wants_sandwich:
                if "panin" in name or "panin" in p_cat:
                    score += 45.0
                elif "caffe" in p_cat or "bevande" in p_cat:
                    score -= 25.0

            if wants_juice:
                if "spremut" in name or "aranc" in name:
                    score += 45.0

            # Locker and thermal affinities
            if wants_locker:
                if not is_hot and "elettronica" not in p_cat and "audio" not in p_cat:
                    score += 35.0
                if is_hot:
                    score -= 80.0  # Locker cannot store hot food

            if wants_cold:
                if not is_hot:
                    score += 20.0
                else:
                    score -= 40.0

            if wants_hot:
                if is_hot:
                    score += 35.0
                else:
                    score -= 30.0

            if score > 0.0:
                scored_candidates.append((score, p))

        # Sort candidate products by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Generate token-optimized summaries
        results = []
        for _, p in scored_candidates[:6]:
            p_cat = p.get("category", "").lower()
            is_hot = p.get("is_hot", False)
            diet_prof = p.get("dietary_profile") or {}
            diet_tags = diet_prof.get("dietary_tags", [])
            sust = p.get("sustainability") or {}
            ful = p.get("fulfillment") or {}

            results.append({
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "price_cents": p["price_cents"],
                "currency": p.get("currency", "EUR"),
                "description": p.get("description", ""),
                "category": p.get("category", ""),
                "is_hot": is_hot,
                "locker_compatible": (not is_hot and "elettronica" not in p_cat and "audio" not in p_cat),
                "image_url": p.get("image_url", ""),
                "packaging_type": p.get("packaging_type", "fresh_service"),
                "net_weight_g": p.get("net_weight_g"),
                "dietary_tags": diet_tags,
                "sustainability_origin": sust.get("origin", ""),
                "fulfillment_methods": ful.get("methods", ["pickup"]),
            })

        return results

    # --- CART MANAGEMENT ---

    def create_cart(self) -> dict[str, Any]:
        cart_id = f"cart_{uuid4().hex[:8]}"
        cart = {
            "cart_id": cart_id,
            "created_at": datetime.now().astimezone().isoformat(),
            "items": [],
            "subtotal_cents": 0,
            "delivery_fee_cents": 0,
            "total_cents": 0,
            "fulfillment": None,
            "contains_hot_items": False,
        }
        self._recalculate_cart(cart)
        self._carts[cart_id] = cart
        return cart

    def get_cart(self, cart_id: str) -> Optional[dict[str, Any]]:
        return self._carts.get(cart_id)

    def add_to_cart(self, cart_id: str, product_id: str, quantity: int = 1) -> dict[str, Any]:
        cart = self.get_cart(cart_id)
        if not cart:
            cart = self.create_cart()
            cart_id = cart["cart_id"]

        product = self.get_product(product_id)
        if not product:
            raise ValueError(f"Prodotto con ID '{product_id}' non trovato nel catalogo")

        existing = next((item for item in cart["items"] if item["product_id"] == product_id), None)
        if existing:
            existing["quantity"] += quantity
        else:
            cart["items"].append({
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "price_cents": product["price_cents"],
                "quantity": quantity,
                "is_hot": product["is_hot"],
                "image_url": product.get("image_url", ""),
            })

        self._recalculate_cart(cart)
        return cart

    def update_cart_item(self, cart_id: str, product_id: str, quantity: int) -> dict[str, Any]:
        cart = self.get_cart(cart_id)
        if not cart:
            raise ValueError(f"Carrello '{cart_id}' non trovato")

        if quantity <= 0:
            cart["items"] = [item for item in cart["items"] if item["product_id"] != product_id]
        else:
            for item in cart["items"]:
                if item["product_id"] == product_id:
                    item["quantity"] = quantity
                    break

        self._recalculate_cart(cart)
        return cart

    def _recalculate_cart(self, cart: dict[str, Any]):
        subtotal = sum(item["price_cents"] * item["quantity"] for item in cart["items"])
        cart["subtotal_cents"] = subtotal
        cart["contains_hot_items"] = any(item.get("is_hot", False) for item in cart["items"])

        # Re-evaluate fulfillment options dynamically based on thermal rules
        now = datetime.now().astimezone()
        first_valid_locker = now + timedelta(minutes=35)
        rem = first_valid_locker.minute % 10
        add = (10 - rem) if rem != 0 else 0
        first_valid_locker = (first_valid_locker + timedelta(minutes=add)).replace(second=0, microsecond=0)

        discrete_slots = []
        for i in range(4):
            s_dt = first_valid_locker + timedelta(minutes=i * 10)
            e_dt = s_dt + timedelta(minutes=10)
            slot_tag = s_dt.strftime("%H%M")
            discrete_slots.append({
                "id": f"pickup_locker_{slot_tag}",
                "title": f"Smart Locker Stazione ({s_dt.strftime('%H:%M')} – {e_dt.strftime('%H:%M')})",
                "price_cents": 0,
                "lead_time_minutes": int((s_dt - now).total_seconds() / 60),
                "description": f"Ritiro contactless nello Smart Locker con PIN. Slot {s_dt.strftime('%H:%M')} – {e_dt.strftime('%H:%M')} (Multiplo di 10 min). Solo cibi freddi.",
            })

        avail_opts = [
            {
                "id": "pickup",
                "title": "Ritiro Rapido al Banco Bistrot (Binario 12)",
                "price_cents": 0,
                "lead_time_minutes": 5,
                "description": "Pronto in 5 min al desk express del Bistrot (disponibile per caldi e freddi)",
            }
        ]

        # Smart Locker rule: STRICTLY cold/ambient only
        if not cart["contains_hot_items"]:
            avail_opts.append({
                "id": "pickup_locker",
                "title": f"Smart Locker Stazione (Primo slot: {first_valid_locker.strftime('%H:%M')})",
                "price_cents": 0,
                "lead_time_minutes": int((first_valid_locker - now).total_seconds() / 60),
                "description": "Ritiro contactless nello Smart Locker con PIN (richiede 30 min di preavviso, solo per cibi freddi)",
            })
            avail_opts.extend(discrete_slots)

        avail_opts.append({
            "id": "in_seat_train",
            "title": "Consegna al Posto Treno (Frecciarossa/Italo)",
            "price_cents": TRAIN_DELIVERY_FEE_CENTS,
            "lead_time_minutes": 30,
            "description": "Consegna diretta alla carrozza/posto prima della partenza (+€6.50 supplemento)",
        })

        cart["available_fulfillment_options"] = avail_opts

        # Re-check active fulfillment validity against thermal constraints
        if cart.get("fulfillment"):
            m = cart["fulfillment"].get("method", "")
            if (m == "pickup_locker" or m.startswith("pickup_locker")) and cart["contains_hot_items"]:
                cart["fulfillment"] = None
                cart["delivery_fee_cents"] = 0

        fee = cart["fulfillment"].get("delivery_fee_cents", 0) if cart.get("fulfillment") else 0
        cart["delivery_fee_cents"] = fee
        cart["total_cents"] = subtotal + fee

    def configure_fulfillment(self, cart_id: str, method: str, details: dict[str, Any]) -> dict[str, Any]:
        cart = self.get_cart(cart_id)
        if not cart:
            raise ValueError(f"Carrello '{cart_id}' non trovato")

        if not cart["items"]:
            raise ValueError("Il carrello è vuoto. Aggiungi almeno un articolo prima di configurare la consegna.")

        now = datetime.now().astimezone()

        if method == "pickup_locker" or method.startswith("pickup_locker"):
            if cart["contains_hot_items"]:
                hot_items = [i["name"] for i in cart["items"] if i.get("is_hot")]
                raise ValueError(
                    f"⚠️ Violazione Regola Termica Smart Locker: il carrello contiene bevande o cibi caldi ({', '.join(hot_items)}). "
                    "I locker interrati non sono riscaldati e non possono preservare la temperatura di alimenti espressi. "
                    "Seleziona 'pickup' (Ritiro al banco in 5 min) o 'in_seat_train' (Consegna al binario)."
                )

            slot_time_str = details.get("slot_time", "")
            if not slot_time_str and method.startswith("pickup_locker_"):
                raw_tag = method.replace("pickup_locker_", "")
                if len(raw_tag) == 4 and raw_tag.isdigit():
                    slot_time_str = f"{raw_tag[:2]}:{raw_tag[2:]}"

            if not slot_time_str:
                target = now + timedelta(minutes=35)
                rem = target.minute % 10
                add = (10 - rem) if rem != 0 else 0
                target = (target + timedelta(minutes=add)).replace(second=0, microsecond=0)
                slot_time_str = target.strftime("%H:%M")

            try:
                hour, minute = map(int, slot_time_str.split(":"))
                slot_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if slot_dt < now:
                    slot_dt += timedelta(days=1)
                
                lead_min = int((slot_dt - now).total_seconds() / 60)
                if lead_min < MIN_LEAD_TIME_LOCKER_MINUTES:
                    first_valid = now + timedelta(minutes=35)
                    rem = first_valid.minute % 10
                    add = (10 - rem) if rem != 0 else 0
                    first_valid = (first_valid + timedelta(minutes=add)).replace(second=0, microsecond=0)
                    raise ValueError(
                        f"⚠️ Preavviso insufficiente per Smart Locker ({lead_min} min). È richiesto un preavviso minimo di 30 minuti. "
                        f"Il primo slot consentito è alle {first_valid.strftime('%H:%M')} (oppure scegli 'pickup' pronto in 5 min)."
                    )
            except ValueError as ve:
                if "⚠️" in str(ve):
                    raise ve
                slot_dt = now + timedelta(minutes=35)
                lead_min = 35

            end_hour, end_minute = map(int, slot_time_str.split(":"))
            slot_end_dt = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0) + timedelta(minutes=10)
            slot_end_str = slot_end_dt.strftime("%H:%M")

            cart["fulfillment"] = {
                "method": method,
                "label": f"Smart Locker Contactless ({slot_time_str} – {slot_end_str})",
                "location": "Stazione Milano Centrale - Smart Locker Piano Interrato",
                "box_number": details.get("box_number", "Box #14"),
                "pin_code": details.get("pin_code", "8492"),
                "slot_start": slot_time_str,
                "slot_end": slot_end_str,
                "window": f"{slot_time_str} – {slot_end_str}",
                "earliest_fulfillment_time": slot_dt.isoformat(),
                "latest_fulfillment_time": slot_end_dt.isoformat(),
                "lead_time_minutes": lead_min if 'lead_min' in locals() else 35,
                "delivery_fee_cents": 0,
            }

        elif method == "in_seat_train":
            train_time_str = details.get("delivery_time") or details.get("train_time") or ""
            train_num = details.get("train_number", "Frecciarossa 9540")
            platform = details.get("platform", "Binario 14")
            carriage = details.get("carriage", "Carrozza 4")
            seat = details.get("seat", "12D")

            if train_time_str:
                try:
                    hour, minute = map(int, train_time_str.split(":"))
                    target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target_dt < now:
                        target_dt += timedelta(days=1)
                    lead_min = int((target_dt - now).total_seconds() / 60)
                    if lead_min < MIN_LEAD_TIME_TRAIN_MINUTES:
                        first_valid = now + timedelta(minutes=35)
                        raise ValueError(
                            f"⚠️ Preavviso insufficiente per Consegna al Treno ({lead_min} min). È richiesto un preavviso di almeno 30 minuti. "
                            f"Il primo orario consentito è {first_valid.strftime('%H:%M')} (oppure scegli 'pickup' pronto in 5 min)."
                        )
                except ValueError as ve:
                    if "⚠️" in str(ve):
                        raise ve

            if not train_time_str:
                target_dt = now + timedelta(minutes=35)
                train_time_str = target_dt.strftime("%H:%M")
                lead_min = 35

            cart["fulfillment"] = {
                "method": "in_seat_train",
                "label": f"Consegna a Bordo Treno ({train_num})",
                "train_number": train_num,
                "platform": platform,
                "carriage": carriage,
                "seat": seat,
                "delivery_time": train_time_str,
                "window": f"{train_time_str} – {(datetime.strptime(train_time_str, '%H:%M') + timedelta(minutes=1)).strftime('%H:%M')}",
                "earliest_fulfillment_time": target_dt.isoformat(),
                "latest_fulfillment_time": (target_dt + timedelta(minutes=1)).isoformat(),
                "lead_time_minutes": lead_min,
                "delivery_fee_cents": TRAIN_DELIVERY_FEE_CENTS,
            }

        elif method in ["pickup", "pickup_express"]:
            table = details.get("table_number", "Al Banco Express")
            ready_dt = now + timedelta(minutes=5)
            end_ready_dt = ready_dt + timedelta(minutes=15)
            cart["fulfillment"] = {
                "method": "pickup",
                "label": "Ritiro Rapido al Banco (Bistrot Binario 12)",
                "location": "Bistrot Binario 12",
                "table_number": table,
                "service_time": ready_dt.strftime("%H:%M"),
                "window": f"{ready_dt.strftime('%H:%M')} – {end_ready_dt.strftime('%H:%M')}",
                "earliest_fulfillment_time": ready_dt.isoformat(),
                "latest_fulfillment_time": end_ready_dt.isoformat(),
                "lead_time_minutes": 5,
                "delivery_fee_cents": 0,
            }

        elif method == "table_service":
            table = details.get("table_number", "Tavolo 5")
            ready_dt = now + timedelta(minutes=5)
            end_dt = ready_dt + timedelta(minutes=5)
            cart["fulfillment"] = {
                "method": "table_service",
                "label": f"Servizio al Tavolo ({table}) - Bistrot Binario 12",
                "location": "Bistrot Binario 12",
                "table_number": table,
                "service_time": f"{ready_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}",
                "window": f"{ready_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}",
                "lead_time_minutes": 5,
                "delivery_fee_cents": 0,
            }
        else:
            raise ValueError(f"Metodo di consegna '{method}' sconosciuto. Usa 'pickup' (standard UCP), 'pickup_locker', 'in_seat_train' o 'table_service'.")

        self._recalculate_cart(cart)
        return cart

    def checkout_cart(self, cart_id: str, buyer_name: str = "Viaggiatore", buyer_email: str = "viaggiatore@devfest.example.it", payment_method: str = "gpay", channel_source: str = "web_mcp", channel_label: str = "Demo 2: Web MCP") -> dict[str, Any]:
        cart = self.get_cart(cart_id)
        if not cart:
            raise ValueError(f"Carrello '{cart_id}' non trovato")

        if not cart["items"]:
            raise ValueError("Impossibile effettuare il checkout: il carrello è vuoto.")

        if not cart.get("fulfillment"):
            self.configure_fulfillment(cart_id, "pickup", {"table_number": "Al Banco"})

        fl = cart["fulfillment"]
        now_dt = datetime.now().astimezone()
        today_str = now_dt.strftime("%d/%m/%Y")
        order_id = f"ORD-MI-{uuid4().hex[:5].upper()}"

        placed_display = now_dt.strftime("%d/%m/%Y %H:%M:%S")
        time_part = fl.get("delivery_time") or fl.get("service_time") or fl.get("slot_start")
        if not time_part and fl.get("window") and "min" not in fl.get("window", "").lower():
            time_part = fl.get("window")
        if not time_part:
            lead = fl.get("lead_time_minutes", 5)
            time_part = (now_dt + timedelta(minutes=lead)).strftime("%H:%M")
        req_display = f"{today_str} {time_part}"
        lead_time = fl.get("lead_time_minutes", 10)

        payment_method = payment_method or "gpay"
        if payment_method == "gpay":
            payment_info = {
                "method": "gpay",
                "label": "Google Pay (Wallet Viaggiatore)",
            }
            ap2_verification = None
            is_ap2 = False
        elif payment_method == "card":
            payment_info = {
                "method": "card",
                "label": "Carta di Credito (Visa •••• 4242)",
            }
            ap2_verification = None
            is_ap2 = False
        else:
            payment_method = "ap2"
            payment_info = {
                "method": "ap2",
                "label": "Mandato AP2 Pre-Approvato",
            }
            ap2_verification = {
                "verified": True,
                "mandate_type": "shopper_ap2_delegation",
                "credential_manager": "LocalCredentialManager",
                "token_id": f"tok_ap2_sig_{order_id.lower()}",
            }
            is_ap2 = True

        bopis_order = {
            "order_id": order_id,
            "created_at": now_dt.isoformat(),
            "updated_at": now_dt.isoformat(),
            "placed_at_display": placed_display,
            "requested_delivery_display": req_display,
            "lead_time_minutes": lead_time,
            "channel_source": channel_source,
            "channel_label": channel_label,
            "status": "preparing",
            "fulfillment_type": fl["method"],
            "fulfillment_details": fl,
            "items": [
                {
                    "id": item["product_id"],
                    "title": item["name"],
                    "quantity": item["quantity"],
                    "price_cents": item["price_cents"],
                    "image_url": item.get("image_url"),
                }
                for item in cart["items"]
            ],
            "totals": {
                "subtotal_cents": cart["subtotal_cents"],
                "delivery_fee_cents": cart["delivery_fee_cents"],
                "total_cents": cart["total_cents"],
                "currency": "EUR",
            },
            "buyer": {
                "name": buyer_name,
                "email": buyer_email,
            },
            "payment_method": payment_method,
            "payment_info": payment_info,
            "ap2_verification": ap2_verification,
        }

        bopis_store.record_order(bopis_order)
        logger.info("Ordine %s registrato con successo nel BOPIS Engine con pagamento '%s'!", order_id, payment_method)

        del self._carts[cart_id]

        return {
            "status": "confirmed",
            "order_id": order_id,
            "placed_at": placed_display,
            "requested_delivery": req_display,
            "lead_time_minutes": lead_time,
            "total_cents": bopis_order["totals"]["total_cents"],
            "total_formatted": f"€{bopis_order['totals']['total_cents'] / 100:.2f}",
            "fulfillment": fl,
            "channel": "Station Commerce Engine",
            "payment_method": payment_method,
            "payment_info": payment_info,
            "ap2_mandate_id": (f"tok_ap2_sig_{order_id.lower()}" if is_ap2 else None),
            "ap2_verification": ap2_verification,
            "message": f"Ordine {order_id} confermato con successo ed inviato alla cucina/dispatcher!",
        }


# Singleton instance exported across the entire backend
catalog_service = CatalogService()
# Aliases for backward compatibility
WebMcpStoreService = CatalogService
mcp_store = catalog_service
