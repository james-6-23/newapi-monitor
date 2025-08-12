#!/bin/bash

# 检查远程MySQL数据库中的数据

echo "🔍 检查远程MySQL数据库中的数据..."

# 读取配置
source .env

MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME"

echo "📊 数据库连接信息："
echo "主机: $DB_HOST:$DB_PORT"
echo "数据库: $DB_NAME"
echo "用户: $DB_USER_RO"
echo ""

echo "📋 检查logs表数据..."
echo "总记录数:"
$MYSQL_CMD -e "SELECT COUNT(*) as total_logs FROM logs;"

echo ""
echo "最新10条记录的时间:"
$MYSQL_CMD -e "SELECT id, created_at, type, model_name FROM logs ORDER BY created_at DESC LIMIT 10;"

echo ""
echo "时间范围:"
$MYSQL_CMD -e "SELECT MIN(created_at) as earliest, MAX(created_at) as latest FROM logs;"

echo ""
echo "按日期统计记录数:"
$MYSQL_CMD -e "SELECT DATE(created_at) as date, COUNT(*) as count FROM logs GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 10;"

echo ""
echo "📊 检查其他表..."
echo "用户数:"
$MYSQL_CMD -e "SELECT COUNT(*) as total_users FROM users;"

echo "Token数:"
$MYSQL_CMD -e "SELECT COUNT(*) as total_tokens FROM tokens;"

echo "通道数:"
$MYSQL_CMD -e "SELECT COUNT(*) as total_channels FROM channels;"

echo ""
echo "🔍 检查聚合表是否存在..."
AGG_EXISTS=$($MYSQL_CMD -e "SHOW TABLES LIKE 'agg_usage_hourly';" | wc -l)
if [ "$AGG_EXISTS" -gt 1 ]; then
    echo "✅ 聚合表存在"
    echo "聚合表记录数:"
    $MYSQL_CMD -e "SELECT COUNT(*) as total_agg FROM agg_usage_hourly;"
else
    echo "❌ 聚合表不存在，需要创建"
fi
