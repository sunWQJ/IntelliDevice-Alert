from __future__ import annotations
from typing import Optional
from datetime import datetime
from .schemas import ReportStored, ReportOut
from .db import get_db
import json

# Get the in-memory database instance
db = get_db()

def upsert_report(stored: ReportStored) -> ReportOut:
    """Insert or update a report in the in-memory database"""
    try:
        # Convert to dict for storage
        report_data = stored.dict()
        
        # Store the report
        db.add_report(stored.report_id, report_data)
        
        # Store fingerprint for duplicate detection
        if stored.fingerprint:
            db.add_fingerprint(stored.fingerprint, stored.report_id)
        
        return ReportOut(**report_data)
    except Exception as e:
        raise Exception(f"Failed to upsert report: {e}")

def by_id(report_id: str) -> Optional[ReportOut]:
    """Get a report by ID"""
    try:
        data = db.get_report(report_id)
        if data is None:
            return None
        return ReportOut(**data)
    except Exception as e:
        raise Exception(f"Failed to get report by ID: {e}")

def find_by_fingerprint(fingerprint: str) -> Optional[str]:
    """Find report ID by fingerprint"""
    try:
        return db.get_by_fingerprint(fingerprint)
    except Exception as e:
        raise Exception(f"Failed to find by fingerprint: {e}")

def now():
    """Get current timestamp"""
    return datetime.now()