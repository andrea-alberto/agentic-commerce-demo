# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
from __future__ import annotations
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field


class TrainTicket(BaseModel):
    train_number: str = Field(default="Frecciarossa 9540", description="Numero treno (es. Frecciarossa 9540)")
    pnr: str = Field(default="FR-9540-MR", description="Codice prenotazione PNR")
    origin: str = Field(default="Milano Centrale", description="Stazione di partenza")
    destination: str = Field(default="Roma Termini", description="Stazione di arrivo")
    departure_time: str = Field(default="13:10", description="Orario di partenza programmato (HH:MM)")
    platform: str = Field(default="14", description="Binario di partenza della stazione")
    carriage: str = Field(default="4", description="Numero carrozza")
    seat: str = Field(default="12D", description="Posto a sedere")
    class_service: str = Field(default="Area Silenzio • Prima Classe", description="Livello di servizio a bordo")


class TravelerPreferences(BaseModel):
    dietary: str = Field(default="No carne rossa • Piatti leggeri e bio", description="Preferenze dietetiche testuali")
    preferred_fulfillment: str = Field(default="in_seat_train", description="Metodo preferito ('in_seat_train', 'pickup_locker', 'pickup_express')")
    max_budget_cents: int = Field(default=2500, description="Massimale di spesa per il pasto in centesimi (es. 2500 = €25.00)")
    notes: str = Field(default="Pasto da consumare a bordo durante il viaggio", description="Note per l'assistente")
    allergens_to_avoid: List[str] = Field(default_factory=list, description="Allergeni da escludere rigorosamente (es. ['glutine', 'lattosio'])")
    health_goals: List[str] = Field(default_factory=list, description="Obiettivi salute (es. ['high_protein', 'low_salt', 'no_added_sugars'])")
    avoid_ultra_processed: bool = Field(default=False, description="Preferenza per alimenti non ultra-processati (solo NOVA 1 o 3)")
    coffee_preference: Optional[str] = Field(default=None, description="Preferenza caffè ('espresso_hot', 'cold_brew_specialty')")


class AP2Delegation(BaseModel):
    enabled: bool = Field(default=True, description="Indica se il mandato autonomo AP2 è attivo")
    mandate_type: str = Field(default="ap2_cart_mandate", description="Tipo di mandato AP2 (ap2_cart_mandate / mcp_shopper_delegation)")
    max_amount_cents: int = Field(default=3000, description="Massimale autorizzato senza tocco biometrico (€30.00)")
    currency: str = Field(default="EUR", description="Valuta del mandato")
    credential_manager: str = Field(default="LocalCredentialManager", description="Gestore chiavi FIDO2 / TPM")
    token_id: str = Field(default="tok_lcm_passkey_fr9540", description="ID token della passkey delegata")


class TravelerContext(BaseModel):
    traveler_id: str = Field(default="usr_devfest_mario_rossi", description="Identificativo univoco viaggiatore")
    name: str = Field(default="Mario Rossi", description="Nome e cognome viaggiatore")
    email: str = Field(default="mario.rossi@devfest.it", description="Email associata")
    loyalty_tier: str = Field(default="CartaFRECCIA Platino", description="Livello programma fedeltà")
    loyalty_code: str = Field(default="FF-884920", description="Codice tessera fedeltà")
    scenario_preset_id: str = Field(default="scenario_departing_soon", description="ID dello scenario preimpostato")
    ticket: TrainTicket = Field(default_factory=TrainTicket)
    preferences: TravelerPreferences = Field(default_factory=TravelerPreferences)
    ap2: AP2Delegation = Field(default_factory=AP2Delegation)


class UcpProduct(BaseModel):
    id: str
    name: str
    category: str
    price_cents: int
    price: float
    is_hot: bool = False
    image_url: Optional[str] = None
    description: Optional[str] = None
    packaging_type: Optional[str] = None  # prepackaged / fresh_service
    net_weight_g: Optional[int] = None
    nutrition: Optional[Dict[str, Any]] = None
    processing_level: Optional[Dict[str, Any]] = None
    dietary_profile: Optional[Dict[str, Any]] = None
    coffee_profile: Optional[Dict[str, Any]] = None
    sustainability: Optional[Dict[str, Any]] = None
    travel_profile: Optional[Dict[str, Any]] = None
    tech_specs: Optional[Dict[str, Any]] = None


class UcpCheckoutItem(BaseModel):
    product_id: str
    title: str
    quantity: int = 1
    price_cents: int
    is_hot: bool = False
    image_url: Optional[str] = None


class UcpFulfillment(BaseModel):
    method: str  # pickup_locker, in_seat_train, pickup_express, table_service
    label: str
    details: Dict[str, Any] = Field(default_factory=dict)
    delivery_fee_cents: int = 0


class BopisOrder(BaseModel):
    order_id: str
    channel_source: str
    channel_label: str
    status: str
    fulfillment_type: str
    fulfillment_details: Dict[str, Any] = Field(default_factory=dict)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    totals: Dict[str, Any] = Field(default_factory=dict)
    buyer: Dict[str, Any] = Field(default_factory=dict)
    payment_method: Optional[str] = None
    payment_info: Optional[Dict[str, Any]] = None
    ap2_verification: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    placed_at_display: Optional[str] = None
    requested_delivery_display: Optional[str] = None
    lead_time_minutes: Optional[int] = None
