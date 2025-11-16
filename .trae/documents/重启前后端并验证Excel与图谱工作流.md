## 重启步骤
- 后端：停止当前 Uvicorn 进程并重新启动 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- 前端：刷新 `http://localhost:8000/ui/index.html`（Shift+刷新避免缓存），确保新脚本加载

## 清库（可选，保证干净验证）
- 清空内存库：`POST /admin/db/clear`
- 清空 Neo4j：`POST /admin/neo4j/clear`

## Excel 导入验证
- 上传含表头：医院名称/设备名称/制造商/型号/批次或序列号/事件时间/事件描述/伤害严重度/处置措施 的文件
- 设置阈值：`auto_threshold=0.6`、`review_threshold=0.3`
- 观察接口返回：`summary.received/auto_confirmed/pending/failed` 与 `report_ids/pending_ids`

## 待确认审核
- 加载待审列表：`GET /reports/review-pending`
- 对低分项：
  - 直接入库：`POST /reports/review-confirm {report_id, use_llm:false}`
  - 用大模型：`POST /reports/review-confirm {report_id, use_llm:true, provider:'openai'}`

## 图谱验证
- 单案图：`GET /case/{report_id}/graph` 检查：
  - Device 属性：`manufacturer/model`
  - Report 属性：`event_datetime/injury_severity`
  - 节点：`FailureMode/Injury/Action/DeviceIssue`
  - 关系：`REPORTED_BY/RESULTS_IN/HAS_FAILUREMODE/HAS_INJURY/CAUSES/HAS_ACTION/MITIGATES/HAS_FAULT/HAS_DEVICEISSUE`
- 总体图：`GET /case/recent-graph?limit=10` 展示近 N 条报告图谱
- 风险识别：点击首页“⚠️ 风险信号识别”，验证风险列表与证据输出

## 前端健壮性检查
- 确认按钮均可点击，控制台无 `await is only valid in async functions` 报错；若出现，确保所有 `await` 在 `async` 函数内或改用 Promise 链

## 预期结果
- 高分项自动入库并写图；低分项进入待审可选择 LLM 后入库
- Case View 与 Overview Graph 按你的模型展示节点与关系；风险识别面板输出前 10 个风险点

确认后我将执行以上步骤并把接口返回与两条报告的图谱节点/关系结果回传给你。