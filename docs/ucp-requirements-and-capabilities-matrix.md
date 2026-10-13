# UCP Requirements, Capabilities & Conformance Matrix

> **Comparative analysis of normative UCP requirements, relevance tiers, and implementation mapping**  
> *Reference project:* [`ucp-demo-mi-devfest2026`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026) — *GDG DevFest Milano 2026*  
> *Analyzed UCP Specifications:* Protocol Specification v2026-01-23 / Draft, Python SDK (`ucp-sdk` 0.5.0), TypeScript SDK (`@ucp-js/sdk` 0.5.1), AP2 Protocol Specification.

---

## 1. Classification Methodology

### 1.1 Normative Specification Levels (RFC 2119 / RFC 8174)
The formal UCP specification adopts standard IETF keywords:
* **MUST / REQUIRED**: An absolute requirement of the specification. Non-conformance breaks interoperability.
* **SHOULD / RECOMMENDED**: A strong architectural recommendation. May be overridden only with valid engineering justification.
* **MAY / OPTIONAL**: An optional capability or modular extension negotiable between parties.

### 1.2 Architectural Relevance Index (Scale 1 – 3)
* **Tier 3 (Critical / Core Foundation)**: Indispensable protocol pillar. Baseline requirement for network interoperability, service discovery, type safety, and core inter-agent transaction security.
* **Tier 2 (High / Production Operational)**: Production standards for real-world enterprise retail (fulfillment & pickup logistics, idempotency, concurrency, anti-hijacking, and order lifecycle).
* **Tier 1 (Advanced / Vertical Extension)**: Specialized or vertical industry features (hotel/lodging bookings, multi-parent loyalty programs, split multi-party payments).

---

## 2. Core Protocol, Governance & Discovery

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Discovery Endpoint `/.well-known/ucp`** | **MUST** | **3** | Merchant must expose a public JSON manifest at the standard well-known path for agents to discover services, transports, and capabilities. | ✅ **Implemented** | [`get_ucp_manifest` in `ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L33) |
| **Reverse-Domain Namespace** | **MUST** | **3** | Conventional naming `{reverse-domain}.{service}.{capability}` (e.g. `dev.ucp.shopping.checkout`). Prefix `dev.ucp.*` reserved. | ✅ **Implemented** | Followed across all manifests, headers, and events ([`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L40)) |
| **Authority Binding** | **MUST** | **3** | The schema URL origin must match the reverse-domain authority to guarantee contract authenticity. | 🟡 **Adapted** | References point to `https://ucp.dev/...`; offline local mode does not fetch live remote HTTPS schemas. |
| **Capability Intersection Algorithm** | **MUST** | **3** | Calculate the mathematical intersection between merchant and buyer agent capabilities (advertised via the `UCP-Agent` header). | 🟡 **Partial** | Advertised in manifests and responses; dynamic remote URL profile fetching bypassed during offline demo. |
| **Enveloping & Reserved `ucp` Namespace** | **MUST** | **3** | UCP protocol objects encapsulate a top-level `ucp` metadata envelope (`version`, `capabilities`, `status`). Domain payload cannot redefine `ucp`. | ✅ **Implemented** | All REST responses include standard envelope `ucp: { version, capabilities, ... }`. |
| **Monetary Minor Units & Currency** | **MUST** | **3** | All prices and amounts must be expressed as integer minor units (cents) with an ISO 4217 currency code (e.g. `EUR`). | ✅ **Implemented** | Consistently enforced: `price_cents`, `subtotal_cents`, `delivery_fee_cents`, `currency: "EUR"` ([`models.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/models.py)). |
| **Date Format RFC 3339 / ISO 8601** | **MUST** | **3** | All timestamps must be serialized in standard ISO 8601 / RFC 3339 UTC format. | ✅ **Implemented** | Used on `created_at`, `updated_at`, `placed_at_display` ([`bopis_store.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/bopis_store.py)). |
| **Tolerant Reader (Open Schema)** | **MUST** | **2** | Clients and servers must silently ignore unknown fields in the UCP envelope for backwards/forwards compatibility. | ✅ **Implemented** | Pydantic models configured with `model_config = ConfigDict(extra="ignore")`. |
| **`map_order` Annotation** | **SHOULD** | **1** | Deterministic key sorting across dictionaries preserved via RFC 8785 canonicalization (e.g. payment handler order). | ⚪ **Not Implemented** | Uses native Python dict insertion order; not formalized in `map_order` attribute. |

