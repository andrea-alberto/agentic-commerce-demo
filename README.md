# Agentic Commerce Demo — UCP, Web MCP & Physical Retail

> **Agentic Commerce: Redefining E-Commerce across UCP, Web MCP, and Physical Retail**  
> *Nx multi-project monorepo featuring 4 Angular 22 applications, 2 Python microservices powered by Gemini 2.5 Flash, AP2 Passkey security, and a physical station retail logistics engine (BOPIS Engine).*  
>  
> 💡 *Originally designed and showcased at GDG DevFest Milano 2026 as a reference architecture for open Agentic Commerce.*

---

## 1. Project Vision

This reference demo suite demonstrates the transition of electronic commerce towards **Agentic Commerce**: an open, standards-based ecosystem where autonomous AI agents cooperate with physical merchants and web storefronts to execute real-world purchases on behalf of travelers.

The concrete demonstration scenario is **High-Speed Travel Retail at Milan Central Station**: a passenger arriving or traveling aboard a high-speed train (Frecciarossa / Italo) requesting meals, coffee, or tech essentials from their personal assistant, with time-critical delivery directly to their train seat, express station counter pickup, or automated Smart Locker retrieval.

### The Three Open Standards
1. **Universal Commerce Protocol (UCP)**: An open standard (co-developed by Google in collaboration with Shopify, Walmart, and retail partners) unifying service discovery (`/.well-known/ucp`), cart lifecycle, checkout sessions, and multi-channel fulfillment (BOPIS).
2. **Agent Payment Protocol (AP2)**: A cryptographic payment protocol featuring non-repudiable delegated mandates (SD-JWT, FIDO2 / TPM Passkey hardware-backed signatures) allowing AI agents to transact autonomously within cryptographic spend and time limits.
3. **Model Context Protocol (Web MCP)**: An open standard for exposing web application tools, state, and browser actions directly to AI models.

---

## 2. The 4 Demos Compared

The suite offers a head-to-head, visual, and architectural comparison across the 4 primary agentic integration paradigms:

| # | Demo Scenario | Protocol Channel | Frontend App | Backend Services | Architectural Focus |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Direct A2A** *(Baseline)* | JSON-RPC 2.0 / A2A | `chat-client` (`:4200`) | `backend-merchant` (`:10999`) | Direct B2C conversational chatbot with merchant agent, intent parsing, and AP2 Passkey payment modal. |
| **2** | **Web MCP** *(E-Commerce)* | Model Context Protocol | `storefront-webmcp` (`:4202`) | `backend-merchant` (`:10999`) | Browser-native shopping agent navigating and executing web tools (`filterProducts`, `addToCart`, `configureFulfillment`). |
| **3** | **Two-Agent Federation** *(Full A2A)* | Semantic M2M A2A with **Gemini 2.5 Flash** | `shopper-client` (`:4203`) | `backend-shopper` (`:10998`) $\longleftrightarrow$ `backend-merchant` (`:10999`) | Autonomous agent-to-agent federation: Personal Shopper injects travel ticket context and negotiates multi-item combos with Station Merchant. |
| **4** | **UCP Standard REST** *(REST Binding)* | HTTP RESTful + **RFC 9421** | `shopper-client` (`:4203`) | `backend-shopper` (`:10998`) $\longrightarrow$ `backend-merchant` (`:10999`) | Official enterprise UCP REST binding with ECDSA-P256 HTTP Message Signatures and compliant checkout sessions. |

---

## 3. Port Allocation & Microservice Map

All services run concurrently without port conflicts:

```
                                  [ USER INTERFACE TIER (Angular 22) ]
                                                   │
         ┌─────────────────────────┬───────────────┴───────────────┬─────────────────────────┐
         ▼                         ▼                               ▼                         ▼
   :4200 chat-client        :4202 storefront-webmcp          :4203 shopper-client      :4201 bopis-dashboard
   (Demo 1 Direct A2A)      (Demo 2 Web MCP)                 (Demo 3 & Demo 4 Split)   (Station Dispatcher Hub)
         │                         │                               │                         ▲
         │ JSON-RPC                │ MCP Tools                     │ SSE Stream / Context    │ Real-time Orders
         ▼                         ▼                               ▼                         │
   ┌────────────────────────────────────────────────────────┐ ┌───────────────────────────┐  │
   │  :10999 backend-merchant                               │ │  :10998 backend-shopper   │  │
   │  • Milan Central Travel Retail Hub                     │ │  • Personal Shopper Agent │  │
   │  • Merchant Agent (Gemini 2.5 Flash)                   │ │  • Intent (Gemini 2.5 Fl.)│──┘
   │  • UCP REST Server (RFC 9421 ECDSA-P256)               │ │  • Ticket & Context Engine│
   │  • Web MCP Server & BOPIS Engine (store.py)            │ │  • AP2 Passkey Validator  │
   └────────────────────────────────────────────────────────┘ └───────────────────────────┘
```

