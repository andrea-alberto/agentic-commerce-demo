# Runbook Operativo: Slot 3 (Two-Agent A2A Federation & UCP REST Binding con RFC 9421)

> **Contesto Evento:** GDG DevFest 2026 Milano  
> **Tema:** Agentic Commerce across UCP, Web MCP & Physical Retail  
> **Fase:** 3 (Ore 8 - 14) - Two-Agent Machine-to-Machine Federation (Demo 3) & Standard UCP REST Binding con RFC 9421 HTTP Message Signatures (Demo 4)

---

## 1. Obiettivi Raggiunti in Questa Fase

1. **Scaffold e Isolamento dei Progetti Shared:**
   - **`libs/shared-frontend/`**: Libreria Angular 22 riutilizzabile contenente modelli TypeScript unificati (`TravelerContext`, `TrainTicket`, `TravelerPreferences`, `AP2Delegation`, `ProtocolStep`), il componente grafico del biglietto ferroviario ([`TravelerTicketCardComponent`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/libs/shared-frontend/src/components/traveler-ticket-card.component.ts)) con scenari rapidi A/B e il modale di personalizzazione contesto ([`TravelerContextModalComponent`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/libs/shared-frontend/src/components/traveler-context-modal.component.ts)).
   - **`backend/src/shared/`**: Modulo Python con modelli Pydantic, validatore dei vincoli termici e logistici di stazione ([`station_rules.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/station_rules.py)), generatore/verificatore di mandati crittografici AP2 ([`ap2_crypto.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/ap2_crypto.py)) e motore di firma crittografica HTTP RFC 9421 ECDSA-P256 ([`rfc9421.py`](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/src/shared/rfc9421.py)).

2. **Estensione Merchant Backend per UCP REST (Porta `10999`):**
   - Esposizione degli endpoint standard conformi alla specifica UCP:
     - `GET /.well-known/ucp` (Discovery manifest aggiornato con servizio REST)
     - `GET /ucp/catalog/products` (Catalogo retail indicizzato)
     - `POST /ucp/checkouts` (Creazione sessione carrello)
     - `PATCH /ucp/checkouts/{id}` (Configurazione opzioni di fulfillment e stazione)
     - `POST /ucp/checkouts/{id}/complete` (Completamento transazione con verifica crittografica RFC 9421 e registrazione automatica nel BOPIS Hub).

3. **Backend Shopper Agent Dedicato (Porta `10998`):**
   - Microservizio Python Starlette (`backend-shopper`) che incarna l'Agente Personale del Viaggiatore.
   - Gestione dinamica dello stato in-memory del contesto del cliente (`GET /shopper/context`, `POST /shopper/context`, `POST /shopper/context/preset/{id}`).
   - Endpoint di streaming Server-Sent Events (SSE) `POST /shopper/mission/stream` per inviare al browser ogni singolo passaggio di protocollo in tempo reale sia per Demo 3 sia per Demo 4.

4. **Frontend Shopper Client Dedicato (Porta `4203`):**
   - Applicazione autonoma in **Angular 22** con Standalone Components, Signal reattivi e supporto dark-mode high-tech.
   - **Header Switcher:** Toggle con 1-click tra `🤖 Demo 3: Two-Agent A2A` e `🌐 Demo 4: UCP REST`.
   - **Traveler Context Bar:** Banner del biglietto ferroviario (Frecciarossa 9540 vs Italo 9923) con PNR, posto a sedere, binario, massimale AP2, switch istantaneo tra scenari e pulsante *✏️ Modifica Contesto*.
   - **Split-View Interattivo:**
     - **Sinistra (45%):** Chat dell'agente con suggerimenti rapidi, animazione streaming e card ordine confermato con badge AP2 FIDO2.
     - **Destra (55%):** **Live Protocol Inspector** con timeline progressiva degli step (1-5), badge attori (`shopper_agent ➔ merchant_agent` / `shopper_agent ➔ ucp_rest_server`), pannello di verifica firme RFC 9421 e visualizzatore JSON payload con copia negli appunti.
     - Pulsante per comprimere/espandere il pannello dell'Inspector a tutta larghezza.

