# 🚀 GitHub 仓库配置指南

## 📋 项目仓库设置

### 1. 创建 GitHub 仓库

1. 访问 [GitHub](https://github.com)
2. 点击右上角的 "+" 图标，选择 "New repository"
3. 填写仓库信息：
   - **Repository name**: `IntelliDevice-Alert`
   - **Description**: `智能医疗器械不良事件监测与预警系统 - 基于知识图谱和AI的风险分析平台`
   - **Visibility**: 选择 Public 或 Private
   - **Initialize**: 不要勾选任何初始化选项（已有代码）

### 2. 推送现有代码

```bash
# 添加远程仓库地址
git remote add origin https://github.com/YOUR_USERNAME/IntelliDevice-Alert.git

# 推送代码到主分支
git branch -M main
git push -u origin main
```

### 3. 仓库配置

#### 设置仓库主题
- 在仓库页面点击 "Settings"
- 滚动到 "Topics" 部分，添加相关标签：
  - `medical-device`
  - `knowledge-graph`
  - `risk-analysis`
  - `fastapi`
  - `neo4j`
  - `artificial-intelligence`
  - `healthcare`
  - `medical-safety`

#### 启用功能
- **Issues**: 启用问题跟踪
- **Discussions**: 启用讨论功能
- **Projects**: 启用项目管理
- **Wiki**: 启用文档wiki
- **Sponsors**: 可选，启用赞助功能

## 🔧 分支策略

### 推荐分支结构
```
main (主分支) - 稳定版本
develop (开发分支) - 集成开发
feature/* (功能分支) - 新功能开发
hotfix/* (热修复分支) - 紧急修复
release/* (发布分支) - 版本发布
```

### 分支保护规则
1. 进入 Settings → Branches
2. 添加分支保护规则：
   - **Branch name pattern**: `main`
   - **Protect matching branches**: 勾选
   - **Require pull request reviews before merging**: 勾选
   - **Require status checks to pass before merging**: 勾选
   - **Require branches to be up to date before merging**: 勾选

## 📊 GitHub Actions 配置

### 创建 CI/CD 工作流

在 `.github/workflows/` 目录下创建以下文件：

#### `ci.yml` - 持续集成
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      neo4j:
        image: neo4j:4.4
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
        options: >-
          --health-cmd "cypher-shell -u neo4j -p testpassword 'RETURN 1'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        cd backend
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
        
    - name: Run tests
      run: |
        cd backend
        pytest tests/ -v --cov=app --cov-report=xml
        
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
```

#### `docker-build.yml` - Docker 构建
```yaml
name: Docker Build

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
      
    - name: Login to DockerHub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}
        
    - name: Build and push backend
      uses: docker/build-push-action@v4
      with:
        context: ./backend
        push: true
        tags: |
          ${{ secrets.DOCKERHUB_USERNAME }}/intellidevice-backend:latest
          ${{ secrets.DOCKERHUB_USERNAME }}/intellidevice-backend:${{ github.ref_name }}
```

#### `deploy.yml` - 部署工作流
```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.PRODUCTION_HOST }}
        username: ${{ secrets.PRODUCTION_USER }}
        key: ${{ secrets.PRODUCTION_SSH_KEY }}
        script: |
          cd /opt/intellidevice-alert
          git pull origin main
          docker-compose down
          docker-compose up -d --build
```

## 🔐 密钥配置

### 必需的环境变量
在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

#### Repository Secrets
```
DOCKERHUB_USERNAME=your_dockerhub_username
DOCKERHUB_TOKEN=your_dockerhub_token
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
PRODUCTION_HOST=your_production_server_ip
PRODUCTION_USER=your_production_user
PRODUCTION_SSH_KEY=your_production_ssh_private_key
PRODUCTION_NEO4J_PASSWORD=your_production_neo4j_password
```

#### Repository Variables
```
NEO4J_VERSION=4.4
PYTHON_VERSION=3.9
DEPLOY_PATH=/opt/intellidevice-alert
```

## 📈 项目徽章

在 README.md 中添加以下徽章：

```markdown
![CI](https://github.com/YOUR_USERNAME/IntelliDevice-Alert/workflows/CI/badge.svg)
![Docker Build](https://github.com/YOUR_USERNAME/IntelliDevice-Alert/workflows/Docker%20Build/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)
![Neo4j](https://img.shields.io/badge/neo4j-4.4+-green.svg)
```

## 📝 贡献指南

创建 `CONTRIBUTING.md` 文件：

```markdown
# 🤝 贡献指南

感谢您为 IntelliDevice-Alert 项目做出贡献！

## 🚀 开始贡献

### 1. Fork 项目
点击右上角的 "Fork" 按钮

### 2. 克隆项目
```bash
git clone https://github.com/YOUR_USERNAME/IntelliDevice-Alert.git
cd IntelliDevice-Alert
```

### 3. 创建分支
```bash
git checkout -b feature/your-feature-name
```

### 4. 开发功能
- 遵循项目代码规范
- 添加必要的测试
- 更新文档

### 5. 提交更改
```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

### 6. 创建 Pull Request
1. 访问原仓库
2. 点击 "New Pull Request"
3. 选择您的分支
4. 填写 PR 描述

## 📋 提交规范

使用 Conventional Commits 规范：

- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具

## 🧪 测试要求

- 所有新功能必须包含测试
- 测试覆盖率不低于80%
- 通过所有CI检查

## 📞 联系方式

- 📧 邮箱: your-email@example.com
- 💬 讨论: GitHub Discussions
- 🐛 问题: GitHub Issues
```

## 🏷️ 发布管理

### 版本号规范
使用语义化版本号 (Semantic Versioning):
- `MAJOR.MINOR.PATCH`
- 例如: `v1.2.3`

### 发布流程
1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Release
4. 打标签: `git tag -a v1.2.3 -m "Release version 1.2.3"`
5. 推送标签: `git push origin v1.2.3`

### Release 模板
```markdown
## 🎉 版本 v1.2.3 发布

### ✨ 新功能
- 新增结构化录入功能
- 集成LLM文本优化

### 🐛 修复
- 修复风险分析算法bug
- 优化图数据库查询性能

### 📈 改进
- 提升用户界面体验
- 增强系统稳定性

### 📋 完整变更日志
查看 [CHANGELOG.md](CHANGELOG.md)

### 📦 下载
- 源代码: [Source code (zip)](archive/refs/tags/v1.2.3.zip)
- Docker镜像: `docker pull yourusername/intellidevice-backend:v1.2.3`
```

## 📊 项目统计

### 启用 GitHub Insights
- **Pulse**: 查看项目活动趋势
- **Contributors**: 分析贡献者统计
- **Traffic**: 查看访问统计
- **Code frequency**: 代码变更频率
- **Network**: 分支网络图

### 外部集成
- **Codecov**: 代码覆盖率报告
- **SonarCloud**: 代码质量分析
- **Dependabot**: 依赖更新管理
- **Snyk**: 安全漏洞扫描

## 🔧 维护建议

### 定期维护任务
1. **每周**:
   - 检查并合并 Dependabot PR
   - 回复 Issues 和 Discussions
   - 更新项目看板

2. **每月**:
   - 发布补丁版本
   - 更新文档
   - 清理过期 Issues

3. **每季度**:
   - 发布功能版本
   - 性能优化
   - 安全审计

### 社区建设
- 回复用户问题和反馈
- 鼓励贡献者参与
- 定期发布项目更新
- 参与相关技术社区

---

**🎯 下一步**: 按照本指南配置您的 GitHub 仓库，然后就可以开始接收用户反馈和贡献了！