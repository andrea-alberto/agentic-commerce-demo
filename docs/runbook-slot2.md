# Runbook Slot 2: Scenario Travel Retail Milano & Ritiro Fisico (BOPIS)

> **Contesto Evento:** GDG DevFest 2026 Milano  
> **Tema:** Agentic Commerce across UCP, Web MCP & Physical Retail  
> **Fase:** 2 (Ore 4 - 8) - Scenario Stazione Milano Centrale, Regole Termiche & Consegna al Posto Treno

---

## 1. Obiettivi Raggiunti in Questa Fase

1. **Isolamento Completo del Progetto Demo:**
   - La demo vive ora interamente all'interno di [`ucp-demo-mi-devfest2026`](file:///C:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026).
   - Il repository upstream di riferimento [`ucp-samples`](file:///C:/Projects/AgenticCommerce/prjs/ucp-samples) rimane intatto come base pulita.

2. **Frontend Moderno in Angular 22 (Google Flagship):**
   - Costruito con l'ultimissima release **Angular 22** (`@angular/core@22.2.1` su Node.js LTS `v24.21.0` via `nvm`).
   - Sfrutta le novità più recenti del framework: Signals reattivi `signal()`, control flow nativo `@if` / `@for`, Standalone Components e compilazione ottimizzata con `@angular/build`.
   - Brandizzato per **Milano Centrale Hub Travel Retail**.
   - Include chip di prompt rapidi preconfigurati per lo speaker/presentatore durante il talk.
   - Proxy di sviluppo configurato per inoltrare le chiamate JSON-RPC `/api` al backend su porta `10999`.

3. **Backend Agente UCP + A2A per Milano Centrale:**
   - Powered da **Gemini 3.8 Flash** (`gemini-3.8-flash`).
   - Gestione valuta standard in Euro (**EUR / €**).
   - Catalogo prodotti personalizzato con classificazione termica e merceologica:
     - **Caldi:** Espresso Doppio Illy, Cappuccino con Brioche al Pistacchio, Focaccia Toast Calda.
     - **Freddi:** Ciabatta Crudo e Bufala, Insalata Caesar, Acqua San Pellegrino, Spremuta d'Arancia.
     - **Tech & Travel Essentials:** Powerbank MagSafe, Caricatore GaN 65W, Cuffie ANC.

---

## 2. Le 3 Regole di Fulfillment (Travel Retail BOPIS & In-Seat)

La demo mette in luce la flessibilità del protocollo UCP (`dev.ucp.shopping.fulfillment`) applicato a un contesto ferroviario reale ad alta densità:

```mermaid
graph TD
    User["👤 Viaggiatore a Milano Centrale"] --> Cart["Carrello UCP"]
    Cart --> CheckTemp{"Il carrello contiene cibi/bevande calde?"}
    
    CheckTemp -- Sì (Espresso / Toast) --> OptExpress1["⚡ Ritiro Express al Banco (Binario 12)<br>Finestra: 5 min | Gratuito"]
    CheckTemp -- Sì (Espresso / Toast) --> OptTrain1["🚄 Consegna al Posto Treno<br>Attesa max fattorino: 1 min | +€6.50<br>Richiede: Treno, Carrozza, Posto"]
    CheckTemp -- Sì (Espresso / Toast) -.-> LockerBlocked["🔒 Smart Locker BLOCCO AUTOMATICO<br>⚠️ Non consentito per deperibilità/temperatura"]
    
    CheckTemp -- No (Solo Freddi / Tech) --> OptExpress2["⚡ Ritiro Express al Banco (Binario 12)<br>Finestra: 5 min | Gratuito"]
    CheckTemp -- No (Solo Freddi / Tech) --> OptLocker2["🔒 Smart Locker Stazione (Piano -1)<br>Finestra sblocco PIN: 10 min | Gratuito"]
    CheckTemp -- No (Solo Freddi / Tech) --> OptTrain2["🚄 Consegna al Posto Treno<br>Attesa max fattorino: 1 min | +€6.50"]
```

### Specifica di Dettaglio delle Modalità, Slot Orari e Regola del Preavviso

> ⏱️ **Regola del Preavviso Minimo di 30 Minuti:** Sia per lo **Smart Locker** sia per la **Consegna al Posto Treno/Binario** è tassativo un **preavviso di almeno 30 minuti** rispetto all'orario corrente della stazione. Se il viaggiatore ha meno di 30 minuti (treno in partenza imminente), l'Agente blocca la richiesta e propone l'alternativa a tempo zero: **Ritiro Express al Banco** (pronto in 5 minuti).

| Modalità | ID UCP | Finestra Oraria | Preavviso Minimo | Tariffa | Vincoli & Regole di Business |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ritiro / Servizio al Tavolo** | `pickup_express` | **5 minuti** (intervalli di 5 min) | **Nessuno** (pronto in 5 min) | **€ 0.00** | Desk prioritario o tavolo (es. *Tavolo 5*, *Al Banco*) al Bistrot Binario 12. Valido per qualsiasi articolo (caldo o freddo). Ideale per passeggeri con treno imminente. |
| **Smart Locker Stazione** | `pickup_locker` | **10 minuti** (**multipli di 10 min**) | **Almeno 30 minuti** | **€ 0.00** | Piano Interrato. **Gli slot partono tutti ai multipli di 10 minuti** (`:00`, `:10`, `:20`, `:30`, `:40`, `:50`). **Escluso automaticamente** se il carrello include articoli caldi. Sblocco contactless con PIN. |
| **Consegna al Posto Treno** | `in_seat_train` | **1 minuto preciso** (durante fermata) | **Almeno 30 minuti** | **€ 6.50** | Consegna a bordo treno al binario. Attesa massima del fattorino: **1 minuto** (es. `17:45 - 17:46`). Richiede: Treno (*FR 9540*), Carrozza (*4*), Posto (*12D*), Binario (*14*) e Orario di arrivo. |

### 2.1 Calcolo Temporale Attuale e Vincoli di Stazione

Nel codice attuale della demo, la dimensione temporale viene gestita nel modo seguente:

1. **Timestamp dell'ordine (`now`)**:
   - È determinato dall'orario di sistema reale del server al momento della ricezione della richiesta (`datetime.now().astimezone()`).
2. **Deducibilità dell'orario di consegna (`delivery_time`)**:
   - Se l'utente esprime indicazioni relative (es. *"tra 10 minuti"*, *"il treno parte tra poco"*), il modello **Gemini 3.8 Flash** comprende il contesto ed estrae l'argomento formale `delivery_time` passato al tool di fulfillment (es. `11:28`).
   - Nel metodo `set_train_delivery()` di `store.py`, il server calcola il preavviso effettivo:
     $$\text{lead\_minutes} = \frac{\text{delivery\_time} - \text{now}}{60}$$
   - Se $\text{lead\_minutes} < 25$, la logica di business rifiuta la consegna a bordo treno (o lo slot locker) per mancanza di tempo utile alla preparazione dell'ordine e al tragitto del fattorino verso i binari di testa, proponendo il fallback su **Ritiro Express al Banco (5 min)**.
3. **Assunzioni del Mock e Vincoli Fisici Ferroviari Reali**:
   - Nel mock attuale, `delivery_time` rappresenta il momento in cui il fattorino sale a bordo della carrozza per consegnare l'ordine al posto del passeggero.
   - Nella realtà della Stazione di Milano Centrale, la consegna può fisicamente avvenire **solo durante la sosta del convoglio al binario** (finestra in cui il convoglio è presente e le porte sono aperte, tipicamente negli ultimi 10-15 minuti prima della partenza, e fino a 1-2 minuti prima della chiusura porte).
   - Se un viaggiatore richiede la consegna quando mancano meno di 30 minuti alla partenza del treno, si genera un **doppio vincolo insanabile**:
     - **Vincolo del Merchant (preparazione):** il bistrot necessita di almeno 30 minuti per ricevere l'ordine, sigillare il pacchetto e percorrere a piedi la stazione fino al binario.
     - **Vincolo Ferroviario (presenza treno):** se mancano 10 minuti alla partenza, il fattorino arriverebbe al binario quando il convoglio è già partito.
   - L'interfaccia utente (sia nella chat con Markdown rich text e action chips, sia nel form del carrello con orari consigliati e badge d'allerta) evidenzia in modo immediato questo vincolo e permette all'utente di deviare con un solo click sul ritiro express al banco.

