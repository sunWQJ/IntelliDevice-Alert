from __future__ import annotations
from typing import Dict, Any


PII_FIELDS = {
    "patient_name",
    "patient_phone",
    "patient_identifier",
    "clinician_name",
}


def remove_pii(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in PII_FIELDS}