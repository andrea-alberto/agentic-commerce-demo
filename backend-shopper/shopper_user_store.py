# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Store e Gestore Utenti per il Dominio Personal Shopper Agent (Assistente Personale Sovrano).
Gestisce la collezione Firestore 'shopper_users' con fallback e persistenza locale.
Nessun auto-provisioning: gli utenti devono essere censiti manualmente.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend/src to path for shared package
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.join(os.path.dirname(current_dir), "backend", "src")
if backend_src_dir not in sys.path:
    sys.path.insert(0, backend_src_dir)

from shared.models import TravelerContext, TrainTicket, TravelerPreferences, AP2Delegation

logger = logging.getLogger("backend_shopper.user_store")

DEFAULT_PROJECT_ID = "agentic-comm-mi-devfest-2026"
SHOPPER_USERS_COLLECTION = "shopper_users"


class ShopperUserStore:
    """Gestione profili viaggiatori per l'agente Personal Shopper."""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or DEFAULT_PROJECT_ID
        self._data_file = Path(__file__).parent / "data" / "shopper_users.json"
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._firestore_client = None
        self._firestore_enabled = False

        self._load_local_cache()
        self._init_firestore()

    def _init_firestore(self):
        """Tenta di connettersi a Firestore per la collezione shopper_users."""
        try:
            from google.cloud import firestore
            self._firestore_client = firestore.Client(project=self.project_id)
            _ = list(self._firestore_client.collection(SHOPPER_USERS_COLLECTION).limit(1).stream())
            self._firestore_enabled = True
            logger.info("ShopperUserStore: Firestore collegato con successo sul progetto '%s'!", self.project_id)
            self._sync_from_firestore()
        except Exception as e:
            self._firestore_enabled = False
            self._firestore_client = None
            logger.info(
                "ShopperUserStore: Firestore non disponibile o credenziali non configurate (fallback locale attivo): %s", e
            )

    def _sync_from_firestore(self):
        """Sincronizza i dati da Firestore."""
        if not self._firestore_enabled or not self._firestore_client:
            return
        try:
            docs = self._firestore_client.collection(SHOPPER_USERS_COLLECTION).stream()
            count = 0
            for doc in docs:
                data = doc.to_dict()
                email = (data.get("email") or doc.id).strip().lower()
                if email:
                    self._local_cache[email] = data
                    count += 1
            if count > 0:
                self._save_local_cache()
                logger.info("ShopperUserStore: Sincronizzati %d viaggiatori da Firestore.", count)
            else:
                self._seed_to_firestore()
        except Exception as e:
            logger.error("ShopperUserStore: Errore sync da Firestore: %s", e)

    def _seed_to_firestore(self):
        """Inizializza la collezione Firestore con i dati locali di seed se vuota."""
        if not self._firestore_enabled or not self._firestore_client:
            return
        try:
            for email, data in self._local_cache.items():
                self._firestore_client.collection(SHOPPER_USERS_COLLECTION).document(email).set(data)
            logger.info("ShopperUserStore: Popolata collezione Firestore shopper_users con dati di seed.")
        except Exception as e:
            logger.warning("ShopperUserStore: Impossibile scrivere seed su Firestore: %s", e)

    def _load_local_cache(self):
        """Carica il file JSON locale."""
        if self._data_file.exists():
            try:
                with self._data_file.open("r", encoding="utf-8") as f:
                    users = json.load(f)
                    for u in users:
                        email = (u.get("email") or "").strip().lower()
                        if email:
                            self._local_cache[email] = u
            except Exception as e:
                logger.warning("ShopperUserStore: Impossibile caricare cache viaggiatori: %s", e)

        # Fallback garantito per il viaggiatore predefinito
        seed_email = os.getenv("DEFAULT_BUYER_EMAIL", "alex.traveler@example.com").strip().lower()
        seed_name = os.getenv("DEFAULT_BUYER_NAME", "Alex Rossi")
        if seed_email not in self._local_cache:
            self._local_cache[seed_email] = {
                "email": seed_email,
                "display_name": seed_name,
                "allowed_apps": ["shopper-client"],
                "active": True,
                "created_at": "2026-10-07T21:00:00Z",
                "loyalty_tier": "FrecciaClub Gold",
                "loyalty_code": "FF-AR2026",
                "ticket": {
                    "train_number": "Frecciarossa 9540",
                    "pnr": "FR-9540-AR",
                    "origin": "Milano Centrale",
                    "destination": "Roma Termini",
                    "departure_time": "13:10",
                    "platform": "14",
                    "carriage": "4",
                    "seat": "12D",
                    "class_service": "Area Silenzio • Prima Classe"
                },
                "preferences": {
                    "preferred_fulfillment": "in_seat_train",
                    "dietary": "Selezione Viaggio Gourmet • Piatti leggeri e bio",
                    "max_budget_cents": 3500,
                    "notes": "Pasto da consegnare al posto prima della partenza"
                },
                "ap2": {
                    "enabled": True,
                    "mandate_type": "ap2_cart_mandate",
                    "max_amount_cents": 3500,
                    "currency": "EUR",
                    "credential_manager": "LocalCredentialManager",
                    "token_id": "tok_lcm_passkey_fr9540_ar"
                }
            }
            self._save_local_cache()

    def _save_local_cache(self):
        """Salva la cache locale."""
        try:
            with self._data_file.open("w", encoding="utf-8") as f:
                json.dump(list(self._local_cache.values()), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("ShopperUserStore: Errore salvataggio file viaggiatori: %s", e)

    def get_user(self, email: Optional[str]) -> Optional[Dict[str, Any]]:
        """Restituisce il record viaggiatore se presente. Nessun auto-provisioning."""
        if not email:
            return None
        return self._local_cache.get(email.strip().lower())

    def get_traveler_context(self, email: Optional[str]) -> TravelerContext:
        """Costruisce l'oggetto TravelerContext per l'utente, usando i dati censiti o il default di fallback."""
        seed_email = os.getenv("DEFAULT_BUYER_EMAIL", "alex.traveler@example.com").strip().lower()
        seed_name = os.getenv("DEFAULT_BUYER_NAME", "Alex Rossi")
        u = self.get_user(email)
        if not u:
            # Fallback sul viaggiatore master censito
            u = self.get_user(seed_email) or {}

        ticket_data = u.get("ticket") or {}
        pref_data = u.get("preferences") or {}
        ap2_data = u.get("ap2") or {}

        return TravelerContext(
            traveler_id=f"usr_shopper_{u.get('email', seed_email).replace('@', '_').replace('.', '_')}",
            name=u.get("display_name", seed_name),
            email=u.get("email", seed_email),
            loyalty_tier=u.get("loyalty_tier", "FrecciaClub Gold"),
            loyalty_code=u.get("loyalty_code", "FF-AR2026"),
            ticket=TrainTicket(**ticket_data) if ticket_data else TrainTicket(),
            preferences=TravelerPreferences(**pref_data) if pref_data else TravelerPreferences(),
            ap2=AP2Delegation(**ap2_data) if ap2_data else AP2Delegation()
        )

    def record_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Salva o aggiorna manualmente un profilo viaggiatore."""
        email = (user_data.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Campo 'email' obbligatorio")
        self._local_cache[email] = user_data
        self._save_local_cache()
        if self._firestore_enabled and self._firestore_client:
            try:
                self._firestore_client.collection(SHOPPER_USERS_COLLECTION).document(email).set(user_data)
            except Exception as e:
                logger.error("ShopperUserStore: Errore scrittura su Firestore: %s", e)
        return user_data


# Global Singleton
shopper_user_store = ShopperUserStore()
