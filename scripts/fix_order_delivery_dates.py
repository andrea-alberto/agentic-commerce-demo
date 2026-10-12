import json
import re
from pathlib import Path
from datetime import datetime, timedelta

data_path = Path("backend/src/travel_retail_agent/data/bopis_orders.json")
with open(data_path, "r", encoding="utf-8") as f:
    orders = json.load(f)

changed = 0
for o in orders:
    raw = o.get("requested_delivery_display", "")
    fld = o.get("fulfillment_details", {})
    
    # Check if raw needs cleaning
    needs_update = False
    if "min" in raw.lower() or not raw or not re.search(r"\b\d{1,2}:\d{2}\b", raw):
        needs_update = True
        
    if needs_update:
        date_m = re.search(r"\b\d{2}/\d{2}/\d{4}\b", raw)
        if date_m:
            date_str = date_m.group(0)
        elif o.get("placed_at_display"):
            date_str = o["placed_at_display"][:10]
        elif o.get("created_at"):
            dt = datetime.fromisoformat(o["created_at"])
            date_str = dt.strftime("%d/%m/%Y")
        else:
            date_str = "06/10/2026"
            
        time_m = re.search(r"\b\d{1,2}:\d{2}(?:\s*[\-–]\s*\d{1,2}:\d{2})?\b", raw)
        if time_m:
            time_str = time_m.group(0)
        else:
            time_str = fld.get("service_time") or fld.get("delivery_time") or fld.get("slot_start")
            if not time_str and fld.get("window") and "min" not in fld.get("window", "").lower():
                time_str = fld.get("window")
            if not time_str:
                dt = datetime.fromisoformat(o["created_at"])
                lead = o.get("lead_time_minutes", 5)
                time_str = (dt + timedelta(minutes=lead)).strftime("%H:%M")
                
        new_val = f"{date_str} {time_str}".strip()
        print(f'{o.get("order_id")}: "{raw}" -> "{new_val}"')
        o["requested_delivery_display"] = new_val
        if fld.get("window") in ["Pronto in 5 min", "Finestra 5 min"]:
            fld["window"] = fld.get("service_time") or time_str
        changed += 1

print(f"Total changed: {changed}")

with open(data_path, "w", encoding="utf-8") as f:
    json.dump(orders, f, indent=2, ensure_ascii=False)

print("Saved bopis_orders.json successfully.")
