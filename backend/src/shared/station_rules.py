# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Physical Retail Domain Rules & Station Constraints for Milano Centrale BOPIS Hub.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

TRAIN_DELIVERY_FEE_CENTS = 650
MIN_LEAD_TIME_TRAIN_MINUTES = 30
MIN_LEAD_TIME_LOCKER_MINUTES = 30


def validate_station_constraints(
    method: str,
    details: Dict[str, Any],
    items: List[Dict[str, Any]],
    now_dt: Optional[datetime] = None,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validate requested fulfillment against Milano Centrale physical station rules.
    Returns: (is_valid, error_message, computed_fulfillment_data)
    """
    if now_dt is None:
        now_dt = datetime.now().astimezone()

    contains_hot_items = any(it.get("is_hot", False) for it in items)

    if method == "pickup_locker":
        # 1. Thermal restriction
        if contains_hot_items:
            hot_titles = [it.get("name") or it.get("title", "Alimento caldo") for it in items if it.get("is_hot")]
            return (
                False,
                f"⚠️ Violazione Regola Termica Smart Locker: il carrello contiene alimenti/bevande calde ({', '.join(hot_titles)}). "
                "I locker interrati non sono riscaldati. Seleziona 'pickup_express' o 'in_seat_train'.",
                {},
            )

        slot_time_str = details.get("slot_time", "")
        if not slot_time_str:
            target = now_dt + timedelta(minutes=35)
            rem = target.minute % 10
            add = (10 - rem) if rem != 0 else 0
            target = (target + timedelta(minutes=add)).replace(second=0, microsecond=0)
            slot_time_str = target.strftime("%H:%M")

        pin = details.get("pin_code", "3819")
        box = details.get("box_number", "Box #14")

        return True, None, {
            "method": "pickup_locker",
            "label": "Smart Locker (Piano Interrato)",
            "location": "Locker Hub Stazione Centrale - Piano Interrato",
            "box_number": box,
            "pin_code": pin,
            "slot_start": slot_time_str,
            "slot_end": (datetime.strptime(slot_time_str, "%H:%M") + timedelta(minutes=10)).strftime("%H:%M"),
            "delivery_fee_cents": 0,
            "lead_time_minutes": 30,
        }

    elif method == "in_seat_train":
        train_num = details.get("train_number", "Frecciarossa 9540")
        carriage = str(details.get("carriage", "4"))
        seat = str(details.get("seat", "12D"))
        platform = str(details.get("platform", "14"))
        train_time_str = details.get("delivery_time", "")

        lead_min = 35
        if train_time_str:
            try:
                target_dt = datetime.combine(
                    now_dt.date(),
                    datetime.strptime(train_time_str, "%H:%M").time(),
                ).astimezone(now_dt.tzinfo)
                if target_dt < now_dt:
                    target_dt += timedelta(days=1)
                lead_min = int((target_dt - now_dt).total_seconds() / 60)
                if lead_min < MIN_LEAD_TIME_TRAIN_MINUTES:
                    first_valid = now_dt + timedelta(minutes=35)
                    return (
                        False,
                        f"⚠️ Preavviso insufficiente per Consegna al Treno ({lead_min} min). È richiesto almeno {MIN_LEAD_TIME_TRAIN_MINUTES} min. "
                        f"Il primo orario disponibile è {first_valid.strftime('%H:%M')} (oppure scegli 'pickup_express').",
                        {},
                    )
            except Exception:
                pass

        if not train_time_str:
            train_time_str = (now_dt + timedelta(minutes=35)).strftime("%H:%M")

        return True, None, {
            "method": "in_seat_train",
            "label": f"Consegna a Bordo ({train_num})",
            "train_number": train_num,
            "platform": platform,
            "carriage": carriage,
            "seat": seat,
            "delivery_time": train_time_str,
            "window": f"{train_time_str} – {(datetime.strptime(train_time_str, '%H:%M') + timedelta(minutes=1)).strftime('%H:%M')}",
            "lead_time_minutes": lead_min,
            "delivery_fee_cents": TRAIN_DELIVERY_FEE_CENTS,
        }

    elif method in ["pickup", "pickup_express"]:
        table = details.get("table_number", "Al Banco Express")
        ready_time = (now_dt + timedelta(minutes=5)).strftime("%H:%M")
        return True, None, {
            "method": "pickup",
            "label": "Ritiro Rapido al Banco (Bistrot Binario 12)",
            "location": "Bistrot Binario 12",
            "table_number": table,
            "service_time": ready_time,
            "window": "Pronto in 5 min",
            "lead_time_minutes": 5,
            "delivery_fee_cents": 0,
        }

    elif method == "table_service":
        table = details.get("table_number", "Tavolo 5")
        ready_time = (now_dt + timedelta(minutes=5)).strftime("%H:%M")
        end_time = (now_dt + timedelta(minutes=10)).strftime("%H:%M")
        return True, None, {
            "method": "table_service",
            "label": f"Servizio al Tavolo ({table})",
            "location": "Bistrot Binario 12",
            "table_number": table,
            "service_time": f"{ready_time} – {end_time}",
            "window": f"{ready_time} – {end_time}",
            "lead_time_minutes": 5,
            "delivery_fee_cents": 0,
        }

    return False, f"Metodo di evasione '{method}' non riconosciuto.", {}
