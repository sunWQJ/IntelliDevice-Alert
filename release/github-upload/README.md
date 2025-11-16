# IntelliDevice-Alert 发布包

## 简介
- 结构化录入医疗器械不良事件，构建知识图谱并识别风险信号。
- 规则抽取 + 术语库匹配 + 一致性映射；低分项可选调用大模型。

## 快速启动
- 依赖安装：
```
pip install -r requirements.txt
```
- 启动 Neo4j（本地或容器），设置：`NEO4J_URI/NEO4J_USER/NEO4J_PASS`。
- 启动后端：
```
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- 配置接口：
```
curl -X POST http://localhost:8000/config/neo4j -H 'Content-Type: application/json' -d '{"uri":"bolt://localhost:7687","user":"neo4j","password":"intellidevice123"}'
```
- 前端访问：`http://localhost:8000/ui/index.html`

## 使用 Docker 启动 Neo4j（推荐）
- 在发布包根目录执行：
```
docker compose -f docker-compose.neo4j.yml up -d
```
- 初始化（可选）：
```
bash scripts/init_neo4j.sh
```
- 更多说明见：`docs/db_setup.md`

## 目录说明
- `backend/`：后端核心文件（FastAPI + Neo4j + 术语匹配 + 结构化分析 + 风险识别）
- `docs/`：两版说明文档（论文版与项目申报版，含 Mermaid 图示）
- `术语库/`：设备问题→故障模式映射与必要术语文件（不含敏感数据）
- `examples/`：Excel 模板与样例 JSON（脱敏）
- `scripts/`：启动脚本示例

## 核心工作流
- 结构化分析 → 确认并写图谱
- Excel 批量导入 → 阈值自动确认/待审队列 → 人工确认或 LLM → 写图谱
- Case/Overview 图谱展示 → 风险识别（折叠面板）

## 接口清单
- `POST /reports/analyze-structure`
- `POST /reports/structured-confirm`
- `POST /reports/upload-excel`
- `GET /reports/review-pending`
- `POST /reports/review-confirm`
- `GET /case/{id}/graph`
- `GET /case/recent-graph?limit=10`
- `POST /graph/risk-analysis`

## 安全与隐私
- 不提交任何密钥或含PII数据；所有示例已脱敏。

## 许可
- 建议使用 MIT；可根据实际需要调整。