---

## 3. Architettura Completa del Talk

```mermaid
flowchart LR
    %% Palette colors matching agentic-commerce-flowcharts-v21
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef wallet fill:#FADBD8,stroke:#C0392B,color:#641E16;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef issuer fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;

    subgraph Local ["Local [On-Device / Client-Side - Port 4200]"]
        User([👤 Viaggiatore])
        UI[Agent Client UI<br/>Angular 22 Signals]
        LCM[Local Credential Manager<br/>Passkey / Biometric Wallet]
    end

    subgraph Cloud ["Cloud [Server-Side Infrastructure - Port 10999]"]
        Agent[Travel Retail Agent<br/>A2A Server]
        Store[RetailStore Engine<br/>UCP BOPIS Models]
        Catalog[("products.json<br/>Catalogo")]
        Gemini[Gemini 3.8 Flash<br/>Google GenAI]
        Issuer[Payment Network /<br/>Bank Issuer (MPP)]
    end

    User -->|1. Chat / Prompt chips| UI
    UI -->|2. JSON-RPC message/send<br/>(X-A2A-Extensions: UCP)| Agent
    Agent -->|3. Tool Calls & Planning| Gemini
    Agent -->|4. Business Rules & Fulfillment| Store
    Store --> Catalog
    Store -->|5. UCP Challenge: ready_for_complete| Agent
    Agent -->|6. Deliver Challenge Payload| UI
    User -->|7. Tap Paga con Mandato AP2| UI
    UI -->|8. Request Credential Authorization| LCM
    User -->|9. Biometric Prompt TouchID / Passkey| LCM
    LCM -->|10. Sign Cart Mandate VC<br/>& Payment Mandate VC (SD-JWT)| LCM
    LCM -->|11. Deliver Signed Mandates| UI
    UI -->|12. complete_checkout + Signed Mandates| Agent
    Agent -->|13. Submit Mandates to Settle| Store
    Store -->|14. Settle with Payment Mandate| Issuer
    Issuer -->|15. Verify Signature & Capture OK| Store
    Store -->|16. Order Confirmation ORD-MI-...| UI

    class User buyer;
    class UI client;
    class LCM wallet;
    class Agent server;
    class Store merchant;
    class Gemini server;
    class Issuer issuer;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

### 3.1 Dove e Come avviene la Comunicazione UCP

Nel flusso della demo, UCP e A2A operano in modo sinergico su due livelli:

1. **Negoziazione e Discovery (Handshake HTTP / A2A):**
   - Ogni richiesta HTTP dal frontend (`POST /api`) include:
     - `X-A2A-Extensions: https://ucp.dev/2026-01-23/specification/overview?v=2026-01-23`
     - `UCP-Agent: profile="http://localhost:4200/profile/agent_profile.json"`
   - Il server A2A valida che il client sia abilitato al protocollo UCP e negozia le capabilities dichiarate (`dev.ucp.shopping.checkout`, `dev.ucp.shopping.fulfillment`).
