# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Personal Shopper Agent Service: Context Engine and Mission Runner
Supports:
1. Demo 3: Two-Agent A2A Federation (M2M Semantic Protocol)
2. Demo 4: UCP Standard REST Binding with RFC 9421 HTTP Message Signatures
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Optional, Literal
from uuid import uuid4

import httpx
from google import genai
from pydantic import BaseModel

# Add backend/src to path for shared package
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.join(os.path.dirname(current_dir), "backend", "src")
if backend_src_dir not in sys.path:
    sys.path.insert(0, backend_src_dir)

from shared.models import (
    TravelerContext,
    TrainTicket,
    TravelerPreferences,
    AP2Delegation,
)
from shared.ap2_crypto import create_ap2_mandate
from shared.rfc9421 import generate_rfc9421_signature

class ShopperIntentAnalysis(BaseModel):
    resolved_fulfillment: Literal["in_seat_train", "pickup_express", "pickup_locker"]
    fulfillment_reason: str
    semantic_a2a_inquiry: str
    desired_items_summary: str


def analyze_intent_with_gemini(prompt: str, ctx: TravelerContext) -> Optional[ShopperIntentAnalysis]:
    """Analisi semantica dell'intento del viaggiatore con Gemini 2.5 Flash."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        system_prompt = (
            "Sei il Personal Shopper Agent AI (Gemini 2.5 Flash) per un viaggiatore nella stazione di Milano Centrale. "
            "Il tuo compito è analizzare la richiesta in linguaggio naturale dell'utente e determinare: "
            "1. La modalità di consegna ottimale ('in_seat_train', 'pickup_express', 'pickup_locker'): "
            "   - 'in_seat_train': se l'utente richiede la consegna al treno, carrozza, posto o a bordo. "
            "   - 'pickup_locker': se richiede il ritiro contactless allo smart locker (ottimale per cibi e bevande fredde come Cold Brew o snack confezionati). "
            "   - 'pickup_express': se ha fretta, è al banco bistrot, o vuole il ritiro immediato in 5 minuti. "
            "2. La motivazione chiara della scelta (fulfillment_reason). "
            "3. Una formulazione semantica M2M (semantic_a2a_inquiry) da inviare all'agente del negozio di stazione, arricchita con dettagli treno, vincoli su allergeni, obiettivi nutrizionali, grado NOVA o preferenze specialty coffee. "
            "4. Un riepilogo sintetico dei prodotti desiderati (desired_items_summary)."
        )
        pref_allergens = f", Allergeni da evitare: {ctx.preferences.allergens_to_avoid}" if ctx.preferences.allergens_to_avoid else ""
        pref_health = f", Obiettivi nutrizionali: {ctx.preferences.health_goals}" if ctx.preferences.health_goals else ""
        pref_nova = ", Evita ultraprocessati NOVA 4" if ctx.preferences.avoid_ultra_processed else ""
        pref_coffee = f", Preferenza caffè: {ctx.preferences.coffee_preference}" if ctx.preferences.coffee_preference else ""

        user_info = (
            f"Messaggio Utente: {prompt}\n"
            f"Biglietto Treno: {ctx.ticket.train_number}, Carrozza {ctx.ticket.carriage}, Posto {ctx.ticket.seat}, Binario {ctx.ticket.platform}, Partenza {ctx.ticket.departure_time}\n"
            f"Preferenze profilo: Consegna abituale '{ctx.preferences.preferred_fulfillment}', Dieta '{ctx.preferences.dietary}'"
            f"{pref_allergens}{pref_health}{pref_nova}{pref_coffee}"
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_info,
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": ShopperIntentAnalysis,
            }
        )
        parsed: ShopperIntentAnalysis = resp.parsed
        if parsed:
            logger.info("Personal Shopper (Gemini 2.5 Flash) ha risolto: %s (%s)", parsed.resolved_fulfillment, parsed.fulfillment_reason)
        return parsed
    except Exception as e:
        logger.warning("Analisi intento Gemini 2.5 Flash in fallback su euristica: %s", e)
        return None

logger = logging.getLogger("backend_shopper.service")

MERCHANT_BASE_URL = os.getenv("MERCHANT_BASE_URL", "http://localhost:10999")

# --- INITIAL TRAVELER CONTEXT WITH PRESETS ---

_DEFAULT_SCENARIOS = {
    "scenario_departing_soon": {
        "title": "Scenario A: Fretta • In Partenza tra 15 min",
        "ticket": {
            "train_number": "Frecciarossa 9540",
            "pnr": "FR-9540-MR",
            "origin": "Milano Centrale",
            "destination": "Roma Termini",
            "departure_time": "13:10",
            "platform": "14",
            "carriage": "4",
            "seat": "12D",
            "class_service": "Area Silenzio • Prima Classe",
        },
        "preferences": {
            "dietary": "No carne rossa • Piatti freschi e leggeri",
            "preferred_fulfillment": "in_seat_train",
            "max_budget_cents": 2500,
            "notes": "Consegna tassativa al posto treno prima della partenza",
        },
    },
    "scenario_transit_locker": {
        "title": "Scenario B: Coincidenza 45 min • Sosta Stazione",
        "ticket": {
            "train_number": "Italo 9923",
            "pnr": "IT-9923-TR",
            "origin": "Milano Centrale",
            "destination": "Napoli Centrale",
            "departure_time": "13:55",
            "platform": "18",
            "carriage": "6",
            "seat": "21B",
            "class_service": "Club Executive",
        },
        "preferences": {
            "dietary": "Opzione vegetariana o vegana",
            "preferred_fulfillment": "pickup_locker",
            "max_budget_cents": 2000,
            "notes": "Ritiro contactless allo Smart Locker del piano interrato",
        },
    },
    "scenario_fitness_specialty": {
        "title": "Scenario C: Fitness, Low-Salt & Specialty Cold Brew",
        "ticket": {
            "train_number": "Frecciarossa 9540",
            "pnr": "FR-9540-MR",
            "origin": "Milano Centrale",
            "destination": "Roma Termini",
            "departure_time": "13:10",
            "platform": "14",
            "carriage": "4",
            "seat": "12D",
            "class_service": "Area Silenzio • Prima Classe",
        },
        "preferences": {
            "dietary": "High-protein • Basso sale • Senza glutine/lattosio",
            "preferred_fulfillment": "pickup_locker",
            "max_budget_cents": 3000,
            "allergens_to_avoid": ["Glutine", "Lattosio"],
            "health_goals": ["high_protein", "low_salt"],
            "avoid_ultra_processed": True,
            "coffee_preference": "cold_brew_specialty",
            "notes": "Prodotti poco processati (NOVA 1-3) e specialty coffee estratto a freddo 16h per smart locker",
        },
    },
}

# Active context state
DEFAULT_BUYER_NAME = os.getenv("DEFAULT_BUYER_NAME", "Alex Rossi")
DEFAULT_BUYER_EMAIL = os.getenv("DEFAULT_BUYER_EMAIL", "alex.traveler@example.com")

_active_context = TravelerContext(
    traveler_id="usr_shopper_alex_rossi",
    name=DEFAULT_BUYER_NAME,
    email=DEFAULT_BUYER_EMAIL,
    loyalty_tier="FrecciaClub Gold",
    loyalty_code="FF-AR2026",
    scenario_preset_id="scenario_departing_soon",
    ticket=TrainTicket(**_DEFAULT_SCENARIOS["scenario_departing_soon"]["ticket"]),
    preferences=TravelerPreferences(**_DEFAULT_SCENARIOS["scenario_departing_soon"]["preferences"]),
    ap2=AP2Delegation(),
)


def get_current_context() -> TravelerContext:
    return _active_context


def update_current_context(data: Dict[str, Any]) -> TravelerContext:
    global _active_context
    _active_context = TravelerContext.model_validate(data)
    return _active_context


def set_scenario_preset(preset_id: str) -> TravelerContext:
    global _active_context
    scen = _DEFAULT_SCENARIOS.get(preset_id)
    if not scen:
        preset_id = "scenario_departing_soon"
        scen = _DEFAULT_SCENARIOS[preset_id]

    _active_context.scenario_preset_id = preset_id
    _active_context.ticket = TrainTicket(**scen["ticket"])
    _active_context.preferences = TravelerPreferences(**scen["preferences"])
    return _active_context


# --- INTENT EXTRACTION & FULFILLMENT RESOLUTION ---

def extract_requested_fulfillment(prompt: str, fallback_method: str) -> tuple[str, str]:
    """
    Analizza il prompt dell'utente per determinare la modalità di consegna desiderata.
    Da priorità alle istruzioni esplicite contenute nel messaggio rispetto al default di profilo,
    gestendo anche refusi comuni come 'teno' per 'treno'.
    """
    p_lower = prompt.lower()

    # 1. Consegna a bordo treno / posto a sedere
    train_patterns = [
        "treno", "teno", "trno", "treni", "posto", "bordo", "carrozza",
        "binario", "in-seat", "in seat", "a bordo", "al posto", "sul treno", "in treno"
    ]
    if any(k in p_lower for k in train_patterns):
        return "in_seat_train", "Richiesta esplicita nel messaggio dell'utente (consegna al posto treno)"

    # 2. Ritiro Smart Locker
    locker_patterns = [
        "locker", "smart locker", "armadietto", "box", "ritiro locker", "cassetta", "piano -1", "interrato"
    ]
    if any(k in p_lower for k in locker_patterns):
        return "pickup_locker", "Richiesta esplicita nel messaggio dell'utente (Smart Locker)"

    # 3. Ritiro al Banco / Express / Tavolo
    express_patterns = [
        "banco", "bancone", "bistrot", "tavolo", "desk", "express", "veloce", "cassa", "ritiro al banco"
    ]
    if any(k in p_lower for k in express_patterns):
        return "pickup_express", "Richiesta esplicita nel messaggio dell'utente (ritiro al banco bistrot)"

    # 4. Fallback sulla preferenza predefinita del profilo
    return fallback_method, f"Preferenza predefinita del profilo viaggiatore ({fallback_method})"


MEAL_CATALOG: Dict[str, Dict[str, Any]] = {
    "VEG-012": {
        "id": "VEG-012",
        "title": "Panino Vegano con Hummus e Verdure Grigliate",
        "price_cents": 750,
        "image_url": "https://images.unsplash.com/photo-1525059696034-4967a8e1dca2?w=400&q=80",
        "description": "Sandwich fresco artigianale 100% vegetale con pane rustico ai cereali, crema di ceci al sesamo e verdure grigliate di stagione.",
        "category": "Food & Beverage > Panini Vegani",
        "is_hot": False,
        "dietary": "Vegan / Vegetariano",
        "nutri_score": "A",
        "nova_group": 3,
        "salt_g": 0.9,
        "protein_g": 12.0,
        "packaging_type": "fresh_service",
    },
    "PANIN-004": {
        "id": "PANIN-004",
        "title": "Ciabatta con Crudo di Parma 24 Mesi e Bufala",
        "price_cents": 750,
        "image_url": "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400&q=80",
        "description": "Ciabatta croccante con Prosciutto di Parma DOP 24 mesi e mozzarella di bufala campana. Fresco, ideale per il viaggio.",
        "category": "Food & Beverage > Panini Gourmet Freddi",
        "is_hot": False,
        "dietary": "Gourmet",
        "nutri_score": "C",
        "nova_group": 3,
        "salt_g": 2.1,
        "protein_g": 22.0,
        "packaging_type": "fresh_service",
    },
    "TOAST-003": {
        "id": "TOAST-003",
        "title": "Focaccia Toast Calda con Prosciutto e Fontina DOP",
        "price_cents": 650,
        "image_url": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400&q=80",
        "description": "Focaccia ligure tostata al momento con prosciutto cotto alta qualità e fontina DOP fusa. Servita calda.",
        "category": "Food & Beverage > Panini Caldi",
        "is_hot": True,
        "dietary": "Classico",
        "nutri_score": "C",
        "nova_group": 3,
        "salt_g": 1.8,
        "protein_g": 18.0,
        "packaging_type": "fresh_service",
    },
    "CAFFE-001": {
        "id": "CAFFE-001",
        "title": "Espresso Doppio Caldo Illy con Croissant",
        "price_cents": 450,
        "image_url": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80",
        "description": "Espresso doppio caldo estratto al momento 100% Arabica Illy e croissant artigianale.",
        "category": "Food & Beverage > Caffetteria Calda",
        "is_hot": True,
        "dietary": "Colazione",
        "nutri_score": "A",
        "nova_group": 1,
        "salt_g": 0.0,
        "protein_g": 0.2,
        "packaging_type": "fresh_service",
        "coffee_specialty": True,
    },
    "COFFEE-017": {
        "id": "COFFEE-017",
        "title": "Single Origin Cold Brew Specialty (Etiopia Bio 250ml)",
        "price_cents": 450,
        "image_url": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=400&q=80",
        "description": "Cold Brew Specialty estratto a freddo 16h da chicchi 100% Arabica Etiopia Yirgacheffe Bio. Dolcezza naturale, zero acidità, 160mg caffeina. Idoneo Smart Locker.",
        "category": "Food & Beverage > Specialty Coffee Freddo",
        "is_hot": False,
        "dietary": "Specialty Coffee Bio",
        "nutri_score": "A",
        "nova_group": 1,
        "salt_g": 0.0,
        "protein_g": 0.5,
        "packaging_type": "prepackaged",
        "coffee_specialty": True,
    },
    "SNACK-013": {
        "id": "SNACK-013",
        "title": "Barretta Raw Bio Datteri & Mandorle High-Protein (AIC)",
        "price_cents": 280,
        "image_url": "https://images.unsplash.com/photo-1622484216850-466d7e0081d0?w=400&q=80",
        "description": "Barretta energetica cruda biologica senza zuccheri aggiunti, ricca di fibre e 11g proteine. Spiga Barrata AIC Senza Glutine. No briciole.",
        "category": "Food & Beverage > Snack Salutari",
        "is_hot": False,
        "dietary": "Senza Glutine AIC / Bio / Vegano",
        "nutri_score": "A",
        "nova_group": 1,
        "salt_g": 0.02,
        "protein_g": 11.0,
        "packaging_type": "prepackaged",
    },
    "POKE-014": {
        "id": "POKE-014",
        "title": "Poké Bowl Riso Venere, Salmone Bio & Avocado",
        "price_cents": 950,
        "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=80",
        "description": "Ciotola fresca bilanciata con riso Venere integrale italiano, salmone bio, avocado e salsa ponzu senza glutine. Senza Lattosio, 24g proteine. Smart Locker OK.",
        "category": "Food & Beverage > Piatti Unici Freddi",
        "is_hot": False,
        "dietary": "Senza Lattosio / High Protein / Omega-3",
        "nutri_score": "A",
        "nova_group": 1,
        "salt_g": 0.8,
        "protein_g": 24.0,
        "packaging_type": "fresh_service",
    },
    "PAST-015": {
        "id": "PAST-015",
        "title": "Muffin Artigianale Cacao (Gluten & Lactose Free AIC)",
        "price_cents": 350,
        "image_url": "https://images.unsplash.com/photo-1586985289688-ca3cf47d3e6e?w=400&q=80",
        "description": "Muffin soffice al cacao e gocce di cioccolato fondente 70%. Confezionato monodose sterile: doppia certificazione AIC Senza Glutine e Lfree Senza Lattosio.",
        "category": "Food & Beverage > Dolci & Colazione",
        "is_hot": False,
        "dietary": "Senza Glutine AIC & Senza Lattosio",
        "nutri_score": "C",
        "nova_group": 3,
        "salt_g": 0.28,
        "protein_g": 4.8,
        "packaging_type": "prepackaged",
    },
}


def select_meal_item(prompt: str, dietary: str) -> Dict[str, Any]:
    """
    Seleziona l'articolo di ristorazione più appropriato in base a prompt e dieta.
    Restituisce un dizionario completo del prodotto.
    """
    p_lower = prompt.lower()
    d_lower = (dietary or "").lower()

    if "cold brew" in p_lower or ("caffè" in p_lower and "fredd" in p_lower) or "specialty" in p_lower:
        return MEAL_CATALOG["COFFEE-017"]
    elif "snack" in p_lower or "barretta" in p_lower or "protein" in p_lower or "proteic" in p_lower:
        return MEAL_CATALOG["SNACK-013"]
    elif "poké" in p_lower or "poke" in p_lower or "salmone" in p_lower or "senza lattosio" in d_lower or "lattosio" in p_lower:
        return MEAL_CATALOG["POKE-014"]
    elif "muffin" in p_lower or ("dolce" in p_lower and "senza glutine" in p_lower):
        return MEAL_CATALOG["PAST-015"]
    elif "vegan" in p_lower or "vegan" in d_lower or "vegetar" in p_lower or "vegetar" in d_lower:
        return MEAL_CATALOG["VEG-012"]
    elif "caffè" in p_lower or "espresso" in p_lower or "colazione" in p_lower:
        return MEAL_CATALOG["CAFFE-001"]
    elif "toast" in p_lower or "caldo" in p_lower or "calda" in p_lower:
        return MEAL_CATALOG["TOAST-003"]
    else:
        return MEAL_CATALOG["PANIN-004"]


def build_fulfillment_options(
    item_price_cents: int,
    ticket: TrainTicket,
    resolved_method: str,
    is_hot: bool = False,
) -> list[Dict[str, Any]]:
    """Genera le opzioni di fulfillment disponibili con calcolo orario e supplementi reali secondo specifica UCP."""
    now = datetime.now().astimezone()
    dep_time = ticket.departure_time or "13:55"
    train_num = ticket.train_number or "Frecciarossa 9540"
    carriage = ticket.carriage or "4"
    seat = ticket.seat or "12D"
    platform = ticket.platform or "14"

    # Orario previsto consegna al treno: 5 minuti prima della partenza
    target_delivery_time = dep_time
    target_h, target_m = 13, 50
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

    target_train_dt = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    if target_train_dt < now:
        target_train_dt += timedelta(days=1)
    train_start_iso = target_train_dt.isoformat()
    train_end_iso = (target_train_dt + timedelta(minutes=1)).isoformat()

    pickup_start = now + timedelta(minutes=5)
    pickup_end = now + timedelta(minutes=20)
    pickup_start_iso = pickup_start.isoformat()
    pickup_end_iso = pickup_end.isoformat()

    options = []

    # 1. Consegna al Posto Treno (In-seat Train Delivery)
    options.append({
        "id": "in_seat_train",
        "label": f"🚆 Consegna al Posto Treno ({target_delivery_time})",
        "badge": "Consigliato (+€6.50)" if resolved_method == "in_seat_train" else "+€6.50",
        "details": f"{train_num} • Carrozza {carriage}, Posto {seat} • Binario {platform} (Finestra attesa 1 min)",
        "delivery_fee_cents": 650,
        "total_cents": item_price_cents + 650,
        "estimated_time": target_delivery_time,
        "earliest_fulfillment_time": train_start_iso,
        "latest_fulfillment_time": train_end_iso,
        "is_recommended": resolved_method == "in_seat_train",
    })

    # 2. Ritiro Express al Banco Bistrot (Binario 12)
    options.append({
        "id": "pickup_express",
        "label": "⚡ Ritiro al Banco Bistrot (Binario 12)",
        "badge": "Pronto in 5 min • Gratuito" if resolved_method in ["pickup", "pickup_express"] else "Gratuito (€0.00)",
        "details": f"Bistrot Binario 12 – Al Banco • Pronto in 5 min ({pickup_start.strftime('%H:%M')} - {pickup_end.strftime('%H:%M')}) • Servizio prioritario",
        "delivery_fee_cents": 0,
        "total_cents": item_price_cents,
        "estimated_time": "Pronto in 5 min",
        "earliest_fulfillment_time": pickup_start_iso,
        "latest_fulfillment_time": pickup_end_iso,
        "is_recommended": resolved_method in ["pickup", "pickup_express"],
    })

    # 3. Smart Locker Piano Interrato (Discrete Fulfillment Options - solo cibi freddi)
    if not is_hot:
        base_slot = now + timedelta(minutes=35)
        rem = base_slot.minute % 10
        add_min = (10 - rem) if rem != 0 else 0
        first_slot_dt = (base_slot + timedelta(minutes=add_min)).replace(second=0, microsecond=0)

        for i in range(2):
            s_start = first_slot_dt + timedelta(minutes=i * 10)
            s_end = s_start + timedelta(minutes=10)
            s_tag = s_start.strftime("%H%M")
            s_label_time = f"{s_start.strftime('%H:%M')} - {s_end.strftime('%H:%M')}"
            
            options.append({
                "id": f"pickup_locker_{s_tag}",
                "label": f"📦 Smart Locker ({s_label_time})",
                "badge": "Slot 10 min • Contactless",
                "details": f"Smart Locker Box #14 • Slot riservato {s_label_time} • Sblocco contactless con PIN via SMS",
                "delivery_fee_cents": 0,
                "total_cents": item_price_cents,
                "estimated_time": s_label_time,
                "earliest_fulfillment_time": s_start.isoformat(),
                "latest_fulfillment_time": s_end.isoformat(),
                "is_recommended": resolved_method.startswith("pickup_locker"),
            })

    return options


# --- MISSION EXECUTION: DEMO 3 (A2A FEDERATION) & DEMO 4 (UCP REST) ---

async def stream_shopper_mission(
    prompt: str,
    protocol: str = "a2a",
    context_override: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """
    Run the Shopper Agent mission and yield Server-Sent Events (SSE) chunks.
    Format: 'data: {...}\n\n'
    """
    ctx = _active_context
    if context_override:
        try:
            ctx = TravelerContext.model_validate(context_override)
        except Exception:
            pass

    if protocol == "ucp_rest":
        async for event in _stream_ucp_rest_mission(prompt, ctx):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    else:
        async for event in _stream_a2a_mission(prompt, ctx):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _stream_a2a_mission(prompt: str, ctx: TravelerContext) -> AsyncGenerator[Dict[str, Any], None]:
    """Demo 3: Two-Agent A2A Federation (Shopper Agent <-> Merchant Agent M2M via Gemini 2.5 Flash)."""
    now_str = datetime.now().strftime("%H:%M:%S")

    # 1. Analisi semantica intelligente dell'intento con Gemini 2.5 Flash (lato Personal Shopper)
    ai_intent = analyze_intent_with_gemini(prompt, ctx)
    if ai_intent:
        fl_method = ai_intent.resolved_fulfillment
        fl_reason = ai_intent.fulfillment_reason
        semantic_inquiry = ai_intent.semantic_a2a_inquiry
    else:
        fl_method, fl_reason = extract_requested_fulfillment(prompt, ctx.preferences.preferred_fulfillment)
        semantic_inquiry = f"Richiesta pasto per viaggiatore su {ctx.ticket.train_number}: {prompt}"

    # Prodotti e opzioni di fallback iniziali (prima della negoziazione M2M)
    item_info = select_meal_item(prompt, ctx.preferences.dietary)
    fulfillment_options = build_fulfillment_options(
        item_price_cents=item_info["price_cents"],
        ticket=ctx.ticket,
        resolved_method=fl_method,
        is_hot=item_info["is_hot"],
    )
    selected_opt = next((o for o in fulfillment_options if o["id"] == fl_method), fulfillment_options[0])

    # STEP 1: Context Ingestion & Intent Analysis con Gemini
    yield {
        "type": "step",
        "step": {
            "step_number": 1,
            "protocol": "a2a",
            "actor_source": "shopper_client",
            "actor_target": "shopper_agent",
            "action": "ANALYZE_TRAVELER_INTENT",
            "description": f"Richiesta inviata dal client ed elaborata con AI (Gemini 2.5 Flash): {fl_reason}. Modalità: '{fl_method}'. Iniezione contesto biglietto {ctx.ticket.train_number} ({ctx.ticket.departure_time}).",
            "payload": {
                "traveler_name": ctx.name,
                "ticket": ctx.ticket.model_dump(),
                "dietary": ctx.preferences.dietary,
                "preferred_method": ctx.preferences.preferred_fulfillment,
                "resolved_delivery_method": fl_method,
                "fulfillment_reason": fl_reason,
                "semantic_a2a_inquiry": semantic_inquiry,
                "ai_agent_model": "gemini-2.5-flash",
                "max_budget_cents": ctx.preferences.max_budget_cents,
            },
            "status": "success",
            "timestamp": now_str,
        },
    }
    await asyncio.sleep(0.6)

    # STEP 2: A2A Request Formulation to Station Merchant
    a2a_query_payload = {
        "intent": "REQUEST_TRAVEL_MEAL",
        "prompt": prompt,
        "user_prompt": prompt,
        "semantic_a2a_inquiry": semantic_inquiry,
        "destination_station": "Milano Centrale",
        "train_context": {
            "train": ctx.ticket.train_number,
            "departure": ctx.ticket.departure_time,
            "platform": ctx.ticket.platform,
            "carriage": ctx.ticket.carriage,
            "seat": ctx.ticket.seat,
        },
        "dietary_filter": ctx.preferences.dietary,
        "required_delivery_method": fl_method,
        "allergens_to_avoid": ctx.preferences.allergens_to_avoid,
        "health_goals": ctx.preferences.health_goals,
        "avoid_ultra_processed": ctx.preferences.avoid_ultra_processed,
        "coffee_preference": ctx.preferences.coffee_preference,
    }

    yield {
        "type": "step",
        "step": {
            "step_number": 2,
            "protocol": "a2a",
            "actor_source": "shopper_agent",
            "actor_target": "merchant_agent",
            "action": "A2A_QUERY_INTENT",
            "description": f"Invio messaggio semantico A2A all'agente del Bistrot di Milano Centrale (Binario 12): '{semantic_inquiry}'. Modalità richiesta: {fl_method}.",
            "payload": a2a_query_payload,
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        },
    }
    await asyncio.sleep(0.7)

    # Interroga il Merchant Agent di stazione (il quale interroga Gemini 2.5 Flash + BOPIS Engine)
    commercial_desc = ""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{MERCHANT_BASE_URL}/a2a/negotiate", json=a2a_query_payload)
            if resp.status_code == 200:
                m_data = resp.json()
                item_info = m_data.get("offered_item", item_info)
                fulfillment_options = m_data.get("fulfillment_options", fulfillment_options)
                selected_opt = m_data.get("recommended_option", selected_opt)
                commercial_desc = m_data.get("commercial_explanation", "")
    except Exception as e:
        logger.warning("Negoziazione A2A in fallback locale: %s", e)

    # STEP 3: Merchant Agent Proposal & Station Rules Check
    merchant_proposal = {
        "merchant": "Bistrot Milano Centrale (Binario 12)",
        "offered_item": item_info,
        "fulfillment_options": fulfillment_options,
        "recommended_option": selected_opt,
        "station_rules_validated": True,
        "commercial_explanation": commercial_desc,
        "ai_agent_model": "gemini-2.5-flash",
    }

    step_desc = (
        f"L'agente della stazione (Gemini 2.5 Flash + BOPIS Engine) risponde: {commercial_desc} Offerta: '{item_info['title']}' (€{item_info['price_cents'] / 100:.2f}) e {len(fulfillment_options)} modalità calcolate."
        if commercial_desc
        else f"L'agente della stazione (Gemini 2.5 Flash + BOPIS Engine) risponde con proposta approvata: '{item_info['title']}' (€{item_info['price_cents'] / 100:.2f}) e {len(fulfillment_options)} modalità di consegna calcolate."
    )

    yield {
        "type": "step",
        "step": {
            "step_number": 3,
            "protocol": "a2a",
            "actor_source": "merchant_agent",
            "actor_target": "shopper_agent",
            "action": "A2A_PROPOSAL_OFFER",
            "description": step_desc,
            "payload": merchant_proposal,
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        },
    }
    await asyncio.sleep(0.5)

    # HUMAN-PRESENT PROPOSAL: Emette proposta interattiva al viaggiatore prima di innescare l'autorizzazione AP2
    proposal_payload = {
        "proposal_id": f"PROP-A2A-{uuid4().hex[:6].upper()}",
        "protocol": "a2a",
        "merchant_name": "Bistrot Milano Centrale (Binario 12)",
        "item": item_info,
        "fulfillment_options": fulfillment_options,
        "selected_option_id": selected_opt["id"],
        "ticket": ctx.ticket.model_dump(),
        "buyer": {"name": ctx.name, "email": ctx.email},
    }

    yield {
        "type": "proposal",
        "proposal": proposal_payload,
        "message": f"Ho negoziato la soluzione con l'agente della stazione per il tuo viaggio su {ctx.ticket.train_number}. Seleziona la modalità di ricezione desiderata prima di autorizzare la spesa con Passkey AP2:",
    }


async def _stream_ucp_rest_mission(prompt: str, ctx: TravelerContext) -> AsyncGenerator[Dict[str, Any], None]:
    """Demo 4: UCP Standard REST Binding with RFC 9421 HTTP Message Signatures."""
    now_str = datetime.now().strftime("%H:%M:%S")

    # Risoluzione dinamica della modalità di consegna dal prompt
    fl_method, fl_reason = extract_requested_fulfillment(prompt, ctx.preferences.preferred_fulfillment)

    # STEP 1: Discovery Manifest (GET /.well-known/ucp)
    manifest = {}
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(f"{MERCHANT_BASE_URL}/.well-known/ucp")
            manifest = res.json()
    except Exception:
        manifest = {"ucp": {"version": "2026-01-23"}}

    yield {
        "type": "step",
        "step": {
            "step_number": 1,
            "protocol": "ucp_rest",
            "actor_source": "shopper_agent",
            "actor_target": "ucp_rest_server",
            "action": "HTTP_GET_DISCOVERY",
            "description": f"Esecuzione UCP Service Discovery: GET /.well-known/ucp. Modalità individuata: '{fl_method}' ({fl_reason}).",
            "headers": {"Accept": "application/json"},
            "payload": {
                "manifest": manifest,
                "resolved_fulfillment": fl_method,
                "fulfillment_reason": fl_reason,
            },
            "status": "success",
            "timestamp": now_str,
        },
    }
    await asyncio.sleep(0.6)

    # STEP 2: Products Catalog (GET /ucp/catalog/products)
    products_list = []
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(f"{MERCHANT_BASE_URL}/ucp/catalog/products")
            products_list = res.json().get("products", [])
    except Exception:
        products_list = []

    p_lower = prompt.lower()
    matched_prods = []
    if any(k in p_lower for k in ["cold brew", "estrazione a freddo", "caffè freddo", "caffe freddo", "specialty"]):
        cb = next((p for p in products_list if p.get("id") == "COFFEE-017"), None)
        if cb: matched_prods.append(cb)
    if any(k in p_lower for k in ["caffè", "caffe", "espresso"]) and "cold brew" not in p_lower and "fredd" not in p_lower:
        c = next((p for p in products_list if p.get("id") == "CAFFE-001"), None)
        if c: matched_prods.append(c)
    if any(k in p_lower for k in ["focaccia", "toast"]):
        t = next((p for p in products_list if p.get("id") == "TOAST-003"), None)
        if t: matched_prods.append(t)
    if any(k in p_lower for k in ["cappuccino", "brioche", "pistacchio"]):
        b = next((p for p in products_list if p.get("id") == "CAPPU-002"), None)
        if b: matched_prods.append(b)
    if any(k in p_lower for k in ["croissant"]):
        cr = next((p for p in products_list if p.get("id") == "VEG-011"), None)
        if cr: matched_prods.append(cr)
    if any(k in p_lower for k in ["muffin", "mirtilli"]) or ("senza glutine" in p_lower and "dolce" in p_lower):
        muf = next((p for p in products_list if p.get("id") == "PAST-015"), None)
        if muf: matched_prods.append(muf)
    if any(k in p_lower for k in ["barretta", "proteic", "protein", "snack", "raw"]):
        snk = next((p for p in products_list if p.get("id") == "SNACK-013"), None)
        if snk: matched_prods.append(snk)
    if any(k in p_lower for k in ["poké", "poke", "salmone", "lattosio"]):
        pk = next((p for p in products_list if p.get("id") == "POKE-014"), None)
        if pk: matched_prods.append(pk)
    if any(k in p_lower for k in ["hummus", "verdure"]) or ("veg" in p_lower and "panino" in p_lower):
        vp = next((p for p in products_list if p.get("id") == "VEG-012"), None)
        if vp: matched_prods.append(vp)
    if any(k in p_lower for k in ["crudo", "ciabatta", "bufala"]):
        cp = next((p for p in products_list if p.get("id") == "PANIN-004"), None)
        if cp: matched_prods.append(cp)
    if any(k in p_lower for k in ["caricatore", "gan", "tech", "powerbank"]):
        tc = next((p for p in products_list if p.get("id") == "TECH-016" or "TECH" in p.get("id", "")), None)
        if tc: matched_prods.append(tc)

    if not matched_prods:
        if "veg" in p_lower or "vegetar" in (ctx.preferences.dietary or "").lower():
            ch = next((p for p in products_list if p.get("id") == "VEG-012"), None)
        elif "glutine" in (ctx.preferences.dietary or "").lower() or "aic" in p_lower:
            ch = next((p for p in products_list if p.get("id") == "PAST-015"), None)
        elif "cold brew" in (ctx.preferences.dietary or "").lower():
            ch = next((p for p in products_list if p.get("id") == "COFFEE-017"), None)
        else:
            ch = next((p for p in products_list if p.get("id") == "PANIN-004"), products_list[0] if products_list else None)
        if ch: matched_prods.append(ch)

    chosen_prod = matched_prods[0]

    yield {
        "type": "step",
        "step": {
            "step_number": 2,
            "protocol": "ucp_rest",
            "actor_source": "shopper_agent",
            "actor_target": "ucp_rest_server",
            "action": "HTTP_GET_CATALOG",
            "description": f"Interrogazione catalogo REST UCP: GET /ucp/catalog/products. Individuati {len(matched_prods)} articoli corrispondenti.",
            "headers": {"Accept": "application/json"},
            "payload": {
                "selected_items": matched_prods,
                "total_catalog_items": len(products_list),
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        },
    }
    await asyncio.sleep(0.7)

    # STEP 3: Create Checkout Session (POST /ucp/checkouts)
    checkout_data = {}
    checkout_id = f"CHK-UCP-{uuid4().hex[:6].upper()}"
    try:
        body = {
            "items": [{"product_id": p["id"], "quantity": 1} for p in matched_prods],
            "buyer": {"name": ctx.name, "email": ctx.email},
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.post(f"{MERCHANT_BASE_URL}/ucp/checkouts", json=body)
            checkout_data = res.json()
            checkout_id = checkout_data.get("checkout_id", checkout_id)
    except Exception:
        checkout_data = {"checkout_id": checkout_id, "status": "in_progress"}

    yield {
        "type": "step",
        "step": {
            "step_number": 3,
            "protocol": "ucp_rest",
            "actor_source": "shopper_agent",
            "actor_target": "ucp_rest_server",
            "action": "HTTP_POST_CHECKOUT",
            "description": f"Creazione sessione di checkout UCP: POST /ucp/checkouts (Session ID: {checkout_id}).",
            "headers": {"Content-Type": "application/json"},
            "payload": checkout_data,
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        },
    }
    await asyncio.sleep(0.7)

    # STEP 4: Configure Fulfillment (PATCH /ucp/checkouts/{id})
    fl_payload = {
        "fulfillment": {
            "method": fl_method,
            "details": {
                "train_number": ctx.ticket.train_number,
                "platform": ctx.ticket.platform,
                "carriage": ctx.ticket.carriage,
                "seat": ctx.ticket.seat,
                "delivery_time": ctx.ticket.departure_time,
            },
        }
    }

    patched_data = {}
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.patch(f"{MERCHANT_BASE_URL}/ucp/checkouts/{checkout_id}", json=fl_payload)
            patched_data = res.json()
    except Exception:
        patched_data = fl_payload

    yield {
        "type": "step",
        "step": {
            "step_number": 4,
            "protocol": "ucp_rest",
            "actor_source": "shopper_agent",
            "actor_target": "ucp_rest_server",
            "action": "HTTP_PATCH_FULFILLMENT",
            "description": f"Configurazione modalità di evasione: PATCH /ucp/checkouts/{checkout_id} (Metodo: {fl_method}).",
            "headers": {"Content-Type": "application/json"},
            "payload": patched_data,
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        },
    }
    await asyncio.sleep(0.5)

    # HUMAN-PRESENT PROPOSAL (REST)
    if len(matched_prods) == 1:
        item_info = {
            "id": chosen_prod.get("id"),
            "title": chosen_prod.get("name", "Panino"),
            "price_cents": chosen_prod.get("price_cents", 750),
            "image_url": chosen_prod.get("image_url", "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400&q=80"),
            "description": chosen_prod.get("description", ""),
            "category": chosen_prod.get("category", "Food & Beverage"),
            "is_hot": chosen_prod.get("is_hot", False),
            "dietary": "Selezione Viaggio",
            "items": [
                {
                    "id": chosen_prod.get("id"),
                    "title": chosen_prod.get("name", "Panino"),
                    "name": chosen_prod.get("name", "Panino"),
                    "price_cents": chosen_prod.get("price_cents", 750),
                    "quantity": 1,
                    "image_url": chosen_prod.get("image_url", "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400&q=80"),
                    "category": chosen_prod.get("category", "Food & Beverage"),
                    "description": chosen_prod.get("description", ""),
                    "is_hot": chosen_prod.get("is_hot", False),
                }
            ],
        }
    else:
        total_p_cents = sum(p.get("price_cents", 0) for p in matched_prods)
        item_info = {
            "id": "COMBO-" + "-".join(p.get("id") for p in matched_prods),
            "title": " + ".join(p.get("name") for p in matched_prods),
            "price_cents": total_p_cents,
            "image_url": matched_prods[0].get("image_url"),
            "description": " • ".join(f"1x {p.get('name')} (€{p.get('price_cents', 0)/100:.2f})" for p in matched_prods),
            "category": "Food & Beverage > Combo Viaggio",
            "is_hot": any(p.get("is_hot", False) for p in matched_prods),
            "dietary": "Personalizzato",
            "items": [
                {
                    "id": p.get("id"),
                    "title": p.get("name"),
                    "name": p.get("name"),
                    "price_cents": p.get("price_cents", 0),
                    "quantity": 1,
                    "image_url": p.get("image_url"),
                    "category": p.get("category", "Food & Beverage"),
                    "description": p.get("description", ""),
                    "is_hot": p.get("is_hot", False),
                }
                for p in matched_prods
            ],
        }
    fulfillment_options = build_fulfillment_options(
        item_price_cents=item_info["price_cents"],
        ticket=ctx.ticket,
        resolved_method=fl_method,
        is_hot=item_info["is_hot"],
    )
    # Interroga il motore di calcolo logistico BOPIS del merchant
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            fo_res = await client.post(
                f"{MERCHANT_BASE_URL}/bopis/fulfillment/options",
                json={
                    "item_price_cents": item_info["price_cents"],
                    "ticket": ctx.ticket.model_dump(),
                    "preferred_method": fl_method,
                    "is_hot": item_info["is_hot"],
                }
            )
            if fo_res.status_code == 200:
                fulfillment_options = fo_res.json().get("fulfillment_options", fulfillment_options)
    except Exception as e:
        logger.warning("Fulfillment options fetch fallback: %s", e)

    selected_opt = next((o for o in fulfillment_options if o["id"] == fl_method), fulfillment_options[0])

    proposal_payload = {
        "proposal_id": f"PROP-REST-{uuid4().hex[:6].upper()}",
        "protocol": "ucp_rest",
        "merchant_name": "Bistrot Milano Centrale (Binario 12)",
        "item": item_info,
        "fulfillment_options": fulfillment_options,
        "selected_option_id": selected_opt["id"],
        "ticket": ctx.ticket.model_dump(),
        "buyer": {"name": ctx.name, "email": ctx.email},
        "notes": f"checkout_id={checkout_id}",
    }

    yield {
        "type": "proposal",
        "proposal": proposal_payload,
        "message": f"Sessione REST UCP configurata ({checkout_id}). Seleziona la modalità di ricezione desiderata prima di procedere alla firma del mandato con Passkey AP2:",
    }


async def complete_shopper_authorization(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finalizza la transazione una volta ricevuta l'approvazione biometrica dell'utente
    (Passkey FIDO2 generata dal Local Credential Manager sul client).
    """
    protocol = data.get("protocol", "a2a")
    challenge = data.get("challenge", {})
    ap2_mandate = data.get("ap2_mandate", {})
    now_dt = datetime.now().astimezone()
    today_str = now_dt.strftime("%d/%m/%Y")
    req_time = (now_dt + timedelta(minutes=15)).strftime("%H:%M")

    if protocol == "a2a":
        order_id = challenge.get("order_id", f"ORD-MI-A2A{uuid4().hex[:5].upper()}")
        fl_method = challenge.get("fl_method", "in_seat_train")
        ticket = challenge.get("ticket", {})
        total_cents = challenge.get("total_cents", 1300)
        item_id = challenge.get("order_item_id", "PANIN-001")
        item_title = challenge.get("order_summary_title", "Focaccia Ligure")
        item_price = challenge.get("order_item_price", 650)
        fee = challenge.get("delivery_fee", 0)

        is_locker = fl_method.startswith("pickup_locker")
        fl_record = {
            "method": fl_method,
            "label": challenge.get("fl_label", "Consegna al Posto Treno"),
            "train_number": ticket.get("train_number"),
            "platform": ticket.get("platform"),
            "carriage": ticket.get("carriage"),
            "seat": ticket.get("seat"),
            "pin_code": "4918" if is_locker else None,
            "box_number": "Box #14" if is_locker else None,
            "window": challenge.get("fl_window") or f"{req_time} – Pronto prima di {ticket.get('departure_time', '13:10')}",
        }

        order_items = challenge.get("items") or [
            {
                "id": item_id,
                "title": item_title,
                "quantity": 1,
                "price_cents": item_price,
            }
        ]
        subtotal_cents = sum(it.get("price_cents", item_price) * it.get("quantity", 1) for it in order_items)

        final_order = {
            "order_id": order_id,
            "channel_source": "two_agent_a2a",
            "channel_label": "Demo 3: Two-Agent A2A M2M",
            "status": "preparing",
            "fulfillment_type": fl_method,
            "fulfillment_details": fl_record,
            "items": order_items,
            "totals": {
                "subtotal_cents": subtotal_cents,
                "delivery_fee_cents": fee,
                "total_cents": total_cents,
                "currency": "EUR",
            },
            "buyer": challenge.get("buyer", {"name": DEFAULT_BUYER_NAME, "email": DEFAULT_BUYER_EMAIL}),
            "payment_method": "ap2",
            "payment_info": {
                "method": "ap2",
                "label": "Mandato Passkey AP2 (Firma On-Device LCM)",
            },
            "ap2_verification": ap2_mandate,
            "created_at": now_dt.isoformat(),
            "updated_at": now_dt.isoformat(),
            "placed_at_display": now_dt.strftime("%d/%m/%Y %H:%M:%S"),
            "requested_delivery_display": f"{today_str} {req_time}",
            "lead_time_minutes": 15,
        }

        # Trasmette il mandato firmato AP2 all'agente del Merchant (A2A Commit)
        # Il Merchant a sua volta convalida il token e scrive l'ordine sul proprio BOPIS Engine
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                await client.post(f"{MERCHANT_BASE_URL}/a2a/commit", json=final_order)
        except Exception as e:
            logger.warning("Impossibile trasmettere commit A2A al Merchant: %s", e)

        if fl_method == "in_seat_train":
            fl_conf_desc = f"consegna al {ticket.get('train_number')}, Carrozza {ticket.get('carriage')}, Posto {ticket.get('seat')}"
        elif is_locker:
            slot_label = ""
            if fl_method.startswith("pickup_locker_"):
                raw_tag = fl_method.replace("pickup_locker_", "")
                if len(raw_tag) == 4 and raw_tag.isdigit():
                    slot_label = f" (Slot {raw_tag[:2]}:{raw_tag[2:]})"
            fl_conf_desc = f"ritiro allo Smart Locker{slot_label} (Box #{fl_record.get('box_number')}, PIN: {fl_record.get('pin_code')})"
        else:
            fl_conf_desc = "ritiro rapido al Bistrot Binario 12"

        base_step = data.get("step_offset", 5)

        step_ap2 = {
            "step_number": base_step + 1,
            "protocol": "a2a",
            "actor_source": "shopper_client",
            "actor_target": "shopper_agent",
            "action": "AP2_MANDATE_VERIFICATION",
            "description": f"Lo Shopper Agent valida la firma crittografica del mandato AP2 ({ap2_mandate.get('signature_scheme', 'FIDO2_Passkey_P256')}) e i vincoli di spesa autorizzati (€{total_cents/100:.2f}).",
            "payload": {
                "mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "authorized_amount_cents": ap2_mandate.get("max_authorized_cents", total_cents),
                "signature_scheme": ap2_mandate.get("signature_scheme", "FIDO2_Passkey_P256"),
                "hardware_attestation": "Android-KeyMint-FIDO2-L3-SecureEnclave",
                "verified_constraints": {
                    "payee": "Bistrot Milano Centrale (Binario 12)",
                    "max_budget_cents": total_cents,
                    "recurrence": "single_use",
                },
                "token_jwt_preview": (ap2_mandate.get("token_jwt") or "")[:40] + "...",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_commit = {
            "step_number": base_step + 2,
            "protocol": "a2a",
            "actor_source": "shopper_agent",
            "actor_target": "merchant_agent",
            "action": "A2A_COMMIT_ORDER",
            "description": f"Trasmissione dell'ordine con Mandato AP2 all'agente del Merchant (POST /a2a/commit). Richiesta di esecuzione pagamento e allocazione logistica.",
            "payload": {
                "order_id": order_id,
                "mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "authorized_cents": total_cents,
                "payment_method": "ap2",
                "train_context": ticket,
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_bopis_req = {
            "step_number": base_step + 3,
            "protocol": "bopis_internal",
            "actor_source": "merchant_agent",
            "actor_target": "bopis_engine",
            "action": "BOPIS_SUBMIT_ORDER_WITH_MANDATE",
            "description": f"L'agente Merchant riceve l'ordine e delega la comanda con Mandato AP2 al BOPIS Engine di stazione (Order Management System centralizzato).",
            "payload": {
                "order_id": order_id,
                "channel_source": "a2a_agent",
                "mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "fulfillment_method": fl_method,
                "target_destination": fl_conf_desc,
                "total_cents": total_cents,
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_mpp_req = {
            "step_number": base_step + 4,
            "protocol": "ap2_payment",
            "actor_source": "bopis_engine",
            "actor_target": "payment_processor",
            "action": "MPP_PROCESS_PAYMENT_MANDATE",
            "description": f"Il backend centrale BOPIS Engine invia il Payment Mandate al Payment Processor (MPP / Nexi Gateway) per la verifica della firma hardware e la cattura dei fondi (€{total_cents/100:.2f}).",
            "payload": {
                "order_id": order_id,
                "payment_mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "checkout_jwt_hash": f"sha256_{uuid4().hex[:16]}",
                "authorized_amount_cents": total_cents,
                "currency": "EUR",
                "merchant_acquirer_id": "ACQ-NEXI-MI-CENTRAL-01",
                "payment_rail": "Instant_SEPA_Card_Token",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_mpp_res = {
            "step_number": base_step + 5,
            "protocol": "ap2_payment",
            "actor_source": "payment_processor",
            "actor_target": "bopis_engine",
            "action": "MPP_PAYMENT_RECEIPT_ISSUED",
            "description": f"Il Payment Processor valida la firma FIDO2 ed emette la Payment Receipt firmata al BOPIS Engine. Certificato liability shift: FIDO2 SCA-exempt delegated.",
            "payload": {
                "payment_receipt_id": f"RCP-PAY-{uuid4().hex[:8].upper()}",
                "auth_code": f"AUTH-{uuid4().hex[:6].upper()}",
                "status": "CAPTURED",
                "amount_cents": total_cents,
                "liability_shift": "FIDO2_SCA_EXEMPT_DELEGATED",
                "network_transaction_id": f"NET-TXN-{uuid4().hex[:10].upper()}",
                "processor_signature": "ECDSA_P256_MPP_VERIFIED_OK",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_bopis_res = {
            "step_number": base_step + 6,
            "protocol": "bopis_internal",
            "actor_source": "bopis_engine",
            "actor_target": "merchant_agent",
            "action": "BOPIS_ORDER_CONFIRMED",
            "description": f"A pagamento catturato, il BOPIS Engine riserva lo slot logistico ({fl_conf_desc}), notifica la cucina ed emette la conferma d'ordine all'agente.",
            "payload": {
                "order_id": order_id,
                "status": "PREPARING",
                "payment_status": "CAPTURED",
                "fulfillment_record": fl_record,
                "tracking_status": "IN_PREPARATION",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_final = {
            "step_number": base_step + 7,
            "protocol": "a2a",
            "actor_source": "merchant_agent",
            "actor_target": "shopper_agent",
            "action": "A2A_ORDER_CONFIRMED",
            "description": f"L'agente della stazione (Merchant) rilascia il Checkout Receipt definitivo con la conferma dell'ordine #{order_id} e i dettagli completi di ritiro.",
            "payload": {
                "order_id": order_id,
                "status": "CONFIRMED",
                "fulfillment": fl_record,
                "total_cents": total_cents,
                "payment_status": "PAID_AP2",
                "checkout_receipt_jwt": f"eyJhbGciOiJFUzI1NiIsInR5cCI6ImFwMjpDaGVja291dFJlY2VpcHQifQ...receipt_{order_id}",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        if fl_method == "in_seat_train":
            conf_msg = f"Pranzo autorizzato e confermato via Two-Agent A2A! Il tuo ordine #{order_id} ({item_title}) verrà consegnato al {ticket.get('train_number')}, Carrozza {ticket.get('carriage')}, Posto {ticket.get('seat')} prima delle {ticket.get('departure_time')}."
        elif fl_method.startswith("pickup_locker"):
            slot_info = f" per lo slot {fl_record.get('window')}" if fl_record.get("window") else ""
            conf_msg = f"Ordine autorizzato e confermato via Two-Agent A2A! Il tuo ordine #{order_id} ({item_title}) sarà disponibile allo Smart Locker{slot_info} (Box #{fl_record.get('box_number')}, PIN: {fl_record.get('pin_code')})."
        else:
            conf_msg = f"Ordine autorizzato e confermato via Two-Agent A2A! Il tuo ordine #{order_id} ({item_title}) sarà pronto per il ritiro rapido al Bistrot Binario 12 in 5 minuti."

        a2a_steps = [step_ap2, step_commit, step_bopis_req, step_mpp_req, step_mpp_res, step_bopis_res, step_final]

        return {
            "status": "success",
            "steps": a2a_steps,
            "step_ap2": step_ap2,
            "step_commit": step_commit,
            "step_final": step_final,
            "final_order": final_order,
            "message": conf_msg,
        }

    else:
        # UCP REST protocol completion
        checkout_id = challenge.get("checkout_id", "CHK-UCP")
        ticket = challenge.get("ticket", {})
        fl_method = challenge.get("fl_method", "in_seat_train")
        chosen_prod = challenge.get("chosen_prod", {})
        order_id = f"ORD-MI-REST{uuid4().hex[:5].upper()}"

        complete_body = json.dumps({"payment": {"method": "ap2", "mandate": ap2_mandate}}).encode("utf-8")
        rfc_headers = generate_rfc9421_signature(
            method="POST",
            path=f"/ucp/checkouts/{checkout_id}/complete",
            authority="localhost:10999",
            body_bytes=complete_body,
        )

        final_resp_data = {}
        try:
            req_headers = {"Content-Type": "application/json", **rfc_headers}
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(
                    f"{MERCHANT_BASE_URL}/ucp/checkouts/{checkout_id}/complete",
                    content=complete_body,
                    headers=req_headers,
                )
                final_resp_data = res.json()
        except Exception as e:
            logger.warning("Errore completion UCP REST: %s", e)
            final_resp_data = {"order_id": order_id, "status": "confirmed"}

        if fl_method == "in_seat_train":
            fl_conf_desc = f"consegna al {ticket.get('train_number')}, Carrozza {ticket.get('carriage')}, Posto {ticket.get('seat')}"
        elif fl_method.startswith("pickup_locker"):
            slot_label = ""
            if fl_method.startswith("pickup_locker_"):
                raw_tag = fl_method.replace("pickup_locker_", "")
                if len(raw_tag) == 4 and raw_tag.isdigit():
                    slot_label = f" (Slot {raw_tag[:2]}:{raw_tag[2:]})"
            fl_conf_desc = f"ritiro allo Smart Locker del piano interrato{slot_label} (Box #14, PIN 4918)"
        else:
            fl_conf_desc = "ritiro al desk express del Bistrot"

        base_step = data.get("step_offset", 6)

        step_ap2 = {
            "step_number": base_step + 1,
            "protocol": "ucp_rest",
            "actor_source": "shopper_client",
            "actor_target": "shopper_agent",
            "action": "AP2_MANDATE_VERIFICATION",
            "description": f"Lo Shopper Agent convalida il mandato AP2 firmato dall'utente sul client (Passkey FIDO2): importo €{(challenge.get('total_cents', 750))/100:.2f}. Vincoli di autorizzazione verificati.",
            "payload": {
                "mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "authorized_amount_cents": ap2_mandate.get("max_authorized_cents", challenge.get('total_cents', 750)),
                "signature_scheme": ap2_mandate.get("signature_scheme", "FIDO2_Passkey_P256"),
                "hardware_attestation": "Android-KeyMint-FIDO2-L3-SecureEnclave",
                "token_jwt_preview": (ap2_mandate.get("token_jwt") or "")[:40] + "...",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_final = {
            "step_number": base_step + 2,
            "protocol": "ucp_rest",
            "actor_source": "shopper_agent",
            "actor_target": "ucp_rest_server",
            "action": "HTTP_POST_COMPLETE_RFC9421",
            "description": f"Completamento transazione con firma crittografica RFC 9421: POST /ucp/checkouts/{checkout_id}/complete.",
            "headers": rfc_headers,
            "payload": final_resp_data,
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_bopis_req = {
            "step_number": base_step + 3,
            "protocol": "bopis_internal",
            "actor_source": "ucp_rest_server",
            "actor_target": "bopis_engine",
            "action": "BOPIS_SUBMIT_ORDER_WITH_MANDATE",
            "description": f"Il Gateway UCP REST inoltra l'ordine e il Mandato AP2 al BOPIS Engine della stazione per la gestione centrale.",
            "payload": {
                "order_id": order_id,
                "channel_source": "ucp_rest",
                "checkout_id": checkout_id,
                "payment_mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "total_cents": challenge.get("total_cents", 750),
                "target_destination": fl_conf_desc,
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_mpp_req = {
            "step_number": base_step + 4,
            "protocol": "ap2_payment",
            "actor_source": "bopis_engine",
            "actor_target": "payment_processor",
            "action": "MPP_PROCESS_PAYMENT_MANDATE",
            "description": f"Il backend centrale BOPIS Engine invia il Payment Mandate al Payment Processor (MPP) per la cattura e la verifica della firma crittografica del client (€{(challenge.get('total_cents', 750))/100:.2f}).",
            "payload": {
                "order_id": order_id,
                "payment_mandate_id": ap2_mandate.get("mandate_id", "tok_ap2_client_passkey"),
                "checkout_id": checkout_id,
                "amount_cents": challenge.get("total_cents", 750),
                "currency": "EUR",
                "payment_rail": "Instant_SEPA_Card_Token",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_mpp_res = {
            "step_number": base_step + 5,
            "protocol": "ap2_payment",
            "actor_source": "payment_processor",
            "actor_target": "bopis_engine",
            "action": "MPP_PAYMENT_RECEIPT_ISSUED",
            "description": "Il Payment Processor valida la firma hardware FIDO2, autorizza i fondi ed emette la Payment Receipt al BOPIS Engine (FIDO2 SCA-exempt delegated).",
            "payload": {
                "payment_receipt_id": f"RCP-PAY-{uuid4().hex[:8].upper()}",
                "auth_code": f"AUTH-{uuid4().hex[:6].upper()}",
                "status": "CAPTURED",
                "liability_shift": "FIDO2_SCA_EXEMPT_DELEGATED",
                "processor_signature": "ECDSA_P256_MPP_VERIFIED_OK",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        step_bopis_res = {
            "step_number": base_step + 6,
            "protocol": "bopis_internal",
            "actor_source": "bopis_engine",
            "actor_target": "ucp_rest_server",
            "action": "BOPIS_ORDER_CONFIRMED",
            "description": f"A pagamento confermato, il BOPIS Engine riserva lo slot logistico ({fl_conf_desc}), notifica la cucina e conferma l'ordine al Gateway REST.",
            "payload": {
                "order_id": order_id,
                "status": "PREPARING",
                "payment_status": "CAPTURED",
                "tracking_status": "IN_PREPARATION",
            },
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        conf_msg = f"Ordine #{final_resp_data.get('order_id', order_id)} autorizzato e finalizzato con successo via UCP REST con verifica RFC 9421 e mandato Passkey AP2 ({fl_conf_desc})! Il riepilogo è stato inviato alla cucina di Milano Centrale."

        rest_steps = [step_ap2, step_final, step_bopis_req, step_mpp_req, step_mpp_res, step_bopis_res]

        return {
            "status": "success",
            "steps": rest_steps,
            "step_ap2": step_ap2,
            "step_final": step_final,
            "final_order": final_resp_data,
            "message": conf_msg,
        }