5. **Integrazione Omnichannel Centralizzata su `bopis-dashboard` (Porta `4201`):**
   - Gli ordini generati da tutte e 4 le demo convergono in tempo reale nella dispatch board del personale di stazione con codifica colore dedicata:
     - 🔵 **Demo 1:** `UCP Direct A2A` (Porta `4200`)
     - 🟢 **Demo 2:** `Web MCP` (Porta `4202`)
     - 🟡 **Demo 3:** `Two-Agent A2A M2M` (Porta `4203`)
     - 🟣 **Demo 4:** `UCP REST Binding (RFC 9421)` (Porta `4203`)

---

## 2. Mappa Completa delle Porte e dei Servizi del Monorepo

Tutti i 6 processi possono girare contemporaneamente senza alcun conflitto di porte:

| Porta | Servizio / Progetto Nx | Tecnologia | Ruolo Architetturale | Canale Protocollo |
| :---: | :--- | :--- | :--- | :--- |
| **`4200`** | `chat-client` | Angular 22 | Client Viaggiatore per Demo 1 (Baseline Chat A2A diretta) | JSON-RPC 2.0 / A2A |
| **`4201`** | `bopis-dashboard` | Angular 22 | Station Dispatcher Hub (Cucina, Barista, Corriere Binario) | Firestore / REST Sync |
| **`4202`** | `storefront-webmcp` | Angular 22 | Storefront E-Commerce per Demo 2 (Web MCP Tools) | Web MCP (Tools Call) |
| **`4203`** | `shopper-client` | Angular 22 | Personal Shopper Client per Demo 3 e Demo 4 (Split-View) | SSE Live Stream |
| **`10998`** | `backend-shopper` | Python / Starlette | Personal Shopper Agent Service (Contesto Viaggiatore & SSE) | SSE / HTTP REST |
| **`10999`** | `backend-merchant` | Python / FastAPI / ADK | Merchant Retail Hub Milano Centrale (A2A + REST + MCP + BOPIS) | A2A, UCP REST, MCP, BOPIS |

---

## 3. Guida Operativa di Avvio Rapido

Dalla root del repository `c:\Projects\AgenticCommerce\prjs\ucp-demo-mi-devfest2026`:

### 3.1 Avvio di Tutti i Servizi in Parallelo
```powershell
npm run serve:all
```

### 3.2 Oppure Avvio Singolo per Progetto (Terminale Dedicato)

```powershell
# 1. Merchant Retail Hub (A2A, UCP REST, MCP, BOPIS) - Porta 10999
npx nx run backend-merchant:serve

# 2. Shopper Agent Service - Porta 10998
npx nx run backend-shopper:serve

# 3. Personal Shopper Client (Demo 3 & 4) - Porta 4203
npx nx run shopper-client:serve

# 4. Central BOPIS Dispatcher Hub - Porta 4201
npx nx run bopis-dashboard:serve

# 5. [Opzionale] Storefront Web MCP (Demo 2) - Porta 4202
npx nx run storefront-webmcp:serve

# 6. [Opzionale] Direct Chat Client (Demo 1) - Porta 4200
npx nx run chat-client:serve
```

---

## 4. Test e Verifica Passo-Passo durante la Demo

### 4.1 Preparazione Schermi per il Talk

1. Apri una finestra browser con **`http://localhost:4203/`** (**Shopper Client** - proiettata come schermo principale).
2. Apri una seconda finestra browser o scheda affiancata con **`http://localhost:4201/`** (**BOPIS Dashboard** - schermo operatore stazione).

---

### 4.2 Esecuzione Demo 3: Two-Agent A2A Federation (M2M Semantic Protocol)

