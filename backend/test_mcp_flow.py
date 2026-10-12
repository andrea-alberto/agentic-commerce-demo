# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Automated E2E Test Suite for Demo 2: Web MCP Server & Shopper Agent."""

from datetime import datetime, timedelta
import json
import sys
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:10999"


def mcp_rpc(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    url = f"{BASE_URL}/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(path: str) -> dict | list:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, data: dict) -> dict:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


print("=================================================================")
print("  AVVIO TEST SUITE: DEMO 2 - WEB MCP E-COMMERCE & SHOPPER AGENT ")
print("=================================================================")

# TEST 1: MCP Initialize
print("\n--- TEST 1: MCP Handshake (initialize) ---")
init_res = mcp_rpc("initialize")
assert "result" in init_res, f"Errore initialize: {init_res}"
server_info = init_res["result"]["serverInfo"]
print(f"✅ Connesso a MCP Server: '{server_info['name']}' v{server_info['version']}")

# TEST 2: MCP Tools List
print("\n--- TEST 2: Scoperta Tool MCP (tools/list) ---")
tools_res = mcp_rpc("tools/list")
tools = tools_res.get("result", {}).get("tools", [])
tool_names = [t["name"] for t in tools]
print("Tool MCP esposti dal negozio:", tool_names)
assert "search_catalog" in tool_names
assert "create_cart" in tool_names
assert "add_to_cart" in tool_names
assert "configure_fulfillment" in tool_names
assert "checkout_cart" in tool_names
print(f"✅ Trovati {len(tools)} tool conformi alla specifica Model Context Protocol")

# TEST 3: Catalog Search via MCP
print("\n--- TEST 3: Ricerca catalogo tramite MCP (tools/call search_catalog) ---")
search_call = mcp_rpc("tools/call", {"name": "search_catalog", "arguments": {"query": "panino"}})
content_str = search_call["result"]["content"][0]["text"]
search_data = json.loads(content_str)
print(f"Prodotti trovati per 'panino': {search_data.get('count', 0)}")
assert search_data.get("count", 0) > 0
first_item = search_data["results"][0]
print(f"Primo prodotto: {first_item['id']} - {first_item['name']} (€{first_item['price']})")
print("✅ Tool search_catalog eseguito con successo")

# TEST 4: Carrello & Regola Termica Smart Locker
print("\n--- TEST 4: Violazione Regola Termica Smart Locker (cibo caldo) ---")
cart_call = mcp_rpc("tools/call", {"name": "create_cart", "arguments": {}})
cart_data = json.loads(cart_call["result"]["content"][0]["text"])["cart"]
cart_id = cart_data["cart_id"]

# Aggiungi caffe caldo
mcp_rpc("tools/call", {"name": "add_to_cart", "arguments": {"cart_id": cart_id, "product_id": "CAFFE-001", "quantity": 1}})

# Tenta di impostare smart locker
locker_err_call = mcp_rpc("tools/call", {
    "name": "configure_fulfillment",
    "arguments": {
        "cart_id": cart_id,
        "method": "pickup_locker",
        "details": {"slot_time": "17:40", "pin_code": "1234"}
    }
})
locker_err_data = json.loads(locker_err_call["result"]["content"][0]["text"])
print("Risposta violazione termica:", locker_err_data.get("error"))
assert "Violazione Regola Termica" in locker_err_data.get("error", "")
print("✅ Protezione termica Smart Locker verificata correttamente su tool MCP!")

# TEST 5: Carrello Freddo & Preavviso Minimo 30 Minuti
print("\n--- TEST 5: Violazione Preavviso Minimo 30 minuti Locker ---")
cold_cart_call = mcp_rpc("tools/call", {"name": "create_cart", "arguments": {}})
cold_cart = json.loads(cold_cart_call["result"]["content"][0]["text"])["cart"]
cold_cart_id = cold_cart["cart_id"]

# Aggiungi panino freddo
mcp_rpc("tools/call", {"name": "add_to_cart", "arguments": {"cart_id": cold_cart_id, "product_id": "PANIN-004", "quantity": 1}})

# Tenta di impostare uno slot con solo 5 minuti di preavviso
now = datetime.now().astimezone()
short_lead_str = (now + timedelta(minutes=5)).strftime("%H:%M")
lead_err_call = mcp_rpc("tools/call", {
    "name": "configure_fulfillment",
    "arguments": {
        "cart_id": cold_cart_id,
        "method": "pickup_locker",
        "details": {"slot_time": short_lead_str, "pin_code": "8492"}
    }
})
lead_err_data = json.loads(lead_err_call["result"]["content"][0]["text"])
print("Risposta violazione preavviso:", lead_err_data.get("error"))
assert "Preavviso insufficiente" in lead_err_data.get("error", "")
print("✅ Protezione preavviso 30 min per Smart Locker verificata su tool MCP!")

# TEST 6: Checkout Valido via MCP & Verifica Inserimento BOPIS
print("\n--- TEST 6: Checkout Valido via MCP & Persistenza BOPIS Engine ---")
# Imposta slot valido (+40 min multiplo di 10)
valid_dt = now + timedelta(minutes=40)
rem = valid_dt.minute % 10
add_m = (10 - rem) if rem != 0 else 0
valid_slot_dt = (valid_dt + timedelta(minutes=add_m)).replace(second=0, microsecond=0)
valid_slot_str = valid_slot_dt.strftime("%H:%M")

valid_fl_call = mcp_rpc("tools/call", {
    "name": "configure_fulfillment",
    "arguments": {
        "cart_id": cold_cart_id,
        "method": "pickup_locker",
        "details": {"slot_time": valid_slot_str, "pin_code": "8492"}
    }
})
assert not valid_fl_call["result"]["isError"]

# Esegui checkout via MCP
checkout_call = mcp_rpc("tools/call", {
    "name": "checkout_cart",
    "arguments": {
        "cart_id": cold_cart_id,
        "buyer_name": "Mario Rossi (MCP)",
        "buyer_email": "mario.rossi@devfest.example.it"
    }
})
checkout_res = json.loads(checkout_call["result"]["content"][0]["text"])
print("Conferma d'ordine MCP:", checkout_res)
assert checkout_res.get("status") == "confirmed"
mcp_order_id = checkout_res["order_id"]
print(f"ID Ordine generato: {mcp_order_id}")

# Verifica nel BOPIS Engine comune
bopis_order = get_json(f"/bopis/orders/{mcp_order_id}")
print("Verifica ordine nel BOPIS Engine:")
print(f"  • ID: {bopis_order['order_id']}")
print(f"  • Canale: {bopis_order['channel_source']} ({bopis_order['channel_label']})")
print(f"  • Inserito alle: {bopis_order['placed_at_display']}")
print(f"  • Consegna richiesta: {bopis_order['requested_delivery_display']}")
print(f"  • Preavviso: {bopis_order['lead_time_minutes']} min")
print(f"  • Totale: €{bopis_order['totals']['total_cents'] / 100:.2f}")

assert bopis_order["channel_source"] == "web_mcp"
assert bopis_order["channel_label"] == "Demo 2: Web MCP"
assert bopis_order["placed_at_display"]
assert bopis_order["requested_delivery_display"]
print("✅ Ordine MCP perfettamente registrato nel BOPIS Engine comune con data e ora!")

# TEST 7: Autonomous Shopper Agent (Missione End-to-End con Gemini)
print("\n--- TEST 7: Shopper Agent Autonomo (Esecuzione Loop Tool MCP) ---")
prompt_test = (
    "Ordina una spremuta d'arancia fresca e una brioche con Ritiro Express al Banco del Bistrot Binario 12 "
    "per Mario Rossi (email: mario@devfest.it)."
)
print(f"Prompt inviato allo Shopper Agent: '{prompt_test}'")

shopper_res = post_json("/mcp/shopper/run", {
    "prompt": prompt_test,
    "buyer_name": "Mario Rossi",
    "buyer_email": "mario@devfest.it"
})

print(f"Stato missione Shopper: {shopper_res.get('status')}")
print(f"Passaggi MCP eseguiti: {shopper_res.get('total_steps')}")
for step in shopper_res.get("steps", []):
    print(f"  [Passo {step['step']}] Tool MCP: {step['tool']}({step['arguments']})")

if shopper_res.get("order"):
    print("Ordine creato autonomamente dallo Shopper Agent:", shopper_res["order"]["order_id"])

assert shopper_res.get("total_steps", 0) >= 3
print("\nRisposta finale Shopper Agent:")
print(shopper_res.get("final_answer"))
print("\n=================================================================")
print("  TUTTI I TEST DEMO 2 (WEB MCP & SHOPPER AGENT) SUPERATI AL 100%! ")
print("=================================================================")
