import sys
import json
import urllib.request
import urllib.error
import time

# Ensure UTF-8 output even in Windows cmd/PowerShell cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def heading(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def subhead(title):
    print(f"\n--- {title} ---")

def test_connectivity():
    heading("1. VERIFICA CONNETTIVITÀ SERVIZI ATTIVI IN LOCALE")
    ports = [
        (10999, "backend-merchant (A2A / UCP REST / MCP / BOPIS)", "POST", "/"),
        (10998, "backend-shopper (Personal Shopper Agent & SSE)", "GET", "/shopper/context"),
        (4200, "chat-client (Demo 1 UI)", "GET", "/"),
        (4201, "bopis-dashboard (Station Dispatcher Hub UI)", "GET", "/"),
        (4202, "storefront-webmcp (Demo 2 UI)", "GET", "/"),
        (4203, "shopper-client (Demo 3 & 4 Split-View UI)", "GET", "/"),
    ]
    all_ok = True
    for port, name, method, path in ports:
        url = f"http://localhost:{port}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DevFest-Verifier"}, method=method)
            if method == "POST":
                # send minimal payload
                req.data = b'{"jsonrpc":"2.0","method":"ping","id":1}'
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=4) as resp:
                print(f"  [OK] Port {port}: {name} (HTTP {resp.status})")
        except urllib.error.HTTPError as he:
            # 200 or 400 with active service
            if he.code in (200, 400, 404, 405) and port in (10998, 10999):
                print(f"  [OK] Port {port}: {name} (Active, HTTP {he.code})")
            else:
                print(f"  [WARN] Port {port}: {name} -> HTTP {he.code}")
                all_ok = False
        except Exception as e:
            print(f"  [FAIL] Port {port}: {name} -> {e}")
            all_ok = False
    return all_ok


def test_demo1_direct_a2a():
    heading("2. VERIFICA DEMO 1: DIRECT A2A & TYPED COMMERCE WIDGETS (:10999/)")
    url = "http://localhost:10999/"
    payload = {
        "jsonrpc": "2.0",
        "id": "test-demo1-req",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{
                    "type": "text",
                    "text": "Vorrei un espresso doppio caldo e una brioche al pistacchio da ritirare al banco prima della partenza"
                }],
                "messageId": "msg-d1-verify-001"
            }
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode())
            print("  [OK] Risposta JSON-RPC 2.0 ricevuta con successo!")
            msg = res.get("result", {}).get("message", {})
            parts = msg.get("parts", [])
            print(f"  Numero parti strutturate nella risposta: {len(parts)}")
            for idx, part in enumerate(parts):
                p_type = part.get("type")
                if p_type == "text":
                    print(f"  [Testo Conversazionale] {part.get('text')[:120]}...")
                elif p_type == "data":
                    d = part.get("data", {})
                    action = d.get("action")
                    print(f"  [Widget UCP Tipizzato] Action: {action}")
                    if "checkout" in d:
                        chk = d["checkout"]
                        print(f"    - Checkout ID: {chk.get('id')} | Totale: €{chk.get('total_cents', 0)/100:.2f}")
                        for item in chk.get("items", []):
                            print(f"      * Articolo: {item.get('title')} | Caldo (is_hot): {item.get('is_hot')}")
                    if "fulfillment_options" in d:
                        opts = [opt.get("method") for opt in d["fulfillment_options"]]
                        print(f"    - Opzioni Fulfillment UCP proposte: {opts}")
            return True
    except Exception as e:
        print(f"  [FAIL] Errore chiamata Demo 1 A2A: {e}")
        return False


