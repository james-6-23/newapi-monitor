-- 在现有的new-api数据库中创建聚合表（远程MySQL版本）
-- 使用方法: mysql -h<host> -P<port> -u<user> -p<password> new-api < create_agg_table.sql

USE `new-api`;

-- 创建小时级聚合表
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

-- 验证表创建
SHOW TABLES LIKE 'agg_%';
DESCRIBE agg_usage_hourly;
