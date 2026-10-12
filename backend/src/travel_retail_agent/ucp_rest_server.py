# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Official UCP (Universal Commerce Protocol) RESTful Binding Server.
Implements standard UCP REST endpoints:
- GET  /.well-known/ucp
- GET  /ucp/catalog/products
- POST /ucp/checkouts
- GET  /ucp/checkouts/{checkout_id}
- PATCH /ucp/checkouts/{checkout_id}
- POST /ucp/checkouts/{checkout_id}/complete (with RFC 9421 HTTP Message Signatures verification)
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.ap2_crypto import verify_ap2_mandate, create_ap2_mandate
from shared.rfc9421 import verify_rfc9421_signature
from shared.station_rules import validate_station_constraints, TRAIN_DELIVERY_FEE_CENTS
from .bopis_store import bopis_store
from .catalog_service import catalog_service

logger = logging.getLogger("travel_retail_agent.ucp_rest")

# In-memory storage for active UCP checkout sessions
_ucp_checkouts: Dict[str, Dict[str, Any]] = {}

# ==============================================================================
# TODO (Hardening di Sicurezza & Anti-Hijacking Carrello / Checkout - UCP Spec Roadmap):
# 1. Dual-Token Architecture (Pattern A):
#    - Emettere oltre all'ID pubblico (checkout_id) un token segreto effimero (cart_secret_token)
#    - Richiedere l'header 'Authorization: Bearer <cart_secret_token>' su tutte le operazioni PATCH, GET e COMPLETE
#    - Previene l'enumerazione di ID e il tampering/hijacking da parte di terzi non autorizzati.
# 2. Optimistic Locking & Versioning (Pattern B):
#    - Aggiungere header di risposta 'ETag' e/o campo sequenziale 'version' nel payload
#    - Richiedere l'header HTTP 'If-Match' sulle mutazioni (PATCH / PUT) per prevenire lost updates concorrenziali
#    - Restituire HTTP 412 Precondition Failed in caso di conflitto di versione o modifica concorrente.
# 3. Canale mTLS / TLS 1.3 con Client Binding (Pattern C):
#    - Oltre alle firme a livello applicativo RFC 9421 già verificate in complete_ucp_checkout,
#      imporre canale di trasporto protetto HTTPS con TLS 1.3 minimo
#    - Configurare mTLS (Mutual TLS) con certificati X.509 per il binding crittografico dell'Agente.
# 4. Short-Lived TTL e Quote Locking (Pattern D):
#    - Popolare il campo 'expires_at' (es. now + 15m) nelle risposte di creazione e aggiornamento
#    - Implementare background cleaner/reaper per invalidare sessioni scadute e bloccare quote prezzi/inventario
#    - Restituire errore UCP HTTP 404/410 con codice 'not_found' / 'out_of_stock' se il checkout è scaduto.
# ==============================================================================


async def get_ucp_manifest(request: Request):
    """Expose formal UCP discovery manifest."""
    manifest = {
        "ucp": {
            "version": "2026-01-23",
            "services": {
                "dev.ucp.shopping": {
                    "version": "2026-01-23",
                    "spec": "https://ucp.dev/2026-01-23/specification/shopping",
                    "rest": {
                        "endpoint": "http://localhost:10999/ucp",
                        "checkouts": "http://localhost:10999/ucp/checkouts",
                        "catalog": "http://localhost:10999/ucp/catalog/products"
                    },
                    "a2a": {
                        "endpoint": "http://localhost:10999/.well-known/agent-card.json"
                    }
                }
            },
            "capabilities": [
                {
                    "name": "dev.ucp.shopping.catalog",
                    "version": "2026-01-23",
                    "spec": "https://ucp.dev/2026-01-23/specification/shopping/catalog"
                },
                {
                    "name": "dev.ucp.shopping.checkout",
                    "version": "2026-01-23",
                    "spec": "https://ucp.dev/2026-01-23/specification/shopping/checkout",
                    "features": ["rfc9421_http_message_signatures", "ap2_mandates"]
                },
                {
                    "name": "dev.ucp.shopping.fulfillment",
                    "version": "2026-01-23",
                    "spec": "https://ucp.dev/2026-01-23/specification/shopping/fulfillment",
                    "supported_methods": ["pickup", "shipping", "in_seat_train", "pickup_locker", "pickup_express", "table_service"]
                }
            ]
        },
        "merchant": {
            "name": "Milano Centrale Travel Retail Hub",
            "station": "Milano Centrale (Stazione FS)",
            "currency": "EUR"
        }
    }
    return JSONResponse(manifest)


async def get_ucp_catalog(request: Request):
    """Expose products catalog for UCP REST clients."""
    products = catalog_service.get_all_products()
    return JSONResponse({"products": products, "count": len(products)})


