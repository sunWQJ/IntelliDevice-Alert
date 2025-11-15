from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi import Body, Query, UploadFile, File
from uuid import uuid4
from .schemas import ReportIn, ReportOut, ReportStored
from .services.deidentify import remove_pii
from .services.cleaning import fingerprint
from .services.severity import classify as classify_severity, classify_with_evidence
from .storage import upsert_report, by_id, find_by_fingerprint, now
from . import audit
from .terminology import load as load_terms, search as term_search, available_categories
from typing import List, Optional
from openpyxl import load_workbook
from openpyxl import Workbook
from io import BytesIO
from . import graph
from .db import init_db
from .llm import llm_standardize, llm_structure
from fastapi.staticfiles import StaticFiles
from .services.risk_analysis import analyze_risks_in_graph
from .services.structure_analyzer import analyze_report_structure


app = FastAPI(title="IntelliDevice-Alert API", version="0.1.0")
init_db()
load_terms()
from pathlib import Path
_static = str((Path(__file__).resolve().parents[1] / "static").resolve())
app.mount("/ui", StaticFiles(directory=_static, html=True), name="static")


def _process_incoming(payload: ReportIn) -> ReportOut:
    clean = payload.dict()
    fp = fingerprint(clean)
    dup_id = find_by_fingerprint(fp)
    report_id = str(uuid4()) if not dup_id else dup_id
    sanitized = remove_pii(clean)
    sev = sanitized.get("injury_severity") or "none"
    if not sev or sev == "none":
        lvl, ev = classify_with_evidence(sanitized.get("event_description", ""))
        sev = lvl
        try:
            import json
            audit.write(report_id, "severity_evidence", json.dumps({"level": lvl, "evidence": ev}, ensure_ascii=False))
        except Exception:
            pass
    # ensure no duplicate kw when building model
    if "injury_severity" in sanitized:
        sanitized.pop("injury_severity")
    stored = ReportStored(
        report_id=report_id,
        processed_at=now(),
        status="duplicate" if dup_id else "received",
        fingerprint=fp,
        source_version="v0",
        injury_severity=sev,
        **sanitized,
    )
    out = upsert_report(stored)
    audit.write(report_id, "received", f"status={out.status}")
    graph.write_report(out)
    return out


@app.post("/reports", response_model=ReportOut)
def create_report(
    payload: ReportIn = Body(...),
    standardize: bool = Query(False),
    categories: Optional[List[str]] = Query(None),
    top_k: int = Query(5),
    threshold: float = Query(0.3),
) -> ReportOut:
    out = _process_incoming(payload)
    if standardize:
        cats = categories or ["A", "E", "F", "G"]
        text = out.event_description
        res = term_search(text, cats, top_k=top_k, threshold=threshold)
        total = sum(len(v) for v in res.values())
        audit.write(out.report_id, "standardized", str(total))
    return out


@app.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: str) -> ReportOut:
    found = by_id(report_id)
    if not found:
        raise HTTPException(status_code=404, detail="Report not found")
    return found


@app.get("/reports/{report_id}/audit")
def get_report_audit(report_id: str):
    logs = audit.for_report(report_id)
    return [
        {
            "id": l.id,
            "created_at": l.created_at.isoformat(),
            "event": l.event,
            "detail": l.detail,
        }
        for l in logs
    ]


@app.post("/standardize")
def standardize(payload: dict = Body(...)):
    text = str(payload.get("text", "")).strip()
    cats = payload.get("categories") or available_categories()
    top_k = int(payload.get("top_k", 5))
    threshold = float(payload.get("threshold", 0.3))
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    res = term_search(text, cats, top_k=top_k, threshold=threshold)
    out = {}
    for c, items in res.items():
        out[c] = [
            {
                "code": t.code,
                "term": t.term,
                "definition": t.definition,
                "category": t.category,
                "score": s,
            }
            for t, s in items
        ]
    return {"text": text, "results": out}


@app.post("/classify/severity")
def classify_severity_endpoint(payload: dict = Body(...)):
    text = str(payload.get("text", ""))
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    lvl, ev = classify_with_evidence(text)
    return {"injury_severity": lvl, "evidence": ev}


