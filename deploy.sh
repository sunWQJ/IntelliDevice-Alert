#!/bin/bash

# 🚀 IntelliDevice-Alert 部署脚本
# 智能医疗器械不良事件监测与预警系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    # 检查 Docker
    if ! command_exists docker; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command_exists docker-compose; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查内存
    if [[ "$OS" == "linux" ]]; then
        MEMORY=$(free -m | awk 'NR==2{print $2}')
        if [[ $MEMORY -lt 4096 ]]; then
            log_warning "建议至少 4GB 内存，当前只有 ${MEMORY}MB"
        fi
    fi
    
    log_success "系统要求检查通过"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p data logs nginx/ssl monitoring
    
    # 设置权限
    chmod 755 data logs
    
    log_success "目录创建完成"
}

# 环境配置
setup_environment() {
    log_info "配置环境变量..."
    
    if [[ ! -f .env ]]; then
        cp .env.example .env
        log_warning "已创建 .env 文件，请编辑配置您的 API 密钥"
        log_info "需要配置的密钥："
        log_info "- OPENAI_API_KEY: OpenAI API 密钥"
        log_info "- GEMINI_API_KEY: Google Gemini API 密钥"
        log_info "- NEO4J_PASSWORD: Neo4j 数据库密码"
        log_info "- SECRET_KEY: 应用密钥"
        
        # 生成随机密钥
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i "s/your_secret_key_here/$SECRET_KEY/g" .env
        
        log_info "已自动生成 SECRET_KEY: $SECRET_KEY"
    else
        log_info "环境文件已存在"
    fi
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."
    
    # 构建后端镜像
    docker build -t intellidevice-backend:latest ./backend
    
    # 构建 nginx 镜像
    docker build -t intellidevice-nginx:latest ./nginx
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 使用 docker-compose 启动
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    check_services
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    # 检查 Neo4j
    if curl -s -u neo4j:intellidevice123 http://localhost:7474/db/data/ >/dev/null; then
        log_success "Neo4j 服务正常运行"
    else
        log_error "Neo4j 服务未正常运行"
        return 1
    fi
    
    # 检查后端服务
    if curl -s http://localhost:8000/health >/dev/null; then
        log_success "后端服务正常运行"
    else
        log_error "后端服务未正常运行"
        return 1
    fi
    
    # 检查 nginx
    if curl -s http://localhost/health >/dev/null; then
        log_success "Nginx 服务正常运行"
    else
        log_error "Nginx 服务未正常运行"
        return 1
    fi
}

# 显示访问信息
show_access_info() {
    log_success "🎉 部署成功！"
    echo ""
    echo "=========================================="
    echo "  🏥 IntelliDevice-Alert 访问信息"
    echo "=========================================="
    echo ""
    echo "📊 主应用: http://localhost"
    echo "📚 API 文档: http://localhost/docs"
    echo "🔍 Neo4j 浏览器: http://localhost:7474"
    echo ""
    echo "📋 默认凭据:"
    echo "   Neo4j 用户名: neo4j"
    echo "   Neo4j 密码: intellidevice123"
    echo ""
    echo "📝 查看日志:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🔄 停止服务:"
    echo "   docker-compose down"
    echo ""
    echo "=========================================="
}

# 测试功能
test_functionality() {
    log_info "测试系统功能..."
    
    # 测试结构化分析
    RESPONSE=$(curl -s -X POST http://localhost:8000/reports/analyze-structure \
        -H "Content-Type: application/json" \
        -d '{
            "event_description": "设备使用过程中突然黑屏，无法继续对患者监护",
            "device_name": "心电监护仪"
        }')
    
    if echo "$RESPONSE" | grep -q "success.*true"; then
        log_success "结构化分析功能正常"
    else
        log_warning "结构化分析功能测试失败"
    fi
    
    # 测试风险分析
    RESPONSE=$(curl -s -X POST http://localhost:8000/graph/risk-analysis \
        -H "Content-Type: application/json" \
        -d '{"limit": 10}')
    
    if echo "$RESPONSE" | grep -q "success.*true"; then
        log_success "风险分析功能正常"
    else
        log_warning "风险分析功能测试失败"
    fi
}

# 显示帮助信息
show_help() {
    echo "🚀 IntelliDevice-Alert 部署脚本"
    echo ""
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --help, -h          显示帮助信息"
    echo "  --build-only        仅构建镜像，不启动服务"
    echo "  --start-only        仅启动服务，不构建镜像"
    echo "  --test              测试系统功能"
    echo "  --logs              查看服务日志"
    echo "  --stop              停止所有服务"
    echo "  --clean             清理所有数据和镜像"
    echo ""
    echo "示例:"
    echo "  $0                  # 完整部署"
    echo "  $0 --build-only     # 仅构建镜像"
    echo "  $0 --test           # 测试功能"
    echo ""
}

# 清理环境
clean_environment() {
    log_warning "清理环境..."
    
    # 停止服务
    docker-compose down
    
    # 删除镜像
    docker rmi intellidevice-backend:latest intellidevice-nginx:latest 2>/dev/null || true
    
    # 删除数据卷
    docker volume prune -f
    
    # 清理构建缓存
    docker builder prune -f
    
    log_success "环境清理完成"
}

# 查看日志
show_logs() {
    docker-compose logs -f
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose down
    log_success "服务已停止"
}

# 主函数
main() {
    case "${1:-}" in
        --help|-h)
            show_help
            ;;
        --build-only)
            check_requirements
            create_directories
            setup_environment
            build_images
            ;;
        --start-only)
            start_services
            show_access_info
            ;;
        --test)
            test_functionality
            ;;
        --logs)
            show_logs
            ;;
        --stop)
            stop_services
            ;;
        --clean)
            clean_environment
            ;;
        "")
            # 完整部署流程
            log_info "🚀 开始部署 IntelliDevice-Alert..."
            check_requirements
            create_directories
            setup_environment
            build_images
            start_services
            test_functionality
            show_access_info
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"