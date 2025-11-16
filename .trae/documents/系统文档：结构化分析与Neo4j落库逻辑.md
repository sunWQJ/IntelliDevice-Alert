# 文档目标
整理风险信号识别、事件描述的结构化分析、术语匹配逻辑与 Neo4j 落库逻辑，形成可复核的系统说明文档，含代码位置与接口清单。

## 目录结构
1. 概览
2. 事件结构化分析逻辑
3. 术语匹配逻辑
4. Neo4j 落库模型与查询
5. 风险信号识别逻辑
6. 接口与前端交互
7. 配置项与运行模式
8. 验证与排错

## 1. 概览
- 功能组成：结构化分析（规则+兜底）、术语匹配（别名+TF-IDF+相似度融合）、图谱落库（属性化 Device、结构化实体与关系）、风险识别（聚集/频发/关联）
- 关键文件：
  - `backend/app/services/structure_analyzer.py`（结构化）
  - `backend/app/terminology.py`（术语匹配）
  - `backend/app/graph.py`（Neo4j 落库与 Case View 查询）
  - `backend/app/services/risk_analysis.py`（风险识别）
  - `backend/app/main.py`（路由与工作流）

## 2. 事件结构化分析逻辑
- 文件：`backend/app/services/structure_analyzer.py`
- 抽取项：
  - 设备问题：`_extract_device_issue`（行 98）关键词聚类
  - 故障模式：`_extract_failure_mode`（行 115）优先术语库 A 类，否则兜底“显示故障/报警系统故障/测量精度故障/未知故障模式”
  - 临床表现：`_extract_clinical_manifestation`（行 144）术语库 E 类，否则“关键词异常”兜底
  - 健康影响：`_extract_health_impact`（行 171）术语库 F 类，否则基于严重度分类兜底（死亡/重度/中度/轻度/无伤害）
  - 处置措施：`_extract_treatment_action`（行 202）原文保留，不做术语匹配
- 术语匹配封装：`_match_standard_terms`（行 211）按字段类别筛选 top1、阈值 0.2
- 置信度：`_calculate_confidence`（行 247）匹配加权、未识别兜底 0.2；整体为字段平均
- 总入口：`analyze_report_structure`（行 285）返回抽取项、匹配项、置信度

## 3. 术语匹配逻辑
- 文件：`backend/app/terminology.py`
- 目录加载：`terminology_dir()`（backend/app/config.py:6）默认仓库根 `术语库`
- 分词与相似度：
  - bigram + jieba 分词 Jaccard 融合 `_score`（行 49）
  - 别名加权 `_aliases_for`（行 106）；别名命中加 0.1 封顶 1.0
  - TF-IDF 向量 `_build_vectors`（行 171），文本向量 `_text_vector`（行 207）
- 搜索入口：`search(text, categories, top_k=5, threshold=0.3)`（行 113），返回候选术语与分数

## 4. Neo4j 落库模型与查询
- 文件：`backend/app/graph.py`
- 报告写入：`write_report` → `_tx_write_report`（行 49）
  - 节点：`Hospital(id)`、`Device(name)`、`Report(id)`
  - 属性：`Report(event_datetime, injury_severity, processed_at, status, lot_sn)`；`Device(manufacturer, model)`
  - 关系：`Report-[:REPORTED_BY]->Hospital`、`Report-[:RESULTS_IN]->Device`
- 结构写入：`write_structure`（行 89）
  - 支持聚合字段：`failure_mode/health_impact/device_issue/treatment_action`（兼容 `injury/action/device_issue` 字段名）
  - 节点：`FailureMode/Injury(Action)/DeviceIssue`；`Injury.severity = Report.injury_severity`
  - 关系：
    - `Report-[:HAS_FAILUREMODE]->FailureMode`
    - `Report-[:HAS_INJURY]->Injury`
    - `FailureMode-[:CAUSES]->Injury`
    - `Report-[:HAS_ACTION]->Action`、`Action-[:MITIGATES]->FailureMode`
    - `Device-[:HAS_FAULT]->DeviceIssue`、`Report-[:HAS_DEVICEISSUE]->DeviceIssue`
