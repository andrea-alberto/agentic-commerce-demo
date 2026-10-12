# Piano di Preparazione Demo: Agentic Commerce al GDG DevFest 2026 Milano

**Tema dello speech:** *Agentic Commerce: Redefining E-Commerce across UCP, Web MCP, and Physical Retail*  
**Documento di riferimento abstract:** [docs/speech.md](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/docs/speech.md)  
**Approccio:** A fasi modulari (slot da 4 ore, da 4h fino a 20h massime)

---

## 1. Visione Narrativa e Architetturale

### 1.1 Il Contesto Storytelling: "Milano Centrale Express Pickup"
Per rendere la tecnologia comprensibile e tangibile alla platea della DevFest, la demo si sviluppa attorno a un caso d'uso di **Travel Retail** in un ambiente ad alto traffico:
- **Scenario:** Un passeggero a bordo di un Frecciarossa in arrivo al binario 12 di Milano Centrale tra 15 minuti.
- **Richiesta all'Agente:** *"Sto arrivando a Milano Centrale tra 15 minuti: ordinami un espresso doppio, una brioche al pistacchio da asporto e un caricatore USB-C 65W pronto per il ritiro immediato senza fare la fila."*
- **Azione dell'Agente:**
  1. Esegue la **Discovery UCP** (`GET /.well-known/ucp`) per identificare i merchant della stazione e le relative capability.
  2. Verifica disponibilità e posizione (`dev.ucp.location` & `dev.ucp.shopping.catalog`).
  3. Costruisce la sessione di checkout con opzione **In-Store Pickup** (`dev.ucp.shopping.fulfillment` con metodo `pickup`).
  4. Richiede la firma del mandato sicuro **AP2** (Intent & Payment Mandate).
  5. Rilascia al viaggiatore il codice/QR per il ritiro immediato al bancone/locker dedicato.

### 1.2 Perché lo stack aperto UCP + AP2 su Google Cloud?
- **Zero dipendenze proprietarie:** Si eliminano costosi cluster GPU locali (es. blueprint NVIDIA con modelli proprietari) a favore delle API serverless di Google (**Vertex AI** / **Gemini 3 Flash**).
- **Crittografia asimmetrica reale:** Dimostrazione matematica di non-ripudiabilità tramite i mandati crittografici AP2 (Verifiable Credentials / SD-JWT).
- **Architettura Cloud-Native su GCP:** Esecuzione serverless ultra-veloce su **Cloud Run** (regione Milano `europe-west8`), scalabile a zero costi a riposo.

---

## 2. Architettura Monorepo Nx & Le 4 Demo a Confronto

Per gestire la complessità multi-progetto ed eliminare l'esecuzione fragile di comandi shell/python diretti da terminale durante le sessioni live, il repository viene organizzato come un **Workspace Multi-Project Nx**:

```
ucp-demo-mi-devfest2026/ (Nx Monorepo)
├── apps/
│   ├── chat-client/           # [Angular 22] UI Viaggiatore per Demo 1 e Demo 3
│   ├── bopis-dashboard/       # [Angular 22] Schermo Cassa / Barista / Fattorino Stazione
│   ├── storefront-webmcp/     # [Angular 22] Mini E-Commerce con tool Web MCP (Demo 2)
│   └── backend-merchant/      # [Python / ADK] Merchant Agent & BOPIS Engine (Porta 10999)
├── libs/
│   ├── shared-models/         # [TypeScript] Modelli dati UCP e payload condivisi
│   └── shared-ui/             # [Angular] Componenti condivisi (LCM Modal AP2, Product Cards)
└── docs/                      # Specifiche, runbook e architettura del talk
```

### 2.1 I 4 Scenari Demo del Talk

