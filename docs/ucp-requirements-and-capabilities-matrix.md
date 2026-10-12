# Matrice dei Requisiti, Capability e Conformità UCP (Universal Commerce Protocol)

> **Analisi comparativa dei requisiti normativi UCP, livelli di rilevanza e mappatura dell'implementazione**  
> *Progetto di riferimento:* [`ucp-demo-mi-devfest2026`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026) — *GDG DevFest Milano 2026*  
> *Specifiche UCP analizzate:* Protocol Specification v2026-01-23 / Draft, SDK Python (`ucp-sdk` 0.5.0), SDK TypeScript (`@ucp-js/sdk` 0.5.1), AP2 Protocol Specification.

---

## 1. Metodologia di Classificazione

### 1.1 Livelli Normativi di Specifica (RFC 2119 / RFC 8174)
La specifica formale UCP adotta le parole chiave convenzionali IETF:
* **MUST / REQUIRED**: Requisito vincolante e obbligatorio. L'omissione rende l'implementazione non conforme al protocollo.
* **SHOULD / RECOMMENDED**: Forte raccomandazione architetturale. Può essere derogato solo per motivate ragioni implementative.
* **MAY / OPTIONAL**: Funzionalità opzionale o estensione modulare negoziabile tra le parti.

### 1.2 Indice di Rilevanza Architetturale (Scala 1 – 3)
* **Livello 3 (Critico / Fondamentale)**: Pilastro irrinunciabile del protocollo. Requisito baseline per l'interoperabilità di rete, la discovery dei servizi, la conformità dei tipi e la sicurezza primaria delle transazioni tra agenti.
* **Livello 2 (Alto / Operativo Enterprise)**: Standard di produzione per scenari reali e commercio su scala (gestione logistica/ritiro, idempotenza, concorrenza, prevenzione hijacking del carrello e ciclo di vita ordini).
* **Livello 1 (Avanzato / Estensione Verticale)**: Funzionalità verticali opzionali o di nicchia (prenotazioni alberghiere, loyalty avanzata multiparent, split payment tra più pagatori).

---

