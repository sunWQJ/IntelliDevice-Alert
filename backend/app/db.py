from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


_root = Path(__file__).resolve().parents[2]
_db_path = _root / "intelli_device_alert.db"
_default_url = f"sqlite:///{_db_path}"  # absolute path
DB_URL = os.getenv("DB_URL", _default_url)


engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from . import models  # noqa
    Base.metadata.create_all(bind=engine)