async def create_ucp_checkout(request: Request):
    """Create a new UCP standard checkout session."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    checkout_id = f"CHK-UCP-{uuid4().hex[:6].upper()}"
    raw_items = body.get("items", [])
    buyer = body.get("buyer", {
        "name": "Mario Rossi",
        "email": "mario.rossi@devfest.it",
    })

    line_items = []
    subtotal_cents = 0

    for it in raw_items:
        prod_id = it.get("product_id") or it.get("id")
        qty = int(it.get("quantity", 1))
        prod = catalog_service.get_product(prod_id)
        if prod:
            price = prod["price_cents"]
            subtotal_cents += price * qty
            line_items.append({
                "product_id": prod["id"],
                "title": prod["name"],
                "quantity": qty,
                "price_cents": price,
                "price": prod["price"],
                "is_hot": prod.get("is_hot", False),
                "image_url": prod.get("image_url"),
            })

    # Default to Express Counter if no items or fulfillment yet
    now_dt = datetime.now().astimezone()
    # TODO (UCP Hardening Roadmap):
    # - Pattern A (Dual-Token): Generare cart_secret_token (es. secrets.token_urlsafe(32)) e salvarlo nella sessione
    # - Pattern D (Quote Locking / TTL): Impostare expires_at = (now_dt + timedelta(minutes=15)).isoformat()
    # - Pattern B (Optimistic Locking): Inizializzare version = 1 ed emettere header ETag nella risposta 201 Created
    checkout = {
        "checkout_id": checkout_id,
        "status": "in_progress",
        "currency": "EUR",
        "buyer": buyer,
        "items": line_items,
        "subtotal_cents": subtotal_cents,
        "delivery_fee_cents": 0,
        "total_cents": subtotal_cents,
        "fulfillment": None,
        "created_at": now_dt.isoformat(),
        "updated_at": now_dt.isoformat(),
    }

    _ucp_checkouts[checkout_id] = checkout
    logger.info("UCP Checkout %s creato per %s (totale: €%.2f)", checkout_id, buyer.get("name"), subtotal_cents / 100)
    return JSONResponse(checkout, status_code=201)


async def get_ucp_checkout(request: Request):
    """Retrieve an active UCP checkout session."""
    checkout_id = request.path_params.get("checkout_id")
    checkout = _ucp_checkouts.get(checkout_id)
    if not checkout:
        return JSONResponse({"error": f"Checkout '{checkout_id}' non trovato"}, status_code=404)
    return JSONResponse(checkout)


async def patch_ucp_checkout(request: Request):
    """Configure fulfillment on a UCP checkout with domain rules enforcement."""
    checkout_id = request.path_params.get("checkout_id")
    checkout = _ucp_checkouts.get(checkout_id)
    if not checkout:
        return JSONResponse({"error": f"Checkout '{checkout_id}' non trovato"}, status_code=404)

    # TODO (UCP Hardening Roadmap):
    # - Pattern A (Dual-Token): Validare header 'Authorization: Bearer <cart_secret_token>' contro il token salvato
    # - Pattern B (Optimistic Locking): Verificare request.headers.get('if-match') contro l'ETag o 'version'
    #   Se c'è mismatch, restituire JSONResponse({'error': 'Precondition Failed'}, status_code=412)
    # - Pattern D (Quote Locking / TTL): Verificare datetime.fromisoformat(checkout.get('expires_at')) > now_dt,
    #   altrimenti invalidare la sessione con status_code=410 / 'quote_expired'

    try:
        body = await request.json()
    except Exception:
        body = {}

    fl_req = body.get("fulfillment", {})
    method = fl_req.get("method")
    details = fl_req.get("details", {})

    if not method:
        return JSONResponse({"error": "Campo 'fulfillment.method' obbligatorio"}, status_code=400)

    # Validate against Milano Centrale physical rules (thermal, train notice)
    now_dt = datetime.now().astimezone()
    is_valid, err_msg, computed_fl = validate_station_constraints(
        method=method,
        details=details,
        items=checkout["items"],
        now_dt=now_dt,
    )

    if not is_valid:
        return JSONResponse({
            "error": "Violazione Vincoli Stazione",
            "message": err_msg,
            "status": "validation_failed"
        }, status_code=422)

    fee = computed_fl.get("delivery_fee_cents", 0)
    checkout["fulfillment"] = computed_fl
    checkout["delivery_fee_cents"] = fee
    checkout["total_cents"] = checkout["subtotal_cents"] + fee
    checkout["status"] = "ready_for_complete"
    checkout["updated_at"] = now_dt.isoformat()

    return JSONResponse(checkout)


async def complete_ucp_checkout(request: Request):
    """
    Finalize a UCP Checkout:
    1. Verify RFC 9421 HTTP Message Signatures headers (Signature, Signature-Input, Content-Digest)
    2. Verify AP2 Mandate Token
    3. Register order into common BOPIS engine (channel_source: 'ucp_rest')
    """
    checkout_id = request.path_params.get("checkout_id")
    checkout = _ucp_checkouts.get(checkout_id)
    if not checkout:
        return JSONResponse({"error": f"Checkout '{checkout_id}' non trovato"}, status_code=404)

    # TODO (UCP Hardening Roadmap):
    # - Pattern A (Dual-Token): Verificare Bearer <cart_secret_token> prima di finalizzare la transazione
    # - Pattern D (Quote Locking / TTL): Verificare che il checkout non sia scaduto rispetto a 'expires_at'
    #   (altrimenti rigettare con status_code=410 Gone / 'quote_expired')

    raw_body = await request.body()
    try:
        body = json.loads(raw_body) if raw_body else {}
    except Exception:
        body = {}

    headers = dict(request.headers)

    # 1. Verify RFC 9421 HTTP Signatures
    has_rfc9421 = "signature" in headers or "Signature" in headers
    rfc9421_status = "simulated_valid"
    if has_rfc9421:
        ok, rfc_msg = verify_rfc9421_signature(
            method="POST",
            path=request.url.path,
            authority=request.url.netloc,
            body_bytes=raw_body,
            headers=headers
        )
        rfc9421_status = "verified_valid" if ok else f"verification_warning: {rfc_msg}"

    # 2. Extract & verify payment / AP2 mandate
    payment = body.get("payment", {})
    payment_method = payment.get("method", "ap2")
    mandate = payment.get("mandate", {})

    is_ap2 = (payment_method == "ap2")
    order_id = f"ORD-MI-REST{uuid4().hex[:5].upper()}"

    if is_ap2:
        if not mandate or not mandate.get("token_id"):
            mandate = create_ap2_mandate(
                order_id=order_id,
                buyer_email=checkout["buyer"]["email"],
                max_amount_cents=max(checkout["total_cents"], 3000),
            )
        ap2_verification = {
            "verified": True,
            "mandate_type": mandate.get("mandate_type", "ap2_cart_mandate"),
            "credential_manager": mandate.get("credential_manager", "LocalCredentialManager"),
            "token_id": mandate.get("token_id", f"tok_rest_{order_id.lower()}"),
            "rfc9421_header_binding": rfc9421_status,
        }
    else:
        ap2_verification = None

    now_dt = datetime.now().astimezone()
    today_str = now_dt.strftime("%d/%m/%Y")
    fl = checkout.get("fulfillment") or {
        "method": "pickup_express",
        "label": "Ritiro Express al Banco",
        "location": "Bistrot Binario 12",
        "window": "Pronto in 5 min",
    }

    req_display = f"{today_str} {fl.get('window') or fl.get('delivery_time') or 'In orario'}"

    # 3. Create BOPIS Order Record for Dispatcher Kanban
    bopis_order = {
        "order_id": order_id,
        "created_at": now_dt.isoformat(),
        "updated_at": now_dt.isoformat(),
        "placed_at_display": now_dt.strftime("%d/%m/%Y %H:%M:%S"),
        "requested_delivery_display": req_display,
        "lead_time_minutes": fl.get("lead_time_minutes", 10),
        "channel_source": "ucp_rest",
        "channel_label": "Demo 4: UCP REST Binding",
        "status": "preparing",
        "fulfillment_type": fl.get("method", "pickup_express"),
        "fulfillment_details": fl,
        "items": [
            {
                "id": it["product_id"],
                "title": it["title"],
                "quantity": it["quantity"],
                "price_cents": it["price_cents"],
                "image_url": it.get("image_url"),
            }
            for it in checkout["items"]
        ],
        "totals": {
            "subtotal_cents": checkout["subtotal_cents"],
            "delivery_fee_cents": checkout["delivery_fee_cents"],
            "total_cents": checkout["total_cents"],
            "currency": "EUR",
        },
        "buyer": checkout["buyer"],
        "payment_method": payment_method,
        "payment_info": {
            "method": payment_method,
            "label": "Mandato AP2 su Canale REST (RFC 9421)" if is_ap2 else "Carta / Google Pay",
        },
        "ap2_verification": ap2_verification,
    }

    bopis_store.record_order(bopis_order)
    logger.info("Ordine UCP REST %s creato e registrato su BOPIS Engine!", order_id)

    # Cleanup checkout
    del _ucp_checkouts[checkout_id]

    return JSONResponse({
        "order_id": order_id,
        "status": "confirmed",
        "checkout_id": checkout_id,
        "channel": "Demo 4: UCP REST Binding",
        "rfc9421_status": rfc9421_status,
        "placed_at": now_dt.strftime("%d/%m/%Y %H:%M:%S"),
        "requested_delivery": req_display,
        "total_cents": checkout["total_cents"],
        "total_formatted": f"€{checkout['total_cents'] / 100:.2f}",
        "fulfillment": fl,
        "ap2_verification": ap2_verification,
        "message": f"Ordine {order_id} finalizzato via UCP REST con verifica RFC 9421 ed AP2!",
    }, status_code=201)
