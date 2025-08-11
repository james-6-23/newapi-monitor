#!/bin/bash

# NewAPI监控系统快速启动脚本
# 用于一键部署和验证系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

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

# 显示横幅
show_banner() {
    echo "========================================"
    echo "  NewAPI 监控与风控系统"
    echo "  快速启动脚本 v1.0.0"
    echo "========================================"
    echo ""
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    local missing_deps=()
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    # 检查curl
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        echo "请安装缺少的依赖后重新运行此脚本"
        exit 1
    fi
    
    log_success "所有依赖检查通过"
}

# 检查环境配置
check_environment() {
    log_info "检查环境配置..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "未找到 .env 文件，正在创建..."
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        
        log_warning "请编辑 .env 文件配置数据库连接信息："
        echo "  - DB_HOST: 数据库主机地址"
        echo "  - DB_USER_RO: 只读用户名"
        echo "  - DB_PASS_RO: 只读用户密码"
        echo "  - DB_USER_AGG: 聚合用户名"
        echo "  - DB_PASS_AGG: 聚合用户密码"
        echo "  - ALERT_WEBHOOK_URL: 告警Webhook地址"
        echo ""
        
        read -p "配置完成后按回车继续..."
    fi
    
    # 检查关键配置项
    source "$ENV_FILE"
    
    if [ -z "$DB_HOST" ] || [ -z "$DB_USER_RO" ] || [ -z "$DB_PASS_RO" ]; then
        log_error "数据库配置不完整，请检查 .env 文件"
        exit 1
    fi
    
    log_success "环境配置检查通过"
}

# 构建和启动服务
start_services() {
    log_info "构建和启动服务..."
    
    cd "$PROJECT_ROOT"
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose build
    
    # 启动服务
    log_info "启动服务..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    log_success "服务启动完成"
}

# 验证服务状态
verify_services() {
    log_info "验证服务状态..."
    
    # 检查容器状态
    log_info "检查容器状态..."
    docker-compose ps
    
    # 等待API服务就绪
    log_info "等待API服务就绪..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost/api/health > /dev/null 2>&1; then
            log_success "API服务就绪"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "API服务启动超时"
            return 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo ""
    
    # 运行健康检查
    if [ -f "$SCRIPT_DIR/health_check.sh" ]; then
        log_info "运行健康检查..."
        chmod +x "$SCRIPT_DIR/health_check.sh"
        "$SCRIPT_DIR/health_check.sh" --url http://localhost
    fi
}

# 运行功能测试
run_tests() {
    log_info "运行功能测试..."
    
    if [ -f "$SCRIPT_DIR/functional_test.py" ]; then
        if command -v python3 &> /dev/null; then
            # 安装Python依赖
            pip3 install requests > /dev/null 2>&1 || true
            
            # 运行测试
            python3 "$SCRIPT_DIR/functional_test.py" --url http://localhost
        else
            log_warning "Python3未安装，跳过功能测试"
        fi
    else
        log_warning "功能测试脚本未找到，跳过测试"
    fi
}

# 显示访问信息
show_access_info() {
    log_success "系统部署完成！"
    echo ""
    echo "访问信息："
    echo "  - 监控面板: http://localhost"
    echo "  - API文档: http://localhost/api/docs"
    echo "  - 健康检查: http://localhost/api/health"
    echo ""
    echo "管理命令："
    echo "  - 查看服务状态: docker-compose ps"
    echo "  - 查看日志: docker-compose logs -f [service-name]"
    echo "  - 停止服务: docker-compose down"
    echo "  - 重启服务: docker-compose restart"
    echo ""
    echo "运维脚本："
    echo "  - 健康检查: ./scripts/health_check.sh"
    echo "  - 功能测试: python3 ./scripts/functional_test.py"
    echo "  - 数据备份: ./scripts/backup.sh"
    echo "  - 性能检查: mysql < ./scripts/performance_check.sql"
    echo ""
}

# 显示故障排除信息
show_troubleshooting() {
    echo "故障排除："
    echo ""
    echo "1. 如果服务无法启动："
    echo "   - 检查端口是否被占用: netstat -tlnp | grep :80"
    echo "   - 检查Docker服务: systemctl status docker"
    echo "   - 查看容器日志: docker-compose logs [service-name]"
    echo ""
    echo "2. 如果数据库连接失败："
    echo "   - 检查数据库配置: cat .env"
    echo "   - 测试数据库连接: mysql -h \$DB_HOST -u \$DB_USER_RO -p"
    echo "   - 检查网络连通性: ping \$DB_HOST"
    echo ""
    echo "3. 如果前端无法访问："
    echo "   - 检查Nginx配置: docker-compose logs frontend"
    echo "   - 检查API代理: curl http://localhost/api/health"
    echo ""
    echo "4. 获取更多帮助："
    echo "   - 查看部署文档: cat DEPLOYMENT.md"
    echo "   - 查看验收清单: cat ACCEPTANCE_CHECKLIST.md"
    echo ""
}

# 清理函数
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "部署过程中出现错误"
        echo ""
        show_troubleshooting
    fi
}

# 主函数
main() {
    # 设置错误处理
    trap cleanup EXIT
    
    show_banner
    
    # 检查是否在项目根目录
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 执行部署步骤
    check_dependencies
    check_environment
    start_services
    verify_services
    
    # 可选的功能测试
    read -p "是否运行功能测试？(y/N): " run_test
    if [[ $run_test =~ ^[Yy]$ ]]; then
        run_tests
    fi
    
    show_access_info
    
    # 移除错误处理
    trap - EXIT
    
    log_success "快速启动完成！"
}

# 显示使用说明
show_usage() {
    echo "NewAPI监控系统快速启动脚本"
    echo ""
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --help, -h    显示此帮助信息"
    echo "  --no-test     跳过功能测试"
    echo ""
    echo "此脚本将："
    echo "  1. 检查系统依赖"
    echo "  2. 检查环境配置"
    echo "  3. 构建和启动服务"
    echo "  4. 验证服务状态"
    echo "  5. 运行功能测试（可选）"
    echo ""
}

# 解析命令行参数
case "${1:-}" in
    --help|-h)
        show_usage
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
