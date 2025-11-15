from __future__ import annotations
import os
import json
from typing import List, Dict, Any
from .terminology import search as term_search, available_categories


def _env(key: str) -> str | None:
    v = os.getenv(key)
    return v if v else None


def _openai_client():
    try:
        from openai import OpenAI
    except Exception:
        return None
    api_key = _env("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _gemini_client():
    try:
        import google.generativeai as genai
    except Exception:
        return None
    api_key = _env("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai


def _build_prompt(text: str, candidates: Dict[str, List[Dict[str, Any]]], top_k: int) -> str:
    obj = {
        "instruction": "根据文本在每个分类中从候选列表中选择最匹配的术语，返回每类最多top_k项，必须从候选中选择，输出JSON。",
        "text": text,
        "top_k": top_k,
        "candidates": candidates,
        "output_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "term": {"type": "string"},
                                "score": {"type": "number"}
                            },
                            "required": ["code", "term"]
                        }
                    }
                }
            },
            "required": ["results"]
        }
    }
    return json.dumps(obj, ensure_ascii=False)


def _prepare_candidates(text: str, categories: List[str], top_k: int) -> Dict[str, List[Dict[str, Any]]]:
    cats = categories or available_categories()
    res = term_search(text, cats, top_k=max(top_k, 10), threshold=0.0)
    out: Dict[str, List[Dict[str, Any]]] = {}
    for c, items in res.items():
        out[c] = [
            {"code": t.code, "term": t.term, "definition": t.definition}
            for (t, s) in items
        ]
    return out


def llm_standardize(provider: str, text: str, categories: List[str] | None, top_k: int) -> Dict[str, Any]:
    candidates = _prepare_candidates(text, categories or [], top_k)
    prompt = _build_prompt(text, candidates, top_k)
    if provider == "openai":
        client = _openai_client()
        if client is None:
            return {"error": "openai_unavailable"}
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是医疗不良事件术语标准化助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            data = json.loads(content)
            return data
        except Exception:
            return {"error": "openai_call_failed"}
    elif provider == "gemini":
        genai = _gemini_client()
        if genai is None:
            return {"error": "gemini_unavailable"}
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text_out = resp.text or "{}"
            data = json.loads(text_out)
            return data
        except Exception:
            return {"error": "gemini_call_failed"}
    else:
        return {"error": "provider_unsupported"}


def llm_structure(provider: str, text: str, top_k: int = 5) -> Dict[str, Any]:
    cats = ["A", "E", "F", "G"]
    candidates = _prepare_candidates(text, cats, top_k)
    obj = {
        "instruction": "从文本中抽取实体与关系：实体包括器械名称、故障表现、伤害表现、处置措施、制造商、科室；关系包括CAUSES(故障->伤害)、MITIGATES(处置->故障)、ASSOCIATED_WITH(器械->事件)。仅从候选术语中选择，输出JSON包括entities与relations。",
        "text": text,
        "candidates": candidates,
        "output_schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"type": {"type": "string"}, "code": {"type": "string"}, "term": {"type": "string"}}, "required": ["type", "term"]}
                },
                "relations": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"type": {"type": "string"}, "from": {"type": "string"}, "to": {"type": "string"}}, "required": ["type", "from", "to"]}
                }
            },
            "required": ["entities", "relations"]
        }
    }
    prompt = json.dumps(obj, ensure_ascii=False)
    if provider == "openai":
        client = _openai_client()
        if client is None:
            return {"error": "openai_unavailable"}
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是医疗不良事件结构化剖析助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            data = json.loads(content)
            return data
        except Exception:
            return {"error": "openai_call_failed"}
    elif provider == "gemini":
        genai = _gemini_client()
        if genai is None:
            return {"error": "gemini_unavailable"}
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text_out = resp.text or "{}"
            data = json.loads(text_out)
            return data
        except Exception:
            return {"error": "gemini_call_failed"}
    else:
        return {"error": "provider_unsupported"}