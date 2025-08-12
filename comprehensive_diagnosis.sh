#!/bin/bash

# 全面诊断脚本 - 检查整个数据流

echo "🔍 NewAPI监控系统全面诊断"
echo "=================================="

source .env
MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME"

echo ""
echo "📊 1. 检查原始logs表数据"
echo "-----------------------------------"
echo "总记录数："
$MYSQL_CMD -e "SELECT COUNT(*) as total_logs FROM logs;"

echo ""
echo "最新10条记录："
$MYSQL_CMD -e "
SELECT 
    id,
    user_id,
    token_id,
    model_name,
    channel_id,
    request_count,
    prompt_tokens,
    completion_tokens,
    quota,
    created_at,
    FROM_UNIXTIME(created_at) as created_dt
FROM logs 
ORDER BY created_at DESC 
LIMIT 10;
"

echo ""
echo "时间范围分析："
$MYSQL_CMD -e "
SELECT 
    COUNT(*) as total_records,
    MIN(created_at) as min_timestamp,
    MAX(created_at) as max_timestamp,
    FROM_UNIXTIME(MIN(created_at)) as min_datetime,
    FROM_UNIXTIME(MAX(created_at)) as max_datetime,
    (MAX(created_at) - MIN(created_at)) / 3600 as hours_span
FROM logs;
"

echo ""
echo "📈 2. 检查聚合表数据"
echo "-----------------------------------"
echo "聚合表记录数："
$MYSQL_CMD -e "SELECT COUNT(*) as total_agg_records FROM agg_usage_hourly;"

echo ""
echo "聚合表结构："
$MYSQL_CMD -e "DESCRIBE agg_usage_hourly;"

echo ""
echo "聚合表最新数据："
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
echo "🔧 3. 检查Redis聚合状态"
echo "-----------------------------------"
echo "最后聚合时间："
docker exec newapi-monitor-redis-1 redis-cli GET last_aggregation_time

echo ""
echo "⏰ 4. 模拟聚合时间计算"
echo "-----------------------------------"
CURRENT_TIMESTAMP=$(date +%s)
CURRENT_HOUR=$(date -d @$CURRENT_TIMESTAMP '+%Y-%m-%d %H:00:00')
LAST_HOUR=$(date -d @$((CURRENT_TIMESTAMP - 3600)) '+%Y-%m-%d %H:00:00')
TWO_HOURS_AGO=$(date -d @$((CURRENT_TIMESTAMP - 7200)) '+%Y-%m-%d %H:00:00')

echo "当前时间: $(date -d @$CURRENT_TIMESTAMP)"
echo "当前小时: $CURRENT_HOUR"
echo "上一小时: $LAST_HOUR"
echo "两小时前: $TWO_HOURS_AGO"

echo ""
echo "检查上一小时是否有数据可聚合："
LAST_HOUR_START=$((CURRENT_TIMESTAMP - 3600))
LAST_HOUR_END=$((CURRENT_TIMESTAMP))

$MYSQL_CMD -e "
SELECT 
    COUNT(*) as records_in_last_hour,
    MIN(created_at) as min_ts,
    MAX(created_at) as max_ts,
    FROM_UNIXTIME(MIN(created_at)) as min_dt,
    FROM_UNIXTIME(MAX(created_at)) as max_dt
FROM logs 
WHERE created_at >= $LAST_HOUR_START 
  AND created_at < $LAST_HOUR_END;
"

echo ""
echo "🎯 5. 检查API查询的数据源"
echo "-----------------------------------"
echo "API是否直接查询logs表？让我们检查最近的API查询范围："

# 模拟前端最新的查询参数
START_MS=1754920231417
END_MS=1755006631417

echo "前端查询时间范围:"
echo "start_ms: $START_MS ($(date -d @$((START_MS/1000))))"
echo "end_ms: $END_MS ($(date -d @$((END_MS/1000))))"

echo ""
echo "在此时间范围内的logs记录："
$MYSQL_CMD -e "
SELECT 
    COUNT(*) as matching_logs,
    MIN(created_at) as min_ts,
    MAX(created_at) as max_ts
FROM logs 
WHERE created_at >= $((START_MS/1000))
  AND created_at < $((END_MS/1000));
"

echo ""
echo "在此时间范围内的聚合记录："
$MYSQL_CMD -e "
SELECT 
    COUNT(*) as matching_agg_records,
    MIN(hour_bucket) as min_bucket,
    MAX(hour_bucket) as max_bucket
FROM agg_usage_hourly 
WHERE hour_bucket >= FROM_UNIXTIME($((START_MS/1000)))
  AND hour_bucket < FROM_UNIXTIME($((END_MS/1000)));
"

echo ""
echo "🔍 6. 检查Worker聚合逻辑问题"
echo "-----------------------------------"
echo "检查是否有数据在当前小时边界："

# 检查最近2小时的数据分布
$MYSQL_CMD -e "
SELECT 
    DATE_FORMAT(FROM_UNIXTIME(created_at), '%Y-%m-%d %H:00:00') as hour_bucket,
    COUNT(*) as record_count,
    MIN(created_at) as min_ts,
    MAX(created_at) as max_ts
FROM logs 
WHERE created_at >= $((CURRENT_TIMESTAMP - 7200))
GROUP BY hour_bucket
ORDER BY hour_bucket DESC;
"

echo ""
echo "✅ 诊断完成！"
echo "=================================="