2. **Scambio Dati Semantici (Multi-Part Messages):**
   - L'agente non invia HTML o grafica proprietaria: risponde con frame JSON-RPC A2A multi-part composti da:
     - **`kind: "text"`**: la spiegazione in linguaggio naturale di Gemini per l'utente.
     - **`kind: "data"` con chiave `"a2a.ucp.checkout"`**: il payload validato dai modelli Pydantic dell'SDK UCP (`FulfillmentOption`, finestre ISO 8601 di 1, 5 o 10 min, totali, supplemento treno €6.50, indirizzi).
   - Il frontend Angular funge da **Client-Driven Renderer**, traducendo lo schema dati standard nei widget visivi (slot chips, form binario/carrozza, pulsante AP2).

### 3.2 Il Ruolo di A2A: L'utente fa la parte di uno dei due agenti?

**Sì, concettualmente il frontend Angular sta recitando la parte dello "Shopper Agent Host".**

- Nel paradigma A2A originario, la topologia target prevede:
  $$\text{Utente} \longleftrightarrow \text{Shopper Agent (es. Gemini personale)} \overset{\text{A2A + UCP}}{\longleftrightarrow} \text{Merchant Agent} \longleftrightarrow \text{Sistemi di Cassa}$$
- In una demo da palco per una conferenza tecnica (GDG DevFest), far dialogare due agenti invisibili in background toglierebbe leggibilità al flusso. Il frontend Angular agisce quindi come un **Agente Acquirente con Interfaccia Visuale**:
  - Dichiara un profilo A2A formale (`agent_profile.json`).
  - Traduce le azioni dell'utente (click su chip orari, bottoni) in messaggi A2A standardizzati diretti al Merchant Agent.