@app.post("/analyze/failure")
def analyze_failure(payload: dict = Body(...)):
    text = str(payload.get("text", "")).strip()
    cats = payload.get("categories") or ["A", "E", "F"]
    top_k = int(payload.get("top_k", 5))
    threshold = float(payload.get("threshold", 0.3))
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    res = term_search(text, cats, top_k=top_k, threshold=threshold)
    injuries = []
    for c in ("E", "F"):
        for t, s in res.get(c, []):
            injuries.append(t.term)
    lvl, ev = classify_with_evidence(text + " " + " ".join(injuries))
    out = {}
    for c, items in res.items():
        out[c] = [
            {
                "code": t.code,
                "term": t.term,
                "definition": t.definition,
                "category": t.category,
                "score": s,
            }
            for t, s in items
        ]
    return {"text": text, "severity": lvl, "evidence": ev, "matches": out}


@app.post("/reports/structured")
def create_structured_report(payload: dict = Body(...)):
    init_db()
    base = {
        "hospital_id": payload.get("hospital_id"),
        "device_name": payload.get("device_name"),
        "manufacturer": payload.get("manufacturer"),
        "model": payload.get("model"),
        "lot_sn": payload.get("lot_sn"),
        "event_datetime": payload.get("event_datetime"),
        "event_description": payload.get("event_description", ""),
        "action_taken": payload.get("action_taken"),
    }
    failure_desc = str(payload.get("failure_desc", ""))
    injury_desc = str(payload.get("injury_desc", ""))
    action_desc = str(payload.get("action_desc", ""))

    out = _process_incoming(ReportIn(**base))
    cats_map = {
        "FailureMode": ["A"],
        "Injury": ["E", "F"],
        "Action": ["C", "D"],
    }
    matches = {}
    if failure_desc:
        res = term_search(failure_desc, cats_map["FailureMode"], top_k=1, threshold=0.3)
        m = None
        for c in cats_map["FailureMode"]:
            if res.get(c):
                m = res[c][0]
                break
        if m:
            t, s = m
            matches["FailureMode"] = {"code": t.code, "term": t.term, "definition": t.definition, "category": t.category}
    if injury_desc:
        res = term_search(injury_desc, cats_map["Injury"], top_k=1, threshold=0.3)
        m = None
        for c in cats_map["Injury"]:
            if res.get(c):
                m = res[c][0]
                break
        if m:
            t, s = m
            matches["Injury"] = {"code": t.code, "term": t.term, "definition": t.definition, "category": t.category}
            lvl, ev = classify_with_evidence(injury_desc)
            try:
                import json
                audit.write(out.report_id, "severity_evidence", json.dumps({"level": lvl, "evidence": ev}, ensure_ascii=False))
            except Exception:
                pass
    if action_desc:
        res = term_search(action_desc, cats_map["Action"], top_k=1, threshold=0.3)
        m = None
        for c in cats_map["Action"]:
            if res.get(c):
                m = res[c][0]
                break
        if m:
            t, s = m
            matches["Action"] = {"code": t.code, "term": t.term, "definition": t.definition, "category": t.category}

    # store entities in DB
    from .db import SessionLocal
    from .models import ReportEntity
    try:
        with SessionLocal() as db_sess:
            for et, m in matches.items():
                db_sess.add(ReportEntity(report_id=out.report_id, entity_type=et, code=m.get("code"), term=m.get("term"), definition=m.get("definition"), category=m.get("category")))
            db_sess.commit()
    except Exception:
        pass

    # write to graph
    structure = {"entities": [], "relations": []}
    for et, m in matches.items():
        structure["entities"].append({"type": et, "code": m.get("code"), "term": m.get("term")})
    if matches.get("FailureMode") and matches.get("Injury"):
        structure["relations"].append({"type": "CAUSES", "from": matches["FailureMode"]["term"], "to": matches["Injury"]["term"]})
    graph.write_structure(out.report_id, structure)
    return {"report": out, "matches": matches}


