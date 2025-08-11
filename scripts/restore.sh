#!/bin/bash

# NewAPI监控系统数据库恢复脚本
# 用于从备份文件恢复数据

# 配置变量
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-new-api}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS}"

# 显示使用说明
show_usage() {
    echo "使用方法: $0 <备份文件路径> [选项]"
    echo ""
    echo "选项:"
    echo "  --config-only    仅恢复配置数据（users, tokens, channels等）"
    echo "  --agg-only       仅恢复聚合数据（agg_usage_hourly）"
    echo "  --dry-run        预览模式，不实际执行恢复"
    echo "  --force          强制恢复，不进行确认"
    echo ""
    echo "示例:"
    echo "  $0 ./backups/newapi_monitor_backup_20240811_120000.sql.gz"
    echo "  $0 ./backups/newapi_monitor_backup_20240811_120000.sql.gz --config-only"
    echo "  $0 ./backups/newapi_monitor_backup_20240811_120000.sql.gz --dry-run"
}

# 检查参数
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

BACKUP_FILE="$1"
CONFIG_ONLY=false
AGG_ONLY=false
DRY_RUN=false
FORCE=false

# 解析选项
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        --agg-only)
            AGG_ONLY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
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

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

# 检查mysql是否可用
if ! command -v mysql &> /dev/null; then
    echo "错误: mysql 命令未找到，请安装MySQL客户端工具"
    exit 1
fi

echo "NewAPI监控系统数据库恢复工具"
echo "================================"
echo "备份文件: $BACKUP_FILE"
echo "目标数据库: $DB_NAME@$DB_HOST:$DB_PORT"
echo "恢复模式: $([ "$CONFIG_ONLY" = true ] && echo "仅配置数据" || [ "$AGG_ONLY" = true ] && echo "仅聚合数据" || echo "全部数据")"
echo "预览模式: $([ "$DRY_RUN" = true ] && echo "是" || echo "否")"
echo ""

# 检查文件类型并准备解压
TEMP_FILE=""
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "检测到压缩文件，正在解压..."
    TEMP_FILE="/tmp/newapi_restore_$(date +%s).sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    if [ $? -ne 0 ]; then
        echo "错误: 解压备份文件失败"
        exit 1
    fi
    RESTORE_FILE="$TEMP_FILE"
else
    RESTORE_FILE="$BACKUP_FILE"
fi

# 分析备份文件内容
echo "正在分析备份文件内容..."
TABLES_IN_BACKUP=$(grep -o "CREATE TABLE \`[^`]*\`" "$RESTORE_FILE" | sed 's/CREATE TABLE `\([^`]*\)`.*/\1/' | sort)
echo "备份文件包含的表:"
echo "$TABLES_IN_BACKUP" | sed 's/^/  - /'
echo ""

# 预览模式
if [ "$DRY_RUN" = true ]; then
    echo "=== 预览模式 ==="
    echo "将要执行的操作:"
    
    if [ "$CONFIG_ONLY" = true ]; then
        echo "  - 恢复配置表: users, tokens, channels, models, vendors, abilities"
    elif [ "$AGG_ONLY" = true ]; then
        echo "  - 恢复聚合表: agg_usage_hourly"
    else
        echo "  - 恢复所有表: $TABLES_IN_BACKUP"
    fi
    
    echo ""
    echo "注意: 这是预览模式，不会实际执行恢复操作"
    echo "要执行实际恢复，请移除 --dry-run 选项"
    
    # 清理临时文件
    [ -n "$TEMP_FILE" ] && rm -f "$TEMP_FILE"
    exit 0
fi

# 确认操作
if [ "$FORCE" != true ]; then
    echo "警告: 此操作将覆盖现有数据！"
    echo "请确认您已经备份了当前数据库"
    echo ""
    read -p "确定要继续恢复操作吗？(输入 'yes' 确认): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "操作已取消"
        [ -n "$TEMP_FILE" ] && rm -f "$TEMP_FILE"
        exit 0
    fi
fi

# 执行恢复
echo "开始恢复数据..."
echo "恢复时间: $(date)"

# 构建mysql命令
MYSQL_CMD="mysql --host=$DB_HOST --port=$DB_PORT --user=$DB_USER --password=$DB_PASS $DB_NAME"

if [ "$CONFIG_ONLY" = true ]; then
    echo "正在恢复配置数据..."
    # 只恢复配置表
    grep -A 1000000 "CREATE TABLE \`users\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    grep -A 1000000 "CREATE TABLE \`tokens\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    grep -A 1000000 "CREATE TABLE \`channels\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    grep -A 1000000 "CREATE TABLE \`models\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    grep -A 1000000 "CREATE TABLE \`vendors\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    grep -A 1000000 "CREATE TABLE \`abilities\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    
elif [ "$AGG_ONLY" = true ]; then
    echo "正在恢复聚合数据..."
    # 只恢复聚合表
    grep -A 1000000 "CREATE TABLE \`agg_usage_hourly\`" "$RESTORE_FILE" | grep -B 1000000 "UNLOCK TABLES;" | $MYSQL_CMD
    
else
    echo "正在恢复全部数据..."
    # 恢复整个备份文件
    $MYSQL_CMD < "$RESTORE_FILE"
fi

# 检查恢复结果
if [ $? -eq 0 ]; then
    echo "数据恢复成功！"
    
    # 显示恢复后的表统计
    echo ""
    echo "恢复后的数据统计:"
    mysql --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" --password="$DB_PASS" "$DB_NAME" -e "
        SELECT 
            TABLE_NAME as '表名',
            TABLE_ROWS as '行数',
            ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as '大小(MB)'
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = '$DB_NAME' 
            AND TABLE_NAME IN ('users', 'tokens', 'channels', 'models', 'vendors', 'abilities', 'agg_usage_hourly')
        ORDER BY TABLE_ROWS DESC;
    "
    
else
    echo "错误: 数据恢复失败！"
    [ -n "$TEMP_FILE" ] && rm -f "$TEMP_FILE"
    exit 1
fi

# 清理临时文件
[ -n "$TEMP_FILE" ] && rm -f "$TEMP_FILE"

echo ""
echo "恢复操作完成！"
echo "建议执行以下检查:"
echo "  1. 验证数据完整性"
echo "  2. 重启NewAPI监控服务"
echo "  3. 检查应用程序连接"
