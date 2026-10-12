import urllib.request
import json

def test_user_query():
    print("Testing prompt: 'vorrei ordinare il pranzo con consegna al teno'")
    # We test with scenario_transit_locker (which has preferred_fulfillment: "pickup_locker")
    req_preset = urllib.request.Request("http://localhost:10998/shopper/context/preset/scenario_transit_locker", data=b"", method="POST")
    with urllib.request.urlopen(req_preset) as resp:
        ctx = json.loads(resp.read().decode())
        print(f"Active preset before mission: {ctx['scenario_preset_id']}, preferred: {ctx['preferences']['preferred_fulfillment']}")

    payload = json.dumps({
        "prompt": "vorrei ordinare il pranzo con consegna al teno",
        "protocol": "a2a"
    }).encode("utf-8")

    req = urllib.request.Request("http://localhost:10998/shopper/mission/stream", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            line_str = line.decode().strip()
            if line_str.startswith("data: "):
                event = json.loads(line_str[6:])
                if event.get("type") == "step":
                    step = event["step"]
                    print(f"\n[Step {step['step_number']}] {step['action']}")
                    print(f"  Description: {step['description']}")
                    if step["step_number"] == 1:
                        print(f"  Resolved method: {step['payload'].get('resolved_delivery_method')} ({step['payload'].get('fulfillment_reason')})")
                    elif step["step_number"] == 2:
                        print(f"  A2A required_delivery_method: {step['payload'].get('required_delivery_method')}")
                    elif step["step_number"] == 3:
                        fl = step['payload'].get('fulfillment_proposal', {})
                        print(f"  Proposal method: {fl.get('method')} ({fl.get('label')}) | Fee: €{fl.get('delivery_fee_cents', 0)/100:.2f}")
                elif event.get("type") == "final":
                    print(f"\n[Final Message]: {event.get('message')}")
                    fo = event.get('final_order', {})
                    print(f"Final Order: #{fo.get('order_id')} | fulfillment_type: {fo.get('fulfillment_type')}")
                    print(f"Fulfillment details: {fo.get('fulfillment_details')}")

if __name__ == "__main__":
    test_user_query()
