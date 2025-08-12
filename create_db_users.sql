-- NewAPI监控系统数据库用户创建脚本
-- 请在MySQL中执行此脚本来创建必要的用户和权限

-- 创建只读用户（用于API查询）
CREATE USER IF NOT EXISTS 'newapi_ro'@'%' IDENTIFIED BY 'newapi_ro_secure_password_2024';

-- 创建聚合用户（用于Worker写入聚合数据）
CREATE USER IF NOT EXISTS 'newapi_agg'@'%' IDENTIFIED BY 'newapi_agg_secure_password_2024';

-- 授权只读用户
GRANT SELECT ON `new-api`.* TO 'newapi_ro'@'%';

-- 授权聚合用户
GRANT SELECT ON `new-api`.logs TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.users TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.tokens TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.channels TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.models TO 'newapi_agg'@'%';

-- 创建聚合表（如果不存在）
CREATE TABLE IF NOT EXISTS `new-api`.agg_usage_hourly (
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

-- 授权聚合用户对聚合表的权限
GRANT SELECT, INSERT, UPDATE ON `new-api`.agg_usage_hourly TO 'newapi_agg'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 验证用户创建
SELECT User, Host FROM mysql.user WHERE User IN ('newapi_ro', 'newapi_agg');

-- 显示权限
SHOW GRANTS FOR 'newapi_ro'@'%';
SHOW GRANTS FOR 'newapi_agg'@'%';
