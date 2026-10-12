# Agentic Commerce Demo — UCP, Web MCP & Physical Retail

> **Agentic Commerce: Redefining E-Commerce across UCP, Web MCP, and Physical Retail**  
> *Monorepo Nx multi-progetto con 4 applicazioni Angular 22, 2 microservizi Python basati su Gemini 2.5 Flash, sicurezza Passkey AP2 e motore logistico di stazione (BOPIS Engine).*  
>  
> 💡 *Originally designed and showcased at GDG DevFest Milano 2026 as a reference architecture for open Agentic Commerce.*

---

## 1. Visione del Progetto

Questa suite dimostrativa presenta l'evoluzione del commercio elettronico verso l'**Agentic Commerce**: un ecosistema aperto basato su standard in cui agenti intelligenti cooperano con merchant fisici ed e-commerce per acquistare autonomamente nel mondo reale per conto del viaggiatore.

Lo scenario concreto è il **Travel Retail ad alta velocità a Milano Centrale**: un passeggero in arrivo o a bordo di un treno Frecciarossa che richiede pasti, caffè o accessori tech all'assistente personale con consegna espressa al posto sul treno, al bancone o tramite Smart Locker.

### I Tre Standard Aperti
1. **Universal Commerce Protocol (UCP)**: Lo standard aperto (sviluppato da Google in collaborazione con Shopify, Walmart e partner retail) che unifica la discovery dei servizi (`/.well-known/ucp`), i carrelli, il checkout e i canali di ritiro/consegna (BOPIS).
2. **Agent Payment Protocol (AP2)**: Il protocollo di pagamento crittografico con mandati delegati non ripudiabili (SD-JWT, firme hardware Passkey FIDO2 / TPM), che consente agli agenti di spendere entro limiti certi senza tocco manuale continuo.
3. **Model Context Protocol (Web MCP)**: Lo standard per esporre tool e risorse di un'applicazione web nativa direttamente agli agenti AI.

---

## 2. Le 4 Demo a Confronto

La suite offre una comparazione chiara, visiva e strutturata tra i 4 paradigmi di integrazione agentica:

| # | Demo | Canale Protocollo | Frontend | Backend Coinvolti | Focus Dimostrativo |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Direct A2A** *(Baseline)* | JSON-RPC 2.0 / A2A | `chat-client` (`:4200`) | `backend-merchant` (`:10999`) | Chatbot B2C diretto con l'agente del negozio, parsing intenti e autorizzazione AP2 con modale LCM. |
| **2** | **Web MCP** *(E-Commerce)* | Model Context Protocol | `storefront-webmcp` (`:4202`) | `backend-merchant` (`:10999`) | L'agente naviga ed esegue tool esposti dal sito web (ricerca catalogo, carrello, calcolo consegna). |
| **3** | **Two-Agent Federation** *(Full A2A)* | A2A Semantico M2M con **Gemini 2.5 Flash** | `shopper-client` (`:4203`) | `backend-shopper` (`:10998`) $\longleftrightarrow$ `backend-merchant` (`:10999`) | Cooperazione tra agenti: il Personal Shopper inietta il biglietto e negozia con il Merchant Agent della stazione; gestione combo multi-articolo. |
| **4** | **UCP Standard REST** *(REST Binding)* | HTTP RESTful + **RFC 9421** | `shopper-client` (`:4203`) | `backend-shopper` (`:10998`) $\longrightarrow$ `backend-merchant` (`:10999`) | Il canale REST enterprise ufficiale di UCP con HTTP Message Signatures ECDSA-P256 e sessioni di checkout conformi. |

---

## 3. Mappa delle Porte e dei Microservizi

Tutti i servizi possono girare contemporaneamente senza conflitti di porta:

```
                                  [ INTERFACCIA UTENTE (Angular 22) ]
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
   │  • Milano Centrale Travel Retail Hub                   │ │  • Personal Shopper Agent │  │
   │  • Merchant Agent (Gemini 2.5 Flash)                   │ │  • Intent (Gemini 2.5 Fl.)│──┘
   │  • UCP REST Server (RFC 9421 ECDSA-P256)               │ │  • Biglietto & Contesto   │
   │  • Web MCP Server & BOPIS Engine (store.py)            │ │  • Validatore Passkey AP2 │
   └────────────────────────────────────────────────────────┘ └───────────────────────────┘
```

