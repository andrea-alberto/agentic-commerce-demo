# Project TODOs & Roadmap — UCP Travel Retail Demo Suite

## 🎯 Architettura & Conformità agli Standard

### [TODO-01] Adattamento Demo 3 (Two-Agent A2A Federation) al Formalismo UCP A2A Ufficiale
- **Priorità:** Media / Roadmap Post-DevFest
- **Area:** `backend-shopper`, `backend-merchant`, `shopper-client`
- **Specifica UCP di Riferimento:** [`specification/shopping/checkout/a2a.md`](https://ucp.dev/latest/specification/shopping/checkout/a2a/)
- **Stato Attuale:**
  - Nella Demo 3 la negoziazione semantica M2M tra il Personal Shopper Agent e il Merchant Agent (entrambi basati su Gemini 2.5 Flash) utilizza due endpoint HTTP dedicati (`POST /a2a/negotiate` e `POST /a2a/commit`).
  - Questo approccio mostra efficacemente il dialogo semantico e il reasoning tra LLM, ma non rispetta l'envelope formale del protocollo A2A previsto da UCP.
- **Task da Implementare:**
  1. **Transport Layer A2A Standard:**
     - Sostituire le chiamate REST custom con chiamate JSON-RPC 2.0 standard (`method: "message/send"`) verso l'endpoint A2A dell'agente del merchant (`POST /api`).
  2. **Header di Protocollo UCP:**
     - Inviare l'header `UCP-Agent: profile="http://localhost:10998/profile/shopper_agent.json"`.
     - Inviare l'header `X-A2A-Extensions: https://ucp.dev/2026-01-23/specification/reference`.
  3. **Envelope Messaggi & DataPart Formale:**
     - Incapsulare l'intento dell'utente, i vincoli di viaggio (biglietto Frecciarossa) e le preferenze alimentari nei `parts` (`TextPart` / `DataPart`) del messaggio A2A.
     - Fare in modo che il Merchant Agent risponda restituendo la struttura del carrello all'interno di un `DataPart` con la chiave formale **`a2a.ucp.checkout`** (come già avviene nella Demo 1 con Google ADK).
  4. **Commit & AP2 Payment Mandate:**
     - Trasmettere la finalizzazione e il mandato AP2 firmato (Passkey FIDO2) attraverso i `DataPart` standard UCP: **`a2a.ucp.checkout.payment`** e **`a2a.ucp.checkout.signals`**.
  5. **Live Protocol Inspector (`shopper-client`):**
     - Aggiornare i tracer e gli eventi SSE in `shopper_service.py` per tracciare a video i messaggi JSON-RPC 2.0 `message/send` e il `DataPart` `a2a.ucp.checkout`, rendendo visibile la conformità alle specifiche UCP.

---

## 🔮 Backlog Dimostrativo & Nuovi Scenari

### [TODO-02] Demo 5: Acquisto Autonomo Delegato (Human-Not-Present)
- **Scenario:** Viaggiatore frequente con budget pre-approvato (€35.00) per prodotto di pregio (es. *Brunello di Montalcino DOCG*).
- **Flusso:** Intent Mandate con Passkey pre-firmato ➔ Trigger calo prezzo sul merchant ➔ Negoziazione autonoma senza tocco umano ➔ Assegnazione Smart Locker con notifica push/SMS.

### [TODO-03] Hardening Sicurezza UCP REST (Demo 4 Roadmap)
- Implementazione del **Dual-Token Pattern** (ID pubblico `checkout_id` + token segreto effimero `cart_secret_token` per prevenire hijacking).
- **Optimistic Locking** con header HTTP `ETag` e `If-Match`.
- **Short-Lived TTL** con quote locking e auto-scadenza carrelli (15 min).

### [TODO-04] Integrazione API Ferroviarie Real-Time
- Sincronizzazione dinamica degli orari treni e dei binari di Milano Centrale con le API Trenitalia / Italo (gestione ritardi e riallineamento finestre logistiche).
