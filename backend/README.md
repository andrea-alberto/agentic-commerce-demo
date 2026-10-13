# Milan Central Travel Retail Agent Suite (UCP, AP2 & BOPIS)

Python backend services for the **Agentic Commerce** demo suite at **GDG DevFest Milano 2026**.

This module provides two agentic microservices powered by **Google Gemini 2.5 Flash** and the physical station fulfillment engine (BOPIS Engine):

1. **`backend-merchant` (Port 10999)**: Milan Central Travel Retail Hub & Merchant Agent.
2. **`backend-shopper` (Port 10998)**: Traveler's Personal Shopper Agent Service.

---

## 1. Microservices Architecture

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

## 2. Dual Artificial Intelligence: Gemini 2.5 Flash

Both agents leverage **`gemini-2.5-flash`** with **Structured Outputs (Pydantic)**:

### 2.1 Personal Shopper Agent (`backend-shopper/shopper_service.py`)
- **Pydantic Schema**: `ShopperIntentAnalysis` (`resolved_fulfillment`, `fulfillment_reason`, `semantic_a2a_inquiry`, `desired_items_summary`).
- **Reasoning**:
  - Infers `in_seat_train` if the traveler specifies coach/seat numbers ("coach 4", "onboard").
  - Injects railway ticket metadata (train, departure time, platform, coach, seat).
  - Generates rich, contextual machine-to-machine A2A inquiries for the station merchant agent.

### 2.2 Merchant Agent (`backend/src/travel_retail_agent/main.py`)
- **Pydantic Schema**: `MerchantProductSelection` (`product_ids: list[str]`, `commercial_explanation: str`).
- **Reasoning**:
  - Evaluates live inventory (`products.json`).
  - Recognizes single items or multi-item combos (e.g. *"double espresso and warm focaccia"* $\to$ `['CAFFE-001', 'TOAST-003']`, total €9.00).
  - Handles precedence of explicitly requested items over generic dietary constraints.
  - Generates a courteous commercial explanation.
- **Delegation to BOPIS Engine (`store.py`)**:
  - Calculates temperature (`is_hot: True`).
  - Automatically bars Smart Lockers for hot items or fresh coffee.
  - Validates time-critical delivery windows (e.g. in-seat delivery at 13:05 for a 13:10 departure on Platform 14).

---

## 3. Exposed Channels & Protocols

### 3.1 Merchant Hub (`:10999`)
- **A2A Semantic Federation**:
  - `POST /a2a/negotiate`: Receives A2A inquiries, invokes Gemini 2.5 Flash and the BOPIS Engine.
  - `POST /a2a/commit`: Commits order with verified AP2 mandate and registers into the BOPIS Hub.
- **UCP Standard REST Binding**:
  - `GET /.well-known/ucp`: Protocol discovery manifest.
  - `GET /ucp/catalog/products`: Indexed catalog with thermal flags and categories.
  - `POST /ucp/checkouts`: Initiates checkout session.
  - `PATCH /ucp/checkouts/{id}`: Configures fulfillment channel and station constraints.
  - `POST /ucp/checkouts/{id}/complete`: Cryptographic verification of **RFC 9421 ECDSA-P256** signatures and AP2 mandates.
- **Web MCP Server (Model Context Protocol)**:
  - `POST /mcp`: JSON-RPC 2.0 endpoint for tool execution.
  - `GET /mcp/tools`: Exposes tools: `search_catalog`, `get_product`, `add_to_cart`, `calculate_station_fulfillment`, `create_checkout_intent`.
- **BOPIS Dispatcher Hub**:
  - `GET /bopis/orders`: Omnichannel aggregated orders.
  - `POST /bopis/orders`: Direct order submission.
  - `PATCH /bopis/orders/{id}/status`: State transitions (`in_preparation`, `ready_for_pickup`, `completed`).
  - `GET /bopis/stats`: Real-time fulfillment metrics.

### 3.2 Personal Shopper Agent (`:10998`)
- `GET /shopper/context`: Read traveler profile, train ticket, and dietary preferences.
- `PUT /shopper/context`: Dynamic context update.
- `POST /shopper/context/preset/{preset_id}`: Instant switch between travel scenarios (`scenario_departing_soon` vs `scenario_long_layover`).
- `POST /shopper/mission/stream`: Server-Sent Events (SSE) progressive streaming of protocol steps (Demo 3 A2A and Demo 4 UCP REST).
- `POST /shopper/mission/authorize`: Cryptographic AP2 Passkey mandate validation and order commit.

---

## 4. Operational Commands

From the monorepo root directory:

```powershell
# Launch Station Merchant Hub (:10999)
npx nx run backend-merchant:serve

# Launch Personal Shopper Agent (:10998)
npx nx run backend-shopper:serve

# Execute Web MCP Test Suite
npx nx run backend-merchant:test:mcp
```

### Environment Variables (`.env`)
```env
GOOGLE_API_KEY=your_google_ai_studio_api_key
FIRESTORE_PROJECT_ID=agentic-comm-mi-devfest-2026
```
*(In the absence of Firestore or Google API keys, the system automatically activates deterministic local fallbacks).*
