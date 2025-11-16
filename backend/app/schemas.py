from __future__ import annotations
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


InjurySeverity = Literal["none", "mild", "moderate", "severe", "death"]


class ReportIn(BaseModel):
    hospital_id: str = Field(..., min_length=1)
    device_name: str = Field(..., min_length=1)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    lot_sn: Optional[str] = None
    event_datetime: Optional[datetime] = None
    event_description: str = Field(..., min_length=1)
    injury_severity: InjurySeverity = "none"
    action_taken: Optional[str] = None
    attachments: Optional[List[str]] = None

    # PII（将被脱敏）
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_identifier: Optional[str] = None
    clinician_name: Optional[str] = None


class ReportOut(BaseModel):
    report_id: str
    hospital_id: str
    device_name: str
    manufacturer: Optional[str]
    model: Optional[str]
    lot_sn: Optional[str]
    event_datetime: datetime
    event_description: str
    injury_severity: InjurySeverity
    action_taken: Optional[str]
    attachments: Optional[List[str]]
    processed_at: datetime
    status: Literal["received", "duplicate"] = "received"


class ReportStored(ReportOut):
    fingerprint: str
    source_version: str
    processing_log_ids: List[str] = []


class ProcessingLog(BaseModel):
    id: str
    report_id: str
    created_at: datetime
    event: str
    detail: Optional[str] = None