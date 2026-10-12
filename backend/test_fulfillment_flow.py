import json
import sys
import urllib.request
from datetime import datetime, timedelta
from uuid import uuid4

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def send_message(parts, context_id=None, task_id=None):
    url = "http://localhost:10999/"
    profile_url = "http://localhost:4200/profile/agent_profile.json"
    
    headers = {
        "Content-Type": "application/json",
        "X-A2A-Extensions": "https://ucp.dev/2026-01-23/specification/overview?v=2026-01-23",
        "UCP-Agent": f'profile="{profile_url}"',
    }
    
    msg_dict = {
        "role": "user",
        "parts": parts,
        "messageId": str(uuid4()),
        "kind": "message",
    }
    if context_id:
        msg_dict["contextId"] = context_id
    if task_id:
        msg_dict["taskId"] = task_id
        
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": msg_dict,
            "configuration": {"historyLength": 0},
        },
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if "error" in data:
            print("ERROR from server:", data["error"])
        return data

def get_options(checkout):
    ful = checkout.get("fulfillment", {})
    methods = ful.get("methods") or ful.get("root", {}).get("methods", [])
    if methods and "groups" in methods[0] and methods[0]["groups"]:
        return methods[0]["groups"][0].get("options", [])
    return []

def get_dest(checkout):
    ful = checkout.get("fulfillment", {})
    methods = ful.get("methods") or ful.get("root", {}).get("methods", [])
    if methods and "destinations" in methods[0] and methods[0]["destinations"]:
        d = methods[0]["destinations"][0]
        return d.get("root", d)
    return {}

now = datetime.now().astimezone()
print(f"Orario Stazione Milano Centrale attuale: {now.strftime('%H:%M:%S')}")

print("\n=== TEST 1: Cerca panino freddo e aggiungi PANIN-004 al carrello ===")
res1 = send_message([{"type": "text", "text": "Aggiungi al carrello PANIN-004 Ciabatta Crudo"}])
result = res1.get("result", {})
ctx_id = result.get("contextId") or result.get("id")
print("Context ID:", ctx_id)

parts1 = res1.get("result", {}).get("parts", [])
checkout_data = None
for p in parts1:
    if p.get("data", {}).get("a2a.ucp.checkout"):
        checkout_data = p["data"]["a2a.ucp.checkout"]
        break

if not checkout_data:
    res1_add = send_message(
        [{"type": "text", "text": json.dumps({"action": "add_to_checkout", "product_id": "PANIN-004", "quantity": 1})}],
        context_id=ctx_id
    )
    for p in res1_add.get("result", {}).get("parts", []):
        if p.get("data", {}).get("a2a.ucp.checkout"):
            checkout_data = p["data"]["a2a.ucp.checkout"]
            break

assert checkout_data is not None, "Checkout non trovato!"
print("Checkout ID:", checkout_data["id"])
options = get_options(checkout_data)
print("Opzioni disponibili nel carrello freddo:", [o["id"] for o in options])
assert any(o["id"] == "pickup_locker" for o in options), "pickup_locker deve essere disponibile per cibi freddi!"
print("Test 1 PASSATO: carrello freddo ha Smart Locker attivo.")

print("\n=== TEST 2A: Regola Preavviso Locker: rifiuto se preavviso < 30 minuti ===")
short_lead_dt = now + timedelta(minutes=10)
short_lead_str = short_lead_dt.strftime("%H:%M")
res2a = send_message(
    [{"type": "text", "text": json.dumps({"action": "set_locker_pickup_details", "slot_time": short_lead_str})}],
    context_id=ctx_id
)
parts2a = res2a.get("result", {}).get("parts", [])
print("parts2a content:", json.dumps(parts2a, indent=2))
found_error = False
for p in parts2a:
    text = p.get("text", "")
    data_msg = p.get("data", {}).get("message", "")
    lower_txt = (text + " " + data_msg).lower()
    if ("preavviso" in lower_txt and "30" in lower_txt) or "error" in p.get("data", {}).get("status", ""):
        found_error = True
        print("Messaggio di protezione preavviso ricevuto correttamente:")
        print(text or data_msg)
        break
assert found_error, "Dovrebbe essere scattato l'errore per preavviso inferiore a 30 minuti per lo Smart Locker!"
print("Test 2A PASSATO: Protezione preavviso 30 min per Locker verificata!")

print("\n=== TEST 2B: Slot Locker valido con preavviso >= 30 min (multiplo di 10 min) ===")
# Calcola orario valido: now + 35 min allineato a multiplo di 10
valid_lead_target = now + timedelta(minutes=35)
remainder = valid_lead_target.minute % 10
add_mins = (10 - remainder) if remainder != 0 else 0
valid_locker_dt = (valid_lead_target + timedelta(minutes=add_mins)).replace(second=0, microsecond=0)
valid_locker_str = valid_locker_dt.strftime("%H:%M")
expected_end_str = (valid_locker_dt + timedelta(minutes=10)).strftime("%H:%M")

