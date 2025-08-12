#!/bin/bash

# 彻底检查时间戳问题

echo "🔍 时间戳问题彻底排查"
echo "=================================="

source .env
MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME"

echo ""
echo "📋 1. 检查logs表结构和时间戳格式"
echo "-----------------------------------"
$MYSQL_CMD -e "DESCRIBE logs;" | grep -E "(created_at|Field|Type)"

echo ""
echo "📊 2. 检查logs表中的时间戳数据"
echo "-----------------------------------"
echo "最新5条记录的时间戳:"
$MYSQL_CMD -e "
SELECT 
    id,
    created_at as raw_timestamp,
    FROM_UNIXTIME(created_at) as converted_datetime,
    NOW() as current_mysql_time,
    UNIX_TIMESTAMP(NOW()) as current_unix_timestamp
FROM logs 
ORDER BY id DESC 
LIMIT 5;
"

echo ""
echo "📈 3. 检查时间戳范围和分布"
echo "-----------------------------------"
$MYSQL_CMD -e "
SELECT 
    MIN(created_at) as min_timestamp,
    MAX(created_at) as max_timestamp,
    FROM_UNIXTIME(MIN(created_at)) as min_datetime,
    FROM_UNIXTIME(MAX(created_at)) as max_datetime,
    COUNT(*) as total_records
FROM logs;
"

echo ""
echo "📅 4. 检查最近24小时的数据分布"
echo "-----------------------------------"
CURRENT_TIMESTAMP=$(date +%s)
YESTERDAY_TIMESTAMP=$((CURRENT_TIMESTAMP - 86400))

echo "当前时间戳: $CURRENT_TIMESTAMP"
echo "24小时前时间戳: $YESTERDAY_TIMESTAMP"

$MYSQL_CMD -e "
SELECT 
    COUNT(*) as records_last_24h,
    MIN(created_at) as min_ts_24h,
    MAX(created_at) as max_ts_24h,
    FROM_UNIXTIME(MIN(created_at)) as min_dt_24h,
    FROM_UNIXTIME(MAX(created_at)) as max_dt_24h
FROM logs 
WHERE created_at >= $YESTERDAY_TIMESTAMP;
"

echo ""
echo "🔧 5. 检查聚合表结构和数据"
echo "-----------------------------------"
AGG_EXISTS=$($MYSQL_CMD -e "SHOW TABLES LIKE 'agg_usage_hourly';" | wc -l)
if [ "$AGG_EXISTS" -gt 1 ]; then
    echo "聚合表结构:"
    $MYSQL_CMD -e "DESCRIBE agg_usage_hourly;" | grep -E "(hour_bucket|created_at|Field|Type)"
    
    echo ""
    echo "聚合表数据:"
    $MYSQL_CMD -e "
    SELECT 
        hour_bucket,
        request_count,
        total_tokens,
        created_at,
        updated_at
    FROM agg_usage_hourly 
    ORDER BY hour_bucket DESC 
    LIMIT 5;
    "
else
    echo "❌ 聚合表不存在"
fi

echo ""
echo "⏰ 6. 时间戳转换测试"
echo "-----------------------------------"
echo "测试当前时间的各种格式:"
$MYSQL_CMD -e "
SELECT 
    UNIX_TIMESTAMP(NOW()) as current_unix_timestamp,
    NOW() as current_datetime,
    UNIX_TIMESTAMP(NOW()) * 1000 as current_ms_timestamp,
    FROM_UNIXTIME(UNIX_TIMESTAMP(NOW())) as converted_back;
"

echo ""
echo "🧪 7. 测试API查询的时间范围"
echo "-----------------------------------"
# 模拟前端发送的时间戳
CURRENT_MS=$((CURRENT_TIMESTAMP * 1000))
START_MS=$((CURRENT_MS - 86400000))  # 24小时前的毫秒时间戳

echo "前端查询参数模拟:"
echo "start_ms: $START_MS"
echo "end_ms: $CURRENT_MS"
echo "转换为秒: $((START_MS / 1000)) - $((CURRENT_MS / 1000))"

$MYSQL_CMD -e "
SELECT 
    COUNT(*) as matching_records,
    MIN(created_at) as min_found,
    MAX(created_at) as max_found
FROM logs 
WHERE created_at >= $((START_MS / 1000))
  AND created_at < $((CURRENT_MS / 1000));
"
