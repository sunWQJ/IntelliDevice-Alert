from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer
from typing import Optional
from .db import Base


class ReportModel(Base):
    __tablename__ = "reports"
    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hospital_id: Mapped[str] = mapped_column(String(128))
    device_name: Mapped[str] = mapped_column(String(256))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lot_sn: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    event_datetime: Mapped[str] = mapped_column(String(64))
    event_description: Mapped[str] = mapped_column(Text)
    injury_severity: Mapped[str] = mapped_column(String(32))
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    fingerprint: Mapped[str] = mapped_column(String(128), unique=True)
    source_version: Mapped[str] = mapped_column(String(32))


class ReportEntity(Base):
    __tablename__ = "report_entities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    term: Mapped[str] = mapped_column(String(256))
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)