| # | Scenario Demo | Topologia Architetturale | Focus Dimostrativo per il Talk | Canale UCP |
| :- | :--- | :--- | :--- | :--- |
| **Demo 1** | **Direct A2A & UCP** *(Baseline)* | `Chat Client UI` $\overset{\text{A2A}}{\longrightarrow}$ `Merchant Agent` $\longrightarrow$ `BOPIS Engine` | Spiega UCP, rendering guidato dai dati semantici, vincoli termici/preavviso e firma AP2 con LCM. | **A2A JSON-RPC** |
| **Demo 2** | **Web MCP E-Commerce** *(Confronto MCP)* | `Chat UI` $\longrightarrow$ `Shopper Agent` $\overset{\text{Web MCP}}{\longrightarrow}$ `Storefront Web` $\longrightarrow$ `BOPIS` | Mostra l'approccio basato su **Model Context Protocol**: l'e-commerce espone tool web e l'AI compra navigando gli strumenti del sito. | **Web MCP (HTTP/SSE)** |
| **Demo 3** | **Two-Agent Federation A2A** *(Full A2A)* | `Chat UI` $\longrightarrow$ `Shopper Agent` $\overset{\text{A2A M2M}}{\longleftrightarrow}$ `Merchant Agent` $\longrightarrow$ `BOPIS` | Dimostra la vera cooperazione tra AI: l'AI personale dell'utente (che conosce il biglietto del treno) negozia autonomamente con l'AI della stazione. | **A2A M2M Federato** |
| **Demo 4** | **Shopper Agent via UCP REST** *(REST Binding)* | `Chat UI` $\longrightarrow$ `Shopper Agent` $\overset{\text{REST + RFC 9421}}{\longrightarrow}$ `UCP REST Server` $\longrightarrow$ `BOPIS` | Dimostra il canale ufficiale **RESTful HTTP** di UCP con HTTP Message Signatures RFC 9421 per sistemi enterprise e checkout headless. | **RESTful HTTP RFC 9421** |

---

### 2.2 Componenti Trasversali a Fattor Comune

1. **Core BOPIS Retail Engine (`store.py`)**:
   - Catalogo unificato `products.json` (caldi, freddi, tech).
   - Regola termica (divieto caldo nello smart locker).
   - Regola del preavviso minimo di 30 minuti.
   - Finestre orarie (1 min treno, 10 min locker, 5 min banco).
   - Calcolo totali UCP e verifica mandati AP2.
2. **BOPIS Engine Front-End (Merchant & Dispatcher Screen)**:
   - Dashboard web dedicata per il personale di stazione (cucina/barista/fattorino).
   - Visualizzazione in tempo reale delle comande in arrivo via WebSockets o polling:
     - 🚆 *In Consegna al Posto Treno:* Frecciarossa 9540, Binario 14, Carrozza 4, Posto 12D (Countdown finestra 1 min).
     - 🔒 *Smart Locker:* Box #14, PIN 8492 (Finestra 10 min).
     - ⚡ *Ritiro Express al Banco:* Tavolo 5 / Banco (Timer 5 min).
     - 🛡️ *Badge Attestazione Hardware AP2:* Firma TPM / FIDO2 verificata.
3. **Simulatore AP2 Local Credential Manager (LCM)**:
   - Componente riutilizzabile per l'autorizzazione biometrica e la generazione dei mandati SD-JWT.

---

### 2.3 Sicurezza & Autenticazione (Pubblicazione su Internet)

In previsione della pubblicazione delle applicazioni sul web:
1. **Frontend Authentication con Firebase Auth (Google Sign-In)**:
   - Accesso protetto tramite account Google sia per il client Shopper sia per la Dashboard BOPIS.
   - Gestione utenti semplificata tramite la **Firebase Console** (abilitazione selettiva degli account Google autorizzati a visionare la demo prima del talk).
2. **Protezione dei Backend e delle API per Agenti**:
   - Gli endpoint di backend esposti agli agenti (specialmente negli scenari a 2 agenti e REST) vengono protetti tramite:
     - Verifica del Bearer Token (Firebase ID Token) per le chiamate da client web.
     - Autenticazione crittografica per le chiamate Machine-to-Machine tra agenti (API Key dedicate o HTTP Message Signatures RFC 9421 conformi a UCP).

---

### 2.4 Matrice delle Priorità di Sviluppo

```
P0 (Fondamenta & UX Visiva) ──> P1 (Core Confronto Talk) ──> P2 (Evoluzione A2A) ──> P3 (UCP REST Binding) ──> Backlog
```

