from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
import json

from .config import terminology_dir
from .synonyms import ALIASES
import numpy as np
try:
    import jieba
except Exception:
    jieba = None


@dataclass
class Term:
    code: str
    term: str
    definition: str
    category: str
    hierarchy: str = ""


_TERMS: Dict[str, List[Term]] = {}
_EXT_ALIASES: Dict[str, Dict[str, List[str]]] = {}
_VOCABS: Dict[str, Dict[str, int]] = {}
_IDF: Dict[str, np.ndarray] = {}
_TERM_VECS: Dict[str, np.ndarray] = {}


def _bigrams(s: str) -> List[str]:
    s = s.strip()
    if len(s) < 2:
        return [s] if s else []
    return [s[i : i + 2] for i in range(len(s) - 1)]


def _tokens(s: str) -> List[str]:
    s = s.strip()
    if not s:
        return []
    if jieba is None:
        return [s]
    toks = [t for t in jieba.lcut(s) if len(t) >= 2]
    return toks


def _score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    A2 = set(_tokens(a))
    B2 = set(_tokens(b))
    inter2 = len(A2 & B2)
    union2 = len(A2 | B2)
    j2 = (inter2 / union2) if union2 else 0.0
    A = set(_bigrams(a))
    B = set(_bigrams(b))
    inter = len(A & B)
    union = len(A | B)
    j = inter / union if union else 0.0
    return max(j2 * 0.8 + j * 0.2, j)


def _normalize_text(s: str) -> str:
    return (
        s.replace("，", ",")
        .replace("。", ".")
        .replace("/", " /")
        .replace("、", " ")
        .strip()
        .lower()
    )


def load() -> None:
    base = terminology_dir()
    if not base:
        return
    _load_aliases(base)
    files = [f for f in base.glob("*.json") if "别名" not in f.name]
    for f in files:
        category = f.name.split("：")[0].strip()
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        items: List[Term] = []
        for x in data:
            items.append(
                Term(
                    code=x.get("code", ""),
                    term=x.get("term", ""),
                    definition=x.get("definition", ""),
                    category=category,
                    hierarchy=x.get("codehierarchy", ""),
                )
            )
        _TERMS[category] = items
    for c, items in _TERMS.items():
        _build_vectors(c, items)


def _aliases_for(category: str, term: str) -> List[str]:
    term_norm = term.replace("/", " ").replace("、", " ").strip()
    base_alias = [x.strip() for x in term_norm.split() if x.strip()]
    extra = _EXT_ALIASES.get(category, {}).get(term, []) or ALIASES.get(category, {}).get(term, [])
    return list({*(base_alias), *extra})


def search(text: str, categories: List[str], top_k: int = 5, threshold: float = 0.3) -> Dict[str, List[Tuple[Term, float]]]:
    res: Dict[str, List[Tuple[Term, float]]] = {}
    text_n = _normalize_text(text)
    for c in categories:
        items = _TERMS.get(c, [])
        scored: List[Tuple[Term, float]] = []
        s_vecs: List[float] = []
        if c in _TERM_VECS and c in _VOCABS and c in _IDF:
            v = _text_vector(text_n, _VOCABS[c], _IDF[c])
            if v is not None and _TERM_VECS[c].size:
                sims = _TERM_VECS[c].dot(v)
                s_vecs = sims.tolist()
        for idx, t in enumerate(items):
            s_base = _score(text_n, _normalize_text(t.term))
            aliases = _aliases_for(c, t.term)
            s_alias = 0.0
            for a in aliases:
                a_n = _normalize_text(a)
                if a_n and a_n in text_n:
                    s_alias = max(s_alias, 0.9)
                else:
                    s_alias = max(s_alias, _score(text_n, a_n))
            s_vec = s_vecs[idx] if idx < len(s_vecs) else 0.0
            s = max(s_base, s_alias, s_vec)
            # 轻微加权：若别名命中则提高权重
            if s_alias >= 0.9:
                s = min(1.0, s + 0.1)
            scored.append((t, s))
        scored = [x for x in scored if x[1] >= threshold]
        scored.sort(key=lambda x: x[1], reverse=True)
        res[c] = scored[:top_k]
    return res


def available_categories() -> List[str]:
    return list(_TERMS.keys())


def _load_aliases(base: Path) -> None:
    global _EXT_ALIASES
    _EXT_ALIASES = {}
    for f in base.glob("*别名*.json"):
        name = f.name
        if "E" in name:
            cat = "E"
        elif "F" in name:
            cat = "F"
        elif "G" in name:
            cat = "G"
        elif "A" in name:
            cat = "A"
        else:
            continue
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        _EXT_ALIASES[cat] = data


def _build_vectors(category: str, items: List[Term]) -> None:
    toks_docs: List[List[str]] = []
    for t in items:
        toks = _tokens(_normalize_text(t.term))
        for a in _aliases_for(category, t.term):
            toks += _tokens(_normalize_text(a))
        toks_docs.append(list({*toks}))
    vocab: Dict[str, int] = {}
    for toks in toks_docs:
        for tok in toks:
            if tok not in vocab:
                vocab[tok] = len(vocab)
    if not vocab:
        _VOCABS[category] = {}
        _IDF[category] = np.array([])
        _TERM_VECS[category] = np.array([])
        return
    N = len(toks_docs)
    df = np.zeros(len(vocab))
    for toks in toks_docs:
        for tok in set(toks):
            df[vocab[tok]] += 1
    idf = np.log((N + 1) / (df + 1)) + 1.0
    mat = np.zeros((N, len(vocab)))
    for i, toks in enumerate(toks_docs):
        for tok in toks:
            mat[i, vocab[tok]] += 1
        mat[i] = mat[i] * idf
        n = np.linalg.norm(mat[i])
        if n > 0:
            mat[i] = mat[i] / n
    _VOCABS[category] = vocab
    _IDF[category] = idf
    _TERM_VECS[category] = mat


def _text_vector(text: str, vocab: Dict[str, int], idf: np.ndarray):
    toks = _tokens(text)
    if not toks:
        return None
    v = np.zeros(len(vocab))
    for tok in toks:
        if tok in vocab:
            v[vocab[tok]] += 1
    v = v * idf
    n = np.linalg.norm(v)
    if n > 0:
        v = v / n
    return v