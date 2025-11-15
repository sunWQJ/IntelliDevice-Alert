from __future__ import annotations
from typing import Optional, List, Dict
from neo4j import GraphDatabase
import os
from pathlib import Path
import json
from .terminology import search as term_search

_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASS")
    if not uri or not user or not password:
        return None
    try:
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    except Exception:
        _driver = None
    return _driver


def write_report(out) -> None:
    drv = _get_driver()
    if drv is None:
        return
    with drv.session() as session:
        session.execute_write(_tx_write_report, out)


def _tx_write_report(tx, out) -> None:
    q = """
    MERGE (h:Hospital {id:$hospital_id})
    MERGE (d:Device {name:$device_name})
    MERGE (r:Report {id:$report_id})
    SET r.event_datetime=$event_datetime,
        r.injury_severity=$injury_severity,
        r.status=$status,
        r.processed_at=$processed_at,
        r.lot_sn=$lot_sn
    MERGE (r)-[:REPORTED_BY]->(h)
    MERGE (r)-[:RESULTS_IN]->(d)
    FOREACH (_ IN CASE WHEN $manufacturer IS NULL THEN [] ELSE [1] END |
        MERGE (m:Manufacturer {name:$manufacturer})
        MERGE (d)-[:MANUFACTURED_BY]->(m)
    )
    FOREACH (_ IN CASE WHEN $model IS NULL THEN [] ELSE [1] END |
        MERGE (md:Model {name:$model})
        MERGE (d)-[:HAS_MODEL]->(md)
    )
    FOREACH (_ IN CASE WHEN $event_datetime IS NULL THEN [] ELSE [1] END |
        MERGE (dt:EventDate {value:$event_datetime})
        MERGE (r)-[:AT_TIME]->(dt)
    )
    """
    tx.run(
        q,
        hospital_id=out.hospital_id,
        device_name=out.device_name,
        manufacturer=out.manufacturer,
        model=out.model,
        report_id=out.report_id,
        event_datetime=str(out.event_datetime),
        injury_severity=out.injury_severity,
        status=out.status,
        processed_at=str(out.processed_at),
        lot_sn=out.lot_sn,
    )


def write_structure(report_id: str, structure: Dict) -> Dict[str, int]:
    drv = _get_driver()
    if drv is None:
        return {"error": 1}
    ents = structure.get("entities") or []
    rels = structure.get("relations") or []
    mapped = {}
    with drv.session() as session:
        for e in ents:
            et = str(e.get("type", "")).lower()
            term = str(e.get("term", ""))
            code = e.get("code")
            label = _entity_label(et)
            if not label or not term:
                continue
            session.execute_write(_tx_upsert_entity, label, term, code)
            session.execute_write(_tx_link_report_entity, report_id, label, term)
            # 映射到标准术语
            cats = _map_categories(label)
            if cats:
                res = term_search(term, cats, top_k=1, threshold=0.4)
                cand = None
                for c in cats:
                    if res.get(c):
                        cand = res[c][0]
                        break
                if cand:
                    t, s = cand
                    session.execute_write(_tx_upsert_standard_term, t.code, t.term, t.definition, t.hierarchy, t.category)
                    session.execute_write(_tx_link_entity_standard, label, term, t.code)
            mapped.setdefault(label, set()).add(term)
        for r in rels:
            rt = str(r.get("type", "")).upper()
            fr = str(r.get("from", ""))
            to = str(r.get("to", ""))
            if rt == "CAUSES":
                session.execute_write(_tx_merge_rel, "FailureMode", fr, "Injury", to, "CAUSES")
            elif rt == "MITIGATES":
                session.execute_write(_tx_merge_rel, "Action", fr, "FailureMode", to, "MITIGATES")
            elif rt == "ASSOCIATED_WITH":
                # 默认设备-故障关联
                session.execute_write(_tx_merge_rel, "Device", fr, "FailureMode", to, "ASSOCIATED_WITH")
    return {"entities": sum(len(v) for v in mapped.values()), "relations": len(rels)}


def _entity_label(et: str) -> Optional[str]:
    if et in ("故障表现", "failure", "failuremode", "failure_mode"):
        return "FailureMode"
    if et in ("伤害表现", "injury"):
        return "Injury"
    if et in ("处置措施", "action"):
        return "Action"
    if et in ("器械名称", "device"):
        return "Device"
    return None


def _map_categories(label: str) -> List[str]:
    if label == "FailureMode":
        return ["A"]
    if label == "Injury":
        return ["E", "F"]
    if label == "Device":
        return ["G"]
    if label == "Action":
        return ["C", "D"]
    return []


def _tx_upsert_entity(tx, label: str, term: str, code: Optional[str]):
    q = f"MERGE (n:{label} {{name:$term}}) SET n.code=$code"
    tx.run(q, term=term, code=code)


def _tx_link_report_entity(tx, report_id: str, label: str, term: str):
    q = f"""
    MERGE (r:Report {{id:$rid}})
    MATCH (n:{label} {{name:$term}})
    MERGE (r)-[:HAS_{label.upper()}]->(n)
    """
    tx.run(q, rid=report_id, term=term)