---

## 3. Transports & Network Bindings

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **REST Transport Binding** | **MUST** *(if supported)* | **3** | Standard HTTP/1.1 or HTTP/2 API documented via OpenAPI 3.x schema. | ✅ **Implemented** | `/ucp/checkouts`, `/ucp/catalog/products` endpoints in [`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py). |
| **Transport Security (TLS 1.3 min)** | **MUST** | **3** | All production REST and MCP communications must use HTTPS with TLS 1.3 minimum. | 🟡 **Adapted** | Local development uses HTTP (`http://localhost:...`) for offline autonomy; TLS termination handled by edge gateway. |
| **MCP (Model Context Protocol) Transport** | **MAY** | **3** | Expose commerce capabilities over MCP protocol (JSON-RPC over Streamable HTTP). | ✅ **Implemented** | Web MCP server on `/mcp/tools` with 7 compliant commerce tools ([`mcp_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/mcp_server.py)). |
| **A2A (Agent-to-Agent) Transport** | **MAY** | **3** | Semantic M2M cooperation channel utilizing Agent Cards (`/.well-known/agent-card.json`). | ✅ **Implemented** | Agent Card and federated semantic negotiation with Gemini 2.5 Flash ([`agent.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/agent.py), [`shopper_service.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend-shopper/shopper_service.py)). |
| **Embedded Protocol Transport** | **MAY** | **1** | JSON-RPC postMessage communication between parent frame and checkout iframe. | ⚪ **Not Needed** | Our architecture is full-agentic/headless rather than an embedded web iframe. |

---

## 4. Core Shopping Capabilities

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Catalog Capability (`dev.ucp.shopping.catalog`)** | **RECOMMENDED** | **3** | Product lookup and search (`GET /catalog/products`, `products/{id}`). | ✅ **Implemented** | `GET /ucp/catalog/products` with unified `products.json` ([`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L81)). |
| **Checkout Capability (`dev.ucp.shopping.checkout`)** | **MUST** | **3** | Create, update, and complete transaction sessions (`POST /checkouts`, `PATCH`, `POST /complete`). | ✅ **Implemented** | Full lifecycle active in [`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L87-L230). |
| **Checkout Status Lifecycle** | **MUST** | **3** | Deterministic checkout state machine: `incomplete` $\to$ `ready_for_complete` $\to$ `completed` / `canceled`. | ✅ **Implemented** | Transitions `in_progress` $\to$ `ready_for_complete` $\to$ `completed` managed in-memory and reflected on client. |
| **Cart Capability (`dev.ucp.shopping.cart`)** | **OPTIONAL** | **2** | Lightweight pre-checkout cart session without payment setup (`/carts`). | 🟡 **Partial** | Managed in Web MCP and in-memory; REST channel directly converts item selections into checkout sessions. |
| **Cart-to-Checkout Conversion** | **RECOMMENDED** | **2** | Idempotent conversion of a `cart_id` into a `checkout_id` preserving line items and context. | ⚪ **Roadmap** | Tracked in `TODO.md`; currently Personal Shopper directly initiates the UCP checkout session. |
| **Order Capability (`dev.ucp.shopping.order`)** | **RECOMMENDED** | **2** | Post-purchase state queries and order lifecycle (`GET /orders/{id}`, tracking webhooks). | ✅ **Implemented** | Central BOPIS Engine with `/bopis/orders`, `/bopis/orders/{id}/status`, and real-time Firestore push. |
| **Permalink Capability (`dev.ucp.shopping.permalink`)** | **OPTIONAL** | **1** | Persistent URL to resume cart or view order via traditional browser (`continue_url`). | 🟡 **Partial** | Fallback `continue_url` provided; formal UCP permalink service not registered. |

---

## 5. Shopping Extensions & Physical Retail

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Fulfillment Extension (`dev.ucp.shopping.fulfillment`)** | **RECOMMENDED** | **3** | Selection and calculation of fulfillment methods: `pickup`, `shipping`, `in_seat_train`, `pickup_locker`. | ✅ **Implemented** | Comprehensive station fulfillment engine: `in_seat_train` (car/seat), `pickup_locker` (box/PIN), `pickup_express` ([`station_rules.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/station_rules.py)). |
| **Fulfillment Lead Time & Physical Constraints** | **RECOMMENDED** | **3** | Validation of physical and timing constraints (min 30 min advance notice for train, hot food barred from Smart Locker). | ✅ **Implemented** | Thermal checks and train timetable validation in [`validate_station_constraints`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/station_rules.py#L38). |
| **Discount Extension (`dev.ucp.shopping.discount`)** | **OPTIONAL** | **2** | Coupon codes, promotional vouchers, and item-level price adjustments (`allocations`). | 🟡 **Partial** | Managed via AI combo bundles (e.g. Sandwich + Coffee negotiated at promotional price by Gemini 2.5 Flash). |
| **Buyer Consent Extension (`dev.ucp.shopping.buyer_consent`)** | **RECOMMENDED** | **2** | Recording and verification of buyer consent (terms of service, privacy, store policies). | 🟡 **Simulated** | Included in buyer agent authorization dialog before signing AP2 mandate. |
| **Loyalty Extension (`dev.ucp.common.loyalty`)** | **OPTIONAL** | **1** | Loyalty programs, points balance, and tier discount application (e.g. FrecciaClub Gold). | ✅ **Implemented** | Personal Shopper injects `loyalty_tier: "FrecciaClub Gold"` into traveler context ([`shopper_service.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend-shopper/shopper_service.py#L101)). |

---

## 6. Transaction Security, Anti-Hijacking & Cryptography

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **RFC 9421 HTTP Message Signatures** | **MUST** *(for auth)* | **3** | Asymmetric cryptographic signing (ES256) of HTTP headers (`Signature`, `Signature-Input`) and body digest (RFC 9530). | ✅ **Implemented** | Standalone ECDSA-P256 signing and verification module ([`rfc9421.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/rfc9421.py), verified in [`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L220)). |
| **AP2 Mandates Extension (`dev.ucp.payment.ap2`)** | **RECOMMENDED** | **3** | Non-repudiable cryptographic mandates (Intent, Cart, and Payment Mandate) with Passkey FIDO2/TPM hardware backing. | ✅ **Implemented** | Generation, LCM hardware signing, and SD-JWT mandate verification ([`ap2_crypto.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/ap2_crypto.py)). |
| **Dual-Token Architecture (Pattern A)** | **RECOMMENDED** | **2** | Decoupling public `checkout_id` from ephemeral `cart_secret_token` to prevent enumeration and cart hijacking. | ⚪ **Tracked in TODO** | Documented in `TODO.md` and server architecture ([`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L32)). High-entropy UUIDv4 used. |
| **Optimistic Locking & ETag (Pattern B)** | **RECOMMENDED** | **2** | Enforce `ETag` and `If-Match` headers on state mutations, rejecting conflicting updates with `HTTP 412 Precondition Failed`. | ⚪ **Tracked in TODO** | Documented in `patch_ucp_checkout` technical roadmap; current mutation is atomic in-memory. |
| **Mutual TLS (mTLS) & Client Pinning (Pattern C)** | **SHOULD** | **2** | Transport-level mutual authentication with X.509 client certificates tied to agent credentials. | ⚪ **Tracked in TODO** | Replaced in local demo by application-layer RFC 9421 signing for offline flexibility without a local PKI. |
| **Short-Lived TTL & Quote Locking (Pattern D)** | **RECOMMENDED** | **2** | `expires_at` timestamp in checkout session freezing pricing, stock, and logistics slots; automated stale session cleanup. | ⚪ **Tracked in TODO** | Documented in `TODO.md`; physical train departure limits are validated without automated TTL sweeping. |
| **Idempotency Key (`idempotency-key`)** | **MUST** *(for POST)* | **2** | `Idempotency-Key` header to prevent duplicate charges and orders during network retries. | 🟡 **Partial** | Deduplication enforced via `order_id` / `checkout_id`; not yet formalized as an arbitrary header with a SHA-256 store. |

---

## 7. Identity, Location & Vertical Capabilities

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Identity Linking (`dev.ucp.common.identity_linking`)** | **OPTIONAL** | **2** | OAuth 2.0 PKCE and Token Exchange (RFC 8693) to federate buyer agent identity with merchant user accounts. | 🟡 **Mode 1** | Implemented **Mode 1 (Declared Email Matching)** with user filters; Modes 2 & 3 tracked in roadmap ([`main.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/main.py#L61)). |
| **Location Capability (`dev.ucp.common.location`)** | **OPTIONAL** | **2** | Discovery of physical stores, train stations, or pickup lockers via geolocation (`search`, `lookup`). | ✅ **Adapted** | Contextualized directly to Milan Central Station pickup points (Platform 12, Smart Locker Floor -1). |
| **Lodging Booking (`dev.ucp.lodging.booking`)** | **OPTIONAL** | **1** | Hotel room reservation, guest check-in, and cancellation flows. | ⚪ **Out of Scope** | Not applicable: demo focuses exclusively on high-speed rail travel retail. |
| **Split Payments (`dev.ucp.payment.split`)** | **OPTIONAL** | **1** | Splitting charges across multiple payment instruments or multiple buyers. | ⚪ **Out of Scope** | Single traveler authorization via cryptographic AP2 mandate. |

---

## 8. Error Handling, Messages & Fault Tolerance

| Requirement / Feature | Spec Level | Tier (1-3) | Technical UCP Description | Demo Status | Codebase Reference |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **UCP Error Envelope & Severity** | **MUST** | **3** | Structured error responses with `type: "error"`, `code`, `severity` (`recoverable` vs `unrecoverable`), and `path`. | ✅ **Implemented** | Returned on station constraint violations (`422 Unprocessable Entity` with `validation_failed`). |
| **Web Fallback (`continue_url`)** | **SHOULD** | **2** | Continuation URL allowing human shopper to complete checkout via browser if agent encounters an unrecoverable error. | ✅ **Implemented** | Demo supports direct transition from agent to web storefront (`storefront-webmcp` on port `4202`). |
| **Standard HTTP Status Codes** | **MUST** | **3** | Strict adherence to HTTP semantics: `201 Created`, `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `422 Unprocessable`. | ✅ **Implemented** | Consistently enforced across Starlette/FastAPI route controllers. |

---

## 9. Conformance Summary & Architecture Trade-Offs

### Coverage by Relevance Tier

```
Tier 3 (Critical / Core Foundation):   [██████████████████░░] ~90% Coverage
Tier 2 (High / Production Operational): [███████████████░░░░░] ~75% Coverage
Tier 1 (Advanced / Vertical Extension): [██████████░░░░░░░░░░] ~50% (Travel Retail Focus)
```

### Engineering Trade-Offs in Reference Implementation

1. **Local HTTP vs HTTPS TLS 1.3:**
   - *Rationale:* To allow the demo to run completely offline without X.509 certificate trust issues during live presentations, services bind to `http://localhost:...`.
   - *Cryptographic Compensation:* Message security and payload integrity are cryptographically enforced at the application layer via **RFC 9421 HTTP Message Signatures (ECDSA-P256)** and RFC 9530 digest hashing.
2. **Dual-Token Architecture vs UUIDv4:**
   - *Rationale:* High-entropy UUIDv4 identifiers are used for carts and checkouts during the demo.
   - *Evolution:* The formal Dual-Token pattern (with separate bearer mutation token) is documented in `TODO.md` as an enterprise hardening task.
3. **Optimistic Locking in Memory vs ETag/If-Match:**
   - *Rationale:* Active checkout sessions are managed in-memory with atomic state transitions.
   - *Evolution:* Formal `ETag` generation and `If-Match` validation (`HTTP 412`) are outlined in the roadmap.
4. **Semantic A2A Negotiation vs Strict `a2a.ucp.checkout` Envelope:**
   - *Rationale (Demo 3):* To highlight multi-agent LLM reasoning and provide educational SSE streaming, Demo 3 uses dedicated semantic endpoints (`/a2a/negotiate` and `/a2a/commit`).
   - *Evolution (TODO-01):* Alignment to standard JSON-RPC 2.0 `message/send` with formal UCP `a2a.ucp.checkout` DataPart envelope is prioritized in [`TODO.md`](../TODO.md).