res2b = send_message(
    [{"type": "text", "text": json.dumps({"action": "set_locker_pickup_details", "slot_time": valid_locker_str})}],
    context_id=ctx_id
)
parts2b = res2b.get("result", {}).get("parts", [])
locker_confirmed = False
for p in parts2b:
    if p.get("data", {}).get("a2a.ucp.checkout"):
        c = p["data"]["a2a.ucp.checkout"]
        dest = get_dest(c)
        print("Locker Destinazione:", dest.get("street_address"), "•", dest.get("extended_address"))
        for opt in get_options(c):
            if opt["id"] == "pickup_locker":
                print("Locker Desc:", opt["description"])
                assert valid_locker_str in opt["description"] and expected_end_str in opt["description"], f"Slot 10 min deve essere {valid_locker_str} - {expected_end_str}!"
                locker_confirmed = True
assert locker_confirmed, "Locker non confermato con slot valido!"
print(f"Test 2B PASSATO: Smart Locker slot {valid_locker_str} - {expected_end_str} confermato!")

print("\n=== TEST 3A: Regola Preavviso Treno: rifiuto se preavviso < 30 minuti ===")
res3a = send_message(
    [{"type": "text", "text": json.dumps({
        "action": "set_train_delivery_details",
        "train_number": "Frecciarossa 9540",
        "carriage": "Carrozza 4",
        "seat": "12D",
        "delivery_time": short_lead_str,
        "platform": "Binario 14"
    })}],
    context_id=ctx_id
)
parts3a = res3a.get("result", {}).get("parts", [])
found_train_error = False
for p in parts3a:
    text = p.get("text", "")
    data_msg = p.get("data", {}).get("message", "")
    lower_txt = (text + " " + data_msg).lower()
    if ("preavviso" in lower_txt and "30" in lower_txt) or "error" in p.get("data", {}).get("status", ""):
        found_train_error = True
        print("Messaggio di protezione preavviso treno ricevuto:")
        print(text or data_msg)
        break
assert found_train_error, "Dovrebbe essere scattato l'errore per preavviso inferiore a 30 minuti per consegna al treno!"
print("Test 3A PASSATO: Protezione preavviso 30 min per consegna a bordo treno verificata!")

print("\n=== TEST 3B: Consegna Treno valida con preavviso >= 30 min (finestra max 1 min, tariffa €6.50) ===")
valid_train_dt = (now + timedelta(minutes=40)).replace(second=0, microsecond=0)
valid_train_str = valid_train_dt.strftime("%H:%M")
expected_train_end_str = (valid_train_dt + timedelta(minutes=1)).strftime("%H:%M")

res3b = send_message(
    [{"type": "text", "text": json.dumps({
        "action": "set_train_delivery_details",
        "train_number": "Frecciarossa 9540",
        "carriage": "Carrozza 4",
        "seat": "12D",
        "delivery_time": valid_train_str,
        "platform": "Binario 14"
    })}],
    context_id=ctx_id
)
parts3b = res3b.get("result", {}).get("parts", [])
train_confirmed = False
for p in parts3b:
    if p.get("data", {}).get("a2a.ucp.checkout"):
        c = p["data"]["a2a.ucp.checkout"]
        dest = get_dest(c)
        print("Train Destinazione:", dest.get("street_address"), "•", dest.get("extended_address"))
        for opt in get_options(c):
            if opt["id"] == "in_seat_train":
                print("Train Desc:", opt["description"])
                assert valid_train_str in opt["description"] and expected_train_end_str in opt["description"], f"Finestra attesa deve essere 1 min: {valid_train_str} - {expected_train_end_str}!"
                train_confirmed = True
        for tot in c["totals"]:
            if tot["type"] == "fulfillment":
                print(f"Supplemento Consegna Treno: {tot['display_text']} = €{tot['amount']/100:.2f}")
                assert tot["amount"] == 650, "Il supplemento per il treno deve essere €6.50!"
assert train_confirmed, "Consegna treno non confermata con orario valido!"
print(f"Test 3B PASSATO: Consegna Treno con finestra di 1 minuto ({valid_train_str} - {expected_train_end_str}) e tariffa €6.50 confermata!")

print("\n=== TEST 4: Configura Servizio al Tavolo Bistrot (nessun preavviso 30m, finestra 5 min) ===")
table_dt = (now + timedelta(minutes=5)).replace(second=0, microsecond=0)
table_str = table_dt.strftime("%H:%M")
expected_table_end = (table_dt + timedelta(minutes=5)).strftime("%H:%M")

res4 = send_message(
    [{"type": "text", "text": json.dumps({
        "action": "set_table_service_details",
        "table_number": "Tavolo 5",
        "service_time": table_str
    })}],
    context_id=ctx_id
)
parts4 = res4.get("result", {}).get("parts", [])
table_confirmed = False
for p in parts4:
    if p.get("data", {}).get("a2a.ucp.checkout"):
        c = p["data"]["a2a.ucp.checkout"]
        dest = get_dest(c)
        print("Tavolo Destinazione:", dest.get("street_address"), "•", dest.get("extended_address"))
        for opt in get_options(c):
            if opt["id"] == "pickup_express":
                print("Tavolo Desc:", opt["description"])
                assert table_str in opt["description"] and expected_table_end in opt["description"], f"Slot 5 min deve essere {table_str} - {expected_table_end}!"
                table_confirmed = True
