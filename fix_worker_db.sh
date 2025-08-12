#!/bin/bash

# NewAPI监控系统Worker数据库修复脚本（远程MySQL版本）

echo "🔧 开始修复Worker数据库连接问题..."

# 1. 运行连接验证
echo "📋 验证远程MySQL连接..."
if [ -f "verify_remote_mysql.sh" ]; then
    chmod +x verify_remote_mysql.sh
    if ./verify_remote_mysql.sh; then
        echo "✅ MySQL连接验证通过"
    else
        echo "❌ MySQL连接验证失败，请检查配置"
        exit 1
    fi
else
    echo "⚠️  验证脚本不存在，跳过验证"
fi

# 2. 创建聚合表
echo "📊 创建聚合表..."
if [ -f "create_remote_agg_table.sh" ]; then
    chmod +x create_remote_agg_table.sh
    if ./create_remote_agg_table.sh; then
        echo "✅ 聚合表创建成功"
    else
        echo "❌ 聚合表创建失败"
        exit 1
    fi
else
    echo "❌ 聚合表创建脚本不存在"
    exit 1
fi

# 3. 重启Worker服务
echo "🔄 重启Worker服务..."
docker compose restart worker

# 4. 等待服务启动
echo "⏳ 等待Worker服务启动..."
sleep 10

# 5. 检查Worker状态
echo "📊 检查Worker服务状态..."
docker compose ps worker

# 6. 查看Worker日志
echo "📋 查看Worker最新日志..."
docker compose logs --tail=20 worker

echo ""
echo "🎉 修复脚本执行完成！"
echo "=================================================="
echo "📝 如果Worker仍有问题，请检查："
echo "1. 远程MySQL连接是否正常"
echo "2. 数据库用户权限是否正确"
echo "3. 环境变量是否正确传递"
echo "4. 网络防火墙设置"
