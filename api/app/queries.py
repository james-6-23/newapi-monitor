"""SQL查询模板模块"""

# 时序数据查询 - 支持不同时间粒度的聚合
SERIES_QUERY = """
WITH RECURSIVE time_series AS (
    -- 生成时间序列
    SELECT
        FROM_UNIXTIME(FLOOR(%(start_ms)s / 1000 / %(slot_sec)s) * %(slot_sec)s) AS bucket
    UNION ALL
    SELECT
        DATE_ADD(bucket, INTERVAL %(slot_sec)s SECOND)
    FROM time_series
    WHERE bucket < FROM_UNIXTIME(%(end_ms)s / 1000)
),
aggregated_data AS (
    SELECT
        FROM_UNIXTIME(FLOOR(created_at / %(slot_sec)s) * %(slot_sec)s) AS bucket,
        COUNT(*) AS reqs,
        COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS tokens,
        COUNT(DISTINCT user_id) AS users,
        COUNT(DISTINCT token_id) AS tokens_cnt
    FROM logs
    WHERE created_at >= %(start_ms)s / 1000
      AND created_at < %(end_ms)s / 1000
    GROUP BY bucket
)
SELECT 
    ts.bucket,
    COALESCE(ad.reqs, 0) AS reqs,
    COALESCE(ad.tokens, 0) AS tokens,
    COALESCE(ad.users, 0) AS users,
    COALESCE(ad.tokens_cnt, 0) AS tokens_cnt
FROM time_series ts
LEFT JOIN aggregated_data ad ON ts.bucket = ad.bucket
ORDER BY ts.bucket;
"""

# TopN查询模板 - 支持按不同维度和指标排序
TOP_QUERY_TEMPLATES = {
    'user': """
        SELECT 
            l.user_id,
            u.username,
            {metric_expr} AS {metric},
            COUNT(*) AS reqs,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS tokens,
            COALESCE(SUM(l.quota), 0) AS quota_sum
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
        GROUP BY l.user_id, u.username
        ORDER BY {metric} DESC
        LIMIT %(limit)s
    """,
    
    'token': """
        SELECT 
            l.token_id,
            t.name AS token_name,
            {metric_expr} AS {metric},
            COUNT(*) AS reqs,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS tokens,
            COALESCE(SUM(l.quota), 0) AS quota_sum
        FROM logs l
        LEFT JOIN tokens t ON l.token_id = t.id
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
        GROUP BY l.token_id, t.name
        ORDER BY {metric} DESC
        LIMIT %(limit)s
    """,
    
    'model': """
        SELECT 
            l.model_name,
            {metric_expr} AS {metric},
            COUNT(*) AS reqs,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS tokens,
            COALESCE(SUM(l.quota), 0) AS quota_sum
        FROM logs l
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
        GROUP BY l.model_name
        ORDER BY {metric} DESC
        LIMIT %(limit)s
    """,
    
    'channel': """
        SELECT 
            l.channel_id,
            c.name AS channel_name,
            {metric_expr} AS {metric},
            COUNT(*) AS reqs,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS tokens,
            COALESCE(SUM(l.quota), 0) AS quota_sum
        FROM logs l
        LEFT JOIN channels c ON l.channel_id = c.id
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
        GROUP BY l.channel_id, c.name
        ORDER BY {metric} DESC
        LIMIT %(limit)s
    """
}

# 指标表达式映射
METRIC_EXPRESSIONS = {
    'tokens': 'COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0)',
    'reqs': 'COUNT(*)',
    'quota_sum': 'COALESCE(SUM(l.quota), 0)'
}