#### Step 1: Selezione Modalità & Contesto
1. In cima alla schermata di `http://localhost:4203/`, assicurati che sia selezionato il pulsante **`[🤖 Demo 3: Two-Agent A2A]`** (sfondo blu/indaco).
2. Nel banner del biglietto, osserva i dettagli precaricati dello **Scenario A (Frecciarossa 9540)**:
   - Treno: *Frecciarossa 9540* · Partenza ore *13:10* · Binario *14* · Carrozza *4* · Posto *12D*.
   - Massimale AP2: *≤ €30.00*.
   - Dieta: *No carne rossa • Piatti freschi e leggeri*.

#### Step 2: Lancio della Missione
1. Digita nel campo di input una richiesta in linguaggio naturale (anche combinata multi-prodotto), come ad esempio:
   ```text
   Prendimi un caffè doppio e una focaccia ligure per la carrozza 4
   ```
   *(oppure clicca sul chip rapido "🥪 Pranzo a bordo treno")*.
2. Clicca su **Invia ➔**.

#### Step 3: Negoziazione Semantica AI Machine-to-Machine (Split-View Inspector)
- A sinistra, la chat mostra in tempo reale l'elaborazione degli agenti.
- A destra, il **Live Protocol Inspector** visualizza i passaggi eseguiti con **Gemini 2.5 Flash**:
  1. **`ANALYZE_TRAVELER_INTENT`** (`shopper_agent ➔ shopper_agent`):
     - L'assistente personale con **Gemini 2.5 Flash** deduce la modalità `in_seat_train` dall'indicazione *"carrozza 4"*.
     - Inietta il contesto del biglietto (*Frecciarossa 9540*, partenza *13:10*, binario *14*, carrozza *4*, posto *12D*).
     - Formula la query semantica A2A: *"Caffè doppio e focaccia ligure per consegna a bordo Frecciarossa 9540, Carrozza 4, Posto 12D..."*.
  2. **`A2A_QUERY_INTENT`** (`shopper_agent ➔ merchant_agent`):
     - Invio della richiesta Machine-to-Machine all'agente del Bistrot di Milano Centrale (porta 10999).
  3. **`A2A_PROPOSAL_OFFER`** (`merchant_agent ➔ shopper_agent`):
     - Il Merchant Agent con **Gemini 2.5 Flash** analizza il catalogo (`products.json`) ed estrae la combo:
       - *Espresso Doppio Illy Caldo* (CAFFE-001, €2.50)
       - *Focaccia Toast Calda con Prosciutto Cotto e Fontina* (TOAST-003, €6.50)
       - Totale articoli negoziato: **€9.00**.
     - Il **BOPIS Engine** applica le regole logistiche e termiche:
       - Identifica gli articoli caldi (`is_hot: True`) ➔ **Esclude automaticamente lo Smart Locker**.
       - Valida la consegna a bordo treno (13:05, Binario 14, +€6.50, totale €15.50) e il ritiro express al banco (+€0.00, totale €9.00).

#### Step 3.5: Selezione dell'Opzione & Autorizzazione Biometrica Human-Present (LCM)
- La chat mostra la proposta negoziata interattiva con la card del combo e il selettore delle modalità di ricezione:
  - Seleziona **🚆 Consegna al Posto Treno (13:05)** (Consigliato).
  - Clicca su **"Conferma e Autorizza (Passkey AP2)"**.
- Si apre a schermo il **Modale di Sistema LCM (Passkey FIDO2)**:
  - **Banner Trusted OS:** *🛡️ AP2 HUMAN-PRESENT SPEC · Local Credential Manager (LCM) • Passkey FIDO2 Client Surface*.
  - **Riepilogo Transazione:** Esercente Verificato (`milano-centrale.ucp.dev`), totale autorizzato (€15.50), dettaglio articoli (Espresso Doppio + Focaccia) e consegna al treno.
  - **Hardware Security Card:** Certificato hardware Android KeyMint / TPM Passkey P-256 (`Key: fido2_p256_mario_rossi`).
  - **Sensore Touch Biometrico:** Clicca sul pulsante con l'impronta digitale: scansione biometrica e generazione on-device dei token SD-JWT (`CartMandate` e `PaymentMandate`).