## 2. Core Protocol, Governance & Discovery

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Discovery Endpoint `/.well-known/ucp`** | **MUST** | **3** | Il merchant deve pubblicare un manifest JSON pubblico al path standard per consentire all'agente di rilevare servizi, trasporti e capability. | ✅ **Implementato** | [`get_ucp_manifest` in `ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L33) |
| **Namespace Reverse-Domain** | **MUST** | **3** | Naming convenzionale `{reverse-domain}.{service}.{capability}` (es. `dev.ucp.shopping.checkout`). Riserva del prefisso `dev.ucp.*`. | ✅ **Implementato** | Rispettato in tutti i manifest, header ed eventi ([`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L40)) |
| **Authority Binding** | **MUST** | **3** | L'origine dell'URL `schema` deve corrispondere all'autorità reverse-domain per garantire la provenienza del contratto. | 🟡 **Adattato** | Riferimenti puntano a `https://ucp.dev/...`; in locale non eseguiamo fetch HTTPS remota per indipendenza offline. |
| **Capability Intersection Algorithm** | **MUST** | **3** | Calcolo dell'intersezione tra le capability del merchant e quelle dell'agente (dichiarate nell'header `UCP-Agent`). | 🟡 **Parziale** | Negoziata nel manifest e nelle risposte; non effettuiamo fetch dinamica del profilo remoto via URL durante la demo. |
| **Enveloping & Namespace `ucp` riservato** | **MUST** | **3** | Gli oggetti UCP contengono l'oggetto `ucp` con metadati (`version`, `capabilities`, `status`). Divieto di ridefinire il campo a livello di dominio. | ✅ **Implementato** | Tutte le risposte REST contengono l'involucro standard `ucp: { version, capabilities, ... }`. |
| **Formato Valute & Importi (Minor Units)** | **MUST** | **3** | Tutti gli importi monetari devono essere espressi in centesimi interi (minor units) con codice valuta ISO 4217 (es. `EUR`). | ✅ **Implementato** | Rispettato ovunque: `price_cents`, `subtotal_cents`, `delivery_fee_cents`, `currency: "EUR"` ([`models.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/models.py)). |
| **Formato Date RFC 3339 / ISO 8601** | **MUST** | **3** | Tutte le date devono essere serializzate nel formato standard ISO 8601 / RFC 3339 UTC. | ✅ **Implementato** | Usato su `created_at`, `updated_at`, `placed_at_display` ([`bopis_store.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/bopis_store.py)). |
| **Tolerant Reader (Open Schema)** | **MUST** | **2** | I client e server devono ignorare campi sconosciuti nell'involucro UCP per garantire retrocompatibilità e forward-compatibility. | ✅ **Implementato** | I modelli Pydantic usano `model_config = ConfigDict(extra="ignore")`. |
| **`map_order` Annotation** | **SHOULD** | **1** | Ordinamento deterministico delle chiavi nei dizionari preservato attraverso la canonicalizzazione RFC 8785 (es. ordine payment handlers). | ⚪ **Non Implementato** | Usiamo ordinamento nativo Python `dict` (inserimento); non formalizzato nell'attributo `map_order`. |

---

## 3. Trasporti e Canali di Rete (Transports)

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **REST Transport Binding** | **MUST** *(se supportato)* | **3** | Esposizione API standard HTTP/1.1 o HTTP/2 documentate tramite schema OpenAPI 3.x. | ✅ **Implementato** | Endpoints `/ucp/checkouts`, `/ucp/catalog/products` in [`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py). |
| **Transport Security (TLS 1.3 min)** | **MUST** | **3** | Tutte le comunicazioni REST ed MCP di produzione devono viaggiare su HTTPS con TLS versione 1.3 minimo. | 🟡 **Parziale** | In locale usiamo HTTP chiaro (`http://localhost:...`) per facilitare la demo offline; TLS è delegabile al reverse-proxy. |
| **MCP (Model Context Protocol) Transport** | **MAY** | **3** | Esposizione dei servizi commerciali tramite protocollo MCP (JSON-RPC over Streamable HTTP). | ✅ **Implementato** | Server Web MCP su `/mcp/tools` con 7 tool commerciali conformi ([`mcp_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/mcp_server.py)). |
| **A2A (Agent-to-Agent) Transport** | **MAY** | **3** | Canale di cooperazione M2M semantica con Agent Card (`/.well-known/agent-card.json`). | ✅ **Implementato** | Agent Card e negoziatore semantico federato con Gemini 2.5 Flash ([`agent.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/agent.py), [`shopper_service.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend-shopper/shopper_service.py)). |
| **Embedded Protocol Transport** | **MAY** | **1** | Comunicazione JSON-RPC postMessage tra parent frame e iframe per checkout embedded. | ⚪ **Non Necessario** | Nella nostra architettura l'integrazione è full-agentic/headless, non embedded web iframe. |

---

## 4. Shopping Capabilities Core

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Catalog Capability (`dev.ucp.shopping.catalog`)** | **RECOMMENDED** | **3** | Ricerca e lookup dei prodotti (`GET /catalog/products`, `products/{id}`). | ✅ **Implementato** | `GET /ucp/catalog/products` con catalogo unificato `products.json` ([`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L81)). |
| **Checkout Capability (`dev.ucp.shopping.checkout`)** | **MUST** | **3** | Creazione, aggiornamento e finalizzazione della transazione (`POST /checkouts`, `PATCH`, `POST /complete`). | ✅ **Implementato** | Ciclo completo attivo su [`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L87-L230). |
| **Checkout Status Lifecycle** | **MUST** | **3** | Macchina a stati deterministica del checkout: `incomplete` $\to$ `ready_for_complete` $\to$ `completed` / `canceled`. | ✅ **Implementato** | Transizioni `in_progress` $\to$ `ready_for_complete` $\to$ `completed` gestite in memoria e riflesse sul client. |
| **Cart Capability (`dev.ucp.shopping.cart`)** | **OPTIONAL** | **2** | Sessione carrello leggera e pre-acquisto senza configurazione di pagamento (`/carts`). | 🟡 **Parziale** | Gestito nel Web MCP e in memoria; il canale REST converte direttamente la selezione in checkout session. |
| **Cart-to-Checkout Conversion** | **RECOMMENDED** | **2** | Conversione idempotente di un `cart_id` in un `checkout_id` mantenendo gli articoli e il contesto. | ⚪ **A Roadmap** | Documentato nei TODO; nella demo il Personal Shopper genera direttamente la sessione di checkout UCP. |
| **Order Capability (`dev.ucp.shopping.order`)** | **RECOMMENDED** | **2** | Consultazione stato e ciclo di vita post-acquisto (`GET /orders/{id}`, tracking webhook). | ✅ **Implementato** | Motore centrale BOPIS Engine con consultazione `/bopis/orders`, `/bopis/orders/{id}/status` e push real-time Firestore. |
| **Permalink Capability (`dev.ucp.shopping.permalink`)** | **OPTIONAL** | **1** | URL persistente per riprendere il carrello o visualizzare l'ordine via web tradizionale (`continue_url`). | 🟡 **Parziale** | Usiamo fallback `continue_url`, ma non il servizio formale permalink UCP. |

---

## 5. Estensioni Shopping & Retail Fisico

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Fulfillment Extension (`dev.ucp.shopping.fulfillment`)** | **RECOMMENDED** | **3** | Selezione e calcolo delle modalità di consegna e ritiro: `pickup`, `shipping`, `in_seat_train`, `pickup_locker`. | ✅ **Implementato** | Motore completo delle regole di stazione: `in_seat_train` (carrozza/posto), `pickup_locker` (box/PIN) e `pickup_express` ([`station_rules.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/station_rules.py)). |
| **Fulfillment Lead Time & Physical Constraints** | **RECOMMENDED** | **3** | Validazione dei vincoli fisici e temporali (preavviso min 30 min per il treno, divieto cibi caldi nello Smart Locker). | ✅ **Implementato** | Logica termica e validazione orari treno implementata in [`validate_station_constraints`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/station_rules.py#L38). |
| **Discount Extension (`dev.ucp.shopping.discount`)** | **OPTIONAL** | **2** | Applicazione di coupon, sconti promozionali e ricalcolo totali `allocations`. | 🟡 **Parziale** | Gestito a livello di bundle combo AI (es. Panino + Caffè negoziato a prezzo speciale da Gemini 2.5 Flash). |
| **Buyer Consent Extension (`dev.ucp.shopping.buyer_consent`)** | **RECOMMENDED** | **2** | Raccolta e formalizzazione del consenso del compratore (termini di servizio, privacy, policy). | 🟡 **Simulato** | Incluso nel flusso di autorizzazione dell'agente prima della firma del mandato AP2. |
| **Loyalty Extension (`dev.ucp.common.loyalty`)** | **OPTIONAL** | **1** | Programmi fedeltà, saldo punti e applicazione sconti livello (es. FrecciaClub Gold). | ✅ **Implementato** | Il Personal Shopper inietta il `loyalty_tier: "FrecciaClub Gold"` nel contesto del viaggiatore ([`shopper_service.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend-shopper/shopper_service.py#L101)). |

---

## 6. Sicurezza Transazionale, Anti-Hijacking & Crittografia

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **RFC 9421 HTTP Message Signatures** | **MUST** *(per auth)* | **3** | Firma crittografica asimmetrica (ES256) degli header HTTP (`Signature`, `Signature-Input`) e digest del corpo (RFC 9530). | ✅ **Implementato** | Modulo autonomo di firma e verifica crittografica ECDSA-P256 ([`rfc9421.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/rfc9421.py), verificato in [`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L220)). |
| **AP2 Mandates Extension (`dev.ucp.payment.ap2`)** | **RECOMMENDED** | **3** | Mandati crittografici non ripudiabili (Intent, Cart e Payment Mandate) con autorizzazione Passkey FIDO2/TPM. | ✅ **Implementato** | Generazione, firma hardware LCM e verifica dei mandati SD-JWT ([`ap2_crypto.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/ap2_crypto.py)). |
| **Dual-Token Architecture (Pattern A)** | **RECOMMENDED** | **2** | Separazione tra `checkout_id` pubblico ed effimero `cart_secret_token` per impedire l'enumerazione e il session hijacking. | ⚪ **Nei TODO** | Documentato nei TODO del server REST e nell'architettura ([`ucp_rest_server.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/ucp_rest_server.py#L32)). Usiamo UUIDv4 casuali. |
| **Optimistic Locking & ETag (Pattern B)** | **RECOMMENDED** | **2** | Uso di `ETag` e dell'header `If-Match` sulle mutazioni con emissione di `HTTP 412 Precondition Failed` contro lost updates. | ⚪ **Nei TODO** | Inserito nei TODO tecnici di `patch_ucp_checkout`; mutazione attuale atomica in memoria. |
| **Mutual TLS (mTLS) & Client Pinning (Pattern C)** | **SHOULD** | **2** | Autenticazione mutua a livello di trasporto con certificati client X.509 legati alla chiave dell'agente. | ⚪ **Nei TODO** | Sostituito in locale dalla firma applicativa RFC 9421 per permettere il deployment offline senza PKI locale. |
| **Short-Lived TTL & Quote Locking (Pattern D)** | **RECOMMENDED** | **2** | Timestamp `expires_at` nella sessione con congelamento di prezzi, inventario e slot logistici; scarto sessioni stantie. | ⚪ **Nei TODO** | Documentato nei TODO; validiamo i limiti fisici dell'orario treno ma senza sweeper automatico del TTL. |
| **Idempotency Key (`idempotency-key`)** | **MUST** *(per POST)* | **2** | Header `Idempotency-Key` per prevenire duplicazione di addebiti e ordini in caso di retry di rete. | 🟡 **Parziale** | Implementato per dedup tramite `order_id` / `checkout_id`; non formalizzato come header HTTP generico con SHA-256 store. |

---

## 7. Identità, Location & Capability Verticali

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Identity Linking (`dev.ucp.common.identity_linking`)** | **OPTIONAL** | **2** | Federazione OAuth 2.0 PKCE e Token Exchange (RFC 8693) per collegare l'account dell'agente con il merchant. | 🟡 **Modalità 1** | Implementata **Modalità 1 (Matching Dichiarato per Email)** con filtri utente; Modalità 2 e 3 salvate come TODO architetturali ([`main.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/travel_retail_agent/main.py#L61)). |
| **Location Capability (`dev.ucp.common.location`)** | **OPTIONAL** | **2** | Discovery di negozi fisici, stazioni o lockers tramite geolocalizzazione (`search`, `lookup`). | ✅ **Adattato** | Contestualizzato direttamente sulla stazione di Milano Centrale e sui suoi punti di ritiro (Binario 12, Smart Locker Piano -1). |
| **Lodging Booking (`dev.ucp.lodging.booking`)** | **OPTIONAL** | **1** | Prenotazione camere, check-in, cancellazioni alberghiere. | ⚪ **Fuori Scope** | Non applicabile: la nostra demo è focalizzata verticalmente sul Travel Retail ferroviario ad alta velocità. |
| **Split Payments (`dev.ucp.payment.split`)** | **OPTIONAL** | **1** | Ripartizione della spesa su più strumenti di pagamento o tra più acquirenti. | ⚪ **Fuori Scope** | La transazione è autorizzata dal singolo viaggiatore tramite mandato AP2. |

---

## 8. Error Handling, Messaggi & Ripristino (Fault Tolerance)

| Requisito / Caratteristica | Livello Specifica | Imp. (1-3) | Descrizione Tecnica UCP | Stato nella Demo | Riferimento nella Codebase |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **UCP Error Envelope & Severity** | **MUST** | **3** | Messaggi di errore strutturati con `type: "error"`, `code`, `severity` (`recoverable` vs `unrecoverable`) e `path`. | ✅ **Implementato** | Struttura adottata nelle risposte di validazione vincoli di stazione (`422 Unprocessable Entity` con `validation_failed`). |
| **Fallback Web (`continue_url`)** | **SHOULD** | **2** | URL di continuazione per consentire all'umano di completare l'acquisto sul browser in caso di errore dell'agente. | ✅ **Implementato** | La demo include la transizione dall'agente allo storefront web (`storefront-webmcp` su porta `4202`). |
| **Codici HTTP Standard** | **MUST** | **3** | Rispetto dei codici `201 Created`, `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `422 Unprocessable`. | ✅ **Implementato** | Pienamente rispettati in tutti i controller Starlette/FastAPI della demo. |

---

## 9. Dashboard di Sintesi e Metriche di Conformità

### Copertura per Livello di Rilevanza

```
Livello 3 (Critico / Baseline):    [██████████████████░░] ~90% Copertura
Livello 2 (Operativo Enterprise):  [███████████████░░░░░] ~75% Copertura
Livello 1 (Verticale / Opzionale): [██████████░░░░░░░░░░] ~50% (Focus Travel Retail)
```

### Trade-off Ingegneristici Adottati nella Demo

1. **Trasporto Locale HTTP vs HTTPS TLS 1.3:**
   - *Scelta:* Per consentire alla demo di girare in modo completamente autonomo, offline o durante una conferenza senza dipendenze da certificati X.509 locali o DNS esterni, i microservizi comunicano su `http://localhost:...`.
   - *Compensazione Crittografica:* La sicurezza e l'integrità dei messaggi sono garantite a livello applicativo tramite **RFC 9421 HTTP Message Signatures (ECDSA-P256)** con hash del corpo RFC 9530.
2. **Architettura Dual-Token vs UUIDv4:**
   - *Scelta:* Nella demo gli identificatori di carrello e checkout utilizzano UUIDv4 crittograficamente casuali ad alta entropia.
   - *Evoluzione:* Il pattern Dual-Token formale (con bearer token separato per la mutazione) è pianificato come estensione di produzione.
3. **Locking Ottimistico in Memoria vs ETag/If-Match:**
   - *Scelta:* I checkout attivi sono mantenuti nello store del server con mutazioni atomiche sincrone.
   - *Evoluzione:* L'emissione di ETag e la verifica di `If-Match` per generare conflitti `HTTP 412` sono formalizzati nei TODO tecnici.
4. **Negoziazione A2A M2M Semantica vs Envelope UCP `a2a.ucp.checkout`:**
   - *Scelta (Demo 3):* Per evidenziare chiaramente il dialogo di reasoning tra i due LLM (Shopper vs Merchant) e lo streaming SSE didattico, la negoziazione M2M usa endpoint semantici dedicati (`/a2a/negotiate` e `/a2a/commit`).
   - *Evoluzione (TODO-01):* Allineamento del trasporto al metodo formale JSON-RPC 2.0 `message/send` con DataPart UCP `a2a.ucp.checkout` (vedi [TODO.md](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/TODO.md) e [docs/demo-plan.md](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/docs/demo-plan.md)).