@app.get("/reports/{report_id}/standardized")
def standardized_for_report(report_id: str, categories: Optional[List[str]] = None, top_k: int = 5, threshold: float = 0.3):
    found = by_id(report_id)
    if not found:
        raise HTTPException(status_code=404, detail="Report not found")
    cats = categories or ["A", "E", "F", "G"]
    text = found.event_description
    res = term_search(text, cats, top_k=top_k, threshold=threshold)
    out = {}
    for c, items in res.items():
        out[c] = [
            {
                "code": t.code,
                "term": t.term,
                "definition": t.definition,
                "category": t.category,
                "score": s,
            }
            for t, s in items
        ]
    return {"report_id": report_id, "text": text, "results": out}


@app.post("/llm/standardize")
def llm_standardize_endpoint(payload: dict = Body(...)):
    provider = str(payload.get("provider", "openai"))
    text = str(payload.get("text", ""))
    categories = payload.get("categories")
    top_k = int(payload.get("top_k", 5))
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    data = llm_standardize(provider, text, categories, top_k)
    if "error" in data:
        raise HTTPException(status_code=503, detail=data["error"])
    return data


@app.post("/llm/structure")
def llm_structure_endpoint(payload: dict = Body(...)):
    provider = str(payload.get("provider", "openai"))
    text = str(payload.get("text", ""))
    top_k = int(payload.get("top_k", 5))
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    data = llm_structure(provider, text, top_k)
    if "error" in data:
        raise HTTPException(status_code=503, detail=data["error"])
    return data


@app.post("/llm/structure/store")
def llm_structure_store(payload: dict = Body(...)):
    provider = str(payload.get("provider", "openai"))
    text = str(payload.get("text", ""))
    report_id = str(payload.get("report_id", ""))
    top_k = int(payload.get("top_k", 5))
    if not text or not report_id:
        raise HTTPException(status_code=400, detail="text and report_id required")
    data = llm_structure(provider, text, top_k)
    if "error" in data:
        raise HTTPException(status_code=503, detail=data["error"])
    out = graph.write_structure(report_id, data)
    if "error" in out:
        raise HTTPException(status_code=503, detail="neo4j_unavailable")
    return {"stored": out, "structure": data}


@app.post("/config/llm")
def set_llm_config(payload: dict = Body(...)):
    import os
    provider = str(payload.get("provider", "")).lower()
    api_key = str(payload.get("api_key", ""))
    model = str(payload.get("model", ""))
    if provider == "openai":
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        if model:
            os.environ["OPENAI_MODEL"] = model
        return {"ok": True, "provider": "openai"}
    elif provider == "gemini":
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
        if model:
            os.environ["GEMINI_MODEL"] = model
        return {"ok": True, "provider": "gemini"}
    else:
        raise HTTPException(status_code=400, detail="unsupported provider")


@app.post("/config/neo4j")
def set_neo4j_config(payload: dict = Body(...)):
    import os
    uri = str(payload.get("uri", ""))
    user = str(payload.get("user", ""))
    password = str(payload.get("password", ""))
    if uri:
        os.environ["NEO4J_URI"] = uri
    if user:
        os.environ["NEO4J_USER"] = user
    if password:
        os.environ["NEO4J_PASS"] = password
    return {"ok": True}


@app.get("/dashboard/summary")
def dashboard_summary():
    from .db import SessionLocal
    from .models import ReportModel
    import collections
    with SessionLocal() as db:
        q = db.query(ReportModel).order_by(ReportModel.processed_at.desc()).limit(100)
        rows = q.all()
    total = len(rows)
    top_devices = collections.Counter([r.device_name for r in rows]).most_common(5)
    top_severity = collections.Counter([r.injury_severity for r in rows]).most_common(5)
    recent = [
        {
            "report_id": r.report_id,
            "hospital_id": r.hospital_id,
            "device_name": r.device_name,
            "injury_severity": r.injury_severity,
            "event_datetime": r.event_datetime,
        }
        for r in rows[:10]
    ]
    return {"total": total, "top_devices": top_devices, "top_severity": top_severity, "recent": recent}


