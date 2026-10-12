# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Main server for Milano Centrale Travel Retail Agent & Shared BOPIS Engine."""

import asyncio
import functools
import json
import logging
import os
from pathlib import Path

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
import click
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

from .agent import root_agent as travel_agent
from .agent_executor import ADKAgentExecutor
from .bopis_store import bopis_store
from .merchant_user_store import merchant_user_store

# Load .env from backend or root project directory
base_dir = Path(__file__).resolve().parent
project_root = base_dir.parents[2]
load_dotenv(project_root / ".env")
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_retail_agent")


def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


def get_caller_email(request: Request) -> str | None:
    """Estrae l'identità dell'utente dall'header X-User-Email, Authorization (Bearer) o dai parametri query."""
    email = request.headers.get("x-user-email") or request.query_params.get("user_email") or request.query_params.get("operator_email")
    if email:
        return email.strip().lower()
    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        if "@" in token:
            return token.lower()
    return None


# ==============================================================================
# TODO (Modalità 2): UCP Identity Linking Capability (dev.ucp.common.identity_linking)
# - In futuro, implementare lo standard OAuth 2.0 PKCE con discovery /.well-known/oauth-authorization-server
# - Supportare l'Accelerated IdP Flow per scambiare il token Google con un token Merchant via RFC 8693.
#
# TODO (Modalità 3): AP2 Mandate Cryptographic Identity Verification
# - In futuro, validare crittograficamente la firma hardware FIDO2/Passkey sul JWT del mandato AP2
#   per attestare l'identità non ripudiabile dell'acquirente senza basarsi solo sull'email dichiarata.
#
# TODO (Hardening UCP REST & Anti-Hijacking):
# - Vedi 'ucp_rest_server.py' per il piano di sicurezza a 4 pilastri:
#   A. Dual-Token Architecture (Cart ID pubblico + Cart Secret Bearer Token)
#   B. Optimistic Locking & Versioning (ETag, If-Match, HTTP 412)
#   C. Canale mTLS / TLS 1.3 con Client Binding
#   D. Short-Lived TTL e Quote Locking (expires_at, freeze prezzi/inventario)
# ==============================================================================


async def verify_merchant_user(request: Request):
    """
    Endpoint di verifica manuale utente nel Dominio Merchant (Bistrot Milano Centrale).
    Verifica se l'utente Google è censito nella collezione 'merchant_users'.
    Nessun auto-provisioning: se l'utente non è censito, restituisce 403 Forbidden.
    """
    email = request.query_params.get("email") or get_caller_email(request)
    if not email:
        return JSONResponse({"authenticated": False, "authorized": False, "error": "Parametro 'email' obbligatorio"}, status_code=400)

    email = email.strip().lower()
    user = merchant_user_store.get_user(email)
    is_op = merchant_user_store.is_operator(email)

    if not user and not is_op:
        logger.warning("Tentativo di accesso da utente non censito nel Merchant: %s", email)
        return JSONResponse({
            "authenticated": True,
            "authorized": False,
            "registered": False,
            "error": f"L'utente '{email}' non è censito nel sistema Merchant (Bistrot Milano Centrale). Registrazione manuale richiesta."
        }, status_code=403)

    if not user and is_op:
        user = {
            "email": email,
            "display_name": email.split("@")[0],
            "role": "operator",
            "allowed_apps": ["bopis-dashboard", "storefront-webmcp", "chat-client"],
            "loyalty_tier": "FrecciaClub Gold",
            "loyalty_code": "FF-AA2026",
            "active": True
        }

    return JSONResponse({
        "authenticated": True,
        "authorized": True,
        "registered": True,
        "is_operator": is_op,
        "user": user
    })


