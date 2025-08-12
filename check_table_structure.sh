#!/bin/bash

# 检查数据库表结构

source .env
MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME"

echo "📋 检查logs表结构..."
$MYSQL_CMD -e "DESCRIBE logs;"

echo ""
echo "📊 检查created_at字段的数据类型和示例值..."
$MYSQL_CMD -e "SELECT created_at, FROM_UNIXTIME(created_at) as datetime_format FROM logs ORDER BY id DESC LIMIT 5;"
