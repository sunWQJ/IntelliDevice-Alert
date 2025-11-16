from __future__ import annotations
import os
import logging
import json
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Simple in-memory storage to avoid SQLite issues
class InMemoryDB:
    def __init__(self):
        self.reports = {}
        self.entities = {}
        self.fingerprints = {}
        self.pending = {}
        logger.info("In-memory database initialized")
    
    def add_report(self, report_id: str, data: Dict[str, Any]) -> None:
        self.reports[report_id] = data
        logger.info(f"Added report {report_id} to in-memory database")
    
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
                # Normalize datetime to ISO string
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
        counts = {
            "reports": len(self.reports),
            "entities": len(self.entities),
            "fingerprints": len(self.fingerprints),
            "pending": len(self.pending),
        }
        self.reports = {}
        self.entities = {}
        self.fingerprints = {}
        self.pending = {}
        return counts

# Global in-memory database instance
_db = InMemoryDB()

def get_db():
    return _db


def init_db():
    try:
        logger.info("In-memory database initialized successfully")
        
        # Add some sample data for testing Dashboard, Case View, and Overview Graph
        _add_sample_data()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def _add_sample_data():
    """Add sample data for testing Dashboard, Case View, and Overview Graph"""
    try:
        from datetime import datetime, timedelta
        import uuid
        
        # Check if we already have data
        existing_reports = _db.get_all_reports()
        if len(existing_reports) > 0:
            logger.info(f"Database already contains {len(existing_reports)} reports")
            return
            
        logger.info("Adding sample data for testing...")
        
        # Sample reports for Dashboard, Case View, and Overview Graph testing
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
            },
            {
                "report_id": str(uuid.uuid4()),
                "hospital_id": "H002",
                "device_name": "呼吸机",
                "manufacturer": "LifeTech",
                "model": "LV-500",
                "lot_sn": "L456",
                "event_datetime": (datetime.now() - timedelta(days=8)).isoformat(),
                "event_description": "呼吸机突然停止工作",
                "injury_severity": "severe",
                "action_taken": "立即更换备用呼吸机",
                "processed_at": datetime.now().isoformat(),
                "status": "processed"
            },
            {
                "report_id": str(uuid.uuid4()),
                "hospital_id": "H003",
                "device_name": "输液泵",
                "manufacturer": "MedFlow",
                "model": "INF-100",
                "lot_sn": "L789",
                "event_datetime": (datetime.now() - timedelta(days=5)).isoformat(),
                "event_description": "输液泵流速异常",
                "injury_severity": "mild",
                "action_taken": "重新校准设备",
                "processed_at": datetime.now().isoformat(),
                "status": "processed"
            }
        ]
        
        for report_data in sample_reports:
            try:
                _db.add_report(report_data['report_id'], report_data)
                logger.info(f"Added sample report: {report_data['device_name']} - {report_data['injury_severity']}")
            except Exception as e:
                logger.error(f"Error adding sample report: {e}")
        
        logger.info("Sample data added successfully")
        
    except Exception as e:
        logger.error(f"Error adding sample data: {e}")