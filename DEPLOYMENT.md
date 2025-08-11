# NewAPI 监控与风控系统部署指南

本文档提供了 NewAPI 监控与风控系统的完整部署指南。

## 📋 部署前准备

### 系统要求

- **操作系统**: Linux (推荐 Ubuntu 20.04+ 或 CentOS 7+)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **内存**: 最低 4GB，推荐 8GB+
- **存储**: 最低 20GB 可用空间
- **网络**: 能够访问现有的 newapi MySQL 数据库

### 现有环境要求

- **MySQL**: 8.0+ (现有的 newapi 数据库)
- **数据库权限**: 能够创建用户和索引的管理员权限

## 🚀 快速部署

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd newapi-monitor
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

**重要配置项**:

```bash
# 数据库配置（连接到现有的 newapi MySQL）
DB_HOST=your-newapi-mysql-host
DB_PORT=3306
DB_NAME=new-api
DB_USER_RO=newapi_ro
DB_PASS_RO=your-secure-password
DB_USER_AGG=newapi_agg
DB_PASS_AGG=your-secure-password

# Redis 配置
REDIS_URL=redis://redis:6379/0

# 告警配置
ALERT_WEBHOOK_URL=your-webhook-url
ALERT_TYPE=dingtalk  # dingtalk, feishu, wechat_work
```

### 3. 数据库初始化

```bash
# 创建数据库用户（需要管理员权限）
mysql -h your-host -u root -p < scripts/create_users.sql

# 创建索引和优化数据库
mysql -h your-host -u root -p < scripts/db_optimization.sql
```

### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 验证部署

访问 http://your-server-ip 查看监控面板。

## 📊 详细配置

### 数据库配置

#### 创建专用用户

系统需要两个数据库用户：

1. **只读用户** (`newapi_ro`): 用于 API 查询
2. **聚合用户** (`newapi_agg`): 用于 Worker 写入聚合数据

```sql
-- 创建用户
CREATE USER 'newapi_ro'@'%' IDENTIFIED BY 'secure_password_1';
CREATE USER 'newapi_agg'@'%' IDENTIFIED BY 'secure_password_2';

-- 授权
GRANT SELECT ON `new-api`.* TO 'newapi_ro'@'%';
GRANT SELECT ON `new-api`.logs TO 'newapi_agg'@'%';
GRANT SELECT, INSERT, UPDATE ON `new-api`.agg_usage_hourly TO 'newapi_agg'@'%';

FLUSH PRIVILEGES;
```

#### 性能优化

执行索引优化脚本：

```bash
mysql -h your-host -u root -p < scripts/db_optimization.sql
```

主要优化包括：
- 为常用查询字段创建复合索引
- 添加 total_tokens 生成列
- 创建 agg_usage_hourly 聚合表

### 告警配置

#### 钉钉告警

1. 创建钉钉群机器人
2. 获取 Webhook URL
3. 配置环境变量：

```bash
ALERT_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=your-token
ALERT_TYPE=dingtalk
```

#### 飞书告警

```bash
ALERT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
ALERT_TYPE=feishu
```

#### 企业微信告警

```bash
ALERT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key
ALERT_TYPE=wechat_work
```

### 风控规则配置

编辑 `worker/rules.yaml` 文件自定义风控规则：

```yaml
rules:
  burst:
    enabled: true
    window_sec: 60
    limit_per_token: 120
  
  multi_user_token:
    enabled: true
    users_threshold: 2
  
  ip_many_users:
    enabled: true
    users_threshold: 5
  
  big_request:
    enabled: true
    sigma: 3

whitelist:
  ips:
    - "127.0.0.1"
    - "10.0.0.0/8"
  users:
    - "system"
    - "admin"
```

## 🔧 运维管理

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f [service-name]

# 更新服务
docker-compose pull
docker-compose up -d
```

### 数据备份

```bash
# 执行备份
chmod +x scripts/backup.sh
./scripts/backup.sh

# 定时备份（添加到 crontab）
0 2 * * * /path/to/newapi-monitor/scripts/backup.sh
```

### 数据恢复

```bash
# 恢复全部数据
chmod +x scripts/restore.sh
./scripts/restore.sh ./backups/newapi_monitor_backup_20240811_120000.sql.gz

# 仅恢复配置数据
./scripts/restore.sh ./backups/newapi_monitor_backup_20240811_120000.sql.gz --config-only
```

### 性能监控

```bash
# 检查数据库性能
mysql -h your-host -u root -p < scripts/performance_check.sql

# 清理旧数据
mysql -h your-host -u root -p < scripts/cleanup_data.sql
```

### 日志管理

```bash
# 查看 API 日志
docker-compose logs -f api

# 查看 Worker 日志
docker-compose logs -f worker

# 查看前端日志
docker-compose logs -f frontend
```

## 🔒 安全配置

### 网络安全

1. **防火墙配置**：只开放必要端口（80, 443）
2. **反向代理**：使用 Nginx 进行反向代理和 SSL 终止
3. **访问控制**：配置 IP 白名单

### 数据库安全

1. **最小权限原则**：使用专用的只读和聚合用户
2. **密码安全**：使用强密码并定期更换
3. **网络隔离**：数据库服务器与应用服务器网络隔离

### 应用安全

1. **环境变量**：敏感信息通过环境变量配置
2. **日志脱敏**：避免在日志中记录敏感信息
3. **定期更新**：及时更新依赖包和基础镜像

## 📈 扩展配置

### 高可用部署

1. **负载均衡**：使用 Nginx 或 HAProxy 进行负载均衡
2. **数据库集群**：配置 MySQL 主从复制
3. **Redis 集群**：配置 Redis 哨兵或集群模式

### 监控告警

1. **Prometheus 监控**：启用 metrics 端点
2. **Grafana 可视化**：创建监控仪表板
3. **健康检查**：配置服务健康检查

### 性能优化

1. **缓存策略**：调整 Redis 缓存 TTL
2. **数据库优化**：定期执行性能检查脚本
3. **资源限制**：配置 Docker 容器资源限制

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置和网络连通性
   - 验证用户权限

2. **前端无法访问**
   - 检查 Nginx 配置
   - 验证端口映射

3. **告警不发送**
   - 检查 Webhook URL 配置
   - 验证网络连通性

4. **数据不更新**
   - 检查 Worker 服务状态
   - 查看 Worker 日志

### 日志分析

```bash
# 查看错误日志
docker-compose logs --tail=100 api | grep ERROR
docker-compose logs --tail=100 worker | grep ERROR

# 查看性能日志
docker-compose logs --tail=100 api | grep "slow"
```

## 📞 技术支持

如遇到部署问题，请：

1. 查看相关服务日志
2. 检查配置文件
3. 参考故障排除章节
4. 提交 Issue 并附上详细的错误信息

---

**注意**: 请在生产环境部署前，先在测试环境验证所有功能正常。
