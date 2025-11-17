"""
结构化分析服务 - 将自然语言医疗事件描述转换为结构化数据
"""
import re
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from ..terminology import search as term_search
from ..services.severity import classify_with_evidence
from ..config import terminology_dir
from ..synonyms import ALIASES


class StructureAnalyzer:
    """医疗事件结构化分析器"""
    
    def __init__(self):
        # 设备问题关键词模式
        self.device_patterns = {
            'display_issue': ['黑屏', '无显示', '屏幕', '显示', '花屏', '闪烁'],
            'power_issue': ['断电', '关机', '重启', '电池', '电源', '无法开机'],
            'alarm_issue': ['报警', '警报', '误报', '无报警', '报警器', '蜂鸣'],
            'measurement_issue': ['测量', '数值', '数据', '读数', '不准', '误差'],
            'connection_issue': ['连接', '断连', '信号', '传输', '通信', '网络'],
            'ventilation_issue': ['压力', '压力升高', '压力异常', '通气', '通气异常', '过度通气', '氧合', '氧合不足', '氧饱和下降']
        }
        
        # 临床表现关键词模式
        self.clinical_patterns = {
            'cardiac': ['心律', '心跳', '心脏', '心电', '血压', '脉搏'],
            'respiratory': ['呼吸', '氧气', '通气', '窒息', '呼吸困难', '肺', '肺水肿', '充血', '低氧'],
            'neurological': ['意识', '昏迷', '抽搐', '痉挛', '神经'],
            'general': ['疼痛', '不适', '发热', '寒战', '恶心']
        }
        
        # 处置措施关键词模式
        self.action_patterns = {
            'replace_device': ['更换', '替换', '换新', '备用', '替代'],
            'repair_device': ['维修', '修理', '修复', '检修', '维护'],
            'monitor_patient': ['监护', '观察', '监测', '检查', '评估'],
            'medical_intervention': ['治疗', '用药', '手术', '抢救', '急救'],
            'transfer': ['转科', '转院', 'ICU', '重症监护', '急诊']
        }
        # 设备问题→故障模式映射缓存
        self._issue_fm_map: Optional[Dict[str, List[Dict[str, Any]]]] = None
        self._mapping_enabled = True
    
    def analyze_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析医疗事件报告并提取结构化信息
        
        Args:
            report_data: 报告数据字典
            
        Returns:
            结构化分析结果
        """
        event_desc = report_data.get('event_description', '')
        action_taken = report_data.get('action_taken', '')
        device_name = report_data.get('device_name', '')
        pre = self._preprocess_text(event_desc, device_name)
        
        # 提取设备问题
        device_issue = self._extract_device_issue(pre, device_name)
        
        # 提取故障模式（初判）
        failure_mode = self._extract_failure_mode(pre)
        
        # 提取临床表现
        clinical_manifestation = self._extract_clinical_manifestation(pre)
        
        # 提取健康影响
        health_impact = self._extract_health_impact(pre)
        
        # 提取处置措施
        treatment_action = self._extract_treatment_action(action_taken)
        
        # 若设备问题高置信且故障为未知，尝试基于映射推导故障模式
        failure_mode = self._derive_failure_mode_if_needed(device_issue, failure_mode, event_desc)

        # 匹配标准术语
        matched_terms = self._match_standard_terms({
            'device_issue': device_issue,
            'failure_mode': failure_mode,
            'clinical_manifestation': clinical_manifestation,
            'health_impact': health_impact,
            'treatment_action': treatment_action
        })

        # 若设备问题匹配到A类编码，按父级编码推导故障模式（如 A0101 -> A01）
        fm_from_code = self._derive_failure_from_device_code(matched_terms)
        if fm_from_code:
            failure_mode = fm_from_code
        
        # 计算分析置信度
        confidence = self._calculate_confidence({
            'device_issue': device_issue,
            'failure_mode': failure_mode,
            'clinical_manifestation': clinical_manifestation,
            'health_impact': health_impact,
            'treatment_action': treatment_action
        }, matched_terms)
        
        return {
            'device_issue': device_issue,
            'failure_mode': failure_mode,
            'clinical_manifestation': clinical_manifestation,
            'health_impact': health_impact,
            'treatment_action': treatment_action,
            'matched_terms': matched_terms,
            'match_details': self._collect_match_details(pre),
            'analysis_confidence': confidence['overall'],
            'confidence_breakdown': confidence['breakdown']
        }
    
    def _extract_device_issue(self, text: str, device_name: str) -> str:
        """提取设备问题"""
        res = term_search(text, ["A"], top_k=1, threshold=0.0)
        items = res.get("A", [])
        if items:
            t, sc = items[0]
            return t.term
        return "未命中术语库"
    
    def _extract_failure_mode(self, text: str) -> str:
        """提取故障模式"""
        res = term_search(text, ["A"], top_k=1, threshold=0.0)
        items = res.get("A", [])
        if items:
            t, sc = items[0]
            return t.term
        return "未命中术语库"

    def _load_issue_fm_mapping(self) -> Dict[str, List[Dict[str, Any]]]:
        if self._issue_fm_map is not None:
            return self._issue_fm_map
        self._issue_fm_map = {}
        try:
            base = terminology_dir()
            if base:
                p = Path(base) / "mappings" / "device_issue_to_failure_mode.json"
                if p.exists():
                    with p.open("r", encoding="utf-8") as fp:
                        self._issue_fm_map = json.load(fp) or {}
        except Exception:
            self._issue_fm_map = {}
        return self._issue_fm_map

    def _derive_failure_mode_if_needed(self, device_issue: str, failure_mode: str, text: str) -> str:
        """当故障模式为未知时，基于设备问题映射推导故障模式"""
        if not self._mapping_enabled:
            return failure_mode
        if not device_issue or device_issue.endswith("功能异常"):
            return failure_mode
        if failure_mode and failure_mode != "未知故障模式":
            return failure_mode
        mapping = self._load_issue_fm_mapping()
        if not mapping:
            return failure_mode
        # 设备问题可能是“关键词1、关键词2”形式，逐个尝试映射
        candidates = []
        for token in re.split(r"[、，,\s]+", device_issue.strip()):
            if not token:
                continue
            items = mapping.get(token) or []
            for it in items:
                term = it.get("term")
                if term:
                    candidates.append(term)
        # 若有候选，结合术语库A类做二次匹配以确认
        for cand in candidates:
            res = term_search(cand, ["A"], top_k=1, threshold=0.2).get("A", [])
            if res:
                t, sc = res[0]
                return t.term or cand
        # 无法命中术语库时，直接返回第一个候选作为推导
        if candidates:
            return candidates[0]
        return failure_mode
    
    def _extract_clinical_manifestation(self, text: str) -> str:
        """提取临床表现"""
        res = term_search(text, ["E"], top_k=1, threshold=0.0)
        items = res.get("E", [])
        if items:
            t, sc = items[0]
            return t.term
        return "未命中术语库"
    
    def _extract_health_impact(self, text: str) -> str:
        """提取健康影响：依赖E类匹配与严重度，允许升级一级"""
        # 先匹配E类（临床表现）用于提供上下文
        res = term_search(text, ["E"], top_k=3, threshold=0.2)
        e_matches = res.get("E", [])
        # 基于严重度分类结果
        lvl, ev = classify_with_evidence(text)
        order = ['none', 'mild', 'moderate', 'severe', 'death']
        idx = order.index(lvl) if lvl in order else 0
        # 若证据显示更高严重度，最多提升一级（不超过 severe）
        has_severe = any(x.get('level') == 'severe' for x in ev)
        has_moderate = any(x.get('level') == 'moderate' for x in ev)
        if has_severe and idx < order.index('severe'):
            idx = min(idx + 1, order.index('severe'))
        elif has_moderate and idx < order.index('moderate'):
            idx = min(idx + 1, order.index('moderate'))
        lvl = order[idx]
        severity_map = {
            'death': '死亡',
            'severe': '重度伤害',
            'moderate': '中度伤害',
            'mild': '轻度伤害',
            'none': '无伤害'
        }
        
        return severity_map.get(lvl, '健康影响未明确')
    
    def _extract_treatment_action(self, text: str) -> str:
        """提取处置措施 - 仅提取文本，不匹配标准术语库"""
        if not text or text.strip() == "":
            return "处置措施未明确"
        
        # 直接返回原始文本，不进行术语匹配
        # 这样可以保留完整的处置措施描述
        return text.strip()
    
    def _match_standard_terms(self, extracted_data: Dict[str, str]) -> List[Dict[str, Any]]:
        """匹配标准术语 - 处置措施不进行术语匹配"""
        matched_terms = []
        
        # 为每个提取的字段匹配标准术语（处置措施除外）
        for field, text in extracted_data.items():
            if field == 'treatment_action':
                # 处置措施不进行标准术语匹配，直接跳过
                continue
                
            if text and text not in ["未知故障模式", "临床表现未明确", "健康影响未明确", "处置措施未明确", "功能异常"]:
                # 根据字段类型选择适当的术语类别
                if field == 'failure_mode':
                    categories = ["A"]
                elif field == 'clinical_manifestation':
                    categories = ["E"]
                elif field == 'health_impact':
                    categories = ["E", "F"]
                else:
                    categories = ["A"]
                
                res = term_search(text, categories, top_k=5, threshold=0.0)
                
                for category, matches in res.items():
                    for term, score in matches:
                        matched_terms.append({
                            'category': category,
                            'term': term.term,
                            'code': term.code,
                            'similarity': score,
                            'field': field
                        })
        
        return matched_terms

    def _collect_match_details(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        res = {}
        for field, cats in {
            'device_issue': ["A"],
            'failure_mode': ["A"],
            'clinical_manifestation': ["E"],
            'health_impact': ["E", "F"],
        }.items():
            r = term_search(text, cats, top_k=5, threshold=0.0)
            details = []
            for c, matches in r.items():
                for t, sc in matches:
                    details.append({'category': c, 'term': t.term, 'code': t.code, 'similarity': sc})
            res[field] = details
        return res

    def _preprocess_text(self, text: str, device_name: str) -> str:
        s = (text or "").strip()
        s = s.replace("，", ",").replace("。", ".").replace("；", ";").replace("、", " ")
        adds: List[str] = []
        for cat in ("A", "E"):
            aliases = ALIASES.get(cat, {})
            for term, al in aliases.items():
                for a in al:
                    if a and a in s:
                        adds.append(term)
                        break
        dn = (device_name or "").strip()
        if dn and "呼吸机" in dn:
            if "压力" in s and "压力问题" not in adds:
                adds.append("压力问题")
            if "通气" in s and "通气异常" not in adds:
                adds.append("通气异常")
        if adds:
            s = s + " " + " ".join(list(dict.fromkeys(adds)))
        return s

    def _derive_failure_from_device_code(self, matched_terms: List[Dict[str, Any]]) -> str:
        """根据设备问题的A类编码推导故障模式的父级术语名称（如 A0101 -> A01）"""
        # 查找设备问题的A类编码
        code = None
        for mt in matched_terms:
            if mt.get('field') == 'device_issue' and mt.get('category') == 'A' and mt.get('code'):
                code = mt.get('code')
                break
        if not code or not code.startswith('A'):
            return ""
        # 计算父级编码：A + 前两位数字
        parent = code
        try:
            digits = ''.join(ch for ch in code[1:] if ch.isdigit())
            if len(digits) >= 2:
                parent = 'A' + digits[:2]
            else:
                parent = code
        except Exception:
            parent = code
        # 通过术语库查找父级术语
        term = self._lookup_term_by_code('A', parent)
        return term or ""

    def _lookup_term_by_code(self, category: str, code: str) -> str:
        """从术语库按类别与编码查找术语名称，结果缓存"""
        try:
            base = terminology_dir()
            if not base:
                return ""
            cache_attr = f"_code_index_{category}"
            idx = getattr(self, cache_attr, None)
            if idx is None:
                idx = {}
                file = None
                for f in Path(base).glob("*.json"):
                    if f.name.startswith(category + "：") and "别名" not in f.name:
                        file = f
                        break
                if not file:
                    setattr(self, cache_attr, idx)
                    return ""
                with file.open("r", encoding="utf-8") as fp:
                    data = json.load(fp)
                for x in data:
                    c = x.get("code")
                    t = x.get("term")
                    if c and t:
                        idx[c] = t
                setattr(self, cache_attr, idx)
            return idx.get(code, "")
        except Exception:
            return ""
    
    def _calculate_confidence(self, extracted_data: Dict[str, str], matched_terms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算分析置信度 - 处置措施不参与术语匹配置信度计算"""
        confidence_breakdown = {}
        total_fields = len(extracted_data) - 1  # 排除处置措施字段
        confident_fields = 0
        
        # 评估每个字段的置信度（处置措施除外）
        for field, value in extracted_data.items():
            if field == 'treatment_action':
                # 处置措施只提取文本，不参与置信度计算
                confidence_breakdown[field] = 1.0  # 处置措施置信度为100%，因为直接提取原文
                continue
                
            if value in ["未知故障模式", "临床表现未明确", "健康影响未明确", "处置措施未明确", "功能异常"]:
                confidence_breakdown[field] = 0.2  # 低置信度
            elif any(term['field'] == field for term in matched_terms):
                # 如果有术语匹配，置信度较高
                field_terms = [term for term in matched_terms if term['field'] == field]
                avg_similarity = sum(term['similarity'] for term in field_terms) / len(field_terms)
                confidence_breakdown[field] = 0.6 + (avg_similarity * 0.4)  # 0.6-1.0
                confident_fields += 1
            else:
                confidence_breakdown[field] = 0.5  # 中等置信度
                confident_fields += 0.5
        
        # 计算整体置信度（不含处置措施）
        overall_confidence = confident_fields / total_fields if total_fields > 0 else 0
        
        return {
            'overall': overall_confidence,
            'breakdown': confidence_breakdown
        }


# 全局分析器实例
analyzer = StructureAnalyzer()


def analyze_report_structure(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """分析报告结构的便捷函数"""
    return analyzer.analyze_report(report_data)