1. **PRIORITÀ P0 (Fondamenta & UX Visiva) - ✅ COMPLETATO:**
   - **P0.1 Setup Nx Monorepo**: Configurazione `nx.json`, root `package.json`, orchestrazione pulita dei target `serve:all`, `serve:chat`, `serve:dashboard`, `serve:storefront`, `serve:backend`, `test:backend`, `test:mcp`.
   - **P0.2 Shared BOPIS Engine & Dashboard**:
     - Backend API REST `/bopis/orders`, `/bopis/orders/{id}/status`, `/bopis/stats`.
     - Persistenza unificata Firestore (`agentic-comm-mi-devfest-2026`) con fallback locale `bopis_orders.json`.
     - Registrazione automatica di ordini con dettagli treno, locker, tavolo e badge canale.
     - Applicazione Angular 22 dedicata per la Dashboard Operatore (`bopis-dashboard`, porta 4201).
     - Tracciamento e visualizzazione di Data/Ora Inserimento + Consegna Richiesta + Preavviso in minuti.
   - **P0.3 Firebase Authentication**:
     - Google Sign-In integrato con Firebase Auth (`agentic-comm-mi-devfest-2026`), accesso obbligatorio su entrambe le app.
2. **PRIORITÀ P1 (Core del Talk - Confronto Web MCP) - ✅ COMPLETATO:**
   - **P1.1 Storefront Web MCP (`storefront-webmcp`, porta 4202)**: Applicazione Angular 22 che espone il catalogo, l'esperienza e-commerce collegata al server MCP e il banner speaker con i 4 sotto-step sequenziali atomici (Filtro Catalogo ➔ Aggiungi Carrello ➔ Smart Locker ➔ Apri Checkout Drawer), dove ogni prompt attiva esattamente 1 sola chiamata a un metodo WebMCP.
   - **P1.2 Web MCP Server (`mcp_server.py`)**: Esposizione di 6 tool standard conformi al Model Context Protocol (`search_catalog`, `get_product_details`, `create_cart`, `add_to_cart`, `configure_fulfillment`, `checkout_cart`) su endpoint JSON-RPC 2.0 (`/mcp`, `/mcp/tools`).
   - **P1.3 Autonomous Shopper Agent (`shopper_agent.py`)**: Agente basato su Gemini (Google GenAI) che pianifica ed esegue autonomamente la spesa via MCP, rispettando i vincoli termici e logistici di stazione.
   - **P1.4 MCP Protocol Inspector Live**: Visualizzatore interattivo real-time dei messaggi JSON-RPC `tools/call` integrato nell'interfaccia.
   - **P1.5 Connessione Unificata BOPIS**: Gli ordini finalizzati via MCP (`channel_source: "web_mcp"`, badge verde smeraldo) appaiono istantaneamente sulla dashboard del dispatcher.
   - **P1.6 Test Suite E2E (`test:mcp`)**: 7/7 test passati al 100% con verifica automatizzata di handshake MCP, scoperta tool, violazioni termiche/preavviso e completamento ordine.
3. **PRIORITÀ P2 (Demo 3: Two-Agent A2A Federation) - ✅ COMPLETATO:**
   - **P2.1 Shopper Client (`shopper-client`, porta 4203)**: Frontend Angular 22 dedicato con Split-View interattivo (Chat + Live Protocol Inspector SSE).
   - **P2.2 Traveler Context Inspector**: Componente visivo riutilizzabile (`libs/shared-frontend/`) che mostra il biglietto (Frecciarossa 9540 / Italo 9923), PNR, posto a sedere, preferenze dietetiche, limite mandato AP2 e modale di modifica dati.
   - **P2.3 Shopper Agent Backend (`backend-shopper`, porta 10998)**: Backend con endpoint SSE streaming (`/shopper/mission/stream`), gestione contesti viaggiatore e negoziazione semantica M2M con l'agente del merchant di Milano Centrale.
   - **P2.4 Registrazione Ordine BOPIS**: Ordini federati generati con canale `two_agent_a2a` (`#ORD-MI-A2A...`) visualizzati in tempo reale sulla dispatch dashboard con badge amber.

