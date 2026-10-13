# Project TODOs & Architecture Roadmap — UCP Travel Retail Demo Suite

This document is the **Single Source of Truth (SSOT)** for all planned evolutions, protocol enhancements, and feature backlog for the **UCP Travel Retail Demo Suite** (GDG DevFest Milano 2026).

---

## 📋 Table of Contents
- [1. Core Protocols & Standards Compliance](#1-core-protocols--standards-compliance)
- [2. In-Browser AI & WebMCP Agents](#2-in-browser-ai--webmcp-agents)
- [3. Catalog Semantics & Vector Search](#3-catalog-semantics--vector-search)
- [4. Multi-Location & Transit Logistics (Milan Central & Linate)](#4-multi-location--transit-logistics-milan-central--linate)
- [5. Standalone Tooling & Client Apps](#5-standalone-tooling--client-apps)

---

## 1. Core Protocols & Standards Compliance

### [TODO-01] Official UCP A2A Transport Layer Adaptation (JSON-RPC 2.0 / `a2a.ucp.checkout`)
- **Priority:** High / Post-DevFest Spec Alignment
- **Target Components:** `backend-shopper`, `backend-merchant`, `shopper-client`
- **UCP Reference Specification:** [`specification/shopping/checkout/a2a.md`](https://ucp.dev/latest/specification/shopping/checkout/a2a/)
- **Context:**
  - Demo 3 currently uses dedicated semantic REST endpoints (`POST /a2a/negotiate` and `POST /a2a/commit`) to showcase M2M reasoning between the Personal Shopper Agent and the Merchant Agent (both powered by Gemini 2.5 Flash).
  - While this clearly demonstrates semantic negotiation and structured outputs, it does not use the official UCP A2A envelope.
- **Implementation Tasks:**
  1. **Standard A2A Transport Layer:** Replace custom REST endpoints with JSON-RPC 2.0 standard (`method: "message/send"`) sent to the merchant's A2A endpoint (`POST /api`).
  2. **UCP Protocol Headers:** Send `UCP-Agent: profile="http://localhost:10998/profile/shopper_agent.json"` and `X-A2A-Extensions: https://ucp.dev/2026-01-23/specification/reference`.
  3. **Envelope & Formal DataPart:** Encapsulate shopper intent, train ticket constraints, and dietary preferences inside message `parts`. The Merchant Agent returns the cart within a formal `DataPart` keyed by **`a2a.ucp.checkout`** (matching Demo 1 Google ADK behavior).
  4. **Commit & AP2 Payment Mandate:** Transmit order confirmation and signed AP2 Passkey FIDO2 mandates via standard UCP keys: **`a2a.ucp.checkout.payment`** and **`a2a.ucp.checkout.signals`**.
  5. **Live Protocol Inspector Update (`shopper-client`):** Update SSE streaming in `shopper_service.py` to display the formal JSON-RPC 2.0 `message/send` payloads and `a2a.ucp.checkout` structures.

### [TODO-03] UCP REST Security & Production Hardening (Demo 4 Roadmap)
- **Priority:** Medium / Security Hardening
- **Target Components:** `backend-merchant` (`ucp_rest_server.py`)
- **Implementation Tasks:**
  1. **Dual-Token Pattern:** Pair the public `checkout_id` with an ephemeral secret `cart_secret_token` to prevent cart enumeration or unauthorized modifications.
  2. **Optimistic Locking:** Enforce HTTP `ETag` and `If-Match` headers on all mutating `PATCH /ucp/checkouts/{id}` operations.
  3. **Short-Lived Reservation TTL:** Implement 15-minute quote reservation locking with automatic expiration for uncommitted stock.

### [TODO-11] Multi-Product A2A Query Optimization (Disjunctive OR vs. Multi-Call Decomposition)
- **Priority:** Medium / Performance & Accuracy
- **Target Components:** `backend-shopper`, `backend-merchant`
- **Context:**
  - When travelers request combinations of distinct items (e.g. *"fresh orange juice + vegan sandwich"* or *"espresso and gluten-free croissant"*), agents need to resolve multiple catalog matches reliably.
- **Implementation Tasks:**
  1. **Benchmark Comparison:**
     - **Option A (Unified Semantic Query):** Single A2A message with multi-item prompt and disjunctive (OR) resolution on the merchant agent backend.
     - **Option B (Intent Decomposition):** Personal Shopper decomposes the user's intent into parallel sub-queries to the merchant, aggregating matched items into an atomic UCP cart.
  2. Implement structured error handling for partial availability (e.g. sandwich available, orange juice out of stock).

---

## 2. In-Browser AI & WebMCP Agents

### [TODO-05] Google Chrome Extension In-Browser LLM (WebMCP Agent Extension)
- **Priority:** High / Innovative Agent Experience
- **Target Components:** `apps/chrome-extension-webmcp` (New Chrome MV3 Extension)
- **Context:**
  - Current in-browser LLM runtimes (e.g. Gemini Nano via built-in `window.ai`) have limitations: single tool invocation per prompt and lack of direct DOM/context extraction.
- **Architecture & Features:**
  1. **Side Panel Conversational Interface:** Native Chrome Side Panel (`chrome.sidePanel`) to interact in natural language while browsing the storefront.
  2. **Automated DOM & UI Context Extraction:** Content script queries the storefront (calling `getPageContextMarkdown` or inspecting `navigator.modelContext`) and automatically prepends active filters, visible products, cart state, and transit constraints into the LLM prompt without manual clipboard copy.
  3. **WebMCP Bridge & Tool Dispatcher:** Intercepts and executes WebMCP tools exposed by the page (`filterProducts`, `addToCart`, `configureFulfillment`, `submitOrder`).
  4. **Multi-Turn Agentic Loop:** Manages the agent reasoning loop inside the extension (thought ➔ tool call ➔ observation ➔ next step), enabling multi-step workflows in a single user turn.

### [TODO-06] WebMCP Demo with Custom Chrome Extension (Full Multi-Tool Calling)
- **Priority:** Medium / Demo Packaging
- **Target Components:** `storefront-webmcp`, Chrome Extension
- **Implementation Tasks:**
  1. Standalone live demonstration scenario pairing the Angular 22 storefront with the custom Chrome Extension.
  2. In-browser AI execution (Gemini Nano or WebLLM with WebGPU) handling complex multi-tool sequences (e.g., *"Filter vegan snacks, add the focaccia, and set locker pickup for 13:00"* in one command).

---

## 3. Catalog Semantics & Vector Search

### [TODO-07] Semantic Vector Search with Embeddings (Firestore Vector Search)
- **Priority:** Medium / Search Quality
- **Target Components:** `backend-merchant`, Google Cloud Firestore
- **Implementation Tasks:**
  1. **Vector Embeddings Generation:** Generate dense embeddings for product titles, descriptions, dietary tags, and keywords using Vertex AI `text-embedding-004` or Gemini embeddings.
  2. **Firestore Vector Store:** Store vectors in Cloud Firestore product documents.
  3. **k-NN Vector Queries:** Use Firestore Vector Search (`find_nearest`) for semantic similarity, enabling natural language search for nuanced queries (e.g. *"light healthy breakfast before boarding"*, *"refreshing non-carbonated drink"*).

### [TODO-08] Google Product Category (GPC) & GS1 Industry Standards Support
- **Priority:** Low / Retail Interoperability
- **Target Components:** `backend-merchant`, `models.py`
- **Implementation Tasks:**
  1. **Taxonomy Mapping:** Map catalog products to standard Google Product Category (GPC) IDs and global GS1 Global Product Classification (GPC) codes.
  2. **Protocol Integration:** Enrich UCP catalog responses with standardized `categories` fields and enable category-based filtering in `GET /ucp/catalog/products`.

---

## 4. Multi-Location & Transit Logistics (Milan Central & Linate)

### [TODO-02] Demo 5: Delegated Autonomous Purchasing (Human-Not-Present)
- **Priority:** High / Next-Gen Agentic Commerce
- **Target Components:** `backend-shopper`, `backend-merchant`, `shopper-client`, AP2 Passkey
- **Storytelling:**
  - A frequent traveler wants a high-value station product (e.g., *Brunello di Montalcino DOCG* wine, normally €48.00) but only if discounted below €35.00.
- **Technical Flow (Scenario 2.2 AP2 Delegated Mode):**
  1. **Pre-Authorized Intent Mandate:** User signs a pre-approved budget mandate with Passkey (max €40.00, valid 7 days).
  2. **Merchant Price Trigger:** Merchant backend drops the price to €32.50 (`POST /merchant/products/{id}/promo`).
  3. **Event Watcher:** Shopper Agent monitors the catalog or receives an SSE webhook.
  4. **Headless Execution:** Autonomous M2M negotiation, headless AP2 mandate emission, and BOPIS dispatch with zero human clicks.
  5. **Asynchronous Notification:** Traveler receives push notification/SMS with Smart Locker PIN.

### [TODO-04] Real-Time Railway API Integration (Milan Central)
- **Priority:** Medium / Live Logistics
- **Target Components:** `backend-merchant`, `station_rules.py`
- **Implementation Tasks:**
  1. Synchronize train schedules, platform/track numbers, and delays with Trenitalia and Italo open APIs.
  2. Automatically dynamically adjust preparation and delivery time windows when trains are delayed.

### [TODO-09] Milan Linate Airport Demo: Multi-Store & Multi-Location Architecture
- **Priority:** Medium / Multi-Store Expansion
- **Target Components:** `backend-merchant`, `bopis-dashboard`
- **Implementation Tasks:**
  1. **Multi-Location Retail Model:** Extend merchant backend to support distinct physical venues (Milan Central Station `MI-CENTRAL` vs. Milan Linate Airport `LIN-AIRPORT`).
  2. **Location-Specific Stock & Fulfillment:** Dedicated inventories, boarding-gate delivery, and airside pickup lockers.
  3. **Smart Routing:** Route buyer agent requests to the appropriate store location based on passenger itinerary.

### [TODO-10] Milan Linate Airport Demo: Real-Time Flight Data Integration
- **Priority:** Medium / Airport Logistics
- **Target Components:** `backend-merchant`, `station_rules.py`
- **Implementation Tasks:**
  1. Connect with real-time flight tracking APIs (departures, arrivals, delays, gate changes, boarding status).
  2. Calculate time-critical fulfillment deadlines to ensure orders reach the departure gate before gate closure.

---

## 5. Standalone Tooling & Client Apps

### [TODO-12] Standalone `ucp-web-client` Application (Angular 22 SPA)
- **Priority:** High / Developer & Community Tooling
- **Target Components:** `apps/ucp-web-client` (New Standalone Angular 22 Application)
- **Architecture & Use Cases:**
  1. **Frontend-Only Architecture:** Lightweight Angular 22 Single Page Application with no backend requirement.
  2. **Universal Merchant Discovery:** Input field for any merchant URL (e.g. `https://shop.example.com` or local servers), automatically fetching and parsing `GET /.well-known/ucp`.
  3. **Catalog Explorer & Filter:** Interactive exploration of `GET /ucp/catalog/products` with keyword and category filters.
  4. **Client-Side Checkout Engine:** Manage complete cart and checkout sessions (`POST /ucp/checkouts`, `PATCH`, `POST /complete`) directly in the browser.
  5. **In-Browser RFC 9421 Signatures:** Native HTTP Message Signing (ECDSA-P256) via the browser's **Web Crypto API** for direct communication with secure UCP merchants.
  6. **Protocol Inspector & Playground:** Transparent visualizer for headers, payloads, and response times — serving as a "Postman for UCP" for developers testing compliance.
