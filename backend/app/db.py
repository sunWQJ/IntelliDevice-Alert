from __future__ import annotations
import os
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()

class ReportRow(Base):
    __tablename__ = "reports"
    report_id = Column(String, primary_key=True)
    data = Column(Text)
    processed_at = Column(String)

class FingerprintRow(Base):
    __tablename__ = "fingerprints"
    fingerprint = Column(String, primary_key=True)
    report_id = Column(String)

class PendingRow(Base):
    __tablename__ = "pending"
    report_id = Column(String, primary_key=True)
    data = Column(Text)

def _db_url():
    v = os.getenv("DB_URL")
    return v if v else "sqlite:///./data.db"

def _use_sql():
    return True

engine = create_engine(_db_url(), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class SqlDB:
    def __init__(self):
        Base.metadata.create_all(engine)
        self.session = SessionLocal()
        logger.info("SQL database initialized")
    def add_report(self, report_id: str, data: Dict[str, Any]) -> None:
        import json as _json
        s = self.session
        row = s.get(ReportRow, report_id) or ReportRow(report_id=report_id)
        row.data = _json.dumps(data, ensure_ascii=False, default=str)
        pa = data.get("processed_at")
        row.processed_at = pa.isoformat() if hasattr(pa, "isoformat") else str(pa)
        s.merge(row)
        s.commit()
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        import json as _json
        s = self.session
        row = s.get(ReportRow, report_id)
        if not row:
            return None
        d = _json.loads(row.data)
        if isinstance(d.get("event_datetime"), str):
            try:
                d["event_datetime"] = datetime.fromisoformat(d["event_datetime"])
            except Exception:
                pass
        if isinstance(d.get("processed_at"), str):
            try:
                d["processed_at"] = datetime.fromisoformat(d["processed_at"])
            except Exception:
                pass
        return d
    def get_all_reports(self) -> List[Dict[str, Any]]:
        import json as _json
        s = self.session
        rows = s.query(ReportRow).all()
        out = []
        for r in rows:
            d = _json.loads(r.data)
            try:
                if isinstance(d.get("event_datetime"), str):
                    d["event_datetime"] = datetime.fromisoformat(d["event_datetime"])
                if isinstance(d.get("processed_at"), str):
                    d["processed_at"] = datetime.fromisoformat(d["processed_at"])
            except Exception:
                pass
            out.append(d)
        return out
    def get_reports_by_limit(self, limit: int) -> List[Dict[str, Any]]:
        import json as _json
        s = self.session
        rows = s.query(ReportRow).order_by(ReportRow.processed_at.desc()).limit(limit).all()
        out = []
        for r in rows:
            d = _json.loads(r.data)
            try:
                if isinstance(d.get("event_datetime"), str):
                    d["event_datetime"] = datetime.fromisoformat(d["event_datetime"])
                if isinstance(d.get("processed_at"), str):
                    d["processed_at"] = datetime.fromisoformat(d["processed_at"])
            except Exception:
                pass
            out.append(d)
        return out
    def add_fingerprint(self, fingerprint: str, report_id: str) -> None:
        s = self.session
        row = s.get(FingerprintRow, fingerprint) or FingerprintRow(fingerprint=fingerprint)
        row.report_id = report_id
        s.merge(row)
        s.commit()
    def get_by_fingerprint(self, fingerprint: str) -> Optional[str]:
        s = self.session
        row = s.get(FingerprintRow, fingerprint)
        return row.report_id if row else None
    def add_pending(self, report_id: str, data: Dict[str, Any]) -> None:
        import json as _json
        s = self.session
        row = s.get(PendingRow, report_id) or PendingRow(report_id=report_id)
        row.data = _json.dumps(data, ensure_ascii=False, default=str)
        s.merge(row)
        s.commit()
    def list_pending(self) -> List[Dict[str, Any]]:
        import json as _json
        s = self.session
        rows = s.query(PendingRow).all()
        out = []
        for r in rows:
            d = _json.loads(r.data)
            d["report_id"] = r.report_id
            out.append(d)
        return out
    def pop_pending(self, report_id: str) -> Optional[Dict[str, Any]]:
        import json as _json
        s = self.session
        row = s.get(PendingRow, report_id)
        if not row:
            return None
        d = _json.loads(row.data)
        s.delete(row)
        s.commit()
        return d
    def clear(self) -> Dict[str, int]:
        s = self.session
        rc = s.query(ReportRow).count()
        ec = 0
        fc = s.query(FingerprintRow).count()
        pc = s.query(PendingRow).count()
        s.query(ReportRow).delete()
        s.query(FingerprintRow).delete()
        s.query(PendingRow).delete()
        s.commit()
        return {"reports": rc, "entities": ec, "fingerprints": fc, "pending": pc}

class InMemoryDB:
    def __init__(self):
        self.reports = {}
        self.entities = {}
        self.fingerprints = {}
        self.pending = {}
        logger.info("In-memory database initialized")
    def add_report(self, report_id: str, data: Dict[str, Any]) -> None:
        self.reports[report_id] = data
        logger.info("Added report %s to in-memory database" % report_id)
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        return self.reports.get(report_id)
    def get_all_reports(self) -> List[Dict[str, Any]]:
        return list(self.reports.values())
    def get_reports_by_limit(self, limit: int) -> List[Dict[str, Any]]:
        reports = list(self.reports.values())
        def _sort_key(x):
            v = x.get('processed_at')
            if v is None:
                return x.get('report_id', '')
            try:
                if hasattr(v, 'isoformat'):
                    return v.isoformat()
                return str(v)
            except Exception:
                return x.get('report_id', '')
        reports.sort(key=_sort_key, reverse=True)
        return reports[:limit]
    def add_fingerprint(self, fingerprint: str, report_id: str) -> None:
        self.fingerprints[fingerprint] = report_id
    def get_by_fingerprint(self, fingerprint: str) -> Optional[str]:
        return self.fingerprints.get(fingerprint)
    def add_pending(self, report_id: str, data: Dict[str, Any]) -> None:
        self.pending[report_id] = data
    def list_pending(self) -> List[Dict[str, Any]]:
        return [dict(x, report_id=k) for k, x in self.pending.items()]
    def pop_pending(self, report_id: str) -> Optional[Dict[str, Any]]:
        return self.pending.pop(report_id, None)
    def clear(self) -> Dict[str, int]:
        counts = {"reports": len(self.reports), "entities": len(self.entities), "fingerprints": len(self.fingerprints), "pending": len(self.pending)}
        self.reports = {}
        self.entities = {}
        self.fingerprints = {}
        self.pending = {}
        return counts

_db = SqlDB() if _use_sql() else InMemoryDB()

def get_db():
    return _db

def init_db():
    try:
        _add_sample_data()
    except Exception as e:
        logger.error("Failed to initialize database: %s" % str(e))
        raise

def _add_sample_data():
    try:
        from datetime import datetime, timedelta
        import uuid
        existing_reports = _db.get_all_reports()
        if len(existing_reports) > 0:
            return
        sample_reports = [
            {
                "report_id": str(uuid.uuid4()),
                "hospital_id": "H001",
                "device_name": "心电监护仪",
                "manufacturer": "ACME",
                "model": "ECG-200",
                "lot_sn": "L123",
                "event_datetime": (datetime.now() - timedelta(days=10)).isoformat(),
                "event_description": "设备屏幕无显示，患者监护中断",
                "injury_severity": "moderate",
                "action_taken": "更换设备并加护观察",
                "processed_at": datetime.now().isoformat(),
                "status": "processed"
            }
        ]
        for report_data in sample_reports:
            _db.add_report(report_data['report_id'], report_data)
    except Exception as e:
        logger.error("Error adding sample data: %s" % str(e))