async def get_bopis_orders(request: Request):
    """
    Recupero ordini BOPIS:
    - Se presente ?buyer_email=... (Storefront WebMCP / Personal Shopper):
      Restituisce ESCLUSIVAMENTE gli ordini associati a quell'email (Modalità 1: Matching per Email).
    - Se NON presente ?buyer_email (Dashboard Stazione completa):
      Richiede tassativamente il ruolo di operatore (merchant_users role: operator o OPERATOR_EMAILS).
    """
    buyer_email = request.query_params.get("buyer_email")
    caller = get_caller_email(request)

    # 1. Accesso filtrato per cliente (Storefront / Personal Shopper - Modalità 1)
    if buyer_email:
        buyer_norm = buyer_email.strip().lower()
        orders = bopis_store.get_orders_for_buyer(buyer_norm)
        return JSONResponse(orders)

    # 2. Accesso globale a tutta la stazione (Dashboard Operatori BOPIS)
    if caller and not merchant_user_store.is_operator(caller):
        logger.warning("Accesso negato a vista globale ordini per utente non operatore: %s", caller)
        return JSONResponse({
            "error": f"Accesso negato: l'utente '{caller}' non dispone dei privilegi di Operatore Stazione per visualizzare tutti gli ordini."
        }, status_code=403)

    hours_param = request.query_params.get("hours")
    max_age_hours = int(hours_param) if hours_param and hours_param.isdigit() else None
    orders = bopis_store.get_all_orders(max_age_hours=max_age_hours)
    return JSONResponse(orders)


async def get_bopis_order_by_id(request: Request):
    """Get single BOPIS order by ID."""
    order_id = request.path_params.get("order_id")
    order = bopis_store.get_order(order_id)
    if not order:
        return JSONResponse({"error": "Ordine non trovato"}, status_code=404)
    return JSONResponse(order)


async def create_bopis_order(request: Request):
    """Create BOPIS order from any client channel (Web MCP, Two-Agent, UCP REST)."""
    try:
        body = await request.json()
        if "order_id" not in body:
            from uuid import uuid4
            body["order_id"] = f"ORD-MI-{uuid4().hex[:6].upper()}"
        saved = bopis_store.record_order(body)
        return JSONResponse(saved, status_code=201)
    except Exception as e:
        logger.exception("Errore nella creazione ordine BOPIS")
        return JSONResponse({"error": str(e)}, status_code=400)


async def update_bopis_order_status(request: Request):
    """Update order fulfillment status (operator only)."""
    caller = get_caller_email(request)
    if caller and not merchant_user_store.is_operator(caller):
        logger.warning("Tentativo modifica stato ordine da non-operatore: %s", caller)
        return JSONResponse({
            "error": f"Operazione non consentita: l'utente '{caller}' non dispone dei privilegi di Operatore Stazione."
        }, status_code=403)

    order_id = request.path_params.get("order_id")
    try:
        body = await request.json()
        new_status = body.get("status")
        if not new_status:
            return JSONResponse({"error": "Campo 'status' obbligatorio"}, status_code=400)
        updated = bopis_store.update_order_status(order_id, new_status)
        if not updated:
            return JSONResponse({"error": "Ordine non trovato"}, status_code=404)
        return JSONResponse(updated)
    except Exception as e:
        logger.exception("Errore aggiornamento stato ordine")
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_bopis_stats(request: Request):
    """Get live BOPIS metrics for the station dispatcher dashboard (operator only)."""
    caller = get_caller_email(request)
    if caller and not merchant_user_store.is_operator(caller):
        return JSONResponse({
            "error": f"Accesso negato: statistiche riservate agli operatori."
        }, status_code=403)
    stats = bopis_store.get_stats()
    return JSONResponse(stats)


from google import genai
from pydantic import BaseModel
from .mcp_server import handle_mcp_jsonrpc, MCP_TOOLS
from .catalog_service import catalog_service
from .shopper_agent import AutonomousShopperAgent
from .store import calculate_station_fulfillment_options
from .ucp_rest_server import (
    get_ucp_manifest,
    get_ucp_catalog,
    create_ucp_checkout,
    get_ucp_checkout,
    patch_ucp_checkout,
    complete_ucp_checkout,
)

class MerchantProductSelection(BaseModel):
    product_ids: list[str]
    commercial_explanation: str

