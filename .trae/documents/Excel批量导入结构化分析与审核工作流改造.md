## 目标
- 适配 Excel 表头（医院名称、设备名称、制造商、型号、批次或序列号、事件时间、事件描述、伤害严重度、处置措施）。
- 对每一行的“事件描述”执行结构化分析与术语匹配，按评分自动入库或进入待确认队列。
- 低分项由用户选择：直接入库、或调用大模型进行结构化分析后再确认入库。

## 字段映射
- Excel → 系统字段
  - 医院名称 → `hospital_id`
  - 设备名称 → `device_name`
  - 制造商 → `manufacturer`
  - 型号 → `model`
  - 批次或序列号 → `lot_sn`
  - 事件时间 → `event_datetime`
  - 事件描述 → `event_description`
  - 伤害严重度 → `injury_severity`（中文枚举映射）
  - 处置措施 → `action_taken`
- 中文严重度枚举映射：轻微/轻度→mild；中度/中等→moderate；重度/严重→severe；死亡→death；无伤害/无→none
- 日期解析：支持 `YYYY-MM-DD HH:mm:ss`、`YYYY-MM-DD`、`YYYY/MM/DD HH:mm:ss`、`YYYY/MM/DD`

## 后端改造
- 文件：`backend/app/main.py`
- 更新 `POST /reports/upload-excel`
  - 读取表头并按上述映射规范化；逐行构造 `ReportIn`
  - 对每行调用 `analyze_report_structure`（backend/app/services/structure_analyzer.py:285）
  - 使用 `analysis_confidence` 作为评分：
    - ≥ `auto_threshold`（默认 0.60）→ 自动执行 `structured-confirm` 入库与写图（backend/app/main.py:643）
    - 介于 `review_threshold` 与 `auto_threshold`（默认 0.30–0.59）→ 进入待确认队列
    - < `review_threshold`（默认 0.30）→ 进入待确认队列，并标注“建议使用大模型”
  - 返回：`{summary, report_ids, pending_ids}`，summary 包含 `{received, auto_confirmed, pending, failed}`
- 待确认工作流接口（若未存在则确保）
  - `GET /reports/review-pending`：返回待确认条目（base+structure+score）
  - `POST /reports/review-confirm`：确认入库；支持参数 `use_llm`（默认 false）与可选 `llm_entities/llm_relations`
    - `use_llm=true` 时：先调用 `llm_structure(provider, text, top_k)`（backend/app/llm.py:118），再入库与写图
    - 否则：用规则分析结果中的 `matched_terms` 或兜底实体入库
- 数据结构
  - 使用内存库的 `pending` 队列（backend/app/db.py:新增 `add_pending/list_pending/pop_pending`）存储待审项目：`{report_id, base, structure, score}`

## 前端改造
- 文件：`backend/static/index.html`
- Excel 区域新增控件
  - 阈值滑杆：`auto_threshold`（默认 0.60）
  - 开关：`review_threshold`（固定 0.30，可隐藏为默认值）
  - 选项：低分项“建议用大模型”提示；按钮进入“待确认列表”
- 待确认列表视图
  - 展示待审行的结构化抽取与匹配评分（默认折叠）
  - 每条提供两个按钮：`直接入库`、`用大模型后入库`
  - 调用 `POST /reports/review-confirm`，`use_llm` 由用户选择

## 结构化与写图逻辑（复用现有）
- 规则抽取：`StructureAnalyzer`（backend/app/services/structure_analyzer.py:40）
- 术语匹配：`terminology.search`（backend/app/terminology.py:113）
- 结构化确认：
  - 写入实体：`FailureMode/Injury/Action/DeviceIssue`（兜底支持），backend/app/main.py:790
  - 关系：`HAS_FAILUREMODE/HAS_INJURY/HAS_ACTION/CAUSES/MITIGATES`，backend/app/graph.py:89/163
  - 设备属性化：`Device(manufacturer, model)`，backend/app/graph.py:49

## 返回与审计
- Excel 导入返回：
  - `summary`: `{received, duplicate, failed, auto_confirmed, pending}`
  - `report_ids`: 自动确认入库的报告 ID 列表
  - `pending_ids`: 待确认报告 ID 列表
- 审计日志：保留结构化与确认过程记录（backend/app/main.py:731）

## 配置与容错
- 可配置：`auto_threshold`（默认 0.60），`review_threshold`（默认 0.30）
- 容错：字段缺失或日期解析失败时置空并继续；严重度中文映射到枚举；事件描述为空时转字符串空串

## 验证计划
- 用你提供的 Excel 模板导入 50 条（或样例），查看：
  - 自动确认数量与待审数量是否符合阈值
  - 待审列表可选择 `用大模型` 后入库是否生效
  - Case View 显示是否包含故障/伤害/处置与设备属性
  - Overview Graph 可加载近 N 条图谱并进行风险识别

## 交付
- 完成后端与前端改造，提供接口返回示例与两条 `report_id` 的 Case View 节点/边 JSON 用于核对。

请确认以上改造方案，我将开始实施并进行验证。