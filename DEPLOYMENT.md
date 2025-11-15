# 🚀 IntelliDevice-Alert 部署指南

## 📋 项目概述

IntelliDevice-Alert 是一个智能医疗器械不良事件监测与预警系统，集成了知识图谱、风险分析、LLM结构化处理等先进功能。

### 🎯 核心功能
- ✅ 医疗事件报告智能录入与结构化分析
- ✅ 知识图谱构建与可视化展示
- ✅ 风险点自动识别与预警
- ✅ LLM大模型文本处理与优化
- ✅ 标准医疗术语匹配与标准化

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (Python)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **图数据库**: Neo4j
- **LLM集成**: OpenAI API / Google Gemini
- **依赖管理**: pip

### 前端
- **技术**: 原生HTML/JavaScript + ECharts
- **样式**: 自定义CSS (响应式设计)
- **可视化**: ECharts 图表库

## 📦 环境要求

### 系统要求
- Python 3.8+
- Node.js 16+ (可选，用于前端构建)
- Neo4j 4.4+
- Git

### Python依赖
```bash
# 核心依赖
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
sqlalchemy==2.0.23
neo4j==5.13.0
openai==1.3.0
google-generativeai==0.3.0

# 数据处理
pandas==2.1.3
numpy==1.25.2
openpyxl==3.1.2

# 文本处理
scikit-learn==1.3.2
jieba==0.42.1
```

## 🔧 部署步骤

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/ntelliDevice-Alert.git
cd ntelliDevice-Alert

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
cd backend
pip install -r requirements.txt
```

### 2. Neo4j 图数据库配置

```bash
# 安装 Neo4j (以Ubuntu为例)
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 4.4' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt update
sudo apt install neo4j

# 启动 Neo4j
sudo systemctl start neo4j
sudo systemctl enable neo4j

# 验证安装
curl -u neo4j:password http://localhost:7474/db/data/
```

### 3. LLM API 配置

```bash
# 创建环境变量文件
cp .env.example .env

# 编辑配置文件
nano .env

# 添加以下配置
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### 4. 数据库初始化

```bash
# 运行数据库初始化
python -c "from backend.app.db import init_db; init_db()"

# 导入标准医疗术语
python -c "from backend.app.terminology import load_terms; load_terms()"
```

### 5. 启动应用

```bash
# 启动后端服务
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境部署 (使用gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. 访问应用

```bash
# 打开浏览器访问
http://localhost:8000/ui

# API 文档
http://localhost:8000/docs
```

## 🐳 Docker 部署 (推荐)

### 1. Docker Compose 配置

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:4.4
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/your_password
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=1G
    volumes:
      - neo4j_data:/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - neo4j
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=your_password
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  neo4j_data:
```

### 2. 构建和启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 🌐 生产环境部署

### 1. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ui {
        alias /path/to/your/static/files;
        try_files $uri $uri/ =404;
    }
}
```

### 2. 使用 systemd 服务

创建 `/etc/systemd/system/intellidevice-alert.service`:

```ini
[Unit]
Description=IntelliDevice-Alert Backend
After=network.target neo4j.service

[Service]
Type=exec
User=www-data
WorkingDirectory=/path/to/ntelliDevice-Alert/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable intellidevice-alert
sudo systemctl start intellidevice-alert
sudo systemctl status intellidevice-alert
```

## 🔒 安全配置

### 1. API 安全
- 使用 API Key 验证
- 配置 CORS 跨域策略
- 实现请求限流
- 敏感数据加密存储

### 2. 数据库安全
- 配置强密码策略
- 限制数据库访问IP
- 定期备份数据
- 启用SSL连接

### 3. LLM API 安全
- 配置 API Key 轮换
- 监控 API 使用量
- 实现请求缓存
- 敏感信息过滤

## 📊 性能优化

### 1. 数据库优化
```python
# 添加索引
CREATE INDEX ON :Report(report_id);
CREATE INDEX ON :Device(name);
CREATE INDEX ON :Manufacturer(name);
```

### 2. 缓存策略
- Redis 缓存热点数据
- 数据库查询结果缓存
- LLM 响应缓存
- 前端静态资源缓存

### 3. 异步处理
- 使用 Celery 处理耗时任务
- WebSocket 实时推送
- 批量数据处理

## 🧪 测试验证

### 1. 功能测试
```bash
# 测试结构化分析
curl -X POST http://localhost:8000/reports/analyze-structure \
  -H "Content-Type: application/json" \
  -d '{
    "event_description": "设备使用过程中突然黑屏，无法继续对患者监护",
    "device_name": "心电监护仪"
  }'

# 测试风险分析
curl -X POST http://localhost:8000/graph/risk-analysis \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'
```

### 2. 性能测试
```bash
# 使用 Apache Bench 测试
ab -n 1000 -c 10 http://localhost:8000/ui

# 使用 Locust 进行负载测试
locust -f tests/load_test.py --host=http://localhost:8000
```

## 📈 监控与维护

### 1. 应用监控
- Prometheus + Grafana 监控指标
- ELK Stack 日志分析
- 错误追踪 (Sentry)
- 性能监控 (APM)

### 2. 健康检查
```bash
# 系统健康检查端点
curl http://localhost:8000/health

# 数据库连接检查
curl http://localhost:8000/health/db

# 外部服务检查
curl http://localhost:8000/health/external
```

## 🔄 备份与恢复

### 1. 数据备份
```bash
# Neo4j 备份
docker exec neo4j neo4j-admin backup --backup-dir=/backups --name=graph.db

# SQLite 备份
cp backend/data.db backend/data.db.backup

# 配置文件备份
tar -czf config_backup.tar.gz backend/config/
```

### 2. 灾难恢复
```bash
# Neo4j 恢复
docker exec neo4j neo4j-admin restore --from=/backups/graph.db --database=graph.db --force

# 配置文件恢复
tar -xzf config_backup.tar.gz
```

## 🆘 常见问题

### Q1: Neo4j 连接失败
**解决方案**: 
- 检查 Neo4j 服务状态: `sudo systemctl status neo4j`
- 验证连接配置: `bolt://localhost:7687`
- 检查防火墙设置

### Q2: LLM API 调用失败
**解决方案**:
- 验证 API Key 有效性
- 检查网络连接
- 查看 API 配额使用情况

### Q3: 内存不足
**解决方案**:
- 增加 JVM 内存: `-Xms2g -Xmx4g`
- 优化数据库查询
- 启用数据分页

## 📞 技术支持

- **项目地址**: https://github.com/YOUR_USERNAME/ntelliDevice-Alert
- **问题反馈**: https://github.com/YOUR_USERNAME/ntelliDevice-Alert/issues
- **文档更新**: https://github.com/YOUR_USERNAME/ntelliDevice-Alert/wiki

---

**⚠️ 重要提醒**: 
- 生产环境请务必配置强密码
- 定期更新系统和依赖包
- 启用HTTPS加密传输
- 定期备份重要数据