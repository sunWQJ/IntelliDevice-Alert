# Neo4j 数据库搭建与初始化

## 1. 使用 Docker 启动 Neo4j

- 在发布包根目录执行：
```
docker compose -f docker-compose.neo4j.yml up -d
```
- 默认账户与密码：`neo4j/intellidevice123`（请在首次登录后修改密码）。
- 控制台：`http://localhost:7474/`，Bolt：`bolt://localhost:7687`

## 2. 后端配置

- 启动后端并调用配置接口：
```
curl -X POST http://localhost:8000/config/neo4j \
  -H 'Content-Type: application/json' \
  -d '{"uri":"bolt://localhost:7687","user":"neo4j","password":"intellidevice123"}'
```

## 3. 基本校验（Cypher）

- 在 Neo4j Browser 执行：
```
RETURN 1;
```
- 可选约束（建议）：
```
CREATE CONSTRAINT report_id_unique IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE;
```

## 4. 图谱结构自检

- 确认最小关系：
```
MATCH (r:Report)-[:RESULTS_IN]->(d:Device) RETURN r,d LIMIT 10;
MATCH (r:Report)-[:HAS_FAILUREMODE]->(fm:FailureMode) RETURN r,fm LIMIT 10;
MATCH (fm:FailureMode)-[:CAUSES]->(i:Injury) RETURN fm,i LIMIT 10;
MATCH (d:Device)-[:HAS_FAULT]->(di:DeviceIssue) RETURN d,di LIMIT 10;
```

## 5. 术语与映射

- 映射文件：`术语库/mappings/device_issue_to_failure_mode.json`
- 说明：设备问题（现象）与故障模式（机制）的一致性推导，降低“未知故障模式”比例。

## 6. 常见问题

- Bolt 连接失败：检查端口 `7687` 是否占用；容器是否启动；密码是否正确。
- 内存不足：调整 `NEO4J_dbms_memory_pagecache_size`；减少批量导入的并发。
- 映射未生效：确认后端已加载术语库目录并存在映射文件。