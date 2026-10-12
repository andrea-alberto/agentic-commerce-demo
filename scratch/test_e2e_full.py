# Test Full E2E for Demo 3 and Demo 4
import urllib.request
import json

def test_full():
    print("--- 1. Testing GET /shopper/context ---")
    req = urllib.request.Request("http://localhost:10998/shopper/context")
    with urllib.request.urlopen(req) as resp:
        ctx = json.loads(resp.read().decode())
        print("Traveler Context:", ctx["name"], ctx["ticket"]["train_number"], ctx["ticket"]["seat"])

    print("\n--- 2. Testing Preset Change (scenario_transit_locker) ---")
    req = urllib.request.Request("http://localhost:10998/shopper/context/preset/scenario_transit_locker", data=b"", method="POST")
    with urllib.request.urlopen(req) as resp:
        ctx2 = json.loads(resp.read().decode())
        print("Updated Context:", ctx2["ticket"]["train_number"], ctx2["preferences"]["preferred_fulfillment"])

    print("\n--- 3. Testing Demo 3 A2A Mission Stream & Human-Present Challenge ---")
    payload_a2a = json.dumps({
        "prompt": "Vorrei ordinare il pranzo con consegna a bordo treno",
        "protocol": "a2a"
    }).encode("utf-8")
    req = urllib.request.Request("http://localhost:10998/shopper/mission/stream", data=payload_a2a, headers={"Content-Type": "application/json"}, method="POST")
    a2a_challenge = None
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            line_str = line.decode().strip()
            if line_str.startswith("data: "):
                event = json.loads(line_str[6:])
                if event.get("type") == "step":
                    step = event["step"]
                    print(f"  [A2A Step {step['step_number']}] {step['action']}: {step['description']}")
                elif event.get("type") == "challenge":
                    a2a_challenge = event["challenge"]
                    print(f"  [A2A Challenge] Received: {a2a_challenge['challenge_id']} | Total: €{a2a_challenge['total_cents']/100:.2f}")

    if a2a_challenge:
        print("  -> Simulating Client Biometric Touch & AP2 Mandate Signing (LCM)...")
        auth_payload = json.dumps({
            "protocol": "a2a",
            "challenge": a2a_challenge,
            "ap2_mandate": {
                "mandate_id": f"tok_ap2_test_{a2a_challenge['order_id']}",
                "max_authorized_cents": a2a_challenge["total_cents"],
                "signature_scheme": "FIDO2_Passkey_P256",
                "token_jwt": "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkFQMi1DZXJ0In0.eyJzdWIiOiAibWFyaW8ucm9zc2kifQ.test_sig"
            }
        }).encode("utf-8")
        auth_req = urllib.request.Request("http://localhost:10998/shopper/mission/authorize", data=auth_payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(auth_req) as auth_resp:
            auth_res = json.loads(auth_resp.read().decode())
            print(f"  [A2A Step 4] {auth_res['step_ap2']['action']}: {auth_res['step_ap2']['description']}")
            print(f"  [A2A Step 5] {auth_res['step_final']['action']}: {auth_res['step_final']['description']}")
            print(f"  [A2A Confirmed] Order ID: {auth_res['final_order']['order_id']}")

    print("\n--- 4. Testing Demo 4 UCP REST Mission Stream & Human-Present Challenge ---")
    payload_rest = json.dumps({
        "prompt": "Prepara snack allo smart locker e verifica con RFC 9421",
        "protocol": "ucp_rest"
    }).encode("utf-8")
    req = urllib.request.Request("http://localhost:10998/shopper/mission/stream", data=payload_rest, headers={"Content-Type": "application/json"}, method="POST")
    rest_challenge = None
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            line_str = line.decode().strip()
            if line_str.startswith("data: "):
                event = json.loads(line_str[6:])
                if event.get("type") == "step":
                    step = event["step"]
                    sig = step.get("headers", {}).get("signature", "")
                    sig_info = f"(Sig: {sig[:15]}...)" if sig else ""
                    print(f"  [REST Step {step['step_number']}] {step['action']}: {step['description']} {sig_info}")
                elif event.get("type") == "challenge":
                    rest_challenge = event["challenge"]
                    print(f"  [REST Challenge] Received: {rest_challenge['challenge_id']} | Total: €{rest_challenge['total_cents']/100:.2f}")

    if rest_challenge:
        print("  -> Simulating Client Biometric Touch & AP2 Mandate Signing (LCM)...")
        auth_payload = json.dumps({
            "protocol": "ucp_rest",
            "challenge": rest_challenge,
            "ap2_mandate": {
                "mandate_id": f"tok_ap2_rest_test_{rest_challenge['checkout_id']}",
                "max_authorized_cents": rest_challenge["total_cents"],
                "signature_scheme": "FIDO2_Passkey_P256",
                "token_jwt": "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkFQMi1DZXJ0In0.eyJzdWIiOiAibWFyaW8ucm9zc2kifQ.test_sig"
            }
        }).encode("utf-8")
        auth_req = urllib.request.Request("http://localhost:10998/shopper/mission/authorize", data=auth_payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(auth_req) as auth_resp:
            auth_res = json.loads(auth_resp.read().decode())
            print(f"  [REST Step 4] {auth_res['step_ap2']['action']}: {auth_res['step_ap2']['description']}")
            print(f"  [REST Step 5] {auth_res['step_final']['action']}: {auth_res['step_final']['description']}")
            print(f"  [REST Confirmed] Order ID: {auth_res['final_order']['order_id']}")

    print("\n--- 5. Checking Central Merchant BOPIS Orders (:10999) ---")
    req = urllib.request.Request("http://localhost:10999/bopis/orders")
    with urllib.request.urlopen(req) as resp:
        orders = json.loads(resp.read().decode())
        print(f"Total BOPIS Orders in Dispatcher: {len(orders)}")
        for o in orders[-4:]:
            print(f" - #{o.get('order_id')}: {o.get('channel_label')} | {o.get('status')} | {o.get('payment_method')} | €{o.get('totals', {}).get('total_cents', 0)/100:.2f}")

    print("\n--- 6. Checking shopper-client HTTP 200 on :4203 ---")
    req = urllib.request.Request("http://localhost:4203/")
    with urllib.request.urlopen(req) as resp:
        print(f"Shopper Client Status: {resp.status}")

if __name__ == "__main__":
    test_full()
