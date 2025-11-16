## 目标

* 按GitHub规范整理一个可直接推送的上传包（纯Markdown说明，无敏感信息）。

* 新建上级目录中的发布文件夹，复制必要代码/术语/文档/示例/脚本，形成清晰结构。

## 目标文件夹

* 建议路径：`/Users/fool/githubspace/ntelliDevice-Alert-release/`

* 替代方案（项目内）：`/Users/fool/githubspace/ntelliDevice-Alert/release/github-upload/`

## 结构与内容

* 根目录

  * `README.md`：项目总览、快速启动、配置、演示截图位（Mermaid/图片）

  * `LICENSE`：如 MIT（可后续选择）

  * `.gitignore`：排除 `.env`、`__pycache__`、`.DS_Store`、日志、临时输出

  * `requirements.txt`：后端依赖最小集（fastapi、uvicorn、neo4j、openpyxl、jieba 等）

  * `docker-compose.neo4j.yml`（如需要用容器启动Neo4j）

  * `docs/`：

    * `论文版_结构化录入与知识图谱风险识别.md`

    * `项目申报版_系统说明.md`

  * `examples/`：

    * `reports_template.xlsx`（从接口生成或现有模板）

    * `医院器械事件数据_sample.json`（脱敏示例，不含真实PII）

  * `術語庫/`（或 `术语库/`）：

    * 保留必要术语文件与别名文件

    * `mappings/device_issue_to_failure_mode.json`

  * `backend/`

    * `app/`：`main.py`、`graph.py`、`terminology.py`、`services/structure_analyzer.py`、`services/risk_analysis.py`、`services/severity.py`

    * `static/index.html`

    * `Dockerfile`（可选）

  * `scripts/`

    * `run_server.sh`：本地启动FastAPI的脚本

    * `init_neo4j.sh`：示例Neo4j配置脚本（仅说明，不含密码）

## 说明文档（Markdown）

* `README.md` 章节建议：

  * 简介（功能概述与价值）

  * 快速启动

    * 安装依赖：`pip install -r requirements.txt`

    * 启动Neo4j（容器或本地）、配置接口（`/config/neo4j`、`/config/neo4j-mapping`）

    * 启动后端：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

    * 前端访问：`http://localhost:8000/ui/index.html`

  * 核心工作流：结构化分析→确认→写图谱；Excel导入与待审；风险识别

  * 图示：Mermaid数据流/架构/图谱结构/风险流程（直接内嵌或引用docs）

  * 接口清单与示例调用

  * 配置项与阈值说明；安全与脱敏提示

  * 贡献与许可

## 复制清单（从当前项目到发布包）

* `backend/app/main.py`

* `backend/app/graph.py`

* `backend/app/terminology.py`

* `backend/app/services/structure_analyzer.py`

* `backend/app/services/risk_analysis.py`

* `backend/app/services/severity.py`

* `backend/static/index.html`

* `docs/论文版_结构化录入与知识图谱风险识别.md`

* `docs/项目申报版_系统说明.md`

* `docker-compose.neo4j.yml`（如存在并可用）

* `术语库/mappings/device_issue_to_failure_mode.json` + 基础术语文件（不含敏感数据）

* 生成或复制 `examples/reports_template.xlsx`

## 敏感信息与大文件处理

* 不复制任何 `.env`、密钥或含PII数据文件；示例数据需脱敏。

* 保留全部的映射与术语结构。

## GitHub推送准备

* 在发布包根写入 `.gitignore`、`README.md`、`LICENSE`、`requirements.txt`。

* 初始化Git并推送：

  * `git init && git add . && git commit -m "feat: release v1.0.0"`

  * `git remote add origin <repo_url> && git push -u origin main`

## 收尾记录（完成情况与改进方向）

* 完成：结构化分析、术语匹配、一致性映射、属性化图谱、Excel工作流、风险识别、两版文档

* 改进：术语库扩展、语义模型引入、本地LLM、风险规则校准、图谱校验与回滚、UI增强、容器化与监控

## 执行计划

* 我将：

  1. 在你确认后创建发布目录并复制清单文件；
  2. 生成 `README.md`、`.gitignore`、`requirements.txt`、示例模板；
  3. 验证启动与文档渲染；
  4. 打包与推送准备完成。

请确认路径选择与清单，我收到确认后开始执行整理与复制。
