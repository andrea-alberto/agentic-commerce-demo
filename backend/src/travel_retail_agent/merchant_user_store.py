# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Store e Gestore Autorizzazioni Utenti per il Dominio Merchant (Bistrot Milano Centrale).
Gestisce la collezione Firestore 'merchant_users' con fallback e persistenza locale.
Nessun auto-provisioning: gli utenti devono essere censiti manualmente.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("travel_retail_agent.merchant_users")

DEFAULT_PROJECT_ID = "agentic-comm-mi-devfest-2026"
MERCHANT_USERS_COLLECTION = "merchant_users"


class MerchantUserStore:
    """Gestione anagrafica e autorizzazioni utenti per il dominio Merchant (Bistrot / Stazione)."""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or DEFAULT_PROJECT_ID
        self._data_file = Path(__file__).parent / "data" / "merchant_users.json"
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._firestore_client = None
        self._firestore_enabled = False

        self._load_local_cache()
        self._init_firestore()

    def _get_operator_whitelist(self) -> List[str]:
        """Estrae la whitelist di operatori dalla variabile d'ambiente OPERATOR_EMAILS."""
        raw = os.getenv("OPERATOR_EMAILS", "merchant@agentic-commerce.demo")
        return [e.strip().lower() for e in raw.split(",") if e.strip()]

    def _init_firestore(self):
        """Tenta di connettersi a Firestore per la sincronizzazione della collezione merchant_users."""
        try:
            from google.cloud import firestore
            self._firestore_client = firestore.Client(project=self.project_id)
            # Test rapido di connettività
            _ = list(self._firestore_client.collection(MERCHANT_USERS_COLLECTION).limit(1).stream())
            self._firestore_enabled = True
            logger.info("MerchantUserStore: Firestore collegato con successo sul progetto '%s'!", self.project_id)
            self._sync_from_firestore()
        except Exception as e:
            self._firestore_enabled = False
            self._firestore_client = None
            logger.info(
                "MerchantUserStore: Firestore non disponibile o credenziali non configurate (fallback locale attivo): %s", e
            )

    def _sync_from_firestore(self):
        """Sincronizza gli utenti da Firestore nella cache locale."""
        if not self._firestore_enabled or not self._firestore_client:
            return
        try:
            docs = self._firestore_client.collection(MERCHANT_USERS_COLLECTION).stream()
            count = 0
            for doc in docs:
                data = doc.to_dict()
                email = (data.get("email") or doc.id).strip().lower()
                if email:
                    self._local_cache[email] = data
                    count += 1
            if count > 0:
                self._save_local_cache()
                logger.info("MerchantUserStore: Sincronizzati %d utenti da Firestore.", count)
            else:
                # Se Firestore è vuoto ma abbiamo dati locali di seed, popoliamo Firestore
                self._seed_to_firestore()
        except Exception as e:
            logger.error("MerchantUserStore: Errore sync da Firestore: %s", e)

    def _seed_to_firestore(self):
        """Scrive i dati locali di seed su Firestore se la collezione remota è vuota."""
        if not self._firestore_enabled or not self._firestore_client:
            return
        try:
            for email, data in self._local_cache.items():
                self._firestore_client.collection(MERCHANT_USERS_COLLECTION).document(email).set(data)
            logger.info("MerchantUserStore: Popolata collezione Firestore merchant_users con dati di seed.")
        except Exception as e:
            logger.warning("MerchantUserStore: Impossibile scrivere seed su Firestore: %s", e)

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
                logger.warning("MerchantUserStore: Impossibile caricare cache utenti locale: %s", e)

        # Assicura la presenza dell'operatore di default come fallback garantito
        seed_email = (self._get_operator_whitelist() or ["merchant@agentic-commerce.demo"])[0]
        seed_name = os.getenv("OPERATOR_NAME", "Store Manager")
        if seed_email not in self._local_cache:
            self._local_cache[seed_email] = {
                "email": seed_email,
                "display_name": seed_name,
                "role": "operator",
                "allowed_apps": ["bopis-dashboard", "storefront-webmcp", "chat-client"],
                "loyalty_tier": "FrecciaClub Gold",
                "loyalty_code": "FF-MGR2026",
                "active": True,
                "created_at": "2026-10-07T21:00:00Z"
            }
            self._save_local_cache()

    def _save_local_cache(self):
        """Salva la cache nel file JSON locale."""
        try:
            with self._data_file.open("w", encoding="utf-8") as f:
                json.dump(list(self._local_cache.values()), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("MerchantUserStore: Errore salvataggio file utenti: %s", e)

    def get_user(self, email: Optional[str]) -> Optional[Dict[str, Any]]:
        """Restituisce il record utente se presente. NESSUN auto-provisioning."""
        if not email:
            return None
        norm = email.strip().lower()
        return self._local_cache.get(norm)

    def is_operator(self, email: Optional[str]) -> bool:
        """Verifica se l'utente ha il ruolo di operatore (nella whitelist .env o in merchant_users)."""
        if not email:
            return False
        norm = email.strip().lower()

        # 1. Controllo immediato whitelist .env
        if norm in self._get_operator_whitelist():
            return True

        # 2. Controllo documento merchant_users
        u = self.get_user(norm)
        if u and u.get("active", True):
            if u.get("role") in ("operator", "admin"):
                return True
            if "bopis-dashboard" in u.get("allowed_apps", []):
                return True

        return False

    def is_allowed_for_app(self, email: Optional[str], app_name: str) -> bool:
        """Verifica se l'utente è autorizzato ad accedere a una specifica applicazione."""
        if not email:
            return False
        norm = email.strip().lower()

        # Operatori whitelist hanno accesso a tutto
        if norm in self._get_operator_whitelist():
            return True

        u = self.get_user(norm)
        if not u or not u.get("active", True):
            return False

        if u.get("role") in ("operator", "admin"):
            return True

        return app_name in u.get("allowed_apps", [])

    def record_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Salva o aggiorna manualmente un utente nella collezione merchant_users."""
        email = (user_data.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Campo 'email' obbligatorio per la registrazione utente")

        self._local_cache[email] = user_data
        self._save_local_cache()

        if self._firestore_enabled and self._firestore_client:
            try:
                self._firestore_client.collection(MERCHANT_USERS_COLLECTION).document(email).set(user_data)
                logger.info("MerchantUserStore: Utente %s salvato su Firestore.", email)
            except Exception as e:
                logger.error("MerchantUserStore: Errore salvataggio utente su Firestore: %s", e)

        return user_data

    def all_users(self) -> List[Dict[str, Any]]:
        """Elenco di tutti gli utenti registrati."""
        return list(self._local_cache.values())


# Istanza Singleton per il backend merchant
merchant_user_store = MerchantUserStore()
