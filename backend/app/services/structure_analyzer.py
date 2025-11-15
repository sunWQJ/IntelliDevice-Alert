"""
结构化分析服务 - 将自然语言医疗事件描述转换为结构化数据
"""
import re
from typing import Dict, List, Any, Optional
from ..terminology import search as term_search
from ..services.severity import classify_with_evidence


class StructureAnalyzer:
    """医疗事件结构化分析器"""
    
    def __init__(self):
        # 设备问题关键词模式
        self.device_patterns = {
            'display_issue': ['黑屏', '无显示', '屏幕', '显示', '花屏', '闪烁'],
            'power_issue': ['断电', '关机', '重启', '电池', '电源', '无法开机'],
            'alarm_issue': ['报警', '警报', '误报', '无报警', '报警器', '蜂鸣'],
            'measurement_issue': ['测量', '数值', '数据', '读数', '不准', '误差'],
            'connection_issue': ['连接', '断连', '信号', '传输', '通信', '网络']
        }
        
        # 临床表现关键词模式
        self.clinical_patterns = {
            'cardiac': ['心律', '心跳', '心脏', '心电', '血压', '脉搏'],
            'respiratory': ['呼吸', '氧气', '通气', '窒息', '呼吸困难'],
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
        
        # 提取设备问题
        device_issue = self._extract_device_issue(event_desc, device_name)
        
        # 提取故障模式
        failure_mode = self._extract_failure_mode(event_desc)
        
        # 提取临床表现
        clinical_manifestation = self._extract_clinical_manifestation(event_desc)
        
        # 提取健康影响
        health_impact = self._extract_health_impact(event_desc)
        
        # 提取处置措施
        treatment_action = self._extract_treatment_action(action_taken)
        
        # 匹配标准术语
        matched_terms = self._match_standard_terms({
            'device_issue': device_issue,
            'failure_mode': failure_mode,
            'clinical_manifestation': clinical_manifestation,
            'health_impact': health_impact,
            'treatment_action': treatment_action
        })
        
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
            'analysis_confidence': confidence['overall'],
            'confidence_breakdown': confidence['breakdown']
        }
    
    def _extract_device_issue(self, text: str, device_name: str) -> str:
        """提取设备问题"""
        issues = []
        
        # 检查每种设备问题模式
        for issue_type, keywords in self.device_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    issues.append(keyword)
                    break
        
        # 如果没有找到具体问题，返回通用描述
        if not issues:
            return f"{device_name}功能异常"
        
        return "、".join(issues)
    
    def _extract_failure_mode(self, text: str) -> str:
        """提取故障模式"""
        # 使用术语匹配来识别故障模式
        res = term_search(text, ["A"], top_k=3, threshold=0.2)
        
        failure_modes = []
        for category, matches in res.items():
            for term, score in matches:
                failure_modes.append({
                    'term': term.term,
                    'code': term.code,
                    'score': score
                })
        
        # 返回最佳匹配的故障模式
        if failure_modes:
            best_match = max(failure_modes, key=lambda x: x['score'])
            return best_match['term']
        
        # 如果没有匹配到术语，基于关键词推断
        if '黑屏' in text or '无显示' in text:
            return "显示故障"
        elif '报警' in text or '误报' in text:
            return "报警系统故障"
        elif '测量' in text or '不准' in text:
            return "测量精度故障"
        else:
            return "未知故障模式"
    
    def _extract_clinical_manifestation(self, text: str) -> str:
        """提取临床表现"""
        # 使用术语匹配来识别临床表现
        res = term_search(text, ["E"], top_k=3, threshold=0.2)
        
        manifestations = []
        for category, matches in res.items():
            for term, score in matches:
                manifestations.append({
                    'term': term.term,
                    'code': term.code,
                    'score': score
                })
        
        # 返回最佳匹配的临床表现
        if manifestations:
            best_match = max(manifestations, key=lambda x: x['score'])
            return best_match['term']
        
        # 如果没有匹配到术语，基于关键词推断
        for condition, keywords in self.clinical_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    return f"{keyword}异常"
        
        return "临床表现未明确"
    
    def _extract_health_impact(self, text: str) -> str:
        """提取健康影响"""
        # 使用术语匹配来识别健康影响
        res = term_search(text, ["F"], top_k=3, threshold=0.2)
        
        impacts = []
        for category, matches in res.items():
            for term, score in matches:
                impacts.append({
                    'term': term.term,
                    'code': term.code,
                    'score': score
                })
        
        # 返回最佳匹配的健康影响
        if impacts:
            best_match = max(impacts, key=lambda x: x['score'])
            return best_match['term']
        
        # 基于严重度分类结果
        lvl, ev = classify_with_evidence(text)
        severity_map = {
            'death': '死亡',
            'severe': '重度伤害',
            'moderate': '中度伤害',
            'mild': '轻度伤害',
            'none': '无伤害'
        }
        
        return severity_map.get(lvl, '健康影响未明确')
    
    def _extract_treatment_action(self, text: str) -> str:
        """提取处置措施"""
        # 使用术语匹配来识别处置措施
        res = term_search(text, ["C", "D"], top_k=3, threshold=0.2)
        
        actions = []
        for category, matches in res.items():
            for term, score in matches:
                actions.append({
                    'term': term.term,
                    'code': term.code,
                    'score': score,
                    'category': category
                })
        
        # 返回最佳匹配的处置措施
        if actions:
            best_match = max(actions, key=lambda x: x['score'])
            return best_match['term']
        
        # 基于关键词推断
        for action_type, keywords in self.action_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    return keyword
        
        return "处置措施未明确"
    
    def _match_standard_terms(self, extracted_data: Dict[str, str]) -> List[Dict[str, Any]]:
        """匹配标准术语"""
        matched_terms = []
        
        # 为每个提取的字段匹配标准术语
        for field, text in extracted_data.items():
            if text and text not in ["未知故障模式", "临床表现未明确", "健康影响未明确", "处置措施未明确", "功能异常"]:
                # 根据字段类型选择适当的术语类别
                if field == 'failure_mode':
                    categories = ["A"]
                elif field == 'clinical_manifestation':
                    categories = ["E"]
                elif field == 'health_impact':
                    categories = ["F"]
                elif field == 'treatment_action':
                    categories = ["C", "D"]
                else:
                    categories = ["A", "E", "F", "C", "D"]
                
                res = term_search(text, categories, top_k=1, threshold=0.2)
                
                for category, matches in res.items():
                    if matches:
                        term, score = matches[0]
                        matched_terms.append({
                            'category': category,
                            'term': term.term,
                            'code': term.code,
                            'similarity': score,
                            'field': field
                        })
        
        return matched_terms
    
    def _calculate_confidence(self, extracted_data: Dict[str, str], matched_terms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算分析置信度"""
        confidence_breakdown = {}
        total_fields = len(extracted_data)
        confident_fields = 0
        
        # 评估每个字段的置信度
        for field, value in extracted_data.items():
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
        
        # 计算整体置信度
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