- **Evoluzione Futura / Simulazione a 2 Agenti:**  
  A tendere, è possibile interporre un secondo agente Gemini (il *Personal Travel Shopper* dell'utente) che conosce l'itinerario e i biglietti del treno. L'utente parlerebbe al suo Personal Shopper, e questo negozierebbe autonomamente via A2A con il Merchant Agent di Milano Centrale, mostrando a schermo il log della conversazione tra i due agenti (*Agent-to-Agent Negotiation Inspector*).

### 3.3 Mappatura Dettagliata: Standard UCP vs Strutture e Azioni Custom

Per chiarezza tecnica durante il talk e nell'architettura, la tabella seguente mappa con precisione cosa fa parte dello standard ufficiale UCP e cosa è stato implementato come estensione di dominio per la demo di Milano Centrale:

#### A. Strutture Dati (Data Models)

| Entità Concettuale | Struttura UCP Standard (Official Schema) | Struttura / Valori Custom della Demo | Note & Meccanismo di Mapping |
| :--- | :--- | :--- | :--- |
| **Sessione Carrello / Cassa** | `ucp_sdk.models.schemas.shopping.checkout_resp.CheckoutResponse` | Campi custom interni `train_confirmed`, `option_id` nel dizionario di stato del server | Lo stato scambiato in A2A (`a2a.ucp.checkout`) è un oggetto **Checkout UCP 100% conforme** (`id`, `currency`, `line_items`, `totals`, `fulfillment`, `payment`). |
| **Voci di Carrello** | `LineItemResponse` (`id`, `quantity`, `totals`, `item`) | — | Standard UCP. |
| **Articolo / Prodotto** | `ItemResponse` (`id`, `price`, `title`, `image_url`) | Classificazione `thermal_category` (`hot` / `cold`) e metadati tech in `products.json` | I prodotti nel catalogo espongono attributi Schema.org / UCP. Il flag termico (`is_hot`) è una regola di business custom usata per validare l'allocazione nel locker. |
| **Metodi di Consegna** | `FulfillmentMethodResponse`, `FulfillmentGroupResponse`, `FulfillmentOptionResponse` | Gli ID delle opzioni: `pickup_express`, `pickup_locker`, `in_seat_train` | La gerarchia è standard UCP (`methods` $\to$ `groups` $\to$ `options`). Gli ID specifici e le relative tariffe (+€6.50 treno) sono istanze di business configurate nel `RetailStore`. |
| **Finestre Temporali di Ritiro/Consegna** | `earliest_fulfillment_time`, `latest_fulfillment_time` (stringhe ISO 8601 conformi RFC 3339) | Finestra di **1 minuto** per il treno, **10 minuti** per il locker, **5 minuti** per il tavolo | Il formato orario nei JSON è **standard UCP ISO 8601**. La granularità (1 min per sosta convoglio, multipli di 10 min per locker) è logica di business custom del merchant. |
| **Destinazione Consegna / Posto Treno** | `PostalAddress` (`street_address`, `extended_address`, `address_locality`, `postal_code`, `address_country`, `first_name`) | Iniezione di: *Treno FR 9540*, *Carrozza 4*, *Posto 12D*, *Binario 14*, *PIN Locker #14*, *Tavolo 5* | Non esistendo nello standard shopping UCP un modello `TrainSeatDestination`, i dettagli ferroviari sono mappati elegantemente su `PostalAddress`: `street_address` = *Stazione Milano Centrale, Treno FR 9540 (Binario 14)*, `extended_address` = *Carrozza 4, Posto 12D*. |
| **Totali e Supplementi** | `TotalResponse` (`type`, `display_text`, `amount` in centesimi) | Supplemento `type: "fee"` con `display_text: "Consegna al Posto Treno"` (€6.50 / 650 cent) | Standard UCP. Il supplemento di consegna a bordo viene sommato al totale finale secondo la specifica UCP dei totali. |
| **Firma e Mandati di Pagamento** | Mandati AP2 (Verifiable Credentials / SD-JWT) | Mock Token in `risk_signals` (`cart_mandate_jwt`, `payment_mandate_jwt`) | I token ricalcano la specifica crittografica AP2 (`intent_mandate`, `cart_mandate`, `payment_mandate`) con binding all'importo e al merchant verificato. |
| **Conferma Ordine** | `OrderConfirmation` (`id`: `ORD-MI-...`, `permalink_url`) | — | Standard UCP emesso a completamento pagamento. |

#### B. Azioni e Ciclo di Vita (Actions & Operations)

| Azione Concettuale | Operazione UCP Standard (REST / A2A) | Implementazione Agente / Tool nella Demo | Natura dell'Azione |
| :--- | :--- | :--- | :--- |
| **Discovery Merchant & Servizi** | `GET /.well-known/ucp` con header `UCP-Agent` e `X-A2A-Extensions` | Endpoint `/.well-known/agent-card.json` e `data/ucp.json` | **UCP Standard**: discovery federata delle capability (`dev.ucp.shopping.checkout`, `dev.ucp.shopping.fulfillment`). |
| **Ricerca Prodotti** | UCP capability `dev.ucp.shopping.catalog` (`catalog_search.json`) | Tool ADK `search_shopping_catalog(query)` $\to$ `a2a.product_results` | Dati conformi allo standard; firma del tool definita nell'Agente ADK. |
| **Creazione / Modifica Carrello** | Transizioni di stato del carrello (`POST /checkouts`, `lines`) | Tool ADK `add_to_checkout`, `remove_from_checkout`, `update_checkout` | I tool operano sul modello `Checkout` UCP standard. |
| **Selezione Opzione di Ritiro** | UCP Fulfillment Option Selection | Tool ADK `select_delivery_method(option_id, slot_time)` | Invoca la selezione standard dell'opzione UCP aggiornando i totali. |
| **Configurazione Dettagli Ferroviari / Locker** | Mapping su `fulfillment.methods[0].destinations` | Tool ADK specializzati: `set_train_delivery_details`, `set_locker_pickup_details`, `set_table_service_details` | **Tool Custom di Dominio**: facilitano l'estrazione da parte di Gemini dei parametri (carrozza, posto, treno, pin, tavolo) e li iniettano nel `PostalAddress` UCP. |
| **Regola Preavviso 30 Minuti & Divieto Termico** | Vincoli operativi del Merchant | Logica di business in `store.py` (`set_train_delivery`, `set_locker_pickup`) | **Logica di Business Custom**: solleva eccezioni guidate che l'agente traduce in spiegazioni e suggerimenti per l'utente. |
| **Inizializzazione Pagamento** | Transizione a `ready_for_complete` | Tool ADK `start_payment(tool_context)` | **UCP Standard**: verifica che tutti i requisiti (destinazione, buyer, fulfillment) siano soddisfatti. |
| **Autorizzazione AP2 & Completamento** | Protocollo AP2 (FIDO2 Passkey / Credential Manager) | Tool ADK `complete_checkout` + `mpp.process_payment` | **Standard AP2 + UCP**: verifica non-ripudiabile dei mandati SD-JWT emessi dal Local Credential Manager e transizione a `completed`. |

---

## 4. Come Avviare la Demo Locale

### Prerequisiti
- Assicurarsi che nel file [`.env`](file:///C:/Projects/AgenticCommerce/prjs/ucp-demo-mi-devfest2026/.env) sia valorizzata la variabile `GOOGLE_API_KEY`.

### Terminale 1: Backend Agente A2A (Porta 10999)
```powershell
cd C:\Projects\AgenticCommerce\prjs\ucp-demo-mi-devfest2026\backend
.venv\Scripts\python.exe -m travel_retail_agent.main --port 10999
```
*Verifica:* Aprire nel browser `http://localhost:10999/.well-known/agent-card.json`.

### Terminale 2: Frontend Angular (Porta 4200)
```powershell
cd C:\Projects\AgenticCommerce\prjs\ucp-demo-mi-devfest2026\frontend
npm start
```
*Verifica:* Aprire nel browser `http://localhost:4200/`.

---

## 5. Casi di Test per la Presentazione (Script Talk)

### Scenario A: La restrizione termica dello Smart Locker
1. Cliccare sulla pillola: `☕ Ho 10 min: caffè caldo e toast al Binario 12` (o digitare la richiesta).
2. L'agente mostrerà le card dell'espresso e del toast e calcolerà il carrello.
3. Se l'utente chiede: *"Posso ritirarli allo Smart Locker?"*, l'agente risponderà spiegando che i cibi caldi non possono essere alloggiati nello locker per preservare temperatura e freschezza, proponendo il ritiro express al banco o la consegna a bordo.

### Scenario B: Selezione dello Smart Locker con Slot ai Multipli di 10 Minuti
1. Chiedere un panino freddo o un accessorio tech: *"Vorrei una ciabatta con crudo di Parma e una powerbank"*.
2. Nel carrello, cliccare sull'opzione **Smart Locker Stazione (Piano Interrato)**.
3. Si aprirà la griglia degli slot disponibili che **partono rigorosamente ai multipli di 10 minuti** (es. `17:10–17:20`, `17:20–17:30`, `17:30–17:40`).
4. Cliccare su uno slot o chiedere in chat *"Voglio ritirarlo al locker alle 17:20"*: l'agente confermerà la finestra di 10 minuti e genererà il codice PIN contactless di sblocco.

### Scenario C: Servizio al Tavolo al Bistrot con Finestra di 5 Minuti
1. Selezionare l'opzione **Ritiro / Servizio al Tavolo (Bistrot Binario 12)**.
2. Scegliere la postazione (es. `Tavolo 5` o `Al Banco`) e uno slot orario a intervalli di 5 minuti (es. `16:55–17:00`).
3. L'agente o il click UI imposta la finestra di 5 minuti confermata nei totali UCP.

### Scenario D: Consegna al Posto Treno con Finestra di Massima Precisione (1 Minuto)
1. Cliccare sulla pillola: `🚄 Frecciarossa 9540 (Carrozza 4, Posto 12D): consegna a bordo!`
2. Inserire o confermare l'orario di arrivo del treno al binario con almeno 30 minuti di preavviso (es. `17:45`).
3. Il carrello mostra chiaramente il badge di precisione: **Attesa massima del fattorino: 1 minuto (finestra `17:45–17:46`)** e applica il supplemento di €6.50.
4. Cliccare su **"Paga con Mandato AP2 (Google Pay)"** per completare l'ordine con emissione di Order ID `ORD-MI-...` e riepilogo della carrozza, posto e finestra oraria di consegna.

### Scenario E: Gestione del Preavviso Minimo (< 30 min) e Pivoting su Ritiro Express
1. L'utente richiede la consegna al treno o al locker con orario imminente (es. *"Il mio treno parte tra 10 minuti, portami il panino in carrozza 4!"*).
2. L'agente risponde spiegando che per motivi di logistica interna e preparazione è richiesto un preavviso di almeno 30 minuti.
3. L'agente offre la soluzione immediata a zero attesa: **Ritiro Express al Banco (Bistrot Binario 12)**, pronto in 5 minuti.
4. L'utente accetta, la transazione viene completata tempestivamente e il passeggero non perde il treno!

---

## 6. Backlog & TODO per Evoluzioni Future

Le seguenti evoluzioni architetturali e di business sono state annotate come backlog di sviluppo:

1. **TODO-1: Modellazione Orario Ferroviario & Finestra di Presenza al Binario (Railway Schedule Mock):**
   - **Contesto:** Attualmente il sistema modella un unico `delivery_time` e verifica solo il tempo minimo di preparazione ($\ge 30$ min dall'ordine).
   - **Evoluzione:** Introdurre un'entità formale per l'orario ferroviario (es. Trenitalia/Italo API mock):
     - `train_arrival_at_platform`: orario in cui il convoglio entra al binario e apre le porte (es. 15-20 min prima della partenza).
     - `train_departure_time`: orario effettivo di partenza.
   - **Doppio vincolo:**
     1. *Vincolo Merchant (preparazione):* $\text{delivery\_time} - \text{order\_time} \ge 30\text{ minuti}$.
     2. *Vincolo Fisico Ferroviario (sosta convoglio):* $\text{delivery\_time} \in [\text{train\_arrival\_at\_platform}, \text{train\_departure\_time} - 2\text{ min}]$.
   - **Rilevamento intelligente dei conflitti:** Segnalare sia l'impossibilità di preparare l'ordine per treni in partenza a breve, sia il divieto di consegna fuori dalla finestra di reale presenza del convoglio al binario.

2. **TODO-2: Architettura a 2 Agenti A2A (Shopper Agent vs Merchant Agent):**
   - **Contesto:** Attualmente il frontend Angular funge da client diretto che parla via A2A con il Merchant Agent.
   - **Evoluzione:** Sdoppiare il flusso in due agenti Gemini cooperanti:
     - *Personal Travel Shopper (Client/PWA):* Agente dell'utente a conoscenza di portafoglio, biglietti e orari treno.
     - *Merchant Agent (Milano Centrale):* Agente di cassa della stazione.
   - **Valore per il talk:** Mostrare in diretta a schermo il log della negoziazione autonoma A2A tra i due agenti (*Agentic Negotiation Inspector*).

3. **TODO-3: Notifiche Push Real-Time & Tracking Posizione Fattorino:**
   - Web Push / WebSocket per notificare il viaggiatore quando il fattorino prende in carico l'ordine e quando raggiunge la carrozza al binario.

4. **TODO-4: OpenAI ACP (Agentic Commerce Protocol) - Studio Comparativo per Futuro Talk:**
   - **Razionale:** Il protocollo ACP di OpenAI/Stripe affronta principalmente la delega di token di pagamento con handler proprietari su chat, ma non supporta la discovery federata multi-merchant né la complessità fisica del fulfillment (BOPIS, smart locker, orari ferroviari ISO 8601, deperibilità termica).
   - **Decisione:** Escluso deliberatamente da questo talk per mantenere il focus chiaro e approfondito sul confronto **UCP vs Web MCP**. L'analisi comparativa ACP verrà sviluppata come estensione successiva per un talk o whitepaper dedicato.

---

## 7. Roadmap delle 4 Implementazioni Autonome & Sicurezza (Nx Monorepo)

Per adempiere alla promessa del talk (*"across UCP, Web MCP and Physical Retail"*) mantenendo il codice modulare, sicuro e testabile separatamente:

| Implementazione | Architettura | Canale UCP | Componenti a Fattor Comune |
| :--- | :--- | :--- | :--- |
| **Demo 1: Direct A2A & UCP** *(Completata ✅)* | `Chat Client UI` $\to$ `Merchant Agent` $\to$ `BOPIS Engine` | **A2A JSON-RPC** | **BOPIS Engine** (`store.py`), catalogo `products.json`, simulatore LCM (`lcm-modal.component.ts`), modelli UCP |
| **Demo 2: Web MCP E-Commerce** *(Priorità P1)* | `Chat UI` $\to$ `Shopper Agent` $\overset{\text{Web MCP}}{\longrightarrow}$ `Storefront Web` $\to$ `BOPIS` | **Web MCP (HTTP/SSE)** | **BOPIS Engine** (`store.py`), catalogo `products.json`, regole preavviso 30m e locker |
| **Demo 3: Two-Agent Federation A2A** *(Priorità P2)* | `Chat UI` $\to$ `Shopper Agent` $\overset{\text{A2A M2M}}{\longleftrightarrow}$ `Merchant Agent` $\to$ `BOPIS` | **A2A M2M Federato** | **BOPIS Engine** (`store.py`), catalogo `products.json`, simulatore LCM, protocollo A2A |
| **Demo 4: Two-Agent via UCP REST** *(Priorità P3)* | `Chat UI` $\to$ `Shopper Agent` $\overset{\text{REST + RFC 9421}}{\longrightarrow}$ `UCP REST Server` $\to$ `BOPIS` | **RESTful HTTP RFC 9421** | **BOPIS Engine** (`store.py`), catalogo `products.json`, standard REST UCP |

### 7.1 Gestione Nx Monorepo
Per eliminare comandi shell manuali fragili:
- **Workspace Nx**: `chat-client`, `bopis-dashboard`, `storefront-webmcp`, `backend-merchant`.
- **Esecutori sicuri**: target `nx:run-commands` per lanciare il backend Python (`travel_retail_agent.main`) senza dover digitare percorsi di file o attivare venv manualmente.
- **Comando unificato**: `npx nx run-many -t serve` o `npm run start:all`.

### 7.2 Sicurezza Firebase & Protezione Backend
In previsione del deploy online:
1. **Frontend Google Sign-In (Firebase Auth)**:
   - Accesso vincolato ad account Google sia per il client viaggiatore sia per la Dashboard BOPIS.
   - Controllo accessi semplificato via Firebase Console per abilitare solo utenti verificati prima del talk.
2. **Protezione Endpoint Agenti**:
   - Validazione Bearer Token (Firebase ID Token) per le chiamate web.
   - Autenticazione M2M (API key o HTTP Signatures RFC 9421) per le interazioni tra agenti.


