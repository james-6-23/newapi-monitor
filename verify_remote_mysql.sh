#!/bin/bash

# NewAPI监控系统 - 远程MySQL连接验证脚本
# 作者: Claude 4.0 sonnet

set -e  # 遇到错误立即退出

echo "🔍 NewAPI监控系统 - 远程MySQL连接验证"
echo "=================================================="

# 1. 检查mysql客户端是否安装
echo "📋 检查MySQL客户端..."
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL客户端未安装，正在安装..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y mysql-client
    elif command -v yum &> /dev/null; then
        sudo yum install -y mysql
    else
        echo "❌ 无法自动安装MySQL客户端，请手动安装"
        exit 1
    fi
fi
echo "✅ MySQL客户端已安装"

# 2. 读取.env文件
echo "📄 读取.env配置文件..."
if [ ! -f ".env" ]; then
    echo "❌ .env文件不存在"
    exit 1
fi

# 加载环境变量
set -a  # 自动导出变量
source .env
set +a

# 验证必要的环境变量
required_vars=("DB_HOST" "DB_PORT" "DB_NAME" "DB_USER_RO" "DB_PASS_RO")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 环境变量 $var 未设置"
        exit 1
    fi
done

echo "✅ 环境变量读取成功"
echo "   数据库主机: $DB_HOST"
echo "   数据库端口: $DB_PORT"
echo "   数据库名称: $DB_NAME"
echo "   只读用户: $DB_USER_RO"

# 3. 测试网络连接
echo ""
echo "🌐 测试网络连接..."
if timeout 10 bash -c "</dev/tcp/$DB_HOST/$DB_PORT"; then
    echo "✅ 网络连接正常 ($DB_HOST:$DB_PORT)"
else
    echo "❌ 无法连接到 $DB_HOST:$DB_PORT"
    echo "   请检查："
    echo "   1. 主机地址是否正确"
    echo "   2. 端口是否开放"
    echo "   3. 防火墙设置"
    exit 1
fi

# 4. 测试MySQL连接（只读用户）
echo ""
echo "🔐 测试MySQL连接（只读用户）..."
MYSQL_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO --connect-timeout=10"

if $MYSQL_CMD -e "SELECT 1;" &>/dev/null; then
    echo "✅ 只读用户连接成功"
else
    echo "❌ 只读用户连接失败"
    echo "   请检查用户名和密码是否正确"
    exit 1
fi

# 5. 验证数据库是否存在
echo ""
echo "🗄️  验证数据库..."
DB_EXISTS=$($MYSQL_CMD -e "SHOW DATABASES LIKE '$DB_NAME';" | wc -l)
if [ "$DB_EXISTS" -gt 1 ]; then
    echo "✅ 数据库 '$DB_NAME' 存在"
else
    echo "❌ 数据库 '$DB_NAME' 不存在"
    exit 1
fi

# 6. 检查必要的表
echo ""
echo "📊 检查必要的表..."
required_tables=("logs" "users" "tokens" "channels")
missing_tables=()

for table in "${required_tables[@]}"; do
    TABLE_EXISTS=$($MYSQL_CMD -e "USE $DB_NAME; SHOW TABLES LIKE '$table';" | wc -l)
    if [ "$TABLE_EXISTS" -gt 1 ]; then
        echo "✅ 表 '$table' 存在"
    else
        echo "❌ 表 '$table' 不存在"
        missing_tables+=("$table")
    fi
done

if [ ${#missing_tables[@]} -gt 0 ]; then
    echo "❌ 缺少必要的表: ${missing_tables[*]}"
    echo "   请确保new-api系统已正确安装"
    exit 1
fi

# 7. 检查聚合表是否存在
echo ""
echo "📈 检查聚合表..."
AGG_TABLE_EXISTS=$($MYSQL_CMD -e "USE $DB_NAME; SHOW TABLES LIKE 'agg_usage_hourly';" | wc -l)
if [ "$AGG_TABLE_EXISTS" -gt 1 ]; then
    echo "✅ 聚合表 'agg_usage_hourly' 已存在"
    
    # 显示表结构
    echo "📋 聚合表结构："
    $MYSQL_CMD -e "USE $DB_NAME; DESCRIBE agg_usage_hourly;"
else
    echo "⚠️  聚合表 'agg_usage_hourly' 不存在，需要创建"
fi

# 8. 测试聚合用户连接（如果配置了）
echo ""
if [ -n "$DB_USER_AGG" ] && [ -n "$DB_PASS_AGG" ]; then
    echo "🔐 测试MySQL连接（聚合用户）..."
    MYSQL_AGG_CMD="mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_AGG -p$DB_PASS_AGG --connect-timeout=10"
    
    if $MYSQL_AGG_CMD -e "SELECT 1;" &>/dev/null; then
        echo "✅ 聚合用户连接成功"
        
        # 测试写入权限
        if $MYSQL_AGG_CMD -e "USE $DB_NAME; SELECT COUNT(*) FROM logs LIMIT 1;" &>/dev/null; then
            echo "✅ 聚合用户具有读取权限"
        else
            echo "❌ 聚合用户缺少读取权限"
        fi
    else
        echo "❌ 聚合用户连接失败"
        echo "   如果使用root用户，请确保密码正确"
    fi
else
    echo "ℹ️  未配置聚合用户，将使用只读用户"
fi

# 9. 显示数据库统计信息
echo ""
echo "📊 数据库统计信息..."
echo "日志记录数: $($MYSQL_CMD -e "USE $DB_NAME; SELECT COUNT(*) FROM logs;" | tail -n1)"
echo "用户数: $($MYSQL_CMD -e "USE $DB_NAME; SELECT COUNT(*) FROM users;" | tail -n1)"
echo "Token数: $($MYSQL_CMD -e "USE $DB_NAME; SELECT COUNT(*) FROM tokens;" | tail -n1)"
echo "通道数: $($MYSQL_CMD -e "USE $DB_NAME; SELECT COUNT(*) FROM channels;" | tail -n1)"

# 10. 生成创建聚合表的命令
if [ "$AGG_TABLE_EXISTS" -le 1 ]; then
    echo ""
    echo "🛠️  创建聚合表命令："
    echo "mysql -h$DB_HOST -P$DB_PORT -u$DB_USER_RO -p$DB_PASS_RO $DB_NAME < create_agg_table.sql"
    echo ""
    echo "或者运行: ./create_remote_agg_table.sh"
fi

echo ""
echo "🎉 MySQL连接验证完成！"
echo "=================================================="