#### Step 4: Finalizzazione dell'Ordine
- Il client invia il mandato firmato a `POST /shopper/mission/authorize`:
  4. **`AP2_MANDATE_VERIFICATION`** (`shopper_agent ➔ shopper_agent`): Validazione crittografica della firma Passkey e massimale.
  5. **`A2A_COMMIT_ORDER`** (`shopper_agent ➔ merchant_agent`): Commit finale della comanda multi-articolo.
  6. **`A2A_ORDER_CONFIRMED`**: Ricezione della conferma d'ordine `#ORD-MI-A2A...`.

#### Step 5: Verifica su BOPIS Dispatcher (:4201)
Passa alla finestra `http://localhost:4201/`:
- Nella colonna **"⏳ In Preparazione"** è presente la comanda con il tag ambra:
  ```
  DEMO 3: TWO-AGENT A2A M2M
  ```
- Dettaglio comanda: *1x Espresso Doppio Illy Caldo + 1x Focaccia Toast Calda con Prosciutto Cotto e Fontina*.
- Dettagli di consegna: *Frecciarossa 9540 • Binario 14 • Carrozza 4 • Posto 12D*.
- Metodo di pagamento: *🛡️ Mandato Passkey AP2 (Firma On-Device LCM)*.

---

### 4.3 Esecuzione Demo 4: UCP Standard REST Binding con RFC 9421 Signatures

#### Step 1: Switch di Modalità
1. Su `http://localhost:4203/`, clicca in testata sul pulsante **`[🌐 Demo 4: UCP REST]`**.
2. Il badge si colora di ciano e l'Inspector si imposta sulla specifica REST UCP con firme RFC 9421.

#### Step 2: Switch Contesto su Scenario B (Smart Locker)
1. Nel banner del biglietto, clicca sul chip rapido **`[⚡ Sosta 45 min]`** (Scenario B):
    - Treno: *Italo 9923* · Partenza *13:55* · Binario *18* · Carrozza *6* · Posto *21B*.
    - Ritiro preferito: *Smart Locker (Piano Interrato)*.
    - Dieta: *Opzione vegetariana o vegana*.

#### Step 3: Lancio della Missione REST
1. Clicca sul chip rapido **"⚡ Snack veloce allo Smart Locker"** oppure digita:
    ```text
    Preparami uno snack da ritirare subito allo Smart Locker con verifica RFC 9421
    ```
2. Clicca su **Invia ➔**.

#### Step 4: Cosa succede a schermo (Split-View Inspector & Modale LCM)
Il **Live Protocol Inspector** visualizza i passaggi della specifica REST ufficiale di UCP:
1. **`HTTP_GET_DISCOVERY`** (`shopper_agent ➔ ucp_rest_server`):
    - `GET /.well-known/ucp` — Recupero del capability manifest del merchant di Milano Centrale.
2. **`HTTP_GET_CATALOG`** (`shopper_agent ➔ ucp_rest_server`):
    - `GET /ucp/catalog/products` — Selezione dell'articolo (*Ciabatta con Crudo di Parma* o panino freddo compatibile con locker).
3. **`HTTP_POST_CHECKOUT`** (`shopper_agent ➔ ucp_rest_server`):
    - `POST /ucp/checkouts` — Creazione della sessione di checkout UCP.
