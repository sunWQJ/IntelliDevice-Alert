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


def _siliconflow_client():
    try:
        from openai import OpenAI
    except Exception:
        return None
    api_key = _env("SILICONFLOW_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")


def _build_prompt(text: str, candidates: Dict[str, List[Dict[str, Any]]], top_k: int) -> str:
    obj = {
        "instruction": "根据文本在每个分类中从候选列表中选择最匹配的术语，返回每类最多top_k项，必须从候选中选择。你必须仅输出有效JSON，严格遵循输出schema，不要添加任何说明或代码块。",
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
            data = _parse_json_strict(content)
            return data
        except Exception:
            out = {"error": "openai_call_failed"}
            if echo_prompt:
                out["prompt"] = prompt
            return out
    elif provider == "gemini":
        genai = _gemini_client()
        if genai is None:
            return {"error": "gemini_unavailable"}
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        try:
            model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
            resp = model.generate_content(prompt)
            text_out = getattr(resp, "text", None) or ""
            if not text_out:
                try:
                    c = resp.candidates[0]
                    p = c.content.parts[0]
                    if hasattr(p, "text"):
                        text_out = p.text
                    else:
                        text_out = json.dumps(p)
                except Exception:
                    text_out = "{}"
            data = _parse_json_strict(text_out)
            return data
        except Exception:
            out = {"error": "gemini_call_failed"}
            if echo_prompt:
                out["prompt"] = prompt
            return out
    elif provider == "siliconflow":
        client = _siliconflow_client()
        if client is None:
            return {"error": "siliconflow_unavailable"}
        model = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是医疗不良事件术语标准化助手。仅输出有效JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            data = _parse_json_strict(content)
            return data
        except Exception:
            return {"error": "siliconflow_call_failed"}
    else:
        return {"error": "provider_unsupported"}


def llm_structure(provider: str, text: str, top_k: int = 5, echo_prompt: bool = False, categories: List[str] | None = None) -> Dict[str, Any]:
    cats = categories or ["A", "E"]
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
            data = _parse_json_strict(content)
            if echo_prompt and isinstance(data, dict):
                data["prompt"] = prompt
            return data
        except Exception:
            return {"error": "openai_call_failed"}
    elif provider == "gemini":
        genai = _gemini_client()
        if genai is None:
            return {"error": "gemini_unavailable"}
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        try:
            model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
            resp = model.generate_content(prompt)
            text_out = getattr(resp, "text", None) or ""
            if not text_out:
                try:
                    c = resp.candidates[0]
                    p = c.content.parts[0]
                    if hasattr(p, "text"):
                        text_out = p.text
                    else:
                        text_out = json.dumps(p)
                except Exception:
                    text_out = "{}"
            data = _parse_json_strict(text_out)
            if echo_prompt and isinstance(data, dict):
                data["prompt"] = prompt
            return data
        except Exception:
            return {"error": "gemini_call_failed"}
    elif provider == "siliconflow":
        client = _siliconflow_client()
        if client is None:
            return {"error": "siliconflow_unavailable"}
        model = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是医疗不良事件结构化剖析助手。仅输出有效JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            data = _parse_json_strict(content)
            if echo_prompt and isinstance(data, dict):
                data["prompt"] = prompt
            return data
        except Exception:
            out = {"error": "siliconflow_call_failed"}
            if echo_prompt:
                out["prompt"] = prompt
            return out
    else:
        return {"error": "provider_unsupported"}
def _parse_json_strict(s: str) -> Dict[str, Any]:
    if not s:
        return {"error": "empty_output"}
    try:
        return json.loads(s)
    except Exception:
        txt = s.strip()
        if txt.startswith("```") and txt.endswith("```"):
            txt = txt.strip("`")
            txt = txt.replace("json", "")
        i = txt.find("{")
        j = txt.rfind("}")
        if i != -1 and j != -1 and j >= i:
            cand = txt[i : j + 1]
            try:
                return json.loads(cand)
            except Exception:
                pass
    return {"error": "json_parse_failed"}