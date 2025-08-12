#!/bin/bash

# NewAPI监控系统 - 远程MySQL聚合表创建脚本
# 作者: Claude 4.0 sonnet

set -e

echo "🛠️  NewAPI监控系统 - 创建远程MySQL聚合表"
echo "=================================================="

# 1. 检查mysql客户端
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL客户端未安装，请先安装"
    exit 1
fi

# 2. 读取.env文件
if [ ! -f ".env" ]; then
    echo "❌ .env文件不存在"
    exit 1
fi

set -a
source .env
set +a

# 3. 验证环境变量
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ]; then
    echo "❌ 数据库连接参数不完整"
    exit 1
fi

# 4. 确定使用哪个用户
if [ -n "$DB_USER_AGG" ] && [ -n "$DB_PASS_AGG" ]; then
    MYSQL_USER="$DB_USER_AGG"
    MYSQL_PASS="$DB_PASS_AGG"
    echo "📋 使用聚合用户: $MYSQL_USER"
else
    MYSQL_USER="$DB_USER_RO"
    MYSQL_PASS="$DB_PASS_RO"
    echo "📋 使用只读用户: $MYSQL_USER"
fi

MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$MYSQL_USER -p$MYSQL_PASS"

# 5. 测试连接
echo "🔐 测试数据库连接..."
if ! $MYSQL_CMD -e "SELECT 1;" &>/dev/null; then
    echo "❌ 数据库连接失败"
    exit 1
fi
echo "✅ 数据库连接成功"

# 6. 检查聚合表是否已存在
echo "📊 检查聚合表..."
AGG_TABLE_EXISTS=$($MYSQL_CMD -e "USE $DB_NAME; SHOW TABLES LIKE 'agg_usage_hourly';" | wc -l)
if [ "$AGG_TABLE_EXISTS" -gt 1 ]; then
    echo "⚠️  聚合表已存在，是否要重新创建？(y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "ℹ️  跳过创建聚合表"
        exit 0
    fi
    echo "🗑️  删除现有聚合表..."
    $MYSQL_CMD -e "USE $DB_NAME; DROP TABLE agg_usage_hourly;"
fi

# 7. 创建聚合表
echo "📈 创建聚合表..."
$MYSQL_CMD << EOF
USE \`$DB_NAME\`;

CREATE TABLE agg_usage_hourly (
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
EOF

if [ $? -eq 0 ]; then
    echo "✅ 聚合表创建成功"
    
    # 验证表结构
    echo "📋 验证表结构..."
    $MYSQL_CMD -e "USE $DB_NAME; DESCRIBE agg_usage_hourly;"
    
    echo ""
    echo "🎉 聚合表创建完成！"
    echo "现在可以重启Worker服务来开始数据聚合"
else
    echo "❌ 聚合表创建失败"
    exit 1
fi

echo "=================================================="