# 异常检测查询模板
ANOMALY_QUERIES = {
    # 突发频率检测
    'burst': """
        SELECT 
            l.token_id,
            t.name AS token_name,
            COUNT(*) AS request_count,
            %(window_sec)s AS window_sec,
            %(limit_per_token)s AS threshold,
            MIN(l.created_at) AS first_request,
            MAX(l.created_at) AS last_request
        FROM logs l
        LEFT JOIN tokens t ON l.token_id = t.id
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
        GROUP BY l.token_id, t.name
        HAVING COUNT(*) >= %(limit_per_token)s
           AND TIMESTAMPDIFF(SECOND, MIN(l.created_at), MAX(l.created_at)) <= %(window_sec)s
        ORDER BY request_count DESC
    """,
    
    # 共享Token检测
    'multi_user_token': """
        SELECT 
            l.token_id,
            t.name AS token_name,
            COUNT(DISTINCT l.user_id) AS user_count,
            %(users_threshold)s AS threshold,
            GROUP_CONCAT(DISTINCT u.username ORDER BY u.username) AS users
        FROM logs l
        LEFT JOIN tokens t ON l.token_id = t.id
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
        GROUP BY l.token_id, t.name
        HAVING COUNT(DISTINCT l.user_id) >= %(users_threshold)s
        ORDER BY user_count DESC
    """,
    
    # 同IP多账号检测
    'ip_many_users': """
        SELECT 
            l.ip,
            COUNT(DISTINCT l.user_id) AS user_count,
            %(users_threshold)s AS threshold,
            GROUP_CONCAT(DISTINCT u.username ORDER BY u.username) AS users,
            COUNT(*) AS total_requests
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.created_at >= %(start_ms)s / 1000
          AND l.created_at < %(end_ms)s / 1000
          AND l.ip IS NOT NULL
          AND l.ip != ''
        GROUP BY l.ip
        HAVING COUNT(DISTINCT l.user_id) >= %(users_threshold)s
        ORDER BY user_count DESC
    """,
    
    # 超大请求检测（3σ原则）
    'big_request': """
        WITH stats AS (
            SELECT 
                AVG(prompt_tokens + completion_tokens) AS mean_tokens,
                STDDEV(prompt_tokens + completion_tokens) AS std_tokens
            FROM logs
            WHERE created_at >= %(start_ms)s / 1000
              AND created_at < %(end_ms)s / 1000
              AND (prompt_tokens + completion_tokens) > 0
        ),
        big_requests AS (
            SELECT 
                l.id,
                l.token_id,
                t.name AS token_name,
                l.user_id,
                u.username,
                (l.prompt_tokens + l.completion_tokens) AS token_count,
                l.created_at,
                s.mean_tokens,
                s.std_tokens,
                (s.mean_tokens + %(sigma)s * s.std_tokens) AS threshold
            FROM logs l
            LEFT JOIN tokens t ON l.token_id = t.id
            LEFT JOIN users u ON l.user_id = u.id
            CROSS JOIN stats s
            WHERE l.created_at >= %(start_ms)s / 1000
              AND l.created_at < %(end_ms)s / 1000
              AND (l.prompt_tokens + l.completion_tokens) > (s.mean_tokens + %(sigma)s * s.std_tokens)
        )
        SELECT 
            token_id,
            token_name,
            user_id,
            username,
            token_count,
            created_at,
            ROUND(mean_tokens, 2) AS mean_tokens,
            ROUND(std_tokens, 2) AS std_tokens,
            ROUND(threshold, 2) AS threshold,
            %(sigma)s AS sigma
        FROM big_requests
        ORDER BY token_count DESC
    """
}

def get_top_query(by: str, metric: str) -> str:
    """获取TopN查询SQL"""
    if by not in TOP_QUERY_TEMPLATES:
        raise ValueError(f"不支持的维度: {by}")
    
    if metric not in METRIC_EXPRESSIONS:
        raise ValueError(f"不支持的指标: {metric}")
    
    template = TOP_QUERY_TEMPLATES[by]
    metric_expr = METRIC_EXPRESSIONS[metric]
    
    return template.format(metric=metric, metric_expr=metric_expr)


def get_anomaly_query(rule: str) -> str:
    """获取异常检测查询SQL"""
    if rule not in ANOMALY_QUERIES:
        raise ValueError(f"不支持的规则: {rule}")
    
    return ANOMALY_QUERIES[rule]