def _tx_merge_rel(tx, l1: str, n1: str, l2: str, n2: str, rel: str):
    q = f"""
    MERGE (a:{l1} {{name:$n1}})
    MERGE (b:{l2} {{name:$n2}})
    MERGE (a)-[:{rel}]->(b)
    """
    tx.run(q, n1=n1, n2=n2)


def _tx_upsert_standard_term(tx, code: str, term: str, definition: str, hierarchy: str, category: str):
    q = """
    MERGE (t:StandardTerm {code:$code})
    SET t.termName=$term,
        t.definition=$definition,
        t.codeHierarchy=$hierarchy,
        t.category=$category
    """
    tx.run(q, code=code, term=term, definition=definition, hierarchy=hierarchy, category=category)


def _tx_link_entity_standard(tx, label: str, term: str, code: str):
    q = """
    MATCH (n:%s {name:$term})
    MATCH (t:StandardTerm {code:$code})
    MERGE (n)-[:MAPS_TO]->(t)
    """ % label
    tx.run(q, term=term, code=code)


def import_standard_terms(base_dir: Path, categories: List[str] | None = None, include_synonyms: bool = True) -> Dict[str, int]:
    drv = _get_driver()
    if drv is None:
        return {"error": 1}
    files = [f for f in base_dir.glob("*.json") if "别名" not in f.name]
    if categories:
        files = [f for f in files if f.name.split("：")[0].strip() in categories]
    count = 0
    with drv.session() as session:
        for f in files:
            cat = f.name.split("：")[0].strip()
            with f.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            for x in data:
                code = x.get("code", "")
                term = x.get("term", "")
                definition = x.get("definition", "")
                hierarchy = x.get("codehierarchy", "")
                session.execute_write(_tx_upsert_term, code, term, definition, hierarchy, cat)
                if hierarchy and "|" in hierarchy:
                    parts = hierarchy.split("|")
                    child = parts[-1]
                    if len(parts) >= 2:
                        parent = parts[-2]
                        session.execute_write(_tx_link_parent, child, parent)
                count += 1
        if include_synonyms:
            for syn_file in base_dir.glob("*别名*.json"):
                cat = syn_file.name.split("_")[0]
                with syn_file.open("r", encoding="utf-8") as fp:
                    syn = json.load(fp)
                for term_name, aliases in syn.items():
                    for alias in aliases:
                        session.execute_write(_tx_link_synonym, term_name, alias, cat)
    return {"imported": count}


def _tx_upsert_term(tx, code: str, term: str, definition: str, hierarchy: str, category: str):
    q = """
    MERGE (t:StandardTerm {code:$code})
    SET t.termName=$term,
        t.definition=$definition,
        t.codeHierarchy=$hierarchy,
        t.category=$category
    """
    tx.run(q, code=code, term=term, definition=definition, hierarchy=hierarchy, category=category)


def _tx_link_parent(tx, child_code: str, parent_code: str):
    q = """
    MATCH (c:StandardTerm {code:$child}), (p:StandardTerm {code:$parent})
    MERGE (c)-[:IS_SUBTERM_OF]->(p)
    """
    tx.run(q, child=child_code, parent=parent_code)


def _tx_link_synonym(tx, term_name: str, alias: str, category: str):
    q = """
    MERGE (t:StandardTerm {termName:$term_name, category:$category})
    MERGE (s:Synonym {name:$alias})
    MERGE (t)-[:HAS_SYNONYM]->(s)
    """
    tx.run(q, term_name=term_name, alias=alias, category=category)


def neighbors_by_code(code: str) -> Dict[str, List[Dict[str, str]]]:
    drv = _get_driver()
    if drv is None:
        return {"error": 1}
    with drv.session() as session:
        result = session.execute_read(_tx_neighbors, code)
    return result


def _tx_neighbors(tx, code: str):
    q = """
    MATCH (t:StandardTerm {code:$code})
    OPTIONAL MATCH (t)-[:IS_SUBTERM_OF]->(p:StandardTerm)
    OPTIONAL MATCH (c:StandardTerm)-[:IS_SUBTERM_OF]->(t)
    OPTIONAL MATCH (t)-[:HAS_SYNONYM]->(s:Synonym)
    RETURN t.code AS code, t.termName AS termName,
           collect(DISTINCT {code:p.code, termName:p.termName}) AS parents,
           collect(DISTINCT {code:c.code, termName:c.termName}) AS children,
           collect(DISTINCT {name:s.name}) AS synonyms
    """
    rec = tx.run(q, code=code).single()
    if not rec:
        return {"code": code, "parents": [], "children": [], "synonyms": []}
    return {
        "code": rec["code"],
        "termName": rec["termName"],
        "parents": [x for x in rec["parents"] if x.get("code")],
        "children": [x for x in rec["children"] if x.get("code")],
        "synonyms": [x for x in rec["synonyms"] if x.get("name")],
    }


def case_graph(report_id: str) -> Dict[str, List[Dict[str, str]]]:
    drv = _get_driver()
    if drv is None:
        return {"error": 1}
    with drv.session() as session:
        return session.execute_read(_tx_case_graph, report_id)


