# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Retail Store logic for Milano Centrale Travel Retail (UCP)."""

from datetime import datetime, timezone, timedelta, time
from decimal import Decimal
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import AnyUrl

from ucp_sdk.models.schemas.shopping.checkout_resp import (
    CheckoutResponse as Checkout,
)
from ucp_sdk.models.schemas.shopping.fulfillment_resp import (
    Checkout as FulfillmentCheckout,
)
from ucp_sdk.models.schemas.shopping.fulfillment_resp import Fulfillment
from ucp_sdk.models.schemas.shopping.payment_resp import PaymentResponse
from ucp_sdk.models.schemas.shopping.types.buyer import Buyer
from ucp_sdk.models.schemas.shopping.types.fulfillment_destination_resp import (
    FulfillmentDestinationResponse,
)
from ucp_sdk.models.schemas.shopping.types.fulfillment_group_resp import (
    FulfillmentGroupResponse,
)
from ucp_sdk.models.schemas.shopping.types.fulfillment_method_resp import (
    FulfillmentMethodResponse,
)
from ucp_sdk.models.schemas.shopping.types.fulfillment_option_resp import (
    FulfillmentOptionResponse,
)
from ucp_sdk.models.schemas.shopping.types.fulfillment_resp import (
    FulfillmentResponse,
)
from ucp_sdk.models.schemas.shopping.types.item_resp import ItemResponse as Item
from ucp_sdk.models.schemas.shopping.types.line_item_resp import (
    LineItemResponse as LineItem,
)
from ucp_sdk.models.schemas.shopping.types.order_confirmation import (
    OrderConfirmation,
)
from ucp_sdk.models.schemas.shopping.types.postal_address import PostalAddress
from ucp_sdk.models.schemas.shopping.types.shipping_destination_resp import (
    ShippingDestinationResponse,
)
from ucp_sdk.models.schemas.shopping.types.total_resp import (
    TotalResponse as Total,
)
from ucp_sdk.models.schemas.ucp import ResponseCheckout as UcpMetadata

from .helpers import get_checkout_type
from .models.product_types import ImageObject, Product, ProductResults
from .bopis_store import bopis_store


DEFAULT_CURRENCY = "EUR"
TRAIN_DELIVERY_FEE_CENTS = 650  # €6.50
MIN_LEAD_TIME_LOCKER_MINUTES = 30
MIN_LEAD_TIME_TRAIN_MINUTES = 30


def parse_time_or_now(time_str: str | None, default_offset_minutes: int = 35) -> datetime:
    """Parse time string (HH:MM or ISO) relative to local station time."""
    now = datetime.now().astimezone()
    if not time_str:
        return now + timedelta(minutes=default_offset_minutes)
    time_str = time_str.strip()
    if "T" in time_str:
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
            return dt
        except Exception:
            pass
    try:
        parts = [int(p) for p in time_str.split(":")]
        t = time(hour=parts[0], minute=parts[1], second=parts[2] if len(parts) > 2 else 0)
        dt = now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)
        if (dt - now).total_seconds() < -12 * 3600:
            dt += timedelta(days=1)
        return dt
    except Exception:
        return now + timedelta(minutes=default_offset_minutes)


def get_next_10_min_boundary(dt: datetime, min_lead_minutes: int = 30) -> datetime:
    """Align forward to the next multiple of 10 minutes (:00, :10, :20, :30, :40, :50) with min lead time."""
    target = dt + timedelta(minutes=min_lead_minutes)
    remainder = target.minute % 10
    add_mins = (10 - remainder) if remainder != 0 else 0
    return target.replace(second=0, microsecond=0) + timedelta(minutes=add_mins)


def get_next_5_min_boundary(dt: datetime, min_lead_minutes: int = 3) -> datetime:
    """Align forward to the next multiple of 5 minutes (:00, :05, :10, etc.)."""
    target = dt + timedelta(minutes=min_lead_minutes)
    remainder = target.minute % 5
    add_mins = (5 - remainder) if remainder != 0 else 0
    return target.replace(second=0, microsecond=0) + timedelta(minutes=add_mins)


def generate_locker_slots(count: int = 6) -> list[dict[str, str]]:
    """Generate smart locker slots starting strictly at multiples of 10 minutes with at least 30 min advance notice."""
    now = datetime.now().astimezone()
    start = get_next_10_min_boundary(now, min_lead_minutes=MIN_LEAD_TIME_LOCKER_MINUTES)
    slots = []
    for i in range(count):
        s_start = start + timedelta(minutes=i * 10)
        s_end = s_start + timedelta(minutes=10)
        slots.append({
            "start": s_start.strftime("%H:%M"),
            "end": s_end.strftime("%H:%M"),
            "iso_start": s_start.isoformat(),
            "iso_end": s_end.isoformat(),
        })
    return slots


def generate_table_slots(count: int = 6) -> list[dict[str, str]]:
    """Generate table/express slots with 5-minute intervals (express, ready in 5 min)."""
    now = datetime.now().astimezone()
    start = get_next_5_min_boundary(now, min_lead_minutes=3)
    slots = []
    for i in range(count):
        s_start = start + timedelta(minutes=i * 5)
        s_end = s_start + timedelta(minutes=5)
        slots.append({
            "start": s_start.strftime("%H:%M"),
            "end": s_end.strftime("%H:%M"),
            "iso_start": s_start.isoformat(),
            "iso_end": s_end.isoformat(),
        })
    return slots


