## 技术栈与基础设施
- 后端：Python（FastAPI）微服务，异步I/O；任务编排：Prefect/Airflow
- 消息总线：Kafka 或 RabbitMQ；对象存储：S3 兼容（附件）
- 数据库：PostgreSQL（含 pgvector 可选）+ Neo4j（知识图谱）
- 前端：React + Ant Design；可视化：ECharts/D3
- 部署：Docker/Compose（MVP），后续 K8s；观测：Prometheus + Grafana

## 阶段1：项目骨架与接入网关
- 建立服务骨架与公共中间件（日志、审计、权限、错误处理）
- 设计 MDAE 数据契约与 Excel 模板；实现 `POST /reports` 与 `POST /reports/upload-excel`
- 数据清洗/校验（必填、类型、枚举）、重复去重、关键信息脱敏（患者/医护 PII）
- 处理状态流转与审计日志 `processing_log`；单元测试与合成数据集
- 验收：成功接入 ≥1000 条样例，校验/脱敏覆盖率 ≥95%，审计日志完备

## 阶段2：NLP 流水线与术语标准化
- 文本预处理：语言检测、分句、医学停用词策略、噪声清理
- NER：识别 `器械名称/故障表现/伤害表现/处置措施/制造商/科室`（中文医疗预训练模型微调）
- 术语标准化：采用语义相似度模型（如 E5/SimCSE/中文医疗嵌入），向量检索（pgvector/FAISS），Top-k 召回+重排序+阈值过滤；规则兜底
- 关系抽取：`CAUSES/MITIGATES/ASSOCIATED_WITH` 等；低置信度入人工复核队列
- 指标：NER F1≥0.80（MVP数据集）、术语映射 Hit@1≥0.85、关系抽取 F1≥0.75
- 验收：实体/关系落库成功，版本与置信度记录，复核接口可用

## 阶段3：统一数据底座
- Neo4j 图谱模式：节点 `Device/FailureMode/AdverseEvent/Injury/Action/Report/Manufacturer/Hospital`
- 关系：`CAUSES`、`MITIGATED_BY`、`RESULTS_IN`、`REPORTED_BY`、`MANUFACTURED_BY`
- PostgreSQL 表：`reports`、`entities`、`relations`、`signals`、`alerts`、`processing_log`
- 一致性与索引：主键/外键、时间/组合索引；图谱与关系库间 ID 映射
- 验收：图谱查询和关系聚合均稳定，关键查询 P95<200ms（1万报告样本）

## 阶段4：风险信号分析
- 统计信号：PRR/ROR 定期计算，最小计数阈值，χ²/置信区间规则
- 时序预测：对高风险“器械-事件”组合做月/周粒度预测（Prophet/ARIMA）
- 图挖掘：Louvain/Leiden 社区发现与 PageRank/Betweenness 中心性
- 编排：日/周批任务 + 增量流处理，结果落库 `signals`
- 验收：强信号列表稳定输出，误报率可控，预测曲线与历史一致性可视化

## 阶段5：前端与可视化
- Dashboard：报告趋势、Top-N 事件/器械、最新强信号、地域分布
- Search：自然语言/关键词混检，语义解析 + 图谱/关系库检索，过滤与排序
- Case View：单报告关系网络可视化，节点置信度与路径展开、时间线叠加
- Alerting：订阅规则（器械/事件/阈值/地域/科室），邮件/短信通知，抑制策略
- 权限与审计：RBAC，操作水印，导出审计
- 验收：核心页面可用，端到端从报告到预警打通

## 核心 API 合约（MVP）
- 接入：`POST /reports`、`POST /reports/upload-excel`、`GET /reports/{id}`
- 分析：`GET /signals?device_id=...&event_id=...`、`GET /signals/{id}`
- 订阅/预警：`POST /subscriptions`、`GET /alerts`、`PATCH /subscriptions/{id}`
- 检索/图谱：`GET /search?q=...&type=device|event`、`GET /graph/paths?from=...&to=...`

## 数据安全与合规
- 传输与存储加密（TLS、静态加密）、密钥托管；最小权限 RBAC
- 脱敏策略与可追溯审计；数据访问分级与导出水印
- 合规检查：日志留存、访问异常告警、渗透测试与风险评估

## 质量与验证
- 合成与匿名化真实样本；覆盖单元/集成测试；基准集持续评估
- 指标面板：NLP 指标、数据质量、信号效果、服务性能

## 交付物与时间表（示例 8–10 周）
- 第1–2周：阶段1 完成与基础设施就绪
- 第3–5周：阶段2 与术语库落地，初步评估
- 第6–7周：阶段3 数据底座与查询
- 第8–9周：阶段4 信号分析与任务编排
- 第10周：阶段5 前端联调与验收

## 需要确认的点
- 术语标准库来源与优先级（IMDRF/NMPA）及更新频率
- 目标数据量级与并发指标；通知渠道与频控规则
- MVP 环境（单机/云）与依赖许可（Neo4j/pgvector）

请确认以上实施计划与里程碑，如无问题我将按照该计划初始化项目骨架与接口契约，并推进到阶段1与2。