assert table_confirmed, "Servizio al tavolo non confermato!"
print("Test 4 PASSATO: Servizio al Tavolo Bistrot senza preavviso lungo confermato con successo!")

print("\n=== TEST 4B: Configura Consegna al Bancone / Ritiro al Banco ('consegna al bancone' -> 'Al Banco') ===")
res4b = send_message(
    [{"type": "text", "text": json.dumps({
        "action": "set_table_service_details",
        "table_number": "consegna al bancone",
        "service_time": table_str
    })}],
    context_id=ctx_id
)
parts4b = res4b.get("result", {}).get("parts", [])
counter_confirmed = False
for p in parts4b:
    if p.get("data", {}).get("a2a.ucp.checkout"):
        c = p["data"]["a2a.ucp.checkout"]
        dest = get_dest(c)
        print("Banco Destinazione:", dest.get("street_address"), "•", dest.get("extended_address"))
        for opt in get_options(c):
            if opt["id"] == "pickup_express":
                print("Banco Title:", opt.get("title"))
                print("Banco Desc:", opt["description"])
                assert "Ritiro al Banco" in opt.get("title", ""), f"Titolo errato: {opt.get('title')}"
                assert "Ritiro al banco confermato (Al Banco)" in opt["description"], f"Descrizione errata: {opt['description']}"
                assert "Al Banco (Ritiro al Banco:" in dest.get("extended_address", ""), f"Destinazione errata: {dest.get('extended_address')}"
                counter_confirmed = True
assert counter_confirmed, "Consegna al bancone non confermata!"
print("Test 4B PASSATO: Ritiro al Banco normalizzato con titolo e descrizione corretti!")

print("\n=== TEST 5: Completa Checkout con Mandato AP2 & Local Credential Manager ===")
res5 = send_message(
    [
        {"type": "data", "data": {"action": "complete_checkout"}},
        {"type": "data", "data": {
            "a2a.ucp.checkout.payment_data": {
                "id": "instr_devfest_card_01",
                "handler_id": "example_payment_provider",
                "type": "card",
                "brand": "Mastercard",
                "last_digits": "4242",
            },
            "a2a.ucp.checkout.risk_signals": {
                "ap2_mandate_id": "mandate_milano_centrale_2026",
                "device_verification": "hardware_backed_tpm",
                "cart_mandate_jwt": "eyJhbGciOiJFUzI1NiIsInR5cCI6ImFwMi1jYXJ0LW1hbmRhdGUrc2Qtand0In0.eyJpc3MiOiJkaWQ6a2V5Ono2TWt1RGV2aWNlUGFzc2tleUxDTV9NaWxhbm9fQ2VudHJhbGUiLCJ0b3RhbF9hbW91bnQiOjY1MCwiY3VycmVuY3kiOiJFVVIifQ.mock_sig",
                "payment_mandate_jwt": "eyJhbGciOiJFUzI1NiIsInR5cCI6ImFwMi1wYXltZW50LW1hbmRhdGUrc2Qtand0In0.eyJpc3MiOiJkaWQ6a2V5Ono2TWt1RGV2aWNlUGFzc2tleUxDTV9NaWxhbm9fQ2VudHJhbGUiLCJkeW5hbWljX2xpbmtpbmciOiJzaGEyNTY6Y2FydCJ9.mock_sig",
            }
        }}
    ],
    context_id=ctx_id
)
parts5 = res5.get("result", {}).get("parts", [])
order_completed = False
for p in parts5:
    if p.get("data", {}).get("a2a.ucp.checkout"):
        c = p["data"]["a2a.ucp.checkout"]
        print("Stato ricevuto:", c["status"])
        order_obj = c.get("order") or {}
        if c["status"] == "completed" and order_obj.get("id"):
            print("Ordine confermato ID:", order_obj.get("id"))
            order_completed = True
            break

if not order_completed:
    print("Stato transitorio ready_for_complete: invio conferma pagamento finale all'agente...")
    res5_final = send_message(
        [{"type": "text", "text": "Ho firmato il mandato AP2 con l'impronta digitale. Completa il pagamento e finalizza l'ordine adesso."}],
        context_id=ctx_id
    )
    for p in res5_final.get("result", {}).get("parts", []):
        if p.get("data", {}).get("a2a.ucp.checkout"):
            c = p["data"]["a2a.ucp.checkout"]
            print("Stato finale:", c["status"])
            order_obj = c.get("order") or {}
            print("Ordine confermato ID:", order_obj.get("id"))
            if c["status"] == "completed":
                order_completed = True
                break

assert order_completed, "Checkout non completato con successo!"
print("Test 5 PASSATO: Ordine completato con successo con mandato AP2!")

print("\n=======================================================")
print("  TUTTI I TEST END-TO-END SONO STATI SUPERATI CON SUCCESSO! ")
print("=======================================================")
