import json
import sys
import urllib.request
from uuid import uuid4

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_prompt():
    url = "http://localhost:10999/"
    profile_url = "http://localhost:4200/profile/agent_profile.json"
    headers = {
        "Content-Type": "application/json",
        "X-A2A-Extensions": "https://ucp.dev/2026-01-23/specification/overview?v=2026-01-23",
        "UCP-Agent": f'profile="{profile_url}"',
    }
    prompt = "Vorrei un espresso doppio caldo e una brioche al pistacchio da ritirare al banco prima della partenza"
    msg_dict = {
        "role": "user",
        "parts": [{"kind": "text", "text": prompt}],
        "messageId": str(uuid4()),
        "kind": "message",
    }
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
    
    print("Response keys:", list(data.keys()))
    res = data.get("result", {})
    parts = res.get("parts", [])
    print(f"Number of parts: {len(parts)}")
    for i, p in enumerate(parts):
        print(f"\n--- Part {i} (kind: {p.get('kind')}) ---")
        print(f"Part keys: {list(p.keys())}")
        if p.get("kind") == "text":
            print("Text:", p.get("text"))
        else:
            print("Raw Part:", json.dumps(p, indent=2))

if __name__ == "__main__":
    test_prompt()
