from __future__ import annotations
from typing import Dict, Any


def normalize_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def fingerprint(payload: Dict[str, Any]) -> str:
    import hashlib

    parts = [
        normalize_string(payload.get("hospital_id")),
        normalize_string(payload.get("event_datetime")),
        normalize_string(payload.get("device_name")),
        normalize_string(payload.get("model")),
        normalize_string(payload.get("lot_sn")),
    ]
    base = "|".join(parts)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()