from __future__ import annotations
from dotenv import load_dotenv, set_key, find_dotenv
from pathlib import Path
from typing import Optional
import os

def load_env():
    load_dotenv()

def _env_path() -> str:
    p = find_dotenv(usecwd=True)
    if p:
        return p
    return str(Path(".env").resolve())

def persist_llm_config(provider: str, api_key: str | None, model: str | None):
    path = _env_path()
    Path(path).touch(exist_ok=True)
    prov = str(provider or "").lower()
    set_key(path, "LLM_PROVIDER", prov)
    if prov == "openai":
        if api_key:
            set_key(path, "OPENAI_API_KEY", api_key)
        if model:
            set_key(path, "OPENAI_MODEL", model)
    elif prov == "gemini":
        if api_key:
            set_key(path, "GEMINI_API_KEY", api_key)
        if model:
            set_key(path, "GEMINI_MODEL", model)
    elif prov == "siliconflow":
        if api_key:
            set_key(path, "SILICONFLOW_API_KEY", api_key)
        if model:
            set_key(path, "SILICONFLOW_MODEL", model)
    return {"ok": True, "provider": prov}

def terminology_dir() -> Optional[Path]:
    env_v = Path(Path(find_dotenv(usecwd=True)).parent / (Path(find_dotenv(usecwd=True)).name or ".env"))
    td = Path(Path.cwd() / "术语库")
    env_override = Path((Path.cwd() / (Path(".") / "术语库")).resolve())
    v = Path((Path(__file__).resolve().parents[2] / "术语库").resolve())
    for p in [Path(os.getenv("TERMINOLOGY_DIR", "")) if "TERMINOLOGY_DIR" in os.environ else None, td, v, Path.cwd() / "release" / "术语库"]:
        if p and Path(p).exists():
            return Path(p)
    return None