@app.get("/case/{report_id}/graph")
def case_graph(report_id: str):
    r = by_id(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    # 尝试从 Neo4j 读取扩展关系
    g = graph.case_graph(report_id)
    if "error" in g:
        # 回退到DB构建视图（包含故障/伤害/处置、制造商/型号/事件日期）
        nodes = {
            r.report_id: {"id": r.report_id, "label": "Report", "name": r.report_id},
            r.hospital_id: {"id": r.hospital_id, "label": "Hospital", "name": r.hospital_id},
            r.device_name: {"id": r.device_name, "label": "Device", "name": r.device_name},
        }
        edges = set()
        edges.add((r.report_id, r.hospital_id, "REPORTED_BY"))
        edges.add((r.report_id, r.device_name, "RESULTS_IN"))
        if r.manufacturer:
            nodes[r.manufacturer] = {"id": r.manufacturer, "label": "Manufacturer", "name": r.manufacturer}
            edges.add((r.device_name, r.manufacturer, "MANUFACTURED_BY"))
        if r.model:
            nodes[r.model] = {"id": r.model, "label": "Model", "name": r.model}
            edges.add((r.device_name, r.model, "HAS_MODEL"))
        if r.event_datetime:
            dt = r.event_datetime.isoformat()
            nodes[dt] = {"id": dt, "label": "EventDate", "name": dt}
            edges.add((r.report_id, dt, "AT_TIME"))
        # 从 report_entities 读取术语映射
        from .db import SessionLocal
        from .models import ReportEntity
        with SessionLocal() as db_sess:
            ents = db_sess.query(ReportEntity).filter(ReportEntity.report_id == report_id).all()
        for e in ents:
            nid = e.term
            nodes[nid] = {"id": nid, "label": e.entity_type, "name": e.term, "code": e.code, "definition": e.definition, "category": e.category}
            edges.add((r.report_id, nid, f"HAS_{e.entity_type.upper()}"))
        # 若存在故障与伤害，补充CAUSES关系
        fm = [e for e in ents if e.entity_type == "FailureMode"]
        inj = [e for e in ents if e.entity_type == "Injury"]
        if fm and inj:
            edges.add((fm[0].term, inj[0].term, "CAUSES"))
        return {"nodes": list(nodes.values()), "edges": [{"source": s, "target": t, "label": l} for (s, t, l) in edges]}
    return g


@app.get("/case/recent-graph")
def case_recent_graph(limit: int = 10):
    from .db import SessionLocal
    from .models import ReportModel
    with SessionLocal() as db:
        rows = db.query(ReportModel).order_by(ReportModel.processed_at.desc()).limit(limit).all()
    nodes_map = {}
    edges_set = set()
    from .models import ReportEntity
    for r in rows:
        g = graph.case_graph(r.report_id)
        if "error" in g:
            nodes_map[r.report_id] = {"id": r.report_id, "label": "AdverseEventReport", "name": r.report_id, "severity": r.injury_severity}
            nodes_map[r.hospital_id] = {"id": r.hospital_id, "label": "Hospital", "name": r.hospital_id}
            nodes_map[r.device_name] = {"id": r.device_name, "label": "MedicalDevice", "name": r.device_name}
            edges_set.add((r.device_name, r.report_id, "RELATED_TO"))
            edges_set.add((r.report_id, r.hospital_id, "REPORTED_BY"))
            if r.manufacturer:
                nodes_map[r.manufacturer] = {"id": r.manufacturer, "label": "Manufacturer", "name": r.manufacturer}
                edges_set.add((r.device_name, r.manufacturer, "MANUFACTURED_BY"))
            if r.model:
                nodes_map[r.model] = {"id": r.model, "label": "Model", "name": r.model}
                edges_set.add((r.device_name, r.model, "HAS_MODEL"))
            if r.event_datetime:
                try:
                    dt = r.event_datetime.isoformat()
                    nodes_map[dt] = {"id": dt, "label": "DiscoveryDate", "name": dt}
                    edges_set.add((r.report_id, dt, "AT_TIME"))
                except Exception:
                    # 如果时间格式有问题，使用字符串形式
                    dt = str(r.event_datetime)
                    nodes_map[dt] = {"id": dt, "label": "DiscoveryDate", "name": dt}
                    edges_set.add((r.report_id, dt, "AT_TIME"))
            with SessionLocal() as db_sess:
                ents = db_sess.query(ReportEntity).filter(ReportEntity.report_id == r.report_id).all()
            fault = None
            harm = None
            measure = None
            for e in ents:
                nid = f"{e.term}:{e.entity_type}:{r.report_id}"
                if e.entity_type == "FailureMode":
                    nodes_map[nid] = {"id": nid, "label": "Fault", "name": e.term, "code": e.code, "severity": "moderate"}
                    edges_set.add((r.device_name, nid, "HAS_FAULT"))
                    fault = nid
                elif e.entity_type == "Injury":
                    nodes_map[nid] = {"id": nid, "label": "Harm", "name": e.term, "code": e.code, "severity": "moderate"}
                    edges_set.add((r.report_id, nid, "CAUSES"))
                    harm = nid
                elif e.entity_type == "Action":
                    nodes_map[nid] = {"id": nid, "label": "Measure", "name": e.term, "code": e.code, "severity": "low"}
                    measure = nid
            if fault and harm:
                edges_set.add((fault, harm, "RESULTS_IN"))
            if fault and measure:
                edges_set.add((fault, measure, "ADDRESSED_BY"))
        else:
            for n in g.get("nodes", []):
                nodes_map[n.get("id")] = n
            for e in g.get("edges", []):
                edges_set.add((e.get("source"), e.get("target"), e.get("label")))
    nodes = list(nodes_map.values())
    edges = [{"source": s, "target": t, "label": l} for (s, t, l) in edges_set]
    return {"nodes": nodes, "edges": edges}


@app.post("/reports/analyze-structure")
def analyze_report_structure_endpoint(payload: dict = Body(...)):
    """分析报告结构并提取关键信息"""
    try:
        # 验证必要字段
        required_fields = ["event_description"]
        for field in required_fields:
            if not payload.get(field):
                return {
                    "success": False,
                    "error": f"缺少必要字段：{field}"
                }
        
        # 调用结构化分析
        result = analyze_report_structure(payload)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"分析失败：{str(e)}"
        }


