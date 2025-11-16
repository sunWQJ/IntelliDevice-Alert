## 操作目标

* 重启后端服务（Uvicorn）与前端界面（静态页面挂载），确保最新逻辑生效

* 清空 Neo4j 图数据，保证无旧结构残留

* 重新导入样例数据并验证 Case View、Overview Graph 与风险识别按钮

## 执行步骤

1. 停止当前后端进程并重启

   * 关闭现有 Uvicorn 进程

   * 重新启动 `python -m uvicorn app.main:app` 并确保启动日志无错误
2. 清空 Neo4j 内容

   * 调用 `POST /admin/neo4j/clear`，返回删除数量（用于确认）

     单独发送一个设备信息，和节点。随机生成相关内容。
3. 验证图谱

   * 随机抽两条 `report_id`，调用 `GET /case/{id}/graph` 返回节点与边

   * 检查以下要点：

     * Device 节点属性：`manufacturer/model`

     * Report 节点属性：`event_datetime/injury_severity`

     * 节点存在：`FailureMode/Injury/Action/DeviceIssue`

     * 关系存在：`REPORTED_BY/RESULTS_IN/HAS_FAILUREMODE/HAS_INJURY/CAUSES/HAS_ACTION/MITIGATES/HAS_FAULT/HAS_DEVICEISSUE`

   * 加载总体图：`GET /case/recent-graph?limit=10` 查看节点/关系规模

   * 首页“⚠️风险信号识别”：点击展开并确认结果输出

## 输出与交付

* 重启与清库的接口返回

* 导入摘要 JSON

* 两个样例 `report_id` 的 Case View 节点/边 JSON（便于你在 Neo4j Browser 对照）

* 总体图节点/边统计与风险识别面板结果简要

## 预计时间

* 全流程约 2–4 分钟（含数据导入与图谱查询）

请确认后我立即执行上述步骤，并提供验证结果。
