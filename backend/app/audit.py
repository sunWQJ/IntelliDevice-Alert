from __future__ import annotations
from typing import List
from datetime import datetime
from uuid import uuid4
from .schemas import ProcessingLog


_LOGS: List[ProcessingLog] = []


def write(report_id: str, event: str, detail: str | None = None) -> ProcessingLog:
    log = ProcessingLog(
        id=str(uuid4()),
        report_id=report_id,
        created_at=datetime.utcnow(),
        event=event,
        detail=detail,
    )
    _LOGS.append(log)
    return log


def for_report(report_id: str) -> List[ProcessingLog]:
    return [l for l in _LOGS if l.report_id == report_id]