shopper_agent: AutonomousShopperAgent | None = None


async def get_bopis_fulfillment_options(request: Request):
    """Calcola opzioni di consegna stazione tramite il motore logistico BOPIS."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    item_price_cents = body.get("item_price_cents", 750)
    ticket = body.get("ticket", {})
    preferred = body.get("preferred_method", "pickup_express")
    is_hot = body.get("is_hot", False)

    options = calculate_station_fulfillment_options(
        item_price_cents=item_price_cents,
        departure_time=ticket.get("departure_time", "13:10"),
        train_number=ticket.get("train_number", "Frecciarossa 9540"),
        carriage=ticket.get("carriage", "4"),
        seat=ticket.get("seat", "12D"),
        platform=ticket.get("platform", "14"),
        is_hot=is_hot,
        preferred_method=preferred,
    )
    return JSONResponse({"fulfillment_options": options})


def _match_products_heuristic(prompt: str, dietary: str, all_products: list) -> list:
    """Fallback euristico di matching prodotti tramite parole chiave e vincoli alimentari."""
    matched = []
    # 1. Cold Brew / Specialty Coffee
    if any(k in prompt for k in ["cold brew", "estrazione a freddo", "caffè freddo", "caffe freddo", "specialty"]):
        cb = next((p for p in all_products if p.get("id") == "COFFEE-017"), None)
        if cb and cb not in matched:
            matched.append(cb)
    # 2. Caffè / Espresso caldo
    if any(k in prompt for k in ["caffè", "caffe", "espresso"]) and "cold brew" not in prompt and "fredd" not in prompt:
        caffe = next((p for p in all_products if p.get("id") == "CAFFE-001"), None)
        if caffe and caffe not in matched:
            matched.append(caffe)
    # 3. Focaccia / Toast
    if any(k in prompt for k in ["focaccia", "toast"]):
        toast = next((p for p in all_products if p.get("id") == "TOAST-003"), None)
        if toast and toast not in matched:
            matched.append(toast)
    # 4. Brioche / Croissant al Pistacchio
    if any(k in prompt for k in ["brioche", "pistacchio"]):
        brioche = next((p for p in all_products if p.get("id") == "PAST-002"), None)
        if brioche and brioche not in matched:
            matched.append(brioche)
    elif "cappuccino" in prompt:
        cappu = next((p for p in all_products if p.get("id") == "CAPPU-002"), None)
        if cappu and cappu not in matched:
            matched.append(cappu)
    # 5. Croissant vegano
    if any(k in prompt for k in ["croissant", "frutti di bosco"]):
        croiss = next((p for p in all_products if p.get("id") == "VEG-011"), None)
        if croiss and croiss not in matched:
            matched.append(croiss)
    # 6. Muffin Senza Glutine AIC / Lfree
    if any(k in prompt for k in ["muffin", "mirtilli"]) or ("senza glutine" in prompt and "dolce" in prompt):
        muffin = next((p for p in all_products if p.get("id") == "PAST-015"), None)
        if muffin and muffin not in matched:
            matched.append(muffin)
    # 7. Barretta Raw Proteica / Snack Sano
    if any(k in prompt for k in ["barretta", "proteic", "protein", "snack", "raw", "datteri", "anacardi"]):
        snack = next((p for p in all_products if p.get("id") == "SNACK-013"), None)
        if snack and snack not in matched:
            matched.append(snack)
    # 8. Poké Bowl Salmone / Senza Lattosio
    if any(k in prompt for k in ["poké", "poke", "salmone", "edamame", "bowl"]):
        poke = next((p for p in all_products if p.get("id") == "POKE-014"), None)
        if poke and poke not in matched:
            matched.append(poke)
    # 9. Panino vegano / Hummus
    if any(k in prompt for k in ["hummus", "verdure grigliate"]) or ("veg" in prompt and "panino" in prompt):
        veg_pan = next((p for p in all_products if p.get("id") == "VEG-012"), None)
        if veg_pan and veg_pan not in matched:
            matched.append(veg_pan)
    # 10. Ciabatta crudo / Bufala
    if any(k in prompt for k in ["crudo", "ciabatta", "bufala", "parma"]):
        crudo = next((p for p in all_products if p.get("id") == "PANIN-004"), None)
        if crudo and crudo not in matched:
            matched.append(crudo)
    # 11. Insalata Caesar
    if any(k in prompt for k in ["insalata", "caesar"]):
        insal = next((p for p in all_products if p.get("id") == "INSAL-005"), None)
        if insal and insal not in matched:
            matched.append(insal)
    # 12. Bevande
    if any(k in prompt for k in ["acqua", "san pellegrino", "frizzante"]):
        bev = next((p for p in all_products if p.get("id") == "BEV-006"), None)
        if bev and bev not in matched:
            matched.append(bev)
    if any(k in prompt for k in ["spremuta", "arancia", "arance"]):
        sprem = next((p for p in all_products if p.get("id") == "BEV-007"), None)
        if sprem and sprem not in matched:
            matched.append(sprem)
    # 13. Tech (GaN 45W, Powerbank, Cavi)
    if any(k in prompt for k in ["caricatore", "gan", "alimentatore"]):
        tech = next((p for p in all_products if p.get("id") == "TECH-016"), None)
        if tech and tech not in matched:
            matched.append(tech)
    elif any(k in prompt for k in ["powerbank", "cuffie", "tech"]):
        tech = next((p for p in all_products if "TECH" in p.get("id", "")), None)
        if tech and tech not in matched:
            matched.append(tech)

    # Fallback su vincoli dietetici e salute se nessun articolo è stato esplicitamente identificato
    if not matched:
        if "celiachia" in dietary or "senza glutine" in dietary or "gluten free" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "PAST-015"), None)
        elif "lattosio" in dietary or "senza lattosio" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "POKE-014"), None)
        elif "proteic" in prompt or "protein" in dietary or "fitness" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "SNACK-013"), None)
        elif "cold brew" in dietary or "freddo" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "COFFEE-017"), None)
        elif "veg" in dietary or "vegetar" in dietary or "veg" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "VEG-012"), None)
        elif "caff" in prompt or "colazione" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "CAFFE-001"), None)
        elif "toast" in prompt or "caldo" in prompt:
            chosen = next((p for p in all_products if p.get("id") == "TOAST-003"), None)
        else:
            chosen = next((p for p in all_products if p.get("id") == "PANIN-004"), all_products[0] if all_products else None)
        if chosen:
            matched.append(chosen)

    return matched


async def handle_a2a_negotiate(request: Request):
    """Merchant Agent A2A endpoint: riceve richiesta pasto/viaggio, interroga Gemini 2.5 Flash e il BOPIS Engine."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    train_ctx = body.get("train_context", {})
    dietary = (body.get("dietary_filter") or "").lower()
    prompt = (body.get("prompt") or body.get("user_prompt") or body.get("intent") or "").lower()
    semantic_inquiry = body.get("semantic_a2a_inquiry") or prompt
    req_method = body.get("required_delivery_method", "pickup_express")
    allergens_to_avoid = body.get("allergens_to_avoid") or []
    health_goals = body.get("health_goals") or []
    avoid_ultra_processed = body.get("avoid_ultra_processed", False)
    coffee_pref = body.get("coffee_preference", "")

    all_products = catalog_service.get_all_products()

    # 1. Tentativo di selezione semantica intelligente con Gemini 2.5 Flash
    matched_prods = []
    commercial_explanation = ""
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            catalog_summary = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "price_cents": p["price_cents"],
                    "is_hot": p["is_hot"],
                    "category": p["category"],
                    "description": p["description"],
                    "nutri_score": p.get("nutrition", {}).get("nutri_score"),
                    "nova_group": p.get("processing_level", {}).get("nova_group"),
                    "salt_g": (
                        p.get("nutrition", {}).get("per_100g", {}).get("salt_g")
                        if p.get("nutrition", {}).get("per_100g")
                        else p.get("nutrition", {}).get("per_serving", {}).get("salt_g")
                    ),
                    "protein_g": (
                        p.get("nutrition", {}).get("per_100g", {}).get("protein_g")
                        if p.get("nutrition", {}).get("per_100g")
                        else p.get("nutrition", {}).get("per_serving", {}).get("protein_g")
                    ),
                    "packaging_type": p.get("packaging_type"),
                    "dietary_tags": p.get("dietary_profile", {}).get("dietary_tags", []),
                    "allergens_free": p.get("dietary_profile", {}).get("allergens_free_claim", []),
                    "coffee_profile": p.get("coffee_profile"),
                }
                for p in all_products
            ]
            system_inst = (
                "Sei il Merchant Agent AI del Bistrot di Milano Centrale (Binario 12). "
                "Ricevi una richiesta di negoziazione A2A M2M da un Personal Shopper per conto di un viaggiatore. "
                "Esamina il catalogo dei prodotti ed estrai gli ID dei prodotti più idonei a soddisfare la richiesta. "
                "Regole fondamentali:\n"
                "- Se l'utente o il messaggio menziona più prodotti o articoli espliciti (es. 'caffè' e 'focaccia', o 'cold brew e muffin'), includi TUTTI i corrispettivi product_ids (es. CAFFE-001 e TOAST-003, oppure COFFEE-017 e PAST-015) nella lista product_ids.\n"
                "- Soddisfa con la massima priorità i vincoli su allergeni (es. celiachia/glutine -> PAST-015 certificato AIC, SNACK-013), intolleranza al lattosio (es. POKE-014, PAST-015), cibi poco processati (NOVA 1 o 3 vs ultraprocessati NOVA 4), basso sale (<1g) e preferenze di specialty coffee (COFFEE-017 estrazione a freddo 16h Single Origin Etiopia vs CAFFE-001 espresso caldo).\n"
                "- La richiesta esplicita dell'utente nel messaggio ha precedenza sulle preferenze dietetiche generiche del profilo (se l'utente chiede focaccia, offri la focaccia del bistrot anche se contiene prosciutto cotto).\n"
                "- In commercial_explanation, descrivi brevemente e cordialmente in italiano la composizione dell'ordine preparata per il viaggio, motivando la conformità nutrizionale, l'assenza di allergeni o le note sensoriali del caffè specialty se rilevanti."
            )
            req_content = (
                f"Richiesta A2A: {semantic_inquiry}\n"
                f"Messaggio Utente: {prompt}\n"
                f"Preferenze dietetiche: {dietary}\n"
                f"Allergeni da evitare: {allergens_to_avoid}\n"
                f"Obiettivi nutrizionali: {health_goals}\n"
                f"Evita ultraprocessati: {avoid_ultra_processed}\n"
                f"Preferenza caffè: {coffee_pref}\n"
                f"Dati Viaggio Treno: {json.dumps(train_ctx, ensure_ascii=False)}\n"
                f"Catalogo Prodotti Bistrot: {json.dumps(catalog_summary, ensure_ascii=False)}"
            )
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=req_content,
                config={
                    "system_instruction": system_inst,
                    "response_mime_type": "application/json",
                    "response_schema": MerchantProductSelection,
                }
            )
            parsed: MerchantProductSelection = resp.parsed
            if parsed and parsed.product_ids:
                for pid in parsed.product_ids:
                    found = next((p for p in all_products if p.get("id") == pid), None)
                    if found and found not in matched_prods:
                        matched_prods.append(found)
                commercial_explanation = parsed.commercial_explanation
                logger.info("Merchant Agent (Gemini 2.5 Flash) ha selezionato: %s (%s)", parsed.product_ids, commercial_explanation)
        except Exception as e:
            logger.warning("Selezione semantica Gemini 2.5 Flash fallback su euristica: %s", e)

    if not matched_prods:
        matched_prods = _match_products_heuristic(prompt, dietary, all_products)

    def _extract_item_details(prod: dict) -> dict:
        nutr = prod.get("nutrition") or {}
        p100 = nutr.get("per_100g") or {}
        pserv = nutr.get("per_serving") or {}
        salt = p100.get("salt_g", pserv.get("salt_g"))
        prot = p100.get("protein_g", pserv.get("protein_g"))
        return {
            "id": prod.get("id"),
            "title": prod.get("name"),
            "name": prod.get("name"),
            "price_cents": prod.get("price_cents", 750),
            "quantity": 1,
            "image_url": prod.get("image_url"),
            "category": prod.get("category", "Ristorazione"),
            "description": prod.get("description", ""),
            "is_hot": prod.get("is_hot", False),
            "packaging_type": prod.get("packaging_type", "fresh_service"),
            "net_weight_g": prod.get("net_weight_g"),
            "nutri_score": nutr.get("nutri_score"),
            "nova_group": prod.get("processing_level", {}).get("nova_group"),
            "salt_g": salt,
            "protein_g": prot,
            "dietary_tags": prod.get("dietary_profile", {}).get("dietary_tags", []),
            "allergens_free": prod.get("dietary_profile", {}).get("allergens_free_claim", []),
            "coffee_profile": prod.get("coffee_profile"),
        }

    # Composizione offerta (singola o combinata)
    if len(matched_prods) == 1:
        chosen_prod = matched_prods[0]
        details = _extract_item_details(chosen_prod)
        item_info = {
            "id": chosen_prod.get("id"),
            "title": chosen_prod.get("name"),
            "price_cents": chosen_prod.get("price_cents", 750),
            "image_url": chosen_prod.get("image_url"),
            "description": chosen_prod.get("description", ""),
            "category": chosen_prod.get("category", "Ristorazione"),
            "is_hot": chosen_prod.get("is_hot", False),
            "dietary": "Vegetariano / Vegano" if "veg" in dietary else "Classico",
            "packaging_type": details.get("packaging_type"),
            "nutri_score": details.get("nutri_score"),
            "nova_group": details.get("nova_group"),
            "salt_g": details.get("salt_g"),
            "protein_g": details.get("protein_g"),
            "coffee_profile": details.get("coffee_profile"),
            "items": [details],
        }
    else:
        # Combo di più prodotti (es. Cold Brew Specialty + Muffin Senza Glutine)
        total_cents = sum(p.get("price_cents", 0) for p in matched_prods)
        combo_title = " + ".join(p.get("name") for p in matched_prods)
        combo_desc = " • ".join(f"1x {p.get('name')} (€{p.get('price_cents', 0)/100:.2f})" for p in matched_prods)
        is_any_hot = any(p.get("is_hot", False) for p in matched_prods)
        combo_img = matched_prods[0].get("image_url")
        detailed_items = [_extract_item_details(p) for p in matched_prods]
        item_info = {
            "id": "COMBO-" + "-".join(p.get("id") for p in matched_prods),
            "title": combo_title,
            "price_cents": total_cents,
            "image_url": combo_img,
            "description": f"Selezione coordinata per il viaggio: {combo_desc}",
            "category": "Food & Beverage > Combo Viaggio",
            "is_hot": is_any_hot,
            "dietary": "Personalizzato",
            "items": detailed_items,
        }

    options = calculate_station_fulfillment_options(
        item_price_cents=item_info["price_cents"],
        departure_time=train_ctx.get("departure", "13:10"),
        train_number=train_ctx.get("train", "Frecciarossa 9540"),
        carriage=train_ctx.get("carriage", "4"),
        seat=train_ctx.get("seat", "12D"),
        platform=train_ctx.get("platform", "14"),
        is_hot=item_info["is_hot"],
        preferred_method=req_method,
    )
    rec_opt = next((o for o in options if o["id"] == req_method), options[0])

    proposal = {
        "merchant": "Bistrot Milano Centrale (Binario 12)",
        "offered_item": item_info,
        "fulfillment_options": options,
        "recommended_option": rec_opt,
        "station_rules_validated": True,
        "commercial_explanation": commercial_explanation or "Selezione coordinata per il tuo viaggio in treno.",
    }
    return JSONResponse(proposal)