| Port | Service Name | Tech Stack | Architectural Role |
| :---: | :--- | :--- | :--- |
| **`4200`** | `chat-client` | Angular 22 | Demo 1 Client (Baseline Direct A2A Chat Interface) |
| **`4201`** | `bopis-dashboard` | Angular 22 | Central Dispatcher Hub for station staff (Kitchen, Barista, Platform Couriers) |
| **`4202`** | `storefront-webmcp` | Angular 22 | Demo 2 Storefront (Web MCP Tool Registry) |
| **`4203`** | `shopper-client` | Angular 22 | Demo 3 & 4 Split-View Client with Real-Time Protocol Inspector |
| **`10998`** | `backend-shopper` | Python / Starlette | Traveler's Personal Shopper Agent (Context Engine, Gemini 2.5 Flash, SSE Stream) |
| **`10999`** | `backend-merchant` | Python / Starlette | Station Merchant Agent (Gemini 2.5 Flash, BOPIS Engine, A2A, UCP REST Server) |

---

## 4. Dual AI Agent Engine: Gemini 2.5 Flash

In multi-agent scenarios (Demo 3 & 4), semantic reasoning is powered by **`gemini-2.5-flash`** with **Structured Outputs (Pydantic)**:

1. **Personal Shopper Agent (`shopper_service.py`)**:
   - Parses user intent from conversational input (e.g. *"Get me a double espresso and warm focaccia for Coach 4"*).
   - Resolves target fulfillment method (`in_seat_train`).
   - Injects wallet context from the traveler's ticket (*Frecciarossa 9540*, departure *13:10*, platform *14*, coach *4*, seat *12D*).
   - Formulates machine-to-machine semantic A2A inquiries for the merchant station agent.

2. **Station Merchant Agent (`main.py`)**:
   - Evaluates the real product inventory (`products.json`).
   - Identifies single items or multi-item combo deals:
     - `CAFFE-001`: *Double Espresso Illy Hot* (€2.50)
     - `TOAST-003`: *Warm Focaccia Toast with Ham and Fontina Cheese* (€6.50)
     - Negotiated subtotal: **€9.00**.
   - Delegates physical verification to the **BOPIS Engine**: thermal validation (`is_hot: True` $\to$ **automatically bars Smart Lockers**) and logistics feasibility (recommends in-seat delivery for €15.50 total, or express counter pickup for €9.00 total).

---

## 5. Quick Start Guide

### Prerequisites
- **Node.js**: v20+ with `npm`
- **Python**: v3.11+ with virtualenv in `backend/.venv`
- Configured `.env` file in the root directory (see `.env.example`):
  ```env
  GOOGLE_API_KEY=your_google_ai_studio_api_key
  # DEFAULT_BUYER_EMAIL=alex.traveler@example.com (optional)
  # OPERATOR_EMAILS=merchant@agentic-commerce.demo (optional)
  ```

### Simultaneous Launch (All 6 Services)
To launch all 6 services with a single command:
```powershell
npm run serve:all
```

### Individual Execution via Nx
```powershell
# Backend Services
npx nx run backend-merchant:serve     # Port 10999
npx nx run backend-shopper:serve      # Port 10998

# Frontend Applications
npx nx run shopper-client:serve       # Port 4203 (Demo 3 & 4)
npx nx run bopis-dashboard:serve      # Port 4201 (Station Logistics Screen)
npx nx run storefront-webmcp:serve    # Port 4202 (Demo 2 Storefront)
npx nx run chat-client:serve          # Port 4200 (Demo 1 Baseline)
```

---

## 6. Technical Documentation

Comprehensive architectural and protocol documentation is available in the `docs/` folder:

- [**`docs/README.md`**](docs/README.md): **Technical Documentation Hub**: complete documentation map, demo comparison matrix, and runtime guide.
- [**`docs/architecture.md`**](docs/architecture.md): Full system specification, sequence diagrams, cryptographic models, and anti-hijacking patterns.
- [**`docs/gcp-ucp-architecture.md`**](docs/gcp-ucp-architecture.md): Serverless cloud-native middleware architecture on Google Cloud Platform (Cloud Run, Firestore, Vertex AI).
- [**`docs/ucp-requirements-and-capabilities-matrix.md`**](docs/ucp-requirements-and-capabilities-matrix.md): Normative UCP requirement matrix (RFC 2119), relevance tiers (1–3), and implementation conformance.
- [**`TODO.md`**](TODO.md): **Official Roadmap & Backlog**: 12 architectural enhancements (including standalone `ucp-web-client`, Chrome Extension, and Linate airport multi-store).
- [**`backend/README.md`**](backend/README.md): Technical deep-dive into Python microservices, Starlette routes, and Gemini 2.5 Flash agents.

