from __future__ import annotations


DEATH = {
    "死亡", "死", "无生命体征", "心跳停止", "呼吸停止", "去世"
}

SEVERE = {
    "危重", "重度", "休克", "呼吸衰竭", "心衰", "昏迷", "骨折", "脊髓损伤", "窒息", "截瘫"
}

MODERATE = {
    "中度", "住院", "手术", "严重不适", "加护", "监护", "输血", "明显疼痛"
}

MILD = {
    "轻度", "轻微", "皮肤红肿", "轻度疼痛", "短暂不适", "轻度不适"
}

NONE = {
    "无伤害", "未造成伤害", "未受影响", "无不适"
}


def classify(text: str) -> str:
    t = (text or "").lower()
    for kw in DEATH:
        if kw in t:
            return "death"
    for kw in SEVERE:
        if kw in t:
            return "severe"
    for kw in MODERATE:
        if kw in t:
            return "moderate"
    for kw in MILD:
        if kw in t:
            return "mild"
    for kw in NONE:
        if kw in t:
            return "none"
    risk_severe = {"危", "衰竭", "休克", "窒息"}
    if any(k in t for k in risk_severe):
        return "severe"
    risk_moderate = {"监护", "手术", "住院", "加护"}
    if any(k in t for k in risk_moderate):
        return "moderate"
    return "none"


def classify_with_evidence(text: str):
    t = (text or "").lower()
    evidence = []
    for kw in DEATH:
        if kw in t:
            evidence.append({"keyword": kw, "level": "death"})
    for kw in SEVERE:
        if kw in t:
            evidence.append({"keyword": kw, "level": "severe"})
    for kw in MODERATE:
        if kw in t:
            evidence.append({"keyword": kw, "level": "moderate"})
    for kw in MILD:
        if kw in t:
            evidence.append({"keyword": kw, "level": "mild"})
    for kw in NONE:
        if kw in t:
            evidence.append({"keyword": kw, "level": "none"})
    if not evidence:
        risk_severe = {"危", "衰竭", "休克", "窒息"}
        for kw in risk_severe:
            if kw in t:
                evidence.append({"keyword": kw, "level": "severe"})
        risk_moderate = {"监护", "手术", "住院", "加护"}
        for kw in risk_moderate:
            if kw in t:
                evidence.append({"keyword": kw, "level": "moderate"})
    level = classify(text)
    return level, evidence