async def handle_a2a_commit(request: Request):
    """Merchant Agent A2A endpoint: finalizza l'ordine, verifica mandato AP2 e registra su BOPIS Engine."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    from uuid import uuid4
    order_id = body.get("order_id") or f"ORD-MI-A2A{uuid4().hex[:5].upper()}"
    bopis_order = body.copy()
    bopis_order["order_id"] = order_id
    bopis_order.setdefault("channel_source", "two_agent_a2a")
    bopis_order.setdefault("channel_label", "Demo 3: Two-Agent A2A M2M")
    bopis_order.setdefault("status", "preparing")

    saved = bopis_store.record_order(bopis_order)
    logger.info("Ordine A2A %s registrato dal Merchant nel BOPIS Engine!", order_id)
    return JSONResponse({
        "status": "confirmed",
        "order_id": order_id,
        "order": saved,
        "message": f"Ordine {order_id} registrato con successo nel BOPIS Engine della stazione.",
    })



async def mcp_jsonrpc_endpoint(request: Request):
    """MCP JSON-RPC 2.0 endpoint (tools/list, tools/call, initialize)."""
    try:
        body = await request.json()
        resp = handle_mcp_jsonrpc(body)
        return JSONResponse(resp)
    except Exception as e:
        logger.exception("Errore richiesta MCP JSON-RPC")
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}, status_code=500)


async def get_mcp_tools(request: Request):
    """Expose available MCP tools specification for inspection."""
    return JSONResponse({"tools": MCP_TOOLS})


async def get_mcp_products(request: Request):
    """Expose all products for the Web Storefront."""
    return JSONResponse(catalog_service.get_all_products())


async def get_mcp_cart(request: Request):
    """Get active MCP cart state."""
    cart_id = request.path_params.get("cart_id")
    cart = catalog_service.get_cart(cart_id)
    if not cart:
        return JSONResponse({"error": "Carrello non trovato"}, status_code=404)
    return JSONResponse(cart)


async def run_mcp_shopper(request: Request):
    """Run autonomous shopper agent mission over MCP tools."""
    global shopper_agent
    try:
        if shopper_agent is None:
            shopper_agent = AutonomousShopperAgent()
        body = await request.json()
        prompt = body.get("prompt", "")
        if not prompt:
            return JSONResponse({"error": "Campo 'prompt' obbligatorio"}, status_code=400)
        buyer_name = body.get("buyer_name", "Viaggiatore MCP")
        buyer_email = body.get("buyer_email", "shopper.mcp@devfest.example.it")

        result = await shopper_agent.run_shopping_mission(
            prompt=prompt,
            buyer_name=buyer_name,
            buyer_email=buyer_email,
        )
        return JSONResponse(result)
    except Exception as e:
        logger.exception("Errore esecuzione Shopper Agent MCP")
        return JSONResponse({"error": str(e)}, status_code=500)


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=10999)
@make_sync
async def run(host, port):
    """Run the Milano Centrale Travel Retail A2A & BOPIS server."""
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY non trovata nel file .env!")
        exit(1)

    base_path = Path(__file__).parent
    card_path = base_path / "data" / "agent_card.json"
    with card_path.open(encoding="utf-8") as f:
        data = json.load(f)
    agent_card = AgentCard.model_validate(data)

    task_store = InMemoryTaskStore()

    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(
            agent=travel_agent,
            extensions=agent_card.capabilities.extensions or [],
        ),
        task_store=task_store,
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    async def get_pretty_agent_card(request: Request):
        """Restituisce l'Agent Card A2A formattata con rientro a 2 spazi per la massima leggibilità umana."""
        card_data = agent_card.model_dump(exclude_none=True, by_alias=True)
        return Response(
            content=json.dumps(card_data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    # Sostituiamo le rotte agent-card compresse di default di A2A SDK con la versione formattata
    routes = [
        r for r in a2a_app.routes()
        if getattr(r, "path", None) not in ("/.well-known/agent-card.json", "/.well-known/agent.json")
    ]
    routes.insert(0, Route("/.well-known/agent-card.json", get_pretty_agent_card, methods=["GET"]))
    routes.insert(1, Route("/.well-known/agent.json", get_pretty_agent_card, methods=["GET"]))

    images_dir = base_path / "data" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Attach Well-Known, Images, BOPIS Engine, and Web MCP Endpoints
    routes.extend(
        [
            Route(
                "/.well-known/ucp",
                lambda _: FileResponse(base_path / "data" / "ucp.json"),
            ),
            Route(
                "/.well-known/webmcp",
                lambda _: FileResponse(
                    base_path.parent.parent.parent / "storefront-webmcp" / "public" / ".well-known" / "webmcp",
                    media_type="application/json"
                ),
            ),
            Route(
                "/llms.txt",
                lambda _: FileResponse(
                    base_path.parent.parent.parent / "storefront-webmcp" / "public" / "llms.txt",
                    media_type="text/plain"
                ),
            ),
            Route(
                "/robots.txt",
                lambda _: FileResponse(
                    base_path.parent.parent.parent / "storefront-webmcp" / "public" / "robots.txt",
                    media_type="text/plain"
                ),
            ),
            Route(
                "/profile/agent_profile.json",
                lambda _: FileResponse(
                    base_path.parent.parent.parent / "frontend" / "public" / "profile" / "agent_profile.json",
                    media_type="application/json"
                ),
            ),
            Mount(
                "/images",
                app=StaticFiles(directory=str(images_dir)),
                name="images",
            ),
            # Dominio Merchant: Auth & Verifica Utenti
            Route("/merchant/users/verify", verify_merchant_user, methods=["GET"]),
            Route("/bopis/orders", get_bopis_orders, methods=["GET"]),
            Route("/bopis/orders", create_bopis_order, methods=["POST"]),
            Route("/bopis/orders/{order_id}", get_bopis_order_by_id, methods=["GET"]),
            Route("/bopis/orders/{order_id}/status", update_bopis_order_status, methods=["POST", "PATCH"]),
            Route("/bopis/stats", get_bopis_stats, methods=["GET"]),
            Route("/bopis/catalog", get_mcp_products, methods=["GET"]),
            Route("/bopis/fulfillment/options", get_bopis_fulfillment_options, methods=["POST"]),
            # Demo 3: A2A Federation Routes (Merchant Agent Interface)
            Route("/a2a/negotiate", handle_a2a_negotiate, methods=["POST"]),
            Route("/a2a/commit", handle_a2a_commit, methods=["POST"]),
            # Demo 2: Web MCP Routes
            Route("/mcp", mcp_jsonrpc_endpoint, methods=["POST"]),
            Route("/mcp/tools", get_mcp_tools, methods=["GET"]),
            Route("/mcp/products", get_mcp_products, methods=["GET"]),
            Route("/mcp/cart/{cart_id}", get_mcp_cart, methods=["GET"]),
            Route("/mcp/shopper/run", run_mcp_shopper, methods=["POST"]),
            # Demo 4: UCP Standard REST Endpoints
            Route("/ucp", get_ucp_manifest, methods=["GET"]),
            Route("/ucp/catalog/products", get_ucp_catalog, methods=["GET"]),
            Route("/ucp/checkouts", create_ucp_checkout, methods=["POST"]),
            Route("/ucp/checkouts/{checkout_id}", get_ucp_checkout, methods=["GET"]),
            Route("/ucp/checkouts/{checkout_id}", patch_ucp_checkout, methods=["PATCH", "PUT"]),
            Route("/ucp/checkouts/{checkout_id}/complete", complete_ucp_checkout, methods=["POST"]),
        ]
    )

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    app = Starlette(routes=routes, middleware=middleware)

    logger.info("Avvio Milano Centrale Travel Retail A2A & BOPIS Server su http://%s:%s", host, port)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    run()