| Porta | Servizio | Stack Tecnologico | Ruolo Architetturale |
| :---: | :--- | :--- | :--- |
| **`4200`** | `chat-client` | Angular 22 | Client per la Demo 1 (Baseline Chat A2A diretta) |
| **`4201`** | `bopis-dashboard` | Angular 22 | Hub centrale per gli operatori di stazione (Cucina, Barista, Corriere al Binario) |
| **`4202`** | `storefront-webmcp` | Angular 22 | Storefront per la Demo 2 (Web MCP Registry) |
| **`4203`** | `shopper-client` | Angular 22 | Client split-view per la Demo 3 (A2A) e Demo 4 (REST) con Live Protocol Inspector |
| **`10998`** | `backend-shopper` | Python / Starlette | Personal Shopper Agent del viaggiatore (Contesto, Gemini 2.5 Flash e SSE stream) |
| **`10999`** | `backend-merchant` | Python / Starlette | Merchant Agent di stazione (Gemini 2.5 Flash, BOPIS Engine, A2A, UCP REST) |

---

## 4. Intelligenza Artificiale Duale: Gemini 2.5 Flash

Negli scenari a due agenti (Demo 3 & 4), l'intelligenza semantica è affidata a **`gemini-2.5-flash`** con **Structured Outputs (Pydantic)**:

1. **Personal Shopper Agent (`shopper_service.py`)**:
   - Analizza il messaggio dell'utente (es. *"Prendimi un caffè doppio e una focaccia ligure per la carrozza 4"*).
   - Riconosce la modalità di consegna desiderata (`in_seat_train`).
   - Inietta il contesto del biglietto (treno *Frecciarossa 9540*, partenza *13:10*, binario *14*, carrozza *4*, posto *12D*).
   - Formula la query semantica A2A machine-to-machine per l'agente della stazione.

2. **Station Merchant Agent (`main.py`)**:
   - Esamina il catalogo reale `products.json`.
   - Riconosce ordini singoli o combinazioni multi-articolo:
     - `CAFFE-001`: *Espresso Doppio Illy Caldo* (€2.50)
     - `TOAST-003`: *Focaccia Toast Calda con Prosciutto Cotto e Fontina* (€6.50)
     - Totale prodotti negoziato: **€9.00**.
   - Delega al **BOPIS Engine** la verifica termica (`is_hot: True` ➔ **esclude automaticamente lo Smart Locker**) e la fattibilità logistica (consegna al posto consigliata a €15.50 tot, oppure ritiro al banco a €9.00 tot).

---

## 5. Guida Rapida di Avvio

### Prerequisiti
- **Node.js**: v20+ con `npm`
- **Python**: v3.11+ con virtualenv in `backend/.venv`
- File `.env` configurato nella root (vedi `.env.example`):
  ```env
  GOOGLE_API_KEY=la_tua_chiave_google_ai_studio
  # DEFAULT_BUYER_EMAIL=alex.traveler@example.com (opzionale)
  # OPERATOR_EMAILS=merchant@agentic-commerce.demo (opzionale)
  ```

### Avvio Simultaneo
Per avviare tutti i 6 servizi con un solo comando:
```powershell
npm run serve:all
```

### Avvio Singolo tramite Nx
```powershell
# Backend
npx nx run backend-merchant:serve     # Porta 10999
npx nx run backend-shopper:serve      # Porta 10998

# Frontend
npx nx run shopper-client:serve       # Porta 4203 (Demo 3 & 4)
npx nx run bopis-dashboard:serve      # Porta 4201 (Schermo Stazione)
npx nx run storefront-webmcp:serve    # Porta 4202 (Demo 2)
npx nx run chat-client:serve          # Porta 4200 (Demo 1)
```

---

## 6. Documentazione Dettagliata

La documentazione architetturale e tecnica è disponibile nella cartella `docs/`:

- [**`docs/architecture.md`**](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/docs/architecture.md): Specifica architetturale completa, diagrammi di sequenza e modelli crittografici.
- [**`docs/gcp-ucp-architecture.md`**](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/docs/gcp-ucp-architecture.md): Pattern di middleware cloud serverless su Google Cloud (Cloud Run, Firestore, Vertex AI).
- [**`docs/ucp-requirements-and-capabilities-matrix.md`**](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/docs/ucp-requirements-and-capabilities-matrix.md): Matrice completa dei requisiti UCP (RFC 2119), livelli di rilevanza (1-3) e conformità della demo.
- [**`docs/demo-plan.md`**](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/docs/demo-plan.md): Panoramica dei 4 scenari dimostrativi e flussi inter-agente.
- [**`backend/README.md`**](file:///c:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/backend/README.md): Dettaglio tecnico dei microservizi Python, delle API e di Gemini 2.5 Flash.


