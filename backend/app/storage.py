from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .schemas import ReportStored, ReportOut
from .db import SessionLocal
from .models import ReportModel
import json


def upsert_report(stored: ReportStored) -> ReportOut:
    with SessionLocal() as db:
        existing = db.get(ReportModel, stored.report_id)
        if existing is None:
            m = ReportModel(
                report_id=stored.report_id,
                hospital_id=stored.hospital_id,
                device_name=stored.device_name,
                manufacturer=stored.manufacturer,
                model=stored.model,
                lot_sn=stored.lot_sn,
                event_datetime=stored.event_datetime.isoformat(),
                event_description=stored.event_description,
                injury_severity=stored.injury_severity,
                action_taken=stored.action_taken,
                attachments=json.dumps(stored.attachments) if stored.attachments else None,
                processed_at=stored.processed_at.isoformat(),
                status=stored.status,
                fingerprint=stored.fingerprint,
                source_version=stored.source_version,
            )
            db.add(m)
        else:
            existing.status = stored.status
            existing.processed_at = stored.processed_at.isoformat()
        db.commit()
    return ReportOut(**stored.dict())


def by_id(report_id: str) -> Optional[ReportOut]:
    with SessionLocal() as db:
        m = db.get(ReportModel, report_id)
        if m is None:
            return None
        data = dict(
            report_id=m.report_id,
            hospital_id=m.hospital_id,
            device_name=m.device_name,
            manufacturer=m.manufacturer,
            model=m.model,
            lot_sn=m.lot_sn,
            event_datetime=datetime.fromisoformat(m.event_datetime),
            event_description=m.event_description,
            injury_severity=m.injury_severity,
            action_taken=m.action_taken,
            attachments=json.loads(m.attachments) if m.attachments else None,
            processed_at=datetime.fromisoformat(m.processed_at),
            status=m.status,
        )
        return ReportOut(**data)


def find_by_fingerprint(fp: str) -> Optional[str]:
    with SessionLocal() as db:
        m = db.query(ReportModel).filter(ReportModel.fingerprint == fp).first()
        return m.report_id if m else None


def now() -> datetime:
    return datetime.utcnow()