class RetailStore:
    """Mock Retail Store for Milano Centrale Travel Retail demo."""

    def __init__(self):
        self._products: dict[str, Product] = {}
        self._checkouts: dict[str, Checkout] = {}
        self._orders: dict[str, Checkout] = {}
        self._checkout_fulfillment_details: dict[str, dict] = {}
        self._initialize_ucp_metadata()
        self._initialize_products()

    def _initialize_ucp_metadata(self):
        """Load UCP metadata from data/ucp.json."""
        base_path = Path(__file__).parent
        ucp_path = base_path / "data" / "ucp.json"
        with ucp_path.open("r", encoding="utf-8") as f:
            self._ucp_metadata = json.load(f)

    def _initialize_products(self):
        """Load products from data/products.json."""
        base_path = Path(__file__).parent
        products_path = base_path / "data" / "products.json"
        with products_path.open("r", encoding="utf-8") as f:
            products_data = json.load(f)
            for product_data in products_data:
                product = Product.model_validate(product_data)
                self._products[product.product_id] = product

    def search_products(self, query: str) -> ProductResults:
        """Search catalog for products matching query."""
        all_products = list(self._products.values())
        if not query or query.strip() == "" or query.lower() in ["all", "tutti", "menu", "catalogo"]:
            return ProductResults(results=all_products)

        matching_products = {}
        keywords = query.lower().split()
        for keyword in keywords:
            for product in all_products:
                desc = product.description.lower() if product.description else ""
                cat = product.category.lower() if product.category else ""
                name = product.name.lower()
                if product.product_id not in matching_products and (
                    keyword in name or keyword in cat or keyword in desc
                ):
                    matching_products[product.product_id] = product

        product_list = list(matching_products.values())
        if not product_list:
            return ProductResults(results=[], content=f"Nessun prodotto trovato per: '{query}'. Prova a cercare 'caffè', 'panino' o 'powerbank'.")

        return ProductResults(results=product_list)

    def get_product(self, product_id: str) -> Product | None:
        """Retrieve a product by its SKU/ID."""
        return self._products.get(product_id)

    def is_hot_product(self, product: Product | None) -> bool:
        """Check if product is hot (not allowed in Smart Locker)."""
        if not product:
            return False
        if product.additional_property:
            props = (
                product.additional_property
                if isinstance(product.additional_property, list)
                else [product.additional_property]
            )
            for p in props:
                if p.name == "temperature" and p.value.lower() == "hot":
                    return True
        name_lower = product.name.lower()
        return any(k in name_lower for k in ["caldo", "calda", "espresso", "cappuccino", "toast"])

    def cart_has_hot_items(self, checkout: Checkout) -> bool:
        """Check if checkout contains any hot item."""
        for line_item in checkout.line_items:
            product = self.get_product(line_item.item.id)
            if self.is_hot_product(product):
                return True
        return False

    def _get_line_item(self, product: Product, quantity: int) -> LineItem:
        if not product.offers or not product.offers.price:
            raise ValueError(f"Product {product.name} does not have a price.")

        unit_price = int(Decimal(product.offers.price) * 100)
        image_url = None

        if isinstance(product.image, list) and product.image:
            first_image = product.image[0]
            if isinstance(first_image, str):
                image_url = first_image
            elif isinstance(first_image, ImageObject):
                image_url = first_image.url
        elif isinstance(product.image, str):
            image_url = product.image

        return LineItem(
            id=uuid4().hex,
            item=Item(
                id=product.product_id,
                price=unit_price,
                title=product.name,
                image_url=AnyUrl(image_url) if image_url else None,
            ),
            quantity=quantity,
            totals=[],
        )

    def add_to_checkout(
        self,
        metadata: UcpMetadata,
        product_id: str,
        quantity: int,
        checkout_id: str | None = None,
    ) -> Checkout:
        product = self.get_product(product_id)
        if not product:
            raise ValueError(f"Prodotto con ID {product_id} non trovato nel catalogo")

        if not checkout_id:
            checkout_id = str(uuid4())
            checkout_type = get_checkout_type(metadata)
            checkout = checkout_type(
                id=checkout_id,
                ucp=metadata,
                line_items=[],
                currency=DEFAULT_CURRENCY,
                totals=[],
                status="incomplete",
                links=[],
                payment=PaymentResponse(
                    handlers=self._ucp_metadata["payment"]["handlers"]
                ),
            )
        else:
            checkout = self._checkouts.get(checkout_id)
            if not checkout:
                raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        found = False
        for line_item in checkout.line_items:
            if line_item.item.id == product_id:
                line_item.quantity += quantity
                found = True
                break
        if not found:
            order_item = self._get_line_item(product, quantity)
            checkout.line_items.append(order_item)

        # Initialize or refresh fulfillment options when cart items change
        if isinstance(checkout, FulfillmentCheckout):
            self._update_fulfillment_structure(checkout)

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def get_checkout(self, checkout_id: str) -> Checkout | None:
        return self._checkouts.get(checkout_id)

    def remove_from_checkout(self, checkout_id: str, product_id: str) -> Checkout:
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        for line_item in checkout.line_items:
            if line_item.item.id == product_id:
                checkout.line_items.remove(line_item)
                break

        if isinstance(checkout, FulfillmentCheckout):
            self._update_fulfillment_structure(checkout)

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def update_checkout(
        self, checkout_id: str, product_id: str, quantity: int
    ) -> Checkout:
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        for line_item in checkout.line_items:
            if line_item.item.id == product_id:
                line_item.quantity = quantity
                break

        if isinstance(checkout, FulfillmentCheckout):
            self._update_fulfillment_structure(checkout)

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def _recalculate_checkout(self, checkout: Checkout) -> None:
        checkout.status = "incomplete"
        items_base_amount = 0
        items_discount = 0

        for line_item in checkout.line_items:
            item = line_item.item
            unit_price = item.price
            base_amount = unit_price * line_item.quantity
            discount = 0
            line_item.totals = [
                Total(type="items_discount", display_text="Sconto", amount=discount),
                Total(type="subtotal", display_text="Subtotale", amount=base_amount - discount),
                Total(type="total", display_text="Totale", amount=base_amount - discount),
            ]
            items_base_amount += base_amount
            items_discount += discount

        subtotal = items_base_amount - items_discount
        discount = 0

        totals = [
            Total(type="items_discount", display_text="Sconto Articoli", amount=items_discount),
            Total(type="subtotal", display_text="Subtotale Prodotti", amount=subtotal),
            Total(type="discount", display_text="Sconto Promozione", amount=discount),
        ]

        final_total = subtotal - discount

        if isinstance(checkout, FulfillmentCheckout) and checkout.fulfillment:
            tax = round(subtotal * 0.10)  # IVA 10% ristorazione / bar
            selected_option = self._get_selected_fulfillment_option(checkout)

            shipping_fee = 0
            if selected_option:
                for total in selected_option.totals:
                    if total.type == "total":
                        shipping_fee = total.amount
                        break

            totals.append(
                Total(
                    type="fulfillment",
                    display_text=selected_option.title if selected_option else "Fulfillment",
                    amount=shipping_fee,
                )
            )
            totals.append(Total(type="tax", display_text="IVA (10%)", amount=tax))
            final_total += shipping_fee + tax

        totals.append(Total(type="total", display_text="Totale Ordine", amount=final_total))
        checkout.totals = totals
        checkout.continue_url = AnyUrl(f"https://milano-centrale.ucp.dev/checkout?id={checkout.id}")

    def _get_selected_fulfillment_option(self, checkout: FulfillmentCheckout) -> FulfillmentOptionResponse | None:
        if checkout.fulfillment and checkout.fulfillment.root.methods:
            for method in checkout.fulfillment.root.methods:
                if method.groups:
                    for group in method.groups:
                        if group.selected_option_id:
                            for option in group.options or []:
                                if option.id == group.selected_option_id:
                                    return option
        return None

    def get_available_slots(self, option_id: str = "all") -> dict[str, list[dict[str, str]]]:
        """Return available time slots for fulfillment options."""
        result = {}
        if option_id in ["all", "pickup_locker", "locker"]:
            result["pickup_locker"] = generate_locker_slots(count=6)
        if option_id in ["all", "pickup_express", "table", "bistrot"]:
            result["pickup_express"] = generate_table_slots(count=6)
        return result

    def _get_fulfillment_options(self, checkout: Checkout) -> list[FulfillmentOptionResponse]:
        """Generate dynamic fulfillment options for Milano Centrale Travel Retail."""
        has_hot = self.cart_has_hot_items(checkout)
        now = datetime.now().astimezone()
        details = self._checkout_fulfillment_details.get(checkout.id, {})

        # 1. Ritiro o Servizio al Tavolo (Binario 12) - Finestra 5 minuti
        table_start = details.get("table_earliest") or get_next_5_min_boundary(now, min_lead_minutes=3)
        table_end = details.get("table_latest") or (table_start + timedelta(minutes=5))
        table_num = details.get("table_number")
        is_counter = False
        if table_num:
            t_lower = table_num.lower()
            is_counter = "banco" in t_lower or "bancone" in t_lower

        if table_num:
            if is_counter:
                table_title = "Ritiro al Banco (Bistrot Binario 12)"
                table_desc = f"Ritiro al banco confermato ({table_num}) per le {table_start.strftime('%H:%M')} - {table_end.strftime('%H:%M')} (Finestra 5 min). Bistrot Binario 12."
            else:
                table_title = f"Servizio al Tavolo ({table_num}) (Bistrot Binario 12)"
                table_desc = f"Servizio al tavolo confermato ({table_num}) per le {table_start.strftime('%H:%M')} - {table_end.strftime('%H:%M')} (Finestra 5 min). Bistrot Binario 12."
        else:
            table_title = "Ritiro al Banco / Servizio al Tavolo (Bistrot Binario 12)"
            table_desc = f"Finestra di 5 minuti ({table_start.strftime('%H:%M')} - {table_end.strftime('%H:%M')}). Nessun preavviso richiesto (pronto in 5 min). Ritiro express al banco o al tavolo. Gratuito."

        options: list[FulfillmentOptionResponse] = [
            FulfillmentOptionResponse(
                id="pickup_express",
                title=table_title,
                description=table_desc,
                carrier="Milano Centrale Bistrot",
                earliest_fulfillment_time=table_start,
                latest_fulfillment_time=table_end,
                totals=[
                    Total(type="subtotal", display_text="Subtotale", amount=0),
                    Total(type="tax", display_text="IVA", amount=0),
                    Total(type="total", display_text="Totale Consegna", amount=0),
                ],
            )
        ]

        # 2. Smart Locker rule: STRICTLY cold/ambient only, intervals at 10-minute multiples, min 30 min notice
        if not has_hot:
            pin_code = details.get("pin_code", "8492")
            if details.get("locker_slot_confirmed"):
                locker_start = details.get("locker_earliest") or get_next_10_min_boundary(now, min_lead_minutes=MIN_LEAD_TIME_LOCKER_MINUTES)
                locker_end = details.get("locker_latest") or (locker_start + timedelta(minutes=10))
                opt_id = details.get("option_id", "pickup_locker")
                if not opt_id.startswith("pickup_locker"):
                    opt_id = "pickup_locker"
                locker_desc = f"Slot confermato: {locker_start.strftime('%H:%M')} - {locker_end.strftime('%H:%M')} (Multiplo di 10 min). PIN sblocco: {pin_code}. Smart Locker Piano Interrato."
                options.append(
                    FulfillmentOptionResponse(
                        id=opt_id,
                        title=f"Smart Locker ({locker_start.strftime('%H:%M')} - {locker_end.strftime('%H:%M')})",
                        description=locker_desc,
                        carrier="Locker Milano Centrale",
                        earliest_fulfillment_time=locker_start,
                        latest_fulfillment_time=locker_end,
                        totals=[
                            Total(type="subtotal", display_text="Subtotale", amount=0),
                            Total(type="tax", display_text="IVA", amount=0),
                            Total(type="total", display_text="Totale Consegna", amount=0),
                        ],
                    )
                )
            else:
                base_locker = get_next_10_min_boundary(now, min_lead_minutes=MIN_LEAD_TIME_LOCKER_MINUTES)
                options.append(
                    FulfillmentOptionResponse(
                        id="pickup_locker",
                        title="Smart Locker Refrigerato (Piazza Duca d'Aosta)",
                        description=(
                            f"Ritiro contactless nello Smart Locker con PIN. Slot di 10 min a partire dalle "
                            f"{base_locker.strftime('%H:%M')}. Preavviso min. 30 min. Solo cibi freddi e tech. Gratuito."
                        ),
                        carrier="Locker Milano Centrale",
                        earliest_fulfillment_time=base_locker,
                        latest_fulfillment_time=base_locker + timedelta(minutes=10),
                        totals=[
                            Total(type="subtotal", display_text="Subtotale", amount=0),
                            Total(type="tax", display_text="IVA", amount=0),
                            Total(type="total", display_text="Totale Consegna", amount=0),
                        ],
                    )
                )

        # 3. In-Seat Train Delivery rule: 1 min wait window, €6.50 fee, min 30 min notice
        train_start = details.get("train_earliest") or get_next_5_min_boundary(now, min_lead_minutes=MIN_LEAD_TIME_TRAIN_MINUTES)
        train_end = details.get("train_latest") or (train_start + timedelta(minutes=1))  # 1 MINUTE WAIT!
        if details.get("train_confirmed"):
            t_name = details.get("train_number", "Frecciarossa 9540")
            raw_carr = details.get("carriage", "4")
            carr_clean = raw_carr.replace("Carrozza", "").replace("carrozza", "").strip() or raw_carr
            t_seat = details.get("seat", "12D")
            t_plat = details.get("platform", "Binario 14")
            train_desc = (
                f"Consegna confermata per le {train_start.strftime('%H:%M')} "
                f"(Finestra {train_start.strftime('%H:%M')} - {train_end.strftime('%H:%M')}, attesa max 1 min). "
                f"Treno {t_name}, Carrozza {carr_clean}, Posto {t_seat} ({t_plat})."
            )
        else:
            train_desc = (
                f"Consegna a bordo treno diretta a carrozza e posto. Finestra di precisione: max 1 minuto di attesa "
                f"durante la sosta ({train_start.strftime('%H:%M')} - {train_end.strftime('%H:%M')}). "
                f"Preavviso min. 30 min. Richiede Treno, Carrozza, Posto e Binario. Supplemento €6.50."
            )

        options.append(
            FulfillmentOptionResponse(
                id="in_seat_train",
                title="Consegna al Posto Treno (Frecciarossa / Italo / Binario)",
                description=train_desc,
                carrier="FrecciaDelivery Centrale",
                earliest_fulfillment_time=train_start,
                latest_fulfillment_time=train_end,
                totals=[
                    Total(type="subtotal", display_text="Subtotale", amount=TRAIN_DELIVERY_FEE_CENTS),
                    Total(type="tax", display_text="IVA", amount=0),
                    Total(type="total", display_text="Totale Consegna", amount=TRAIN_DELIVERY_FEE_CENTS),
                ],
            )
        )

        return options

    def _update_fulfillment_structure(self, checkout: FulfillmentCheckout):
        """Update fulfillment options and preserve or adjust selected option."""
        options = self._get_fulfillment_options(checkout)
        available_ids = [opt.id for opt in options]

        # Get existing selected option id from details or current group
        details = self._checkout_fulfillment_details.get(checkout.id, {})
        current_selected = details.get("option_id")
        if not current_selected and checkout.fulfillment and checkout.fulfillment.root.methods:
            for method in checkout.fulfillment.root.methods:
                if method.groups:
                    for group in method.groups:
                        current_selected = group.selected_option_id

        # If current option is no longer available (e.g. hot item added while locker was selected)
        if not current_selected or current_selected not in available_ids:
            selected_id = options[0].id
        else:
            selected_id = current_selected

        line_item_ids = [li.id for li in checkout.line_items]

        dest_id = "dest_milano_centrale"
        if (
            checkout.fulfillment
            and checkout.fulfillment.root.methods
            and checkout.fulfillment.root.methods[0].destinations
        ):
            dest_id = checkout.fulfillment.root.methods[0].destinations[0].root.id
            destination = checkout.fulfillment.root.methods[0].destinations[0]
        else:
            destination = FulfillmentDestinationResponse(
                root=ShippingDestinationResponse(
                    id=dest_id,
                    street_address="Piazza Duca d'Aosta 1 - Stazione Centrale",
                    address_locality="Milano",
                    address_region="MI",
                    postal_code="20124",
                    address_country="IT",
                )
            )

        group = FulfillmentGroupResponse(
            id=f"group_{uuid4().hex[:8]}",
            line_item_ids=line_item_ids,
            options=options,
            selected_option_id=selected_id,
        )

        method = FulfillmentMethodResponse(
            id=f"method_{uuid4().hex[:8]}",
            type="pickup" if selected_id != "in_seat_train" else "shipping",
            line_item_ids=line_item_ids,
            destinations=[destination],
            selected_destination_id=dest_id,
            groups=[group],
        )

        checkout.fulfillment = Fulfillment(root=FulfillmentResponse(methods=[method]))

    def add_delivery_address(
        self, checkout_id: str, address: PostalAddress
    ) -> Checkout:
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        if isinstance(checkout, FulfillmentCheckout):
            dest_id = f"dest_{uuid4().hex[:8]}"
            destination = FulfillmentDestinationResponse(
                root=ShippingDestinationResponse(id=dest_id, **address.model_dump())
            )

            fulfillment_options = self._get_fulfillment_options(checkout)
            details = self._checkout_fulfillment_details.get(checkout_id, {})
            selected_option_id = details.get("option_id") or fulfillment_options[0].id

            line_item_ids = [li.id for li in checkout.line_items]

            group = FulfillmentGroupResponse(
                id=f"package_{uuid4().hex[:8]}",
                line_item_ids=line_item_ids,
                options=fulfillment_options,
                selected_option_id=selected_option_id,
            )

            method = FulfillmentMethodResponse(
                id=f"method_{uuid4().hex[:8]}",
                type="shipping" if selected_option_id == "in_seat_train" else "pickup",
                line_item_ids=line_item_ids,
                destinations=[destination],
                selected_destination_id=dest_id,
                groups=[group],
            )

            checkout.fulfillment = Fulfillment(
                root=FulfillmentResponse(methods=[method])
            )

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def select_fulfillment_option(
        self,
        checkout_id: str,
        option_id: str,
        slot_time: str | None = None,
    ) -> Checkout:
        """Select a specific fulfillment option (pickup_express, pickup_locker, in_seat_train)."""
        checkout = self.get_checkout(checkout_id)
        if not checkout or not isinstance(checkout, FulfillmentCheckout):
            raise ValueError(f"Checkout con ID {checkout_id} non trovato o senza supporto fulfillment")

        is_locker = option_id == "pickup_locker" or option_id.startswith("pickup_locker")
        if is_locker and self.cart_has_hot_items(checkout):
            raise ValueError(
                "I prodotti caldi (come espresso o toast) non possono essere inseriti nello Smart Locker. "
                "Seleziona 'Ritiro / Servizio al Tavolo' (5 min) o 'Consegna al Posto Treno' (1 min)."
            )

        if not slot_time and option_id.startswith("pickup_locker_"):
            raw_tag = option_id.replace("pickup_locker_", "")
            if len(raw_tag) == 4 and raw_tag.isdigit():
                slot_time = f"{raw_tag[:2]}:{raw_tag[2:]}"

        if slot_time:
            if is_locker:
                return self.set_locker_pickup(checkout_id, slot_time=slot_time)
            elif option_id in ["pickup", "pickup_express"]:
                return self.set_table_service(checkout_id, service_time=slot_time)
            elif option_id == "in_seat_train":
                return self.set_train_delivery(
                    checkout_id,
                    train_number="Frecciarossa 9540",
                    carriage="Carrozza 4",
                    seat="12D",
                    delivery_time=slot_time,
                )

        details = self._checkout_fulfillment_details.setdefault(checkout_id, {})
        details["option_id"] = option_id

        if checkout.fulfillment and checkout.fulfillment.root.methods:
            self._update_fulfillment_structure(checkout)

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def set_train_delivery(
        self,
        checkout_id: str,
        train_number: str,
        carriage: str,
        seat: str,
        delivery_time: str | None = None,
        platform: str | None = None,
        passenger_name: str = "Passeggero",
        email: str = "viaggiatore@trenitalia.example.it",
    ) -> Checkout:
        """Configure in-seat train delivery with 1-minute courier wait window."""
        checkout = self.get_checkout(checkout_id)
        if not checkout:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        now = datetime.now().astimezone()
        if delivery_time:
            earliest = parse_time_or_now(delivery_time, default_offset_minutes=35)
            lead_minutes = (earliest - now).total_seconds() / 60
            if lead_minutes < 25:
                raise ValueError(
                    f"Per la consegna a bordo treno/binario è richiesto un preavviso minimo di almeno 30 minuti "
                    f"(l'orario indicato {earliest.strftime('%H:%M')} concede solo {max(0, int(lead_minutes))} min di preavviso). "
                    f"Per chi ha fretta o parte a breve, seleziona 'Ritiro Express al Banco' (pronto in 5 min)."
                )
        else:
            earliest = get_next_5_min_boundary(now, min_lead_minutes=MIN_LEAD_TIME_TRAIN_MINUTES)
        latest = earliest + timedelta(minutes=1)  # EXACT 1-MINUTE COURIER WAIT!

        carr_str = (carriage or "4").strip()
        carr_clean = carr_str.replace("Carrozza", "").replace("carrozza", "").strip() or carr_str
        plat_str = platform or "Binario 14"
        details = self._checkout_fulfillment_details.setdefault(checkout_id, {})
        details.update({
            "option_id": "in_seat_train",
            "train_confirmed": True,
            "locker_slot_confirmed": False,
            "table_confirmed": False,
            "train_number": train_number,
            "carriage": carr_clean,
            "seat": seat,
            "platform": plat_str,
            "train_earliest": earliest,
            "train_latest": latest,
        })

        address = PostalAddress(
            street_address=f"Stazione Milano Centrale, Treno {train_number} ({plat_str})",
            extended_address=f"Carrozza {carr_clean}, Posto {seat} (Orario consegna: {earliest.strftime('%H:%M')}, attesa max 1 min)",
            address_locality="Milano",
            address_region="MI",
            postal_code="20124",
            address_country="IT",
            first_name=passenger_name,
            last_name="",
        )

        checkout = self.add_delivery_address(checkout_id, address)
        checkout.buyer = Buyer(email=email)
        self.select_fulfillment_option(checkout_id, "in_seat_train")
        return checkout

    def set_table_service(
        self,
        checkout_id: str,
        table_number: str = "Al Banco",
        service_time: str | None = None,
        customer_name: str = "Cliente Bistrot",
        email: str = "cliente@devfest.example.it",
    ) -> Checkout:
        """Configure table service / express pickup with 5-minute interval."""
        checkout = self.get_checkout(checkout_id)
        if not checkout:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        if service_time:
            earliest = parse_time_or_now(service_time, default_offset_minutes=5)
        else:
            earliest = get_next_5_min_boundary(datetime.now().astimezone(), min_lead_minutes=3)
        latest = earliest + timedelta(minutes=5)  # 5-MINUTE WINDOW!

        t_clean = (table_number or "").strip()
        t_lower = t_clean.lower()
        if not t_clean or "banco" in t_lower or "bancone" in t_lower:
            table_str = "Al Banco"
            is_counter = True
        elif t_lower.startswith("tavolo"):
            parts = t_clean.split()
            table_str = f"Tavolo {parts[1]}" if len(parts) > 1 else t_clean.title()
            is_counter = False
        else:
            table_str = f"Tavolo {t_clean}"
            is_counter = False

        details = self._checkout_fulfillment_details.setdefault(checkout_id, {})
        details.update({
            "option_id": "pickup_express",
            "table_confirmed": True,
            "train_confirmed": False,
            "locker_slot_confirmed": False,
            "table_number": table_str,
            "is_counter": is_counter,
            "table_earliest": earliest,
            "table_latest": latest,
        })

        service_label = "Ritiro al Banco" if is_counter else "Servizio al Tavolo"
        address = PostalAddress(
            street_address="Stazione Milano Centrale, Bistrot Binario 12",
            extended_address=f"{table_str} ({service_label}: {earliest.strftime('%H:%M')} - {latest.strftime('%H:%M')}, finestra 5 min)",
            address_locality="Milano",
            address_region="MI",
            postal_code="20124",
            address_country="IT",
            first_name=customer_name,
            last_name="",
        )

        checkout = self.add_delivery_address(checkout_id, address)
        checkout.buyer = Buyer(email=email)
        self.select_fulfillment_option(checkout_id, "pickup_express")
        return checkout

    def set_locker_pickup(
        self,
        checkout_id: str,
        slot_time: str | None = None,
        pin_code: str = "8492",
        customer_name: str = "Cliente Locker",
        email: str = "cliente@devfest.example.it",
    ) -> Checkout:
        """Configure Smart Locker pickup strictly at multiples of 10 minutes with 10-minute window and at least 30 min notice."""
        checkout = self.get_checkout(checkout_id)
        if not checkout:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        if self.cart_has_hot_items(checkout):
            raise ValueError(
                "I prodotti caldi (come espresso o toast) non possono essere inseriti nello Smart Locker. "
                "Seleziona 'Ritiro / Servizio al Tavolo' (5 min) o 'Consegna al Posto Treno' (1 min)."
            )

        now = datetime.now().astimezone()
        if slot_time:
            dt = parse_time_or_now(slot_time, default_offset_minutes=35)
            # Align to 10-minute multiple
            remainder = dt.minute % 10
            if remainder != 0:
                dt = dt.replace(second=0, microsecond=0) + timedelta(minutes=(10 - remainder))
            earliest = dt
            lead_minutes = (earliest - now).total_seconds() / 60
            if lead_minutes < 25:
                raise ValueError(
                    f"Per il ritiro nello Smart Locker è richiesto un preavviso minimo di almeno 30 minuti "
                    f"(lo slot {dt.strftime('%H:%M')} concede solo {max(0, int(lead_minutes))} min di preavviso). "
                    f"Seleziona uno slot successivo oppure scegli 'Ritiro Express al Banco' (pronto in 5 min)."
                )
        else:
            earliest = get_next_10_min_boundary(now, min_lead_minutes=MIN_LEAD_TIME_LOCKER_MINUTES)
        latest = earliest + timedelta(minutes=10)  # 10-MINUTE WINDOW!

        details = self._checkout_fulfillment_details.setdefault(checkout_id, {})
        details.update({
            "option_id": "pickup_locker",
            "locker_slot_confirmed": True,
            "train_confirmed": False,
            "table_confirmed": False,
            "pin_code": pin_code,
            "locker_earliest": earliest,
            "locker_latest": latest,
        })

        address = PostalAddress(
            street_address="Stazione Milano Centrale, Smart Locker Piano Interrato",
            extended_address=f"Box Locker #14 (Slot ritiro: {earliest.strftime('%H:%M')} - {latest.strftime('%H:%M')}, PIN: {pin_code})",
            address_locality="Milano",
            address_region="MI",
            postal_code="20124",
            address_country="IT",
            first_name=customer_name,
            last_name="",
        )

        checkout = self.add_delivery_address(checkout_id, address)
        checkout.buyer = Buyer(email=email)
        self.select_fulfillment_option(checkout_id, "pickup_locker")
        return checkout

    def start_payment(self, checkout_id: str) -> Checkout | str:
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        if checkout.status == "ready_for_complete":
            return checkout

        messages = []
        if checkout.buyer is None:
            messages.append("Fornisci un indirizzo email per il buyer")

        if isinstance(checkout, FulfillmentCheckout) and checkout.fulfillment is None:
            messages.append("Fornisci i dettagli per il ritiro o la consegna al treno")

        if messages:
            return "\n".join(messages)

        self._recalculate_checkout(checkout)
        checkout.status = "ready_for_complete"
        self._checkouts[checkout_id] = checkout
        return checkout

    def place_order(self, checkout_id: str, channel_source: str = "ucp_direct_a2a") -> Checkout:
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout con ID {checkout_id} non trovato")

        order_id = f"ORD-MI-{uuid4().hex[:6].upper()}"

        checkout.status = "completed"
        checkout.order = OrderConfirmation(
            id=order_id,
            permalink_url=f"https://milano-centrale.ucp.dev/orders/{order_id}",
        )

        self._orders[order_id] = checkout

        # Record into BOPIS Dispatcher Store
        details = self._checkout_fulfillment_details.get(checkout_id, {})
        opt_id = details.get("option_id", "pickup_express")

        total_cents = 0
        subtotal_cents = 0
        delivery_fee_cents = 0
        if checkout.totals:
            for t in checkout.totals:
                if t.type == "total":
                    total_cents = t.amount
                elif t.type == "subtotal":
                    subtotal_cents = t.amount
                elif t.type == "shipping":
                    delivery_fee_cents = t.amount

        if opt_id == "in_seat_train":
            fl_details = {
                "train_number": details.get("train_number", "Frecciarossa 9540"),
                "platform": details.get("platform", "Binario 14"),
                "carriage": details.get("carriage", "Carrozza 4"),
                "seat": details.get("seat", "12D"),
                "delivery_time": details.get("train_delivery_time").strftime("%H:%M") if details.get("train_delivery_time") else "In orario",
                "window": f"{details.get('train_earliest').strftime('%H:%M')} - {details.get('train_latest').strftime('%H:%M')}" if details.get("train_earliest") else "Finestra 1 min",
                "delivery_fee_cents": TRAIN_DELIVERY_FEE_CENTS,
                "passenger_name": details.get("passenger_name", "Passeggero Treno"),
            }
        elif opt_id == "pickup_locker":
            fl_details = {
                "location": "Smart Locker Piano Interrato",
                "box_number": "Box #14",
                "pin_code": details.get("pin_code", "8492"),
                "slot_start": details.get("locker_earliest").strftime("%H:%M") if details.get("locker_earliest") else "",
                "slot_end": details.get("locker_latest").strftime("%H:%M") if details.get("locker_latest") else "",
                "delivery_fee_cents": 0,
            }
        else:
            fl_details = {
                "location": "Bistrot Binario 12",
                "table_number": details.get("table_number", "Al Banco"),
                "service_time": details.get("table_earliest").strftime("%H:%M") if details.get("table_earliest") else "Immediato (5 min)",
                "window": "Finestra 5 min",
                "delivery_fee_cents": 0,
            }

        items = []
        for line in checkout.line_items:
            items.append({
                "id": line.item.id,
                "title": line.item.title,
                "quantity": line.quantity,
                "price_cents": line.item.price,
                "image_url": str(line.item.image_url) if line.item.image_url else None,
            })

        channel_labels = {
            "ucp_direct_a2a": "Demo 1: UCP Direct A2A",
            "web_mcp": "Demo 2: Web MCP",
            "two_agent_a2a": "Demo 3: Two-Agent A2A M2M",
            "ucp_rest": "Demo 4: UCP REST Binding",
        }

        now_dt = datetime.now().astimezone()
        placed_datetime_display = now_dt.strftime("%d/%m/%Y %H:%M:%S")

        req_delivery_display = ""
        lead_mins = 0

        if opt_id == "in_seat_train":
            target_dt = details.get("train_earliest") or details.get("train_delivery_time")
            if target_dt:
                req_delivery_display = target_dt.strftime('%d/%m/%Y %H:%M')
                lead_mins = max(0, int((target_dt - now_dt).total_seconds() / 60))
            else:
                req_delivery_display = f"{now_dt.strftime('%d/%m/%Y')} {fl_details.get('window', 'In orario')}"
        elif opt_id == "pickup_locker":
            target_dt = details.get("locker_earliest")
            if target_dt:
                req_delivery_display = f"{target_dt.strftime('%d/%m/%Y')} {target_dt.strftime('%H:%M')} - {(target_dt + timedelta(minutes=10)).strftime('%H:%M')}"
                lead_mins = max(0, int((target_dt - now_dt).total_seconds() / 60))
            else:
                req_delivery_display = f"{now_dt.strftime('%d/%m/%Y')} {fl_details.get('slot_start', '')} - {fl_details.get('slot_end', '')}"
        else:
            target_dt = details.get("table_earliest")
            if target_dt:
                req_delivery_display = target_dt.strftime('%d/%m/%Y %H:%M')
                lead_mins = max(0, int((target_dt - now_dt).total_seconds() / 60))
            else:
                target_dt = now_dt + timedelta(minutes=5)
                req_delivery_display = target_dt.strftime('%d/%m/%Y %H:%M')
                lead_mins = 5

        bopis_record = {
            "order_id": order_id,
            "created_at": now_dt.isoformat(),
            "updated_at": now_dt.isoformat(),
            "placed_at_display": placed_datetime_display,
            "requested_delivery_display": req_delivery_display,
            "lead_time_minutes": lead_mins,
            "channel_source": channel_source,
            "channel_label": channel_labels.get(channel_source, channel_source),
            "status": "preparing",
            "fulfillment_type": opt_id,
            "fulfillment_details": fl_details,
            "items": items,
            "totals": {
                "subtotal_cents": subtotal_cents,
                "delivery_fee_cents": delivery_fee_cents,
                "total_cents": total_cents,
                "currency": DEFAULT_CURRENCY,
            },
            "buyer": {
                "name": checkout.buyer.email if checkout.buyer else "Cliente Milano Centrale",
                "email": checkout.buyer.email if checkout.buyer else "cliente@devfest.example.it",
            },
            "ap2_verification": {
                "verified": True,
                "mandate_type": "ap2_cart_mandate",
                "credential_manager": "LocalCredentialManager",
                "token_id": f"tok_lcm_{order_id.lower()}",
            },
        }
        bopis_store.record_order(bopis_record)

        del self._checkouts[checkout_id]
        return checkout