- 标签映射：`_entity_label`（行 134）包含 `failure_mode/injury/action/device_issue`
- 链接实现：`_tx_link_report_entity`（行 163）按标签分别处理 `HAS_INJURY/ HAS_DEVICEISSUE/ HAS_*` 关系；设备问题另外补 `Device-[:HAS_FAULT]`
- Case View 查询：`case_graph` → `_tx_case_graph`（行 307）返回设备属性 manufacturer/model 与报告属性 event_datetime/injury_severity，同时包含 `FailureMode/Injury/Action/DeviceIssue` 与关系

## 5. 风险信号识别逻辑
- 文件：`backend/app/services/risk_analysis.py`
- 入口：`analyze_risks_in_graph(graph_data)`（行 363）
- 规则：
  - 严重伤害聚集：设备维度严重事件聚集（阈值 2 起即触发；评分按事件数）
  - 故障模式频繁：同故障模式出现次数（阈值 3 起；评分按频次）
  - 型号风险：型号维度严重度加权与事件量（评分≥0.2 触发）
  - 制造商风险：制造商维度事件聚集与平均严重度（事件≥3 触发）
  - 设备-伤害强关联：设备→伤害成对出现频次与严重度加权（出现≥2，强度≥0.5 触发）
- 证据与建议：每条风险返回 `description/risk_score/risk_level/evidence/recommendation`

## 6. 接口与前端交互
- 后端接口：
  - 结构化分析：`POST /reports/analyze-structure`（backend/app/main.py:616）
  - 结构化确认：`POST /reports/structured-confirm`（backend/app/main.py:643）
  - 批量导入：`POST /reports/import-json`（backend/app/main.py:1232）；`POST /reports/upload-excel`（backend/app/main.py:950）
  - 清库：`POST /admin/db/clear`、`POST /admin/neo4j/clear`（backend/app/main.py:1232 之后新增接口位置）
  - Case View：`GET /case/{id}/graph`（backend/app/graph.py:299）
  - 总体图：`GET /case/recent-graph?limit=10`（backend/app/main.py:456）
  - 风险识别：`POST /graph/risk-analysis`（backend/app/main.py:817）
- 前端关键点：
  - 首页按钮流：结构化分析→查看评分→不满意用大模型→确认并录入→Case View/Overview Graph
  - 风险识别：`btnRiskAnalysis` 折叠面板调用 `POST /graph/risk-analysis` 并展示结果（backend/static/index.html:186）

## 7. 配置项与运行模式
- 标注库写入开关：`NEO4J_MAP_STANDARD_TERMS`（默认 false，Neo4j只承载报告图谱）
- 术语库路径：`TERMINOLOGY_DIR`（backend/app/config.py:6）
- LLM 配置：`POST /config/llm`（backend/app/main.py:331）
- Neo4j 连接：`POST /config/neo4j`（backend/app/main.py:353）

## 8. 验证与排错
- 验证结构：
  - 导入后抽两个 `report_id` 调用 `GET /case/{id}/graph` 验证 Device 属性、Report 属性与实体/关系是否齐全
  - 加载总体图与风险识别，观察结果是否与模型一致
- 常见问题：
  - 前端脚本 `await` 用法错误（报错：`await is only valid in async functions`）→ 将事件处理函数改为 `async` 或使用顶层 `type="module"`
  - 仅调用 `POST /reports` 未执行结构化确认，导致无故障/伤害/处置节点 → 使用 `structured-confirm` 或批量导入 `auto_threshold=0.0`

## 交付方式
- 我将把以上内容整理为一份文档文件（建议 `docs/系统说明.md`），包含以上章节与代码位置，便于团队复核与后续维护。请确认后我开始生成文档文件并提交。