4. **PRIORITÀ P3 (Demo 4: UCP Standard REST Binding con RFC 9421) - ✅ COMPLETATO:**
   - **P3.1 Merchant UCP REST Endpoints (`backend-merchant`, porta 10999)**: Implementazione degli endpoint ufficiali UCP (`GET /.well-known/ucp`, `GET /ucp/catalog/products`, `POST /ucp/checkouts`, `PATCH /ucp/checkouts/{id}`, `POST /ucp/checkouts/{id}/complete`).
   - **P3.2 HTTP Message Signatures RFC 9421 (`shared.rfc9421`)**: Firma crittografica automatica ECDSA-P256 e verifica di intestazioni (`Signature-Input`, `Signature`, `Content-Digest`).
   - **P3.3 Modalità Switcher Integrata**: Switch rapido tra Demo 3 e Demo 4 nell'interfaccia di `shopper-client`, con visualizzazione step-by-step dei pacchetti HTTP firmati.
   - **P3.4 Registrazione Ordine BOPIS**: Ordini finalizzati con canale `ucp_rest` (`#ORD-MI-REST...`) con verifica RFC 9421 e AP2 registrati sulla dashboard del dispatcher con badge viola.

5. **BACKLOG & FUTURE DEMOS (TODO):**
   - **Adattamento Demo 3 al Formalismo Formale UCP A2A (JSON-RPC 2.0 / `a2a.ucp.checkout`)**:
     - *Obiettivo:* Evolvere la comunicazione M2M di Demo 3 (attualmente basata su endpoint REST semantici dedicati `/a2a/negotiate` e `/a2a/commit`) verso il trasporto standard A2A di UCP ([`specification/shopping/checkout/a2a.md`](file:///c:/Projects/AgenticCommerce/prjs/ucp/docs/specification/shopping/checkout/a2a.md)).
     - *Dettagli:* Utilizzo del metodo JSON-RPC 2.0 `message/send` su `POST /api`, attivazione dell'estensione UCP con gli header `UCP-Agent` e `X-A2A-Extensions`, incapsulamento dell'intento semantico e restituzione del carrello nel `DataPart` con chiave formale **`a2a.ucp.checkout`**, e commit con mandati AP2 in **`a2a.ucp.checkout.payment`**.
   - **Demo 5: Acquisto Autonomo Delegato (Human-Not-Present / Autonomous Agentic Commerce)**:
     - *Storytelling:* Un viaggiatore frequente è interessato a un prodotto di pregio (es. una bottiglia di vino pregiato *Brunello di Montalcino DOCG* o *Barolo Riserva*) venduta dall'enoteca di stazione, ma intende procedere all'acquisto **solamente se il prezzo scende sotto una soglia prestabilita** (es. offerta speciale < €35.00 invece di €48.00).
     - *Flusso Tecnico (Scenario 2.2 AP2 / Delegated Autonomous Mode):*
       1. **Pre-autorizzazione del Mandato (Intent Mandate Delegato):** L'utente configura sul client un limite di spesa autonomo pre-approvato (es. max €40.00, validità 7 giorni) firmato una tantum con la propria Passkey.
       2. **Trigger di Mercato (Merchant Price Drop):** Simulazione di sconto promozionale sul backend del merchant (es. endpoint `POST /merchant/products/{id}/promo` che abbassa il prezzo del vino a €32.50).
       3. **Monitoraggio Periodico / Event Watcher:** Lo Shopper Agent monitora periodicamente il catalogo o riceve un webhook SSE di evento variazione prezzo.
       4. **Headless Execution (Human Not Present):** Rilevata la condizione favorevole, l'agente completa la sequenza d'acquisto in modo totalmente autonomo: negoziazione M2M, generazione del mandato headless nei limiti autorizzati, inoltro dell'ordine al BOPIS hub.
       5. **Notifica Asincrona al Viaggiatore:** L'utente riceve una notifica push: *"Affare concluso! Brunello di Montalcino acquistato a €32.50 (risparmio €15.50). Pronto per il ritiro allo Smart Locker Box #08 con PIN 5291 quando passerai da Milano Centrale."*
   - **Studio comparativo OpenAI ACP (Agentic Commerce Protocol)**: Benchmark di interoperabilità tra specifiche JSON-RPC/REST di UCP e ACP.
   - **Integrazione API Ferroviarie Real-Time**: Sincronizzazione automatica degli orari treno e binari con le API reali di Trenitalia e Italo (ritardi, cambi binario dinamici).
   - **Estensione Google Chrome In-Browser LLM (WebMCP Agent Extension)**:
     - *Obiettivo:* Superare le attuali limitazioni dei modelli In-Browser LLM (es. Gemini Nano / built-in AI single-tool call o assenza di accesso diretto allo stato/DOM) sviluppando un'estensione Chrome nativa dedicata agli agenti e-commerce.
     - *Architettura e Funzionalità:*
       1. **Side Panel Conversazionale:** UI laterale nativa Chrome (tramite `chrome.sidePanel`) per dialogare in linguaggio naturale con l'assistente mentre si naviga lo storefront.
       2. **Automatic DOM & UI Context Extraction:** Content script che interroga programmaticamente lo storefront (o invoca `window.__webmcp` / `navigator.modelContext`) ed estrae automaticamente il contesto Markdown (prodotti a video, filtri attivi, stato del carrello, vincoli di stazione) inserendolo nel prompt dell'LLM senza richiedere click manuali dell'utente.
       3. **WebMCP Bridge & Tool Dispatcher:** Intercettazione ed esecuzione sicura dei comandi WebMCP esposti dalla pagina (`filterProducts`, `addToCart`, `configureFulfillment`, `submitOrder`).
       4. **Multi-Turn Agentic Loop:** Gestione autonoma del loop agentico all'interno dell'estensione (pensiero ➔ tool call ➔ osservazione ➔ prossimo step), consentendo all'assistente di concatenare più azioni o recuperare da ambiguità in un unico flusso utente.
   - **Demo WebMCP con Estensione Chrome Custom (In-Browser AI Full Multi-Tool Calling)**:
     - *Obiettivo:* Fornire una modalità demo completa e autonoma con l'estensione Chrome custom, alimentata da un modello In-Browser AI (Gemini Nano / WebLLM) capace di pianificazione multi-step e chiamate tool multiple (multi-tool calling) per singolo prompt conversazionale, integrandosi direttamente con i metodi WebMCP dello storefront.
   - **Ricerca Semantica Vettoriale con Embeddings (Google Cloud Firestore Vector Search)**:
     - *Obiettivo:* Potenziare la scoperta prodotti tramite embeddings vettoriali sui nomi, descrizioni e chiavi/tag di ricerca nel catalogo.
     - *Dettagli:* Generazione degli embeddings (es. Vertex AI `text-embedding-004` / Gemini embeddings), persistenza e interrogazione con Firestore Vector Search (query k-NN `find_nearest`) per gestire ricerche sfumate, sinonimi o richieste complesse dell'utente.
   - **Supporto Categorie Standard di Settore Google Product Category (GPC) + GS1**:
     - *Obiettivo:* Conformità con le tassonomie commerciali aperte per la classificazione e la ricerca prodotti nel protocollo UCP.
     - *Dettagli:* Integrazione nei modelli di catalogo UCP dei codici Google Product Category (GPC) e degli standard globali GS1 (GPC / GTIN / attributi di settore Food & Beverage/Retail), con filtri di ricerca dedicati per categoria standard.
   - **Demo Milano Linate: Architettura Multi-Store / Multi-Location**:
     - *Obiettivo:* Dimostrare la scalabilità multi-location di UCP su punti vendita distribuiti (Milano Centrale vs. Milano Linate).
     - *Dettagli:* Gestione di cataloghi, disponibilità e punti di ritiro/consegna indipendenti per location; routing dinamico delle richieste e degli ordini dell'agente verso il punto vendita competente in base alla geolocalizzazione o all'itinerario del viaggiatore.
   - **Demo Milano Linate: Integrazione Orari Aerei Real-Time**:
     - *Obiettivo:* Coordinamento logistico e temporizzazione del ritiro/consegna in ambito aeroportuale.
     - *Dettagli:* Connessione con API di tracking voli real-time (partenze/arrivi Linate, ritardi, gate changes, orari imbarco) con calcolo dei tempi critici di consegna al Gate prima della chiusura dell'imbarco.
   - **Verifica e Ottimizzazione Query A2A con Prodotti Multipli**:
     - *Obiettivo:* Testare e ottimizzare la negoziazione semantica M2M quando l'utente richiede combinazioni di prodotti diversi (es. *"spremuta d'arancia fresca + panino vegano"*).
     - *Dettagli:* Analisi comparativa tra: (a) query semantica congiunta/disgiunta con risoluzione multi-match (OR) sul backend del merchant; (b) decomposizione dell'intento in chiamate A2A multiple/parallele con successiva aggregazione atomica nel carrello UCP.
   - **Applicazione Client `ucp-web-client` (Standalone Angular Client per Servizi UCP)**:
     - *Obiettivo:* Creare un'applicazione web client-only aperta (Angular 22 SPA, senza backend dedicato) per connettersi, interrogare ed effettuare operazioni di e-commerce su qualsiasi merchant conforme alle specifiche UCP.
     - *Funzionalità Chiave:*
       1. **Universal Merchant Discovery:** Inserimento dell'URL di un sito merchant ed esecuzione automatica della discovery (`GET /.well-known/ucp`), con parsing del profilo di capacità e versioni supportate.
       2. **Catalog Explorer & Search:** Navigazione del catalogo prodotti (`GET /ucp/catalog/products`), ricerca per parola chiave e filtraggio per categorie.
       3. **Client-Side Checkout Flow:** Gestione interattiva della sessione di carrello e checkout (`POST /ucp/checkouts`, `PATCH /ucp/checkouts/{id}`, `POST /ucp/checkouts/{id}/complete`).
       4. **RFC 9421 Signatures in-Browser:** Implementazione delle HTTP Message Signatures tramite Web Crypto API client-side per firmare le richieste verso server che richiedono autenticazione non ripudiabile.
       5. **Developer & Inspection Playground:** Visualizzazione trasparente dei payload scambiati, intestazioni di protocollo e tempi di risposta per il collaudo di servizi UCP di terze parti.

---

## 3. Guida Operativa per lo SLOT 1 (Prime 4 Ore)

I repository necessari sono già presenti in `c:\Projects\AgenticCommerce\prjs`. Ecco la sequenza operativa passo-passo per il primo slot:

### Step 1: Esplorare il Server di Riferimento UCP
- **Directory:** `c:\Projects\AgenticCommerce\prjs\ucp-samples\rest\python\server`
- **Comandi di riferimento:**
  ```bash
  cd c:\Projects\AgenticCommerce\prjs\ucp-samples\rest\python\server
  uv sync
  # Creazione database SQLite di test
  mkdir \tmp\ucp_test
  uv run import_csv.py --products_db_path=\tmp\ucp_test\products.db --transactions_db_path=\tmp\ucp_test\transactions.db --data_dir=..\test_data\flower_shop
  # Avvio server su porta 8182
  uv run server.py --products_db_path=\tmp\ucp_test\products.db --transactions_db_path=\tmp\ucp_test\transactions.db --port=8182 --allow_insecure_profile_urls
  ```
- **Test Discovery:**
  ```bash
  curl http://localhost:8182/.well-known/ucp
  ```
- **Esecuzione Client:**
  ```bash
  cd c:\Projects\AgenticCommerce\prjs\ucp-samples\rest\python\client\flower_shop
  uv run simple_happy_path_client.py --server_url=http://localhost:8182
  ```

### Step 2: Esplorare l'Agente Cymbal Retail A2A
- **Directory Backend:** `c:\Projects\AgenticCommerce\prjs\ucp-samples\a2a\business_agent`
  ```bash
  cd c:\Projects\AgenticCommerce\prjs\ucp-samples\a2a\business_agent
  uv sync
  # Configura GOOGLE_API_KEY nel file .env
  uv run business_agent
  ```
- **Directory Frontend:** `c:\Projects\AgenticCommerce\prjs\ucp-samples\a2a\chat-client`
  ```bash
  cd c:\Projects\AgenticCommerce\prjs\ucp-samples\a2a\chat-client
  npm install
  npm run dev
  ```
- Navigare su `http://localhost:3000` e testare la conversazione per familiarizzare con il rendering delle capability UCP.

### Step 3: Esplorare i Mandati Crittografici AP2
- **Directory:** `c:\Projects\AgenticCommerce\prjs\AP2\code\samples\python\scenarios\a2a\human-present\cards`
- Analizzare il flusso di generazione e firma dei mandati (`IntentMandate`, `CartMandate`, `PaymentMandate`) descritto in [AP2/README.md](file:///c:/Projects/AgenticCommerce/prjs/AP2/README.md).
