#!/bin/bash

# 检查聚合表中的数据

echo "🔍 检查聚合表数据状态"
echo "=================================="

source .env
MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME"

echo ""
echo "📊 1. 检查聚合表记录数"
echo "-----------------------------------"
$MYSQL_CMD -e "SELECT COUNT(*) as total_records FROM agg_usage_hourly;"

echo ""
echo "📅 2. 检查最新的聚合数据"
echo "-----------------------------------"
$MYSQL_CMD -e "
SELECT 
    hour_bucket,
    user_id,
    model_name,
    channel_id,
    request_count,
    total_tokens,
    created_at,
    updated_at
FROM agg_usage_hourly 
ORDER BY updated_at DESC 
LIMIT 10;
"

echo ""
echo "📈 3. 检查聚合数据的时间范围"
echo "-----------------------------------"
$MYSQL_CMD -e "
SELECT 
    MIN(hour_bucket) as earliest_bucket,
    MAX(hour_bucket) as latest_bucket,
    COUNT(DISTINCT hour_bucket) as unique_hours,
    SUM(request_count) as total_requests,
    SUM(total_tokens) as total_tokens
FROM agg_usage_hourly;
"

echo ""
echo "🔍 4. 检查最近1小时的原始数据"
echo "-----------------------------------"
CURRENT_TIMESTAMP=$(date +%s)
HOUR_AGO_TIMESTAMP=$((CURRENT_TIMESTAMP - 3600))

echo "当前时间戳: $CURRENT_TIMESTAMP"
echo "1小时前时间戳: $HOUR_AGO_TIMESTAMP"

$MYSQL_CMD -e "
SELECT 
    COUNT(*) as recent_logs,
    MIN(created_at) as min_ts,
    MAX(created_at) as max_ts,
    FROM_UNIXTIME(MIN(created_at)) as min_dt,
    FROM_UNIXTIME(MAX(created_at)) as max_dt
FROM logs 
WHERE created_at >= $HOUR_AGO_TIMESTAMP;
"

echo ""
echo "🎯 5. 检查API查询的时间范围是否有聚合数据"
echo "-----------------------------------"
# 模拟前端最新的查询参数
START_MS=1754918987619
END_MS=1755005387619

echo "前端查询时间范围:"
echo "start_ms: $START_MS ($(date -d @$((START_MS/1000))))"
echo "end_ms: $END_MS ($(date -d @$((END_MS/1000))))"

$MYSQL_CMD -e "
SELECT 
    COUNT(*) as matching_agg_records,
    MIN(hour_bucket) as min_bucket,
    MAX(hour_bucket) as max_bucket
FROM agg_usage_hourly 
WHERE hour_bucket >= FROM_UNIXTIME($((START_MS/1000)))
  AND hour_bucket < FROM_UNIXTIME($((END_MS/1000)));
"