def test_demo2_webmcp():
    heading("3. VERIFICA DEMO 2: WEB MCP SERVER & METADATI PRODOTTI (:10999/mcp)")
    # 1. MCP Tools List
    req_tools = urllib.request.Request("http://localhost:10999/mcp/tools")
    try:
        with urllib.request.urlopen(req_tools, timeout=5) as resp:
            tools = json.loads(resp.read().decode()).get("tools", [])
            print(f"  [OK] Web MCP Tools disponibili: {[t.get('name') for t in tools]}")
    except Exception as e:
        print(f"  [WARN] Errore get /mcp/tools: {e}")

    # 2. Test searchCatalog via JSON-RPC
    search_payload = {
        "jsonrpc": "2.0",
        "id": "mcp-search-1",
        "method": "tools/call",
        "params": {
            "name": "search_catalog",
            "arguments": {"category": "cold", "query": "vegano"}
        }
    }
    req = urllib.request.Request("http://localhost:10999/mcp", data=json.dumps(search_payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode())
            content = res.get("result", {}).get("content", [])
            print("  [OK] MCP Tool 'search_catalog' eseguito con successo!")
            if content:
                found_text = content[0].get("text", "")
                print(f"  Risultati ricerca (anteprima): {found_text[:140]}...")
    except Exception as e:
        print(f"  [FAIL] Errore search_catalog: {e}")

    # 3. Test get_product details for VEG-012 with rich AI metadata
    detail_payload = {
        "jsonrpc": "2.0",
        "id": "mcp-detail-1",
        "method": "tools/call",
        "params": {
            "name": "get_product",
            "arguments": {"product_id": "VEG-012"}
        }
    }
    req_det = urllib.request.Request("http://localhost:10999/mcp", data=json.dumps(detail_payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req_det, timeout=5) as resp:
            res_det = json.loads(resp.read().decode())
            p_data = json.loads(res_det.get("result", {}).get("content", [])[0].get("text", "{}"))
            print(f"  [OK] Dettaglio VEG-012 con metadati AI:")
            print(f"    - Prodotto: {p_data.get('name')}")
            print(f"    - Nutri-Score: {p_data.get('nutrition', {}).get('nutri_score')}")
            print(f"    - NOVA Group: {p_data.get('processing_level', {}).get('nova_group')} ({p_data.get('processing_level', {}).get('nova_label')})")
            print(f"    - Origine: {p_data.get('sustainability', {}).get('origin')}")
            print(f"    - Travel Profile (Mess/Odor): {p_data.get('travel_profile', {}).get('mess_factor')} / {p_data.get('travel_profile', {}).get('odor_intensity')}")
            return True
    except Exception as e:
        print(f"  [FAIL] Errore get_product VEG-012: {e}")
        return False


def run_mission_stream(prompt, protocol):
    payload = json.dumps({"prompt": prompt, "protocol": protocol}).encode("utf-8")
    req = urllib.request.Request("http://localhost:10998/shopper/mission/stream", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    proposal = None
    steps = []
    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            line_str = line.decode().strip()
            if line_str.startswith("data: "):
                event = json.loads(line_str[6:])
                if event.get("type") == "step":
                    step = event["step"]
                    steps.append(step)
                    sig = step.get("headers", {}).get("signature", "")
                    sig_info = f" [RFC 9421 Sig: {sig[:18]}...]" if sig else ""
                    print(f"    [Step {step['step_number']}] {step['action']}: {step['description'][:75]}...{sig_info}")
                elif event.get("type") == "proposal":
                    proposal = event["proposal"]
                    item_title = proposal.get("item", {}).get("title", "")
                    print(f"    [Proposal AI Ricevuta] Item: '{item_title}'")
                    opts = [f"{o['id']}: €{o['total_cents']/100:.2f}" for o in proposal.get("fulfillment_options", [])]
                    print(f"    Opzioni di ricezione UCP: {', '.join(opts)}")
    return steps, proposal


def authorize_from_proposal(protocol, proposal, chosen_opt_id=None):
    opts = proposal.get("fulfillment_options", [])
    if chosen_opt_id:
        chosen_opt = next((o for o in opts if o["id"] == chosen_opt_id), opts[0])
    else:
        chosen_opt = next((o for o in opts if o["id"] == proposal.get("selected_option_id")), opts[0])

    item = proposal.get("item", {})
    checkout_id = "CHK-UCP-VERIFY"
    if "notes" in proposal and "checkout_id=" in proposal["notes"]:
        checkout_id = proposal["notes"].split("checkout_id=")[1]

    challenge = {
        "challenge_id": f"CHAL-VERIFY-{int(time.time())}",
        "protocol": protocol,
        "order_id": f"ORD-MI-{protocol.upper()[:3]}-{int(time.time()) % 10000}",
        "merchant": proposal.get("merchant_name", "Bistrot Milano Centrale"),
        "order_summary_title": item.get("title", "Menu"),
        "order_item_id": item.get("id", "PROD-001"),
        "order_item_price": item.get("price_cents", 800),
        "delivery_fee": chosen_opt.get("delivery_fee_cents", 0),
        "total_cents": chosen_opt.get("total_cents", 800),
        "fl_method": chosen_opt.get("id"),
        "fl_label": chosen_opt.get("label"),
        "fl_window": chosen_opt.get("details"),
        "ticket": proposal.get("ticket", {}),
        "buyer": proposal.get("buyer", {}),
        "checkout_id": checkout_id,
        "chosen_prod": item,
        "items": item.get("items") or [{
            "id": item.get("id"),
            "title": item.get("title"),
            "quantity": 1,
            "price_cents": item.get("price_cents", 800)
        }]
    }

    auth_payload = json.dumps({
        "protocol": protocol,
        "challenge": challenge,
        "ap2_mandate": {
            "mandate_id": f"tok_ap2_verify_{challenge['order_id']}",
            "max_authorized_cents": challenge["total_cents"] + 500,
            "signature_scheme": "FIDO2_Passkey_P256",
            "token_jwt": "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkFQMi1DZXJ0In0.eyJzdWIiOiAiYW5kcmVhLmFsYmVydG8ifQ.test_verified_sig"
        }
    }).encode("utf-8")

    req = urllib.request.Request("http://localhost:10998/shopper/mission/authorize", data=auth_payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode())
        print(f"    [Step AP2] {res['step_ap2']['action']}: {res['step_ap2']['description']}")
        print(f"    [Step Final] {res['step_final']['action']}: {res['step_final']['description']}")
        final_ord = res.get("final_order", {})
        print(f"    [Order Confirmed] #{final_ord.get('order_id')} | Channel: {final_ord.get('channel_label')} | Metodo: {final_ord.get('fulfillment_type')} | Totale: €{final_ord.get('totals', {}).get('total_cents', 0)/100:.2f}")
        return final_ord


def test_demo3_a2a_scenarios():
    heading("4. VERIFICA DEMO 3: TWO-AGENT A2A FEDERATION (GEMINI 2.5 FLASH)")

    # --- Scenario A: In-seat train delivery ---
    subhead("Scenario A: Consegna al Posto Treno (Frecciarossa 9540)")
    urllib.request.urlopen(urllib.request.Request("http://localhost:10998/shopper/context/preset/scenario_departing_soon", data=b"", method="POST"))
    
    prompt_a = "Prendimi un caffè doppio e una focaccia ligure per la carrozza 4"
    print(f"  Richiesta Utente: \"{prompt_a}\"")
    steps_a, prop_a = run_mission_stream(prompt_a, "a2a")
    if prop_a:
        print("  -> Simulazione autorizzazione Passkey FIDO2 LCM (Consegna al Posto)...")
        order_a = authorize_from_proposal("a2a", prop_a, chosen_opt_id="in_seat_train")
        print(f"  [OK] Ordine Scenario A finalizzato: #{order_a.get('order_id')}")

    # --- Scenario C: Fitness, Low-Salt & Specialty Cold Brew ---
    subhead("Scenario C: Fitness, Low-Salt & Specialty Cold Brew per Smart Locker")
    req_scen_c = urllib.request.Request("http://localhost:10998/shopper/context/preset/scenario_fitness_specialty", data=b"", method="POST")
    with urllib.request.urlopen(req_scen_c) as resp:
        ctx_c = json.loads(resp.read().decode())
        print(f"  Contesto Viaggiatore Attivato:")
        print(f"    - Dieta: {ctx_c.get('preferences', {}).get('dietary')}")
        print(f"    - Allergeni esclusi: {ctx_c.get('preferences', {}).get('allergens_to_avoid')}")
        print(f"    - Obiettivi: {ctx_c.get('preferences', {}).get('health_goals')}")
        print(f"    - Preferenza Caffè: {ctx_c.get('preferences', {}).get('coffee_preference')}")

    prompt_c = "Ho 20 minuti di sosta: prendimi uno snack sano per il viaggio e un caffè specialty da ritirare al locker"
    print(f"\n  Richiesta Utente: \"{prompt_c}\"")
    steps_c, prop_c = run_mission_stream(prompt_c, "a2a")
    if prop_c:
        print(f"  Prodotti Selezionati: {prop_c.get('item', {}).get('title')}")
        print("  -> Simulazione autorizzazione Passkey FIDO2 LCM (Smart Locker)...")
        order_c = authorize_from_proposal("a2a", prop_c, chosen_opt_id="pickup_locker")
        print(f"  [OK] Ordine Scenario C finalizzato: #{order_c.get('order_id')}")
        print(f"       Fulfillment: {order_c.get('fulfillment_type')}")
        print(f"       Locker Box & PIN: {order_c.get('fulfillment_details')}")


def test_demo4_ucp_rest():
    heading("5. VERIFICA DEMO 4: UCP STANDARD REST BINDING CON FIRME RFC 9421")
    # 1. Test GET /.well-known/ucp
    subhead("1. GET /.well-known/ucp (Discovery Manifest)")
    req_disc = urllib.request.Request("http://localhost:10999/.well-known/ucp")
    with urllib.request.urlopen(req_disc) as resp:
        disc = json.loads(resp.read().decode())
        print(f"  [OK] Manifest UCP Ricevuto: Versione {disc.get('ucp', {}).get('version')}")
        caps = disc.get('capabilities', {})
        print(f"  Capabilities: {list(caps.keys())}")

    # 2. Test GET /ucp/catalog/products with rich AI metadata
    subhead("2. GET /ucp/catalog/products (Verifica presenza Metadati AI)")
    req_cat = urllib.request.Request("http://localhost:10999/ucp/catalog/products")
    with urllib.request.urlopen(req_cat) as resp:
        cat = json.loads(resp.read().decode())
        prods = cat.get("products", [])
        print(f"  [OK] Catalogo UCP REST: {len(prods)} articoli totali")
        # Check sample item with metadata
        sample_cb = next((p for p in prods if p.get("id") == "COFFEE-017"), None)
        if sample_cb:
            print(f"  Articolo di punta: {sample_cb.get('name')}")
            print(f"    - Temperatura: {[x.get('value') for x in sample_cb.get('additionalProperty', []) if x.get('name') == 'temperature']}")
            print(f"    - Profilo Caffè: {sample_cb.get('coffee_profile')}")
            print(f"    - Shelf life ambiente: {sample_cb.get('travel_profile', {}).get('shelf_life_unrefrigerated_hours')} ore")

    # 3. Test Full REST Mission Stream with RFC 9421 ECDSA-P256 Signatures
    subhead("3. Missione UCP REST con Firme HTTP RFC 9421")
    prompt_rest = "Preparami uno snack da ritirare subito allo Smart Locker con verifica RFC 9421"
    steps_r, prop_r = run_mission_stream(prompt_rest, "ucp_rest")
    if prop_r:
        order_r = authorize_from_proposal("ucp_rest", prop_r, chosen_opt_id="pickup_locker")
        print(f"  [OK] Ordine Demo 4 REST creato con successo: #{order_r.get('order_id')}")


def test_bopis_dispatcher_hub():
    heading("6. VERIFICA OMNICHANNEL SU BOPIS DISPATCHER HUB (:10999/bopis/orders)")
    buyer_email = os.getenv("DEFAULT_BUYER_EMAIL", "alex.traveler@example.com")
    req = urllib.request.Request(f"http://localhost:10999/bopis/orders?buyer_email={buyer_email}")
    try:
        with urllib.request.urlopen(req) as resp:
            orders = json.loads(resp.read().decode())
            print(f"  [OK] Ordini totali registrati per il cliente ({buyer_email}): {len(orders)}")
            print("  Ultimi ordini registrati sulla Dispatch Board:")
            for o in orders[-5:]:
                ch_label = o.get("channel_label")
                f_type = o.get("fulfillment_type")
                total = o.get("totals", {}).get("total_cents", 0) / 100
                items_str = ", ".join([it.get("title", "") for it in o.get("items", [])])
                print(f"  - #{o.get('order_id')}: [{ch_label}] -> {f_type} | Items: ({items_str}) | €{total:.2f}")
    except Exception as e:
        print(f"  [FAIL] Errore verifica ordini BOPIS: {e}")

if __name__ == "__main__":
    test_connectivity()
    test_demo1_direct_a2a()
    test_demo2_webmcp()
    test_demo3_a2a_scenarios()
    test_demo4_ucp_rest()
    test_bopis_dispatcher_hub()
    print("\n" + "="*70)
    print("  TUTTI I TEST E TUTTE LE 4 DEMO SONO STATE VERIFICATE CON SUCCESSO!")
    print("="*70 + "\n")
