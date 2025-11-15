# IntelliDevice-Alert
智能医疗器械不良事件监测与预警系统 - 基于知识图谱和AI的风险分析平台
# 🏥 IntelliDevice-Alert

智能医疗器械不良事件监测与预警系统

## 🎯 项目简介

IntelliDevice-Alert 是一个基于知识图谱和人工智能的医疗器械不良事件监测与预警系统。系统通过智能分析医疗事件报告，构建设备-事件-伤害的知识图谱，实现风险识别、预警和分析功能。

### ✨ 核心特性

- **🤖 智能结构化录入**: 自然语言描述自动转换为结构化医疗数据
- **🧠 LLM文本优化**: 集成OpenAI/Gemini大模型进行文本处理
- **📊 知识图谱构建**: 自动构建设备-事件-伤害关联网络
- **⚠️ 风险智能预警**: 基于图算法识别潜在风险点
- **📈 可视化分析**: ECharts图表展示数据洞察
- **🔄 标准术语匹配**: 自动匹配医疗标准术语库

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Neo4j 4.4+
- OpenAI API Key (可选)
- Google Gemini API Key (可选)

### 安装部署

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/ntelliDevice-Alert.git
cd ntelliDevice-Alert

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加 API Keys

# Docker 一键部署
docker-compose up -d
```

访问: http://localhost:8000/ui

## 📋 功能演示

### 1. 智能结构化录入
输入自然语言描述，系统自动提取关键信息：
```
输入: "设备使用过程中突然黑屏，无法继续对患者监护，最后更换新设备。"
输出: 
- 设备问题: 黑屏
- 故障模式: 设备使用问题 (A23)
- 健康影响: 设备修订或更换 (F1905)
- 置信度: 90%
```

### 2. 风险分析预警
基于知识图谱自动识别风险点：
- 严重伤害事件聚集
- 故障模式频繁出现
- 特定设备型号风险
- 制造商风险聚集

### 3. 知识图谱可视化
- 设备-事件-伤害关联网络
- 支持200+节点的大规模图展示
- 交互式节点探索和详情查看

## 🛠️ 技术架构

### 后端技术栈
- **框架**: FastAPI (高性能异步Python框架)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **图数据库**: Neo4j (知识图谱存储)
- **LLM集成**: OpenAI GPT-4 / Google Gemini
- **术语库**: 标准医疗术语匹配

### 前端技术栈
- **UI**: 原生HTML/JavaScript + Tailwind CSS
- **可视化**: Apache ECharts
- **交互**: 原生DOM操作 + Fetch API

### 核心算法
- **结构化分析**: 基于关键词模式和术语匹配
- **风险识别**: 图算法 + 统计分析
- **术语标准化**: 向量相似度计算
- **LLM处理**: 提示工程 + 结果解析

## 📊 数据模型

### 实体类型
- **Report**: 医疗事件报告
- **Device**: 医疗器械
- **Manufacturer**: 制造商
- **Model**: 设备型号
- **Hospital**: 医疗机构
- **FailureMode**: 故障模式 (A类术语)
- **Injury**: 伤害类型 (E/F类术语)
- **Action**: 处置措施 (C/D类术语)

### 关系类型
- `RESULTS_IN`: 报告导致设备事件
- `HAS_MODEL`: 设备具有型号
- `MANUFACTURED_BY`: 设备由制造商生产
- `HAS_FAILURE_MODE`: 报告具有故障模式
- `HAS_INJURY`: 报告具有伤害
- `HAS_ACTION`: 报告具有处置措施

## 🧪 API 接口

### 核心接口

#### 结构化分析
```http
POST /reports/analyze-structure
Content-Type: application/json

{
  "event_description": "设备使用过程中突然黑屏",
  "device_name": "心电监护仪",
  "action_taken": "立即更换设备"
}
```

#### 风险分析
```http
POST /graph/risk-analysis
Content-Type: application/json

{
  "limit": 50
}
```

#### 标准术语匹配
```http
POST /standardize
Content-Type: application/json

{
  "text": "设备屏幕无显示",
  "categories": ["A", "E", "F"],
  "top_k": 5
}
```

完整API文档: http://localhost:8000/docs

## 🔧 配置说明

### 环境变量
```bash
# LLM API 配置
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# 数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# 应用配置
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your_secret_key
```

### 术语库配置
系统内置标准医疗术语库，支持以下类别：
- A类: 设备问题 (Device Problems)
- B类: 设备操作问题 (Device Operational Issues)  
- C类: 调查结果 (Investigation Results)
- D类: 调查结论 (Investigation Conclusions)
- E类: 临床症状/病症 (Clinical Signs/Symptoms)
- F类: 健康影响 (Health Impacts)
- G类: 器械组件 (Device Components)

## 📈 性能指标

### 处理能力
- **结构化分析**: < 500ms
- **术语匹配**: < 200ms
- **风险分析**: < 2s (100个案例)
- **图谱可视化**: 支持200+节点实时渲染

### 扩展性
- 支持水平扩展
- 异步任务处理
- 缓存优化策略
- 数据库连接池

## 🧪 测试

```bash
# 运行单元测试
cd backend
pytest tests/

# 运行集成测试
pytest tests/integration/

# 性能测试
locust -f tests/load_test.py --host=http://localhost:8000
```

## 🚀 部署

### Docker 部署 (推荐)
```bash
# 生产环境部署
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 手动部署
详见 [DEPLOYMENT.md](DEPLOYMENT.md)

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 文档

- [部署指南](DEPLOYMENT.md) - 详细部署说明
- [API文档](http://localhost:8000/docs) - 在线API文档
- [结构化录入演示](结构化录入功能演示.md) - 新功能演示
- [论文初稿](论文初稿.md) - 学术研究文档

## 📞 支持

- 📧 邮箱: your-email@example.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/YOUR_USERNAME/ntelliDevice-Alert/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/YOUR_USERNAME/ntelliDevice-Alert/discussions)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- Apache ECharts 团队提供优秀的可视化库
- Neo4j 提供强大的图数据库支持
- OpenAI 和 Google 提供大模型API服务
- 医疗术语标准化组织提供标准术语库

---

⭐ 如果这个项目对您有帮助，请给我们一个星标!
