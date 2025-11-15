from __future__ import annotations
from pathlib import Path
import os


def terminology_dir() -> Path | None:
    env = os.getenv("TERMINOLOGY_DIR")
    if env:
        p = Path(env)
        return p if p.exists() else None
    root = Path(__file__).resolve().parents[2]
    p = root / "术语库"
    return p if p.exists() else None