@app.post("/reports/structured-confirm")
def confirm_structured_report(payload: dict = Body(...)):
    """确认结构化数据并录入系统"""
    try:
        # 首先进行结构化分析
        structure_result = analyze_report_structure(payload)
        
        # 创建标准报告
        base_report = {
            "hospital_id": payload.get("hospital_id"),
            "device_name": payload.get("device_name"),
            "manufacturer": payload.get("manufacturer"),
            "model": payload.get("model"),
            "lot_sn": payload.get("lot_sn"),
            "event_datetime": payload.get("event_datetime"),
            "event_description": payload.get("event_description"),
            "injury_severity": payload.get("injury_severity", "none"),
            "action_taken": payload.get("action_taken"),
        }
        
        # 处理报告
        report_out = _process_incoming(ReportIn(**base_report))
        
        # 存储结构化实体
        from .db import SessionLocal
        from .models import ReportEntity
        
        try:
            with SessionLocal() as db_sess:
                # 存储匹配的标准术语
                for term_info in structure_result.get("matched_terms", []):
                    db_sess.add(ReportEntity(
                        report_id=report_out.report_id,
                        entity_type=term_info["field"].upper(),
                        code=term_info["code"],
                        term=term_info["term"],
                        definition="",  # 可以从术语库获取
                        category=term_info["category"]
                    ))
                
                # 存储结构化分析结果
                db_sess.add(ReportEntity(
                    report_id=report_out.report_id,
                    entity_type="STRUCTURE_ANALYSIS",
                    code="ANALYSIS",
                    term="结构化分析结果",
                    definition=str(structure_result),
                    category="ANALYSIS"
                ))
                
                db_sess.commit()
        except Exception as e:
            print(f"存储结构化实体失败：{e}")
        
        # 构建图结构
        structure = {
            "entities": [],
            "relations": []
        }
        
        # 添加实体
        for term_info in structure_result.get("matched_terms", []):
            structure["entities"].append({
                "type": term_info["field"].upper(),
                "code": term_info["code"],
                "term": term_info["term"]
            })
        
        # 添加关系
        failure_modes = [t for t in structure_result.get("matched_terms", []) if t["field"] == "failure_mode"]
        injuries = [t for t in structure_result.get("matched_terms", []) if t["field"] == "health_impact"]
        actions = [t for t in structure_result.get("matched_terms", []) if t["field"] == "treatment_action"]
        
        if failure_modes and injuries:
            structure["relations"].append({
                "type": "CAUSES",
                "from": failure_modes[0]["term"],
                "to": injuries[0]["term"]
            })
        
        if injuries and actions:
            structure["relations"].append({
                "type": "ADDRESSED_BY",
                "from": injuries[0]["term"],
                "to": actions[0]["term"]
            })
        
        # 写入图数据库
        graph.write_structure(report_out.report_id, structure)
        
        # 记录审计日志
        import json
        audit.write(report_out.report_id, "structured_confirmed", json.dumps({
            "confidence": structure_result.get("analysis_confidence", 0),
            "matched_terms_count": len(structure_result.get("matched_terms", [])),
            "device_issue": structure_result.get("device_issue"),
            "failure_mode": structure_result.get("failure_mode"),
            "clinical_manifestation": structure_result.get("clinical_manifestation"),
            "health_impact": structure_result.get("health_impact"),
            "treatment_action": structure_result.get("treatment_action")
        }, ensure_ascii=False))
        
        return {
            "success": True,
            "data": {
                "report": report_out,
                "structure": structure_result,
                "entities_stored": len(structure_result.get("matched_terms", [])),
                "confidence": structure_result.get("analysis_confidence", 0)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"确认录入失败：{str(e)}"
        }


@app.post("/llm/restructure")
def restructure_with_llm(payload: dict = Body(...)):
    """使用LLM重新构建和优化报告内容"""
    try:
        provider = payload.get("provider", "openai")
        
        # 构建提示词
        prompt = f"""
        请根据以下医疗事件报告信息，重新组织和优化描述，使其更清晰、准确：
        
        设备名称：{payload.get('device_name', '')}
        事件描述：{payload.get('event_description', '')}
        处理措施：{payload.get('action_taken', '')}
        
        要求：
        1. 保持医疗专业性和准确性
        2. 突出关键信息（设备问题、患者影响、处置措施）
        3. 使用标准医疗术语
        4. 语言简洁明了
        
        请返回优化后的JSON格式数据，包含：device_name, event_description, action_taken
        """
        
        # 调用LLM服务
        from .llm import llm_standardize
        
        llm_result = llm_standardize(
            text=prompt,
            provider=provider,
            categories=[],
            top_k=1
        )
        
        # 解析LLM响应
        if llm_result and "results" in llm_result:
            # 提取优化后的内容
            optimized_content = llm_result["results"]
            
            return {
                "success": True,
                "data": {
                    "device_name": payload.get("device_name"),  # 保持原设备名称
                    "event_description": optimized_content.get("event_description", payload.get("event_description")),
                    "action_taken": optimized_content.get("action_taken", payload.get("action_taken"))
                }
            }
        else:
            return {
                "success": False,
                "error": "LLM处理失败"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"LLM重构失败：{str(e)}"
        }


@app.post("/graph/risk-analysis")
def graph_risk_analysis(payload: dict = Body(...)):
    """分析图数据中的风险点"""
    try:
        # 获取图数据
        limit = payload.get("limit", 50)
        graph_data = case_recent_graph(limit=limit)
        
        # 分析风险点
        risk_results = analyze_risks_in_graph(graph_data)
        
        return {
            "success": True,
            "data": risk_results,
            "graph_summary": {
                "total_nodes": len(graph_data.get("nodes", [])),
                "total_edges": len(graph_data.get("edges", [])),
                "analysis_limit": limit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "total_risks": 0,
                "high_risks": 0,
                "medium_risks": 0,
                "low_risks": 0,
                "risk_details": []
            }
        }


@app.get("/evaluate/terms")
def evaluate_terms(file_path: str = "IMDRF测试集.json", category: str = "E", top_k: int = 5, threshold: float = 0.0):
    import json
    from pathlib import Path
    p = Path(file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="dataset not found")
    with p.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    samples = [
        {"text": x.get("伤害描述", ""), "code": x.get("正确IMDRF编码", ""), "term": x.get("术语", "")}
        for x in data
    ]
    k_list = [1, 3, top_k]
    correct = {k: 0 for k in k_list}
    mrr_sum = 0.0
    mismatches = []
    for s in samples:
        res = term_search(s["text"], [category], top_k=top_k, threshold=threshold).get(category, [])
        codes = [t.code for (t, sc) in res]
        terms = [t.term for (t, sc) in res]
        gold_code = s["code"].strip()
        gold_term = s["term"].strip()
        rank = None
        for i, (c, tm) in enumerate(zip(codes, terms), start=1):
            if c == gold_code or tm == gold_term:
                rank = i
                break
        for k in k_list:
            if rank is not None and rank <= k:
                correct[k] += 1
        if rank is not None:
            mrr_sum += 1.0 / rank
        else:
            mismatches.append({
                "text": s["text"],
                "gold_code": gold_code,
                "gold_term": gold_term,
                "pred_top1": {"code": codes[0] if codes else None, "term": terms[0] if terms else None}
            })
    total = len(samples)
    return {
        "samples": total,
        "hit@1": correct[1] / total,
        "hit@3": correct[3] / total,
        "hit@k": correct[top_k] / total,
        "mrr": mrr_sum / total,
        "mismatches": mismatches[:50]
    }


@app.post("/graph/import-terms")
def graph_import_terms(payload: dict = Body(...)):
    from .config import terminology_dir
    base = terminology_dir()
    if not base:
        raise HTTPException(status_code=404, detail="terminology dir not found")
    cats = payload.get("categories")
    include_syn = bool(payload.get("include_synonyms", True))
    out = graph.import_standard_terms(base, categories=cats, include_synonyms=include_syn)
    if "error" in out:
        raise HTTPException(status_code=503, detail="neo4j_unavailable")
    return out


@app.get("/graph/term/{code}/neighbors")
def graph_term_neighbors(code: str):
    out = graph.neighbors_by_code(code)
    if "error" in out:
        raise HTTPException(status_code=503, detail="neo4j_unavailable")
    return out


@app.get("/graph/status")
def graph_status():
    return graph.status()
@app.post("/reports/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    content = await file.read()
    wb = load_workbook(filename=BytesIO(content), read_only=True)
    ws = wb.active
    headers_raw = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    zh_map = {
        "医院编号": "hospital_id",
        "器械名称": "device_name",
        "制造商": "manufacturer",
        "型号": "model",
        "批次或序列号": "lot_sn",
        "事件时间": "event_datetime",
        "事件描述": "event_description",
        "伤害严重度": "injury_severity",
        "处置措施": "action_taken",
    }
    headers = [zh_map.get(h, h) for h in headers_raw]
    results = {"received": 0, "duplicate": 0, "failed": 0}
    ids: List[str] = []
    for row in ws.iter_rows(min_row=2):
        data = {}
        for i, cell in enumerate(row):
            key = headers[i] if i < len(headers) else ""
            if not key:
                continue
            val = cell.value
            if key == "injury_severity" and isinstance(val, str):
                val = val.strip().lower()
            data[key] = val
        try:
            payload = ReportIn(**data)
            out = _process_incoming(payload)
            results[out.status] += 1
            ids.append(out.report_id)
        except Exception:
            results["failed"] += 1
    return {"summary": results, "report_ids": ids}


@app.get("/templates/reports.xlsx")
def reports_template(lang: str = "zh"):
    wb = Workbook()
    ws = wb.active
    if lang == "zh":
        headers = [
            "医院编号",
            "器械名称",
            "制造商",
            "型号",
            "批次或序列号",
            "事件时间",
            "事件描述",
            "伤害严重度",
            "处置措施",
        ]
        ws.append(headers)
        ws.append([
            "H001",
            "心电监护仪",
            "ACME",
            "ECG-200",
            "L123",
            "2025-01-01T10:20:30Z",
            "设备屏幕无显示，患者监护中断",
            "moderate",
            "更换设备并加护观察",
        ])
    else:
        headers = [
            "hospital_id",
            "device_name",
            "manufacturer",
            "model",
            "lot_sn",
            "event_datetime",
            "event_description",
            "injury_severity",
            "action_taken",
        ]
        ws.append(headers)
        ws.append([
            "H001",
            "ECG Monitor",
            "ACME",
            "ECG-200",
            "L123",
            "2025-01-01T10:20:30Z",
            "Screen blank during monitoring",
            "moderate",
            "Replace device and ICU observation",
        ])
    import tempfile, os
    from fastapi.responses import FileResponse
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    fname = "MDAE模板.xlsx" if lang == "zh" else "MDAE_template.xlsx"
    return FileResponse(path=tmp.name, filename=fname, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")