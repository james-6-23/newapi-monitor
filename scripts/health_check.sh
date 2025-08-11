#!/bin/bash

# NewAPI监控系统健康检查脚本
# 用于验证系统各组件是否正常运行

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_BASE_URL="${API_BASE_URL:-http://localhost}"
TIMEOUT=10
VERBOSE=false

# 显示使用说明
show_usage() {
    echo "NewAPI监控系统健康检查工具"
    echo ""
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --url URL        API基础URL (默认: http://localhost)"
    echo "  --timeout SEC    请求超时时间 (默认: 10秒)"
    echo "  --verbose        显示详细信息"
    echo "  --help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0"
    echo "  $0 --url http://your-server.com --verbose"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            API_BASE_URL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
done

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

# HTTP请求函数
make_request() {
    local url="$1"
    local expected_status="${2:-200}"
    
    if [ "$VERBOSE" = true ]; then
        log_info "请求: $url"
    fi
    
    local response=$(curl -s -w "%{http_code}" --connect-timeout $TIMEOUT --max-time $TIMEOUT "$url" 2>/dev/null)
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$status_code" = "$expected_status" ]; then
        if [ "$VERBOSE" = true ]; then
            log_success "状态码: $status_code"
        fi
        echo "$body"
        return 0
    else
        log_error "请求失败: $url (状态码: $status_code)"
        return 1
    fi
}

# 检查Docker服务
check_docker_services() {
    log_info "检查Docker服务状态..."
    
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        log_warning "Docker未安装或不在PATH中，跳过Docker检查"
        return 0
    fi
    
    # 检查docker-compose服务
    if command -v docker-compose &> /dev/null; then
        local services=$(docker-compose ps --services 2>/dev/null || echo "")
        if [ -n "$services" ]; then
            log_info "Docker Compose服务状态:"
            docker-compose ps
            
            # 检查每个服务是否健康
            for service in $services; do
                local status=$(docker-compose ps -q $service | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
                if [ "$status" = "healthy" ] || [ "$status" = "unknown" ]; then
                    log_success "服务 $service: 运行中"
                else
                    log_error "服务 $service: 状态异常 ($status)"
                fi
            done
        fi
    fi
}

# 检查前端服务
check_frontend() {
    log_info "检查前端服务..."
    
    local response=$(make_request "$API_BASE_URL/health" 2>/dev/null || echo "")
    if [ -n "$response" ]; then
        log_success "前端服务正常"
        return 0
    fi
    
    # 尝试检查主页
    local response=$(make_request "$API_BASE_URL/" 2>/dev/null || echo "")
    if [ -n "$response" ]; then
        log_success "前端主页可访问"
        return 0
    fi
    
    log_error "前端服务不可访问"
    return 1
}

# 检查API服务
check_api() {
    log_info "检查API服务..."
    
    # 健康检查
    local health_response=$(make_request "$API_BASE_URL/api/health")
    if [ $? -eq 0 ]; then
        log_success "API健康检查通过"
        if [ "$VERBOSE" = true ]; then
            echo "响应: $health_response"
        fi
    else
        log_error "API健康检查失败"
        return 1
    fi
    
    # 检查时序数据接口
    local end_ms=$(date +%s)000
    local start_ms=$((end_ms - 3600000))  # 1小时前
    
    local series_response=$(make_request "$API_BASE_URL/api/stats/series?start_ms=$start_ms&end_ms=$end_ms&slot_sec=300")
    if [ $? -eq 0 ]; then
        log_success "时序数据接口正常"
        if [ "$VERBOSE" = true ]; then
            echo "数据点数: $(echo "$series_response" | grep -o '"total_points":[0-9]*' | cut -d: -f2)"
        fi
    else
        log_error "时序数据接口异常"
        return 1
    fi
    
    # 检查TopN接口
    local top_response=$(make_request "$API_BASE_URL/api/stats/top?start_ms=$start_ms&end_ms=$end_ms&by=user&metric=tokens&limit=10")
    if [ $? -eq 0 ]; then
        log_success "TopN接口正常"
    else
        log_error "TopN接口异常"
        return 1
    fi
    
    # 检查异常检测接口
    local anomaly_response=$(make_request "$API_BASE_URL/api/stats/anomalies?start_ms=$start_ms&end_ms=$end_ms&rule=burst")
    if [ $? -eq 0 ]; then
        log_success "异常检测接口正常"
    else
        log_error "异常检测接口异常"
        return 1
    fi
}

# 检查数据库连接
check_database() {
    log_info "检查数据库连接..."
    
    # 通过API健康检查间接验证数据库连接
    local health_response=$(make_request "$API_BASE_URL/api/health")
    if [ $? -eq 0 ]; then
        log_success "数据库连接正常（通过API验证）"
    else
        log_error "数据库连接异常"
        return 1
    fi
}

# 检查Redis连接
check_redis() {
    log_info "检查Redis连接..."
    
    # 通过API健康检查间接验证Redis连接
    local health_response=$(make_request "$API_BASE_URL/api/health")
    if [ $? -eq 0 ]; then
        log_success "Redis连接正常（通过API验证）"
    else
        log_error "Redis连接异常"
        return 1
    fi
}

# 检查Worker服务
check_worker() {
    log_info "检查Worker服务..."
    
    # 检查聚合数据是否在更新
    local end_ms=$(date +%s)000
    local start_ms=$((end_ms - 86400000))  # 24小时前
    
    local series_response=$(make_request "$API_BASE_URL/api/stats/series?start_ms=$start_ms&end_ms=$end_ms&slot_sec=3600")
    if [ $? -eq 0 ]; then
        local data_points=$(echo "$series_response" | grep -o '"total_points":[0-9]*' | cut -d: -f2)
        if [ "$data_points" -gt 0 ]; then
            log_success "Worker服务正常（有聚合数据）"
        else
            log_warning "Worker服务可能异常（无聚合数据）"
        fi
    else
        log_error "无法验证Worker服务状态"
        return 1
    fi
}

# 性能测试
performance_test() {
    log_info "执行性能测试..."
    
    local end_ms=$(date +%s)000
    local start_ms=$((end_ms - 3600000))  # 1小时前
    
    # 测试API响应时间
    local start_time=$(date +%s%N)
    make_request "$API_BASE_URL/api/stats/series?start_ms=$start_ms&end_ms=$end_ms&slot_sec=60" >/dev/null
    local end_time=$(date +%s%N)
    local duration=$(((end_time - start_time) / 1000000))  # 转换为毫秒
    
    if [ $duration -lt 5000 ]; then
        log_success "API响应时间: ${duration}ms (良好)"
    elif [ $duration -lt 10000 ]; then
        log_warning "API响应时间: ${duration}ms (一般)"
    else
        log_error "API响应时间: ${duration}ms (较慢)"
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "NewAPI监控系统健康检查"
    echo "========================================"
    echo "检查时间: $(date)"
    echo "API地址: $API_BASE_URL"
    echo "超时时间: ${TIMEOUT}秒"
    echo "========================================"
    echo ""
    
    local failed_checks=0
    
    # 执行各项检查
    check_docker_services || ((failed_checks++))
    echo ""
    
    check_frontend || ((failed_checks++))
    echo ""
    
    check_api || ((failed_checks++))
    echo ""
    
    check_database || ((failed_checks++))
    echo ""
    
    check_redis || ((failed_checks++))
    echo ""
    
    check_worker || ((failed_checks++))
    echo ""
    
    performance_test
    echo ""
    
    # 总结
    echo "========================================"
    if [ $failed_checks -eq 0 ]; then
        log_success "所有检查通过！系统运行正常"
        echo "========================================"
        exit 0
    else
        log_error "有 $failed_checks 项检查失败"
        echo "========================================"
        exit 1
    fi
}

# 执行主函数
main
