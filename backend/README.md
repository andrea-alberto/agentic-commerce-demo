# Milano Centrale Travel Retail Agent Suite (UCP, AP2 & BOPIS)

Backend Python per la demo **Agentic Commerce** al **GDG DevFest Milano 2026**.

Questo modulo fornisce i due microservizi agentici basati su **Google Gemini 2.5 Flash** e il motore logistico di stazione (BOPIS Engine):

1. **`backend-merchant` (Porta 10999)**: Milano Centrale Travel Retail Hub & Merchant Agent.
2. **`backend-shopper` (Porta 10998)**: Personal Shopper Agent Service del Viaggiatore.

---

## 1. Architettura dei Microservizi

```
                             [ Personal Shopper Client (:4203) ]
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │ SSE Mission Stream & Traveler Context        │
                      ▼                                               ▼
          ┌───────────────────────────┐                   ┌───────────────────────────┐
          │  backend-shopper (:10998) │                   │ backend-merchant (:10999) │
          │  • Gemini 2.5 Flash       │ ── A2A M2M ────►  │ • Gemini 2.5 Flash        │
          │  • Intent & Delivery      │                   │ • Catalog & Combo Bundling│
          │  • Rail Ticket Context    │ ── UCP REST ───►  │ • UCP REST + RFC 9421     │
          │  • Passkey AP2 Validator  │                   │ • Station BOPIS Engine    │
          └───────────────────────────┘                   └─────────────┬─────────────┘
                                                                        │
                                                                        ▼
                                                          [ BOPIS Dashboard (:4201) ]
```

---

## 2. Intelligenza Artificiale con Gemini 2.5 Flash

Entrambi gli agenti utilizzano **`gemini-2.5-flash`** con **Structured Outputs (Pydantic)**:

### 2.1 Personal Shopper Agent (`backend-shopper/shopper_service.py`)
- **Schema Pydantic**: `ShopperIntentAnalysis` (`resolved_fulfillment`, `fulfillment_reason`, `semantic_a2a_inquiry`, `desired_items_summary`).
- **Ragionamento**:
  - Se l'utente specifica la carrozza o il posto ("carrozza 4", "a bordo"), deduce `in_seat_train`.
  - Inietta i dati del biglietto ferroviario (treno, orario, binario, carrozza, posto).
  - Formula una richiesta A2A Machine-to-Machine ricca e contestualizzata per l'agente della stazione.

### 2.2 Merchant Agent (`backend/src/travel_retail_agent/main.py`)
- **Schema Pydantic**: `MerchantProductSelection` (`product_ids: list[str]`, `commercial_explanation: str`).
- **Ragionamento**:
  - Esamina il catalogo reale `products.json`.
  - Riconosce ordini singoli o combo multi-articolo (es. *"caffè doppio e focaccia ligure"* ➔ `['CAFFE-001', 'TOAST-003']`, totale €9.00).
  - Gestisce la precedenza dei prodotti esplicitamente richiesti rispetto a vincoli dietetici generici.
  - Genera una spiegazione commerciale cordiale in italiano.
- **Delega al BOPIS Engine (`store.py`)**:
  - Calcola la temperatura (`is_hot: True`).
  - Esclude automaticamente gli Smart Locker per cibi caldi o caffè.
  - Verifica la finestra oraria di consegna (es. consegna al posto 13:05 per partenza 13:10 al Binario 14).

---

## 3. Canali e Protocolli Esposti

### 3.1 Merchant Hub (`:10999`)
- **A2A Semantic Federation**:
  - `POST /a2a/negotiate`: Riceve la richiesta A2A, interroga Gemini 2.5 Flash e il BOPIS Engine.
  - `POST /a2a/commit`: Finalizza l'ordine con mandato AP2 verificato e registra nel BOPIS Hub.
- **UCP Standard REST Binding**:
  - `GET /.well-known/ucp`: Discovery manifest del protocollo.
  - `GET /ucp/catalog/products`: Catalogo prodotti indicizzato con temperature e categorie.
  - `POST /ucp/checkouts`: Creazione sessione di checkout.
  - `PATCH /ucp/checkouts/{id}`: Configurazione del canale di fulfillment e stazione.
  - `POST /ucp/checkouts/{id}/complete`: Convalida crittografica delle firme **RFC 9421 ECDSA-P256** e del mandato AP2.
- **Web MCP Server (Model Context Protocol)**:
  - `POST /mcp`: Endpoint JSON-RPC 2.0 per tool execution.
  - `GET /mcp/tools`: Esposizione dei tool `search_catalog`, `get_product`, `add_to_cart`, `calculate_station_fulfillment`, `create_checkout_intent`.
- **BOPIS Dispatcher Hub**:
  - `GET /bopis/orders`: Lista ordini unificati omnichannel.
  - `POST /bopis/orders`: Creazione ordine diretto.
  - `PATCH /bopis/orders/{id}/status`: Aggiornamento stato (in preparazione, pronto, completato).
  - `GET /bopis/stats`: Metriche in tempo reale.

### 3.2 Personal Shopper Agent (`:10998`)
- `GET /shopper/context`: Lettura profilo viaggiatore, biglietto treno e preferenze.
- `PUT /shopper/context`: Aggiornamento dinamico del contesto.
- `POST /shopper/context/preset/{preset_id}`: Switch istantaneo tra scenari (`scenario_departing_soon` vs `scenario_long_layover`).
- `POST /shopper/mission/stream`: Streaming Server-Sent Events (SSE) progressivo dei passaggi del protocollo (Demo 3 A2A e Demo 4 UCP REST).
- `POST /shopper/mission/authorize`: Convalida crittografica del mandato Passkey AP2 e commit finale dell'ordine.

---

## 4. Comandi Operativi

Dalla cartella principale del monorepo:

```powershell
# Avvio Merchant Agent Hub (:10999)
npx nx run backend-merchant:serve

# Avvio Personal Shopper Agent (:10998)
npx nx run backend-shopper:serve

# Esecuzione test Web MCP
npx nx run backend-merchant:test:mcp
```

### Variabili d'Ambiente (`.env`)
```env
GOOGLE_API_KEY=la_tua_chiave_google_ai_studio
FIRESTORE_PROJECT_ID=agentic-comm-mi-devfest-2026
```
*(In assenza di Firestore o API Key, il sistema attiva automaticamente i fallback deterministici locali).*
