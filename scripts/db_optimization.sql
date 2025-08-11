-- NewAPI 监控系统数据库优化脚本
-- 执行前请确保已连接到正确的数据库

USE `new-api`;

-- 1. 创建性能索引
-- 这些索引针对监控查询模式进行优化

-- 用户维度查询索引
CREATE INDEX IF NOT EXISTS idx_logs_user_time ON logs(user_id, created_at);

-- Token维度查询索引  
CREATE INDEX IF NOT EXISTS idx_logs_token_time ON logs(token_id, created_at);

-- 模型维度查询索引
CREATE INDEX IF NOT EXISTS idx_logs_model_time ON logs(model_name, created_at);

-- IP维度查询索引（用于风控）
CREATE INDEX IF NOT EXISTS idx_logs_ip_time ON logs(ip, created_at);

-- 通道维度查询索引
CREATE INDEX IF NOT EXISTS idx_logs_channel_time ON logs(channel_id, created_at);

-- 2. 添加生成列（如果不存在）
-- 总Token数生成列，便于统计和异常检测
ALTER TABLE logs 
ADD COLUMN IF NOT EXISTS total_tokens BIGINT AS (prompt_tokens + completion_tokens) STORED;

-- 为生成列创建索引
CREATE INDEX IF NOT EXISTS idx_logs_total_tokens ON logs(total_tokens);

-- 3. 创建聚合表（如果不存在）
-- 小时级预聚合表，提升大盘查询性能
CREATE TABLE IF NOT EXISTS agg_usage_hourly (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hour_bucket DATETIME NOT NULL COMMENT '小时时间桶',
    user_id INT DEFAULT NULL COMMENT '用户ID，NULL表示全局聚合',
    model_name VARCHAR(255) DEFAULT NULL COMMENT '模型名称，NULL表示全局聚合',
    channel_id INT DEFAULT NULL COMMENT '通道ID，NULL表示全局聚合',
    
    -- 聚合指标
    request_count BIGINT NOT NULL DEFAULT 0 COMMENT '请求数',
    total_tokens BIGINT NOT NULL DEFAULT 0 COMMENT '总Token数',
    prompt_tokens BIGINT NOT NULL DEFAULT 0 COMMENT '输入Token数',
    completion_tokens BIGINT NOT NULL DEFAULT 0 COMMENT '输出Token数',
    quota_sum DECIMAL(20,2) NOT NULL DEFAULT 0.00 COMMENT '配额消耗总和',
    unique_users INT NOT NULL DEFAULT 0 COMMENT '独立用户数',
    unique_tokens INT NOT NULL DEFAULT 0 COMMENT '独立Token数',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 唯一约束，支持幂等更新
    UNIQUE KEY uk_agg_hourly (hour_bucket, user_id, model_name, channel_id),
    
    -- 查询索引
    KEY idx_agg_hour_bucket (hour_bucket),
    KEY idx_agg_user_hour (user_id, hour_bucket),
    KEY idx_agg_model_hour (model_name, hour_bucket),
    KEY idx_agg_channel_hour (channel_id, hour_bucket)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='小时级使用量聚合表';

-- 4. 创建数据库用户（如果不存在）
-- 只读用户，用于API查询
CREATE USER IF NOT EXISTS 'newapi_ro'@'%' IDENTIFIED BY 'newapi_ro_password_change_me';
GRANT SELECT ON `new-api`.* TO 'newapi_ro'@'%';

-- 聚合用户，用于Worker写入聚合数据
CREATE USER IF NOT EXISTS 'newapi_agg'@'%' IDENTIFIED BY 'newapi_agg_password_change_me';
GRANT SELECT ON `new-api`.logs TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.users TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.tokens TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.channels TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.models TO 'newapi_agg'@'%';
GRANT SELECT, INSERT, UPDATE ON `new-api`.agg_usage_hourly TO 'newapi_agg'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 5. 优化配置建议（需要DBA权限）
-- 以下配置需要在my.cnf中设置，这里仅作为参考

/*
-- 增加CTE递归深度限制
SET GLOBAL cte_max_recursion_depth = 10000;

-- 优化查询缓存（MySQL 8.0已移除query_cache）
-- 改为使用Redis缓存

-- 优化InnoDB设置
innodb_buffer_pool_size = 1G  # 根据内存大小调整
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

-- 优化连接设置
max_connections = 200
wait_timeout = 28800
interactive_timeout = 28800
*/

-- 6. 分区表建议（大数据量场景）
-- 如果logs表数据量很大（>1000万行），可以考虑按月分区

/*
-- 分区示例（需要重建表，请谨慎操作）
ALTER TABLE logs PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
    PARTITION p202401 VALUES LESS THAN (202402),
    PARTITION p202402 VALUES LESS THAN (202403),
    PARTITION p202403 VALUES LESS THAN (202404),
    -- ... 继续添加分区
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
*/

-- 脚本执行完成
SELECT 'NewAPI监控系统数据库优化完成！' AS message;