def _tx_case_graph(tx, rid: str):
    q = """
    MATCH (r:Report {id:$rid})
    OPTIONAL MATCH (r)-[:REPORTED_BY]->(h:Hospital)
    OPTIONAL MATCH (r)-[:RESULTS_IN]->(d:Device)
    OPTIONAL MATCH (r)-[:HAS_FAILUREMODE]->(fm:FailureMode)
    OPTIONAL MATCH (r)-[:HAS_INJURY]->(inj:Injury)
    OPTIONAL MATCH (r)-[:HAS_ACTION]->(act:Action)
    OPTIONAL MATCH (fm)-[:CAUSES]->(inj)
    OPTIONAL MATCH (fm)-[:MAPS_TO]->(stFM:StandardTerm)
    OPTIONAL MATCH (inj)-[:MAPS_TO]->(stINJ:StandardTerm)
    OPTIONAL MATCH (d)-[:MANUFACTURED_BY]->(man:Manufacturer)
    OPTIONAL MATCH (d)-[:HAS_MODEL]->(md:Model)
    OPTIONAL MATCH (r)-[:AT_TIME]->(dt:EventDate)
    RETURN r,h,d,man,md,dt,fm,inj,act,stFM,stINJ
    """
    res = tx.run(q, rid=rid).single()
    nodes = []
    edges = []
    if not res:
        return {"nodes": [], "edges": []}
    r = res["r"]
    nodes.append({"id": r["id"], "label": "Report", "name": r["id"]})
    if res["h"]:
        nodes.append({"id": res["h"]["id"], "label": "Hospital", "name": res["h"]["id"]})
        edges.append({"source": r["id"], "target": res["h"]["id"], "label": "REPORTED_BY"})
    if res["d"]:
        name = res["d"]["name"]
        nodes.append({"id": name, "label": "Device", "name": name})
        edges.append({"source": r["id"], "target": name, "label": "RESULTS_IN"})
    if res["man"]:
        nodes.append({"id": res["man"]["name"], "label": "Manufacturer", "name": res["man"]["name"]})
        edges.append({"source": res["d"]["name"], "target": res["man"]["name"], "label": "MANUFACTURED_BY"})
    if res["md"]:
        nodes.append({"id": res["md"]["name"], "label": "Model", "name": res["md"]["name"]})
        edges.append({"source": res["d"]["name"], "target": res["md"]["name"], "label": "HAS_MODEL"})
    if res["dt"]:
        nodes.append({"id": res["dt"]["value"], "label": "EventDate", "name": res["dt"]["value"]})
        edges.append({"source": r["id"], "target": res["dt"]["value"], "label": "AT_TIME"})
    if res["fm"]:
        nodes.append({"id": res["fm"]["name"], "label": "FailureMode", "name": res["fm"]["name"]})
        edges.append({"source": r["id"], "target": res["fm"]["name"], "label": "HAS_FAILUREMODE"})
    if res["inj"]:
        nodes.append({"id": res["inj"]["name"], "label": "Injury", "name": res["inj"]["name"]})
        edges.append({"source": r["id"], "target": res["inj"]["name"], "label": "HAS_INJURY"})
    if res["act"]:
        nodes.append({"id": res["act"]["name"], "label": "Action", "name": res["act"]["name"]})
        edges.append({"source": r["id"], "target": res["act"]["name"], "label": "HAS_ACTION"})
    if res["fm"] and res["inj"]:
        edges.append({"source": res["fm"]["name"], "target": res["inj"]["name"], "label": "CAUSES"})
    if res["stFM"]:
        code = res["stFM"]["code"]
        termName = res["stFM"].get("termName", "")
        name = f"{termName} [{code}]" if termName and code else (termName or code)
        nodes.append({
            "id": code,
            "label": "StandardTerm",
            "name": name,
            "code": code,
            "hierarchy": res["stFM"].get("codeHierarchy", ""),
            "definition": res["stFM"].get("definition", ""),
            "category": res["stFM"].get("category", "")
        })
        edges.append({"source": res["fm"]["name"], "target": code, "label": "MAPS_TO"})
    if res["stINJ"]:
        code = res["stINJ"]["code"]
        termName = res["stINJ"].get("termName", "")
        name = f"{termName} [{code}]"
        nodes.append({
            "id": code,
            "label": "StandardTerm",
            "name": name,
            "code": code,
            "hierarchy": res["stINJ"].get("codeHierarchy", ""),
            "definition": res["stINJ"].get("definition", ""),
            "category": res["stINJ"].get("category", "")
        })
        edges.append({"source": res["inj"]["name"], "target": code, "label": "MAPS_TO"})
    return {"nodes": nodes, "edges": edges}


def status() -> Dict[str, str]:
    drv = _get_driver()
    if drv is None:
        return {"ok": "false", "reason": "no_config_or_connect_fail"}
    try:
        with drv.session() as session:
            session.run("RETURN 1")
        return {"ok": "true"}
    except Exception as e:
        return {"ok": "false", "reason": str(e)}