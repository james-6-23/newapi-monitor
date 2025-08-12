#!/bin/bash

# 检查logs表结构和数据

echo "🔍 检查logs表结构和数据"
echo "=================================="

source .env
MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME"

echo ""
echo "📋 1. logs表结构"
echo "-----------------------------------"
$MYSQL_CMD -e "DESCRIBE logs;"

echo ""
echo "📊 2. logs表最新10条记录"
echo "-----------------------------------"
$MYSQL_CMD -e "
SELECT 
    id,
    user_id,
    token_id,
    model_name,
    channel_id,
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
echo "🎯 3. 检查Worker聚合SQL是否正确"
echo "-----------------------------------"
echo "测试聚合SQL（全局维度）："

CURRENT_TIMESTAMP=$(date +%s)
HOUR_AGO_TIMESTAMP=$((CURRENT_TIMESTAMP - 3600))

$MYSQL_CMD -e "
SELECT 
    DATE_FORMAT(FROM_UNIXTIME(created_at), '%Y-%m-%d %H:00:00') AS hour_bucket,
    COUNT(*) AS request_count,
    COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
    COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
    COALESCE(SUM(quota), 0) AS quota_sum,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(DISTINCT token_id) AS unique_tokens
FROM logs
WHERE created_at >= $HOUR_AGO_TIMESTAMP
  AND created_at < $CURRENT_TIMESTAMP
GROUP BY hour_bucket
ORDER BY hour_bucket;
"

echo ""
echo "🔍 4. 检查聚合表插入权限"
echo "-----------------------------------"
echo "测试插入一条聚合数据："

$MYSQL_CMD -e "
INSERT INTO agg_usage_hourly (
    hour_bucket, user_id, model_name, channel_id,
    request_count, total_tokens, prompt_tokens, completion_tokens,
    quota_sum, unique_users, unique_tokens
) VALUES (
    '2025-08-12 13:00:00', NULL, NULL, NULL,
    1, 100, 50, 50, 0.01, 1, 1
) ON DUPLICATE KEY UPDATE
    request_count = VALUES(request_count),
    total_tokens = VALUES(total_tokens),
    updated_at = CURRENT_TIMESTAMP;
"

echo "检查插入结果："
$MYSQL_CMD -e "SELECT COUNT(*) as test_records FROM agg_usage_hourly;"

echo ""
echo "🧹 5. 清理测试数据"
echo "-----------------------------------"
$MYSQL_CMD -e "DELETE FROM agg_usage_hourly WHERE request_count = 1 AND total_tokens = 100;"

echo ""
echo "✅ 检查完成！"
echo "=================================="
