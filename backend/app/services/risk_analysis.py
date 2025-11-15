from __future__ import annotations
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
import json


class RiskAnalyzer:
    """风险点识别分析器"""
    
    def __init__(self):
        # 定义风险规则
        self.risk_rules = {
            "high_severity_cluster": {
                "description": "严重伤害事件聚集",
                "severity_levels": ["severe", "death"],
                "threshold": 3,  # 同一设备类型在短时间内出现3个及以上严重事件
                "time_window_days": 30
            },
            "frequent_fault_pattern": {
                "description": "故障模式频繁出现",
                "threshold": 5,  # 同一故障模式出现5次及以上
                "time_window_days": 60
            },
            "device_model_risk": {
                "description": "特定型号设备风险",
                "severity_weight": 0.7,  # 考虑严重程度的权重
                "threshold": 4  # 风险评分阈值
            },
            "manufacturer_risk": {
                "description": "制造商风险聚集",
                "threshold": 6  # 同一制造商出现6个及以上事件
            },
            "injury_device_correlation": {
                "description": "伤害-设备强关联",
                "threshold": 0.8  # 关联强度阈值
            }
        }
        
        # 严重度权重映射
        self.severity_weights = {
            "death": 1.0,
            "severe": 0.8,
            "moderate": 0.5,
            "mild": 0.2,
            "none": 0.0
        }
    
    def analyze_graph_data(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """分析图数据中的风险点"""
        risks = []
        
        # 1. 分析严重伤害聚集
        high_severity_risks = self._analyze_high_severity_clusters(nodes, edges)
        risks.extend(high_severity_risks)
        
        # 2. 分析故障模式频繁出现
        fault_pattern_risks = self._analyze_fault_patterns(nodes, edges)
        risks.extend(fault_pattern_risks)
        
        # 3. 分析设备型号风险
        device_model_risks = self._analyze_device_model_risks(nodes, edges)
        risks.extend(device_model_risks)
        
        # 4. 分析制造商风险
        manufacturer_risks = self._analyze_manufacturer_risks(nodes, edges)
        risks.extend(manufacturer_risks)
        
        # 5. 分析伤害-设备关联
        injury_correlation_risks = self._analyze_injury_device_correlation(nodes, edges)
        risks.extend(injury_correlation_risks)
        
        # 按风险级别排序
        risks.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        
        return {
            "total_risks": len(risks),
            "high_risks": len([r for r in risks if r.get("risk_level") == "high"]),
            "medium_risks": len([r for r in risks if r.get("risk_level") == "medium"]),
            "low_risks": len([r for r in risks if r.get("risk_level") == "low"]),
            "risk_details": risks[:10]  # 返回前10个最重要的风险点
        }
    
    def _analyze_high_severity_clusters(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """分析严重伤害事件聚集"""
        risks = []
        
        # 收集严重伤害事件
        severe_events = []
        for node in nodes:
            if node.get("label") == "AdverseEventReport" and node.get("severity") in ["severe", "death"]:
                severe_events.append(node)
        
        # 按设备类型分组
        device_severity_groups = defaultdict(list)
        for event in severe_events:
            # 找到相关的设备节点
            device_nodes = self._get_related_devices(event["id"], nodes, edges)
            for device in device_nodes:
                device_name = device.get("name", "")
                if device_name:
                    device_severity_groups[device_name].append(event)
        
        # 识别风险点 - 降低阈值以更容易触发
        for device_name, events in device_severity_groups.items():
            if len(events) >= 2:  # 降低到2个事件就触发
                risk_score = min(len(events) * 0.4, 1.0)  # 增加权重
                risks.append({
                    "risk_type": "high_severity_cluster",
                    "risk_level": "high" if len(events) >= 3 else "medium",  # 3个及以上为高风险
                    "risk_score": risk_score,
                    "description": f"设备类型'{device_name}'存在{len(events)}个严重伤害事件",
                    "evidence": {
                        "device_name": device_name,
                        "event_count": len(events),
                        "severity_levels": [e.get("severity", "") for e in events],
                        "recent_events": events[:3]  # 最近3个事件
                    },
                    "recommendation": f"建议对{device_name}进行重点监测和质量评估"
                })
        
        return risks
    
    def _analyze_fault_patterns(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """分析故障模式频繁出现"""
        risks = []
        
        # 收集故障节点
        fault_nodes = [n for n in nodes if n.get("label") in ["Fault", "FailureMode"]]
        
        # 统计故障模式出现频率
        fault_counter = Counter()
        fault_details = defaultdict(list)
        
        for fault in fault_nodes:
            fault_name = fault.get("name", "")
            fault_code = fault.get("code", "")
            if fault_name or fault_code:
                key = f"{fault_name}({fault_code})" if fault_code else fault_name
                fault_counter[key] += 1
                fault_details[key].append(fault)
        
        # 识别频繁出现的故障模式 - 降低阈值
        for fault_key, count in fault_counter.items():
            if count >= 3:  # 降低到3次就触发
                risk_score = min(count * 0.25, 1.0)  # 增加权重
                risks.append({
                    "risk_type": "frequent_fault_pattern",
                    "risk_level": "high" if count >= 5 else "medium",  # 5次及以上为高风险
                    "risk_score": risk_score,
                    "description": f"故障模式'{fault_key}'频繁出现，共{count}次",
                    "evidence": {
                        "fault_pattern": fault_key,
                        "occurrence_count": count,
                        "related_faults": fault_details[fault_key][:3]
                    },
                    "recommendation": f"建议分析{fault_key}的根本原因并制定预防措施"
                })
        
        return risks
    
    def _analyze_device_model_risks(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """分析特定型号设备风险"""
        risks = []
        
        # 按设备型号分组事件
        model_events = defaultdict(list)
        
        for node in nodes:
            if node.get("label") == "AdverseEventReport":
                # 找到相关的设备型号
                model_nodes = self._get_related_models(node["id"], nodes, edges)
                for model in model_nodes:
                    model_name = model.get("name", "")
                    if model_name:
                        model_events[model_name].append(node)
        
        # 计算每个型号的风险评分 - 降低阈值
        for model_name, events in model_events.items():
            if len(events) >= 1:  # 只要有1个事件就分析
                # 计算加权风险评分（考虑严重程度和事件数量）
                total_weight = 0
                severity_counts = defaultdict(int)
                
                for event in events:
                    severity = event.get("severity", "none")
                    weight = self.severity_weights.get(severity, 0)
                    total_weight += weight
                    severity_counts[severity] += 1
                
                avg_severity = total_weight / len(events) if events else 0
                risk_score = min(avg_severity * (1 + len(events) * 0.15), 1.0)
                
                if risk_score >= 0.2:  # 降低风险评分阈值
                    risks.append({
                        "risk_type": "device_model_risk",
                        "risk_level": "high" if risk_score > 0.5 else "medium",  # 降低高风险阈值
                        "risk_score": risk_score,
                        "description": f"设备型号'{model_name}'风险评分{risk_score:.2f}，共{len(events)}个事件",
                        "evidence": {
                            "model_name": model_name,
                            "total_events": len(events),
                            "severity_distribution": dict(severity_counts),
                            "avg_severity_score": avg_severity
                        },
                        "recommendation": f"建议对{model_name}型号设备进行重点检查或召回评估"
                    })
        
        return risks
    
    def _analyze_manufacturer_risks(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """分析制造商风险聚集"""
        risks = []
        
        # 按制造商分组事件
        manufacturer_events = defaultdict(list)
        
        for node in nodes:
            if node.get("label") == "AdverseEventReport":
                # 找到相关的制造商
                manufacturer_nodes = self._get_related_manufacturers(node["id"], nodes, edges)
                for manufacturer in manufacturer_nodes:
                    manufacturer_name = manufacturer.get("name", "")
                    if manufacturer_name:
                        manufacturer_events[manufacturer_name].append(node)
        
        # 识别高风险制造商 - 降低阈值
        for manufacturer_name, events in manufacturer_events.items():
            if len(events) >= 3:  # 降低到3个事件就触发
                # 计算制造商的综合风险评分
                severity_scores = []
                for event in events:
                    severity = event.get("severity", "none")
                    severity_scores.append(self.severity_weights.get(severity, 0))
                
                avg_severity = sum(severity_scores) / len(severity_scores) if events else 0
                risk_score = min(avg_severity * (len(events) / 8), 1.0)  # 调整权重计算
                
                risks.append({
                    "risk_type": "manufacturer_risk",
                    "risk_level": "high" if len(events) >= 6 else "medium",  # 降低高风险阈值
                    "risk_score": risk_score,
                    "description": f"制造商'{manufacturer_name}'聚集{len(events)}个事件，平均严重度{avg_severity:.2f}",
                    "evidence": {
                        "manufacturer_name": manufacturer_name,
                        "total_events": len(events),
                        "avg_severity": avg_severity,
                        "high_severity_events": len([e for e in events if e.get("severity") in ["severe", "death"]])
                    },
                    "recommendation": f"建议对{manufacturer_name}的产品质量进行全面审查"
                })
        
        return risks
    
    def _analyze_injury_device_correlation(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """分析伤害-设备强关联"""
        risks = []
        
        # 构建伤害-设备关联矩阵
        injury_device_pairs = defaultdict(list)
        
        for node in nodes:
            if node.get("label") == "AdverseEventReport":
                # 找到相关的伤害和设备
                injury_nodes = self._get_related_injuries(node["id"], nodes, edges)
                device_nodes = self._get_related_devices(node["id"], nodes, edges)
                
                for injury in injury_nodes:
                    injury_name = injury.get("name", "")
                    for device in device_nodes:
                        device_name = device.get("name", "")
                        if injury_name and device_name:
                            pair_key = f"{device_name}→{injury_name}"
                            injury_device_pairs[pair_key].append({
                                "event": node,
                                "injury": injury,
                                "device": device
                            })
        
        # 识别强关联对 - 降低阈值
        for pair_key, occurrences in injury_device_pairs.items():
            if len(occurrences) >= 2:  # 降低到2次关联就触发
                device_name, injury_name = pair_key.split("→")
                
                # 计算关联强度（考虑严重程度和频率）
                severity_scores = []
                for occ in occurrences:
                    severity = occ["event"].get("severity", "none")
                    severity_scores.append(self.severity_weights.get(severity, 0))
                
                avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0
                correlation_strength = min(avg_severity * (len(occurrences) / 3), 1.0)  # 调整权重
                
                if correlation_strength >= 0.5:  # 降低关联强度阈值
                    risks.append({
                        "risk_type": "injury_device_correlation",
                        "risk_level": "high" if correlation_strength > 0.7 else "medium",  # 降低高风险阈值
                        "risk_score": correlation_strength,
                        "description": f"设备'{device_name}'与伤害'{injury_name}'存在强关联（强度{correlation_strength:.2f}）",
                        "evidence": {
                            "device_name": device_name,
                            "injury_name": injury_name,
                            "correlation_frequency": len(occurrences),
                            "avg_severity": avg_severity,
                            "correlation_strength": correlation_strength
                        },
                        "recommendation": f"建议重点关注{device_name}设备导致{injury_name}伤害的机制研究"
                    })
        
        return risks
    
    def _get_related_devices(self, event_id: str, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """获取与事件相关的设备节点"""
        devices = []
        for edge in edges:
            if edge.get("source") == event_id and edge.get("label") in ["RELATED_TO", "HAS_FAULT"]:
                target_node = self._find_node_by_id(edge.get("target"), nodes)
                if target_node and target_node.get("label") in ["MedicalDevice", "Device"]:
                    devices.append(target_node)
        return devices
    
    def _get_related_models(self, event_id: str, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """获取与事件相关的型号节点"""
        models = []
        for edge in edges:
            if edge.get("source") == event_id and edge.get("label") == "HAS_MODEL":
                target_node = self._find_node_by_id(edge.get("target"), nodes)
                if target_node and target_node.get("label") == "Model":
                    models.append(target_node)
        return models
    
    def _get_related_manufacturers(self, event_id: str, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """获取与事件相关的制造商节点"""
        manufacturers = []
        for edge in edges:
            if edge.get("source") == event_id and edge.get("label") == "MANUFACTURED_BY":
                target_node = self._find_node_by_id(edge.get("target"), nodes)
                if target_node and target_node.get("label") == "Manufacturer":
                    manufacturers.append(target_node)
        return manufacturers
    
    def _get_related_injuries(self, event_id: str, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """获取与事件相关的伤害节点"""
        injuries = []
        for edge in edges:
            if edge.get("source") == event_id and edge.get("label") in ["RESULTS_IN", "HAS_INJURY"]:
                target_node = self._find_node_by_id(edge.get("target"), nodes)
                if target_node and target_node.get("label") in ["Harm", "Injury"]:
                    injuries.append(target_node)
        return injuries
    
    def _find_node_by_id(self, node_id: str, nodes: List[Dict]) -> Dict:
        """根据ID查找节点"""
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return {}


# 全局分析器实例
risk_analyzer = RiskAnalyzer()


def analyze_risks_in_graph(graph_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    分析图数据中的风险点
    
    Args:
        graph_data: 包含nodes和edges的图数据
        
    Returns:
        风险分析结果
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    if not nodes or not edges:
        return {
            "total_risks": 0,
            "high_risks": 0,
            "medium_risks": 0,
            "low_risks": 0,
            "risk_details": [],
            "message": "图数据为空，无法进行风险分析"
        }
    
    try:
        return risk_analyzer.analyze_graph_data(nodes, edges)
    except Exception as e:
        return {
            "total_risks": 0,
            "high_risks": 0,
            "medium_risks": 0,
            "low_risks": 0,
            "risk_details": [],
            "error": f"风险分析过程中出现错误: {str(e)}"
        }