4. **`HTTP_PATCH_FULFILLMENT`** (`shopper_agent ➔ ucp_rest_server`):
    - `PATCH /ucp/checkouts/{id}` — Configurazione della modalità Smart Locker (Box #14, PIN).
5. **Apertura Modale LCM Passkey (Human-Present):**
    - L'utente tocca il sensore d'impronta autorizzando l'importo del checkout REST (€7.50).
6. **`HTTP_POST_COMPLETE_RFC9421`** (`shopper_agent ➔ ucp_rest_server`):
    - `POST /ucp/checkouts/{id}/complete` con firma RFC 9421 ECDSA-P256 e mandato AP2.
    - **Riquadro Crittografico RFC 9421:** L'Inspector evidenzia le intestazioni crittografiche verificate:
      - `Signature-Input: sig1=("@method" "@path" "@authority" "content-digest");keyid="...';alg="ecdsa-p256"`
      - `Signature: sig1=:MEQCIG...:`
      - `Content-Digest: sha-256=:...:`

#### Step 5: Verifica su BOPIS Dispatcher (:4201)
Passa alla finestra `http://localhost:4201/`:
- Nella colonna **"⏳ In Preparazione"** appare la nuova comanda con tag viola:
  ```
  DEMO 4: UCP REST BINDING
  ```
- Dettagli di consegna: *Smart Locker Piano Interrato • Box #14 • PIN 3819*.

---

### 4.4 Test della Personalizzazione del Contesto ("Modifica Contesto")

Per dimostrare alla platea come l'Agente adatti istantaneamente le proprie decisioni ai vincoli dell'utente:
1. Su `http://localhost:4203/`, clicca sul pulsante **`✏️ Modifica Contesto`** nel banner del biglietto.
2. Nel modale che si apre:
   - Modifica il **Numero Treno** (es. `Frecciarossa 9511`).
   - Modifica il **Posto a Sedere** (es. `3A`).
   - Modifica il **Massimale Delegato AP2** impostandolo a `€ 5.00`.
3. Clicca su **`💾 Salva Contesto`**.
4. Invia una nuova richiesta di ordine: la chat e l'Inspector mostreranno come l'assistente gestisce il nuovo contesto aggiornato!

---

## 5. Test Suite Automatizzata E2E

Per verificare programmaticamente la salute di tutte le componenti (Discovery, Contesto, Preset, A2A Stream, REST RFC 9421 Stream e BOPIS Hub) in un unico comando senza aprire il browser:

```powershell
python scratch/test_e2e_full.py
```

**Output atteso:**
```text
--- 1. Testing GET /shopper/context ---
Traveler Context: Mario Rossi Frecciarossa 9540 12D

--- 2. Testing Preset Change (scenario_transit_locker) ---
Updated Context: Italo 9923 pickup_locker

--- 3. Testing Demo 3 A2A Mission Stream ---
  [A2A Step 1] ANALYZE_TRAVELER_INTENT: Analisi richiesta viaggiatore: ...
  [A2A Step 2] A2A_QUERY_INTENT: Invio messaggio semantico A2A all'agente del Bistrot ...
  [A2A Step 3] A2A_PROPOSAL_OFFER: L'agente della stazione risponde con proposta approvata ...
  [A2A Step 4] AP2_MANDATE_VERIFICATION: L'assistente valida il mandato AP2 ...
  [A2A Step 5] ORDER_CONFIRMED: Negoziazione M2M conclusa con successo! Ordine #ORD-MI-A2A...
  [A2A Final] Order ID: ORD-MI-A2A...

--- 4. Testing Demo 4 UCP REST Mission Stream ---
  [REST Step 1] HTTP_GET_DISCOVERY: Esecuzione UCP Service Discovery: GET /.well-known/ucp.
  [REST Step 2] HTTP_GET_CATALOG: Interrogazione catalogo REST UCP: GET /ucp/catalog/products.
  [REST Step 3] HTTP_POST_CHECKOUT: Creazione sessione di checkout UCP: POST /ucp/checkouts.
  [REST Step 4] HTTP_PATCH_FULFILLMENT: Configurazione modalità di ritiro stazione: PATCH /ucp/checkouts/...
  [REST Step 5] HTTP_POST_COMPLETE_RFC9421: Completamento transazione con firma crittografica RFC 9421.
  [REST Final] Order ID: ORD-MI-REST...

--- 5. Checking Central Merchant BOPIS Orders (:10999) ---
Total BOPIS Orders in Dispatcher: 43+
 - #ORD-MI-...: Demo 3: Two-Agent A2A M2M | preparing | ap2 | €...
 - #ORD-MI-...: Demo 4: UCP REST Binding | preparing | ap2 | €...

--- 6. Checking shopper-client HTTP 200 on :4203 ---
Shopper Client Status: 200
```

---

## 6. Script Narrativo per lo Speaker durante il Talk

| Minuto | Azione a Schermo | Cosa Dire alla Platea (Messaggio Chiave) |
| :---: | :--- | :--- |
| **00:00 - 01:30** | Mostra `http://localhost:4203/` e il banner del biglietto | *"Nelle prime due demo abbiamo visto l'interazione diretta con il merchant e la navigazione via Web MCP. Ora facciamo il vero salto di paradigma dell'Agentic Commerce: **l'interazione tra due agenti autonomi** (Two-Agent Federation)."* |
| **01:30 - 03:00** | Mostra i dati del viaggiatore nel banner e il massimale AP2 | *"Il mio assistente personale non è il server del negozio: vive nel mio smartphone, conosce il mio biglietto del Frecciarossa per Roma, sa che sono seduto al posto 12D e possiede un **mandato AP2** con budget massimo delegato di 30 euro."* |
| **03:00 - 05:00** | Clicca su *"Pranzo a bordo treno"* e indica l'**Inspector** a destra | *"Guardate cosa accade nel protocol inspector in tempo reale: l'utente non seleziona prodotti né orari. I due agenti negoziano via A2A Machine-to-Machine. L'agente di stazione valida la finestra di 1 minuto all'arrivo del treno, l'assistente valida il mandato crittografico AP2, e l'ordine è confermato."* |
| **05:00 - 06:30** | Passa alla **BOPIS Dashboard (:4201)** | *"Spostiamoci nella cucina di Milano Centrale: il cuoco riceve la comanda marchiata 'Demo 3 A2A M2M' con l'indicazione esatta di carrozza e posto treno. Nessuna app intermediaria, zero commissioni di delivery proprietarie."* |
| **06:30 - 08:30** | Switch su **Demo 4 (UCP REST)** e invia snack per lo Smart Locker | *"Cosa succede invece se l'infrastruttura del merchant non usa agenti conversazionali ma un classico backend enterprise headless? UCP definisce il binding REST ufficiale. Qui vedete i 5 passaggi HTTP con **RFC 9421 HTTP Message Signatures**: ogni payload è firmato crittograficamente con ECDSA-P256 garantendo la non-ripudiabilità legale della transazione."* |
| **08:30 - 10:00** | Q&A e conclusione architetturale | *"UCP e AP2 unificano tutto: A2A per la negoziazione semantica tra AI, REST con RFC 9421 per i sistemi aziendali tradizionali, e Web MCP per le web application ibride. Questo è il futuro dell'Agentic Commerce aperto."* |

---

## 7. Troubleshooting Rapido in Live

- **Se lo streaming SSE sembra non partire:**
  - Verifica che `backend-shopper` sia attivo su porta `10998` (`curl.exe http://localhost:10998/health`).
- **Se la dashboard non mostra il nuovo ordine:**
  - Ricarica la pagina `http://localhost:4201/`: la sincronizzazione riprende istantaneamente sia tramite Firestore WebSockets sia tramite fallback REST su `http://localhost:10999/bopis/orders`.
- **Se vuoi ripulire gli ordini di test:**
  - Nel backend merchant, elimina o svuota il file locale `backend/src/travel_retail_agent/data/bopis_orders.json` oppure avvia una nuova sessione.
