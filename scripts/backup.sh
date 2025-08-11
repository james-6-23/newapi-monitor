#!/bin/bash

# NewAPI监控系统数据库备份脚本
# 用于备份重要的配置数据和聚合数据

# 配置变量
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-new-api}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS}"

# 备份目录
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/newapi_monitor_backup_${DATE}.sql"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "开始备份NewAPI监控系统数据..."
echo "备份时间: $(date)"
echo "备份文件: $BACKUP_FILE"

# 检查mysqldump是否可用
if ! command -v mysqldump &> /dev/null; then
    echo "错误: mysqldump 命令未找到，请安装MySQL客户端工具"
    exit 1
fi

# 备份配置表和聚合数据（不包含大量的logs原始数据）
echo "正在备份配置数据和聚合数据..."

mysqldump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --add-drop-table \
    --complete-insert \
    --extended-insert \
    --comments \
    --dump-date \
    "$DB_NAME" \
    users \
    tokens \
    channels \
    models \
    vendors \
    abilities \
    agg_usage_hourly \
    > "$BACKUP_FILE"

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "配置数据备份成功！"
    
    # 压缩备份文件
    echo "正在压缩备份文件..."
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # 显示备份文件信息
    echo "备份完成！"
    echo "备份文件: $BACKUP_FILE"
    echo "文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # 可选：备份最近7天的logs数据样本
    echo "正在备份最近7天的logs数据样本..."
    LOGS_BACKUP_FILE="${BACKUP_DIR}/newapi_logs_sample_${DATE}.sql"
    
    mysqldump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --user="$DB_USER" \
        --password="$DB_PASS" \
        --single-transaction \
        --where="created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)" \
        "$DB_NAME" \
        logs \
        > "$LOGS_BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        gzip "$LOGS_BACKUP_FILE"
        echo "logs样本数据备份成功: ${LOGS_BACKUP_FILE}.gz"
    else
        echo "警告: logs样本数据备份失败"
        rm -f "$LOGS_BACKUP_FILE"
    fi
    
else
    echo "错误: 备份失败！"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 清理旧备份文件（保留最近30天）
echo "正在清理30天前的旧备份文件..."
find "$BACKUP_DIR" -name "newapi_*_backup_*.sql.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "newapi_logs_sample_*.sql.gz" -mtime +30 -delete

echo "备份脚本执行完成！"
echo "建议定期执行此脚本以确保数据安全"