def calculate_station_fulfillment_options(
    item_price_cents: int,
    departure_time: str | None = None,
    train_number: str | None = None,
    carriage: str | None = None,
    seat: str | None = None,
    platform: str | None = None,
    is_hot: bool = False,
    preferred_method: str = "pickup_express",
) -> list[dict[str, Any]]:
    """Generates standard fulfillment options computed by the station BOPIS logistics engine."""
    dep_time = departure_time or "13:55"
    train_num = train_number or "Frecciarossa 9540"
    carr = carriage or "4"
    st = seat or "12D"
    plat = platform or "14"

    target_delivery_time = dep_time
    try:
        parts = dep_time.split(":")
        h, m = int(parts[0]), int(parts[1])
        target_m = m - 5
        target_h = h
        if target_m < 0:
            target_m += 60
            target_h = (h - 1) % 24
        target_delivery_time = f"{target_h:02d}:{target_m:02d}"
    except Exception:
        pass

    options = []
    # 1. Consegna al Posto Treno (In-seat Train Delivery)
    options.append({
        "id": "in_seat_train",
        "label": f"🚆 Consegna al Posto Treno ({target_delivery_time})",
        "badge": "Consigliato (+€6.50)" if preferred_method == "in_seat_train" else "+€6.50",
        "details": f"{train_num} • Carrozza {carr}, Posto {st} • Binario {plat} (Finestra attesa 1 min)",
        "delivery_fee_cents": TRAIN_DELIVERY_FEE_CENTS,
        "total_cents": item_price_cents + TRAIN_DELIVERY_FEE_CENTS,
        "estimated_time": target_delivery_time,
        "is_recommended": preferred_method == "in_seat_train",
    })

    # 2. Ritiro Express al Banco Bistrot (Binario 12)
    options.append({
        "id": "pickup_express",
        "label": "⚡ Ritiro al Banco Bistrot (Binario 12)",
        "badge": "Pronto in 5 min • Gratuito" if preferred_method == "pickup_express" else "Gratuito (€0.00)",
        "details": "Bistrot Binario 12 – Al Banco • Nessun preavviso • Servizio rapido prioritario",
        "delivery_fee_cents": 0,
        "total_cents": item_price_cents,
        "estimated_time": "Pronto in 5 min",
        "is_recommended": preferred_method == "pickup_express",
    })

    # 3. Smart Locker Piano Interrato (ammesso solo per cibi freddi / ambient)
    if not is_hot:
        options.append({
            "id": "pickup_locker",
            "label": "📦 Smart Locker Piano Interrato",
            "badge": "Contactless • Gratuito",
            "details": "Smart Locker Box #14 • Slot 10 min • Sblocco contactless con PIN via SMS (Min. 30 min preavviso)",
            "delivery_fee_cents": 0,
            "total_cents": item_price_cents,
            "estimated_time": "Slot 10 min",
            "is_recommended": preferred_method == "pickup_locker",
        })

    return options

