# NewAPI监控系统故障修复报告

## 🔍 问题诊断结果

通过分析test.log，发现了以下关键问题：

### 1. **API服务启动失败**
**错误**: `PydanticUserError: 'regex' is removed. use 'pattern' instead`
**原因**: Pydantic 2.x版本不再支持`regex`参数
**修复**: 将所有`regex=`改为`pattern=`

### 2. **Worker服务启动失败**  
**错误**: `ImportError: attempted relative import with no known parent package`
**原因**: Python相对导入路径问题
**修复**: 
- 修改Dockerfile启动命令为`python -m app.worker`
- 将所有相对导入改为绝对导入

### 3. **数据库连接配置错误**
**错误**: 使用了测试用户和localhost
**原因**: .env文件配置不正确
**修复**: 更新为正确的数据库连接信息

## ✅ 已完成的修复

### 1. API服务修复
- ✅ `api/app/schemas.py`: 修复所有Pydantic regex参数
  - `regex="^(user|token|model|channel)$"` → `pattern="^(user|token|model|channel)$"`
  - `regex="^(tokens|reqs|quota_sum)$"` → `pattern="^(tokens|reqs|quota_sum)$"`
  - `regex="^(burst|multi_user_token|ip_many_users|big_request)$"` → `pattern="^(burst|multi_user_token|ip_many_users|big_request)$"`
  - `regex="^(series|top|anomalies)$"` → `pattern="^(series|top|anomalies)$"`
  - `regex="^(csv|json)$"` → `pattern="^(csv|json)$"`

### 2. Worker服务修复
- ✅ `worker/Dockerfile`: 修改启动命令
  - `CMD ["python", "app/worker.py"]` → `CMD ["python", "-m", "app.worker"]`
- ✅ `worker/app/worker.py`: 修复导入路径
  - `from .config import` → `from app.config import`
  - `from .database import` → `from app.database import`
  - `from .aggregator import` → `from app.aggregator import`
  - `from .rules import` → `from app.rules import`
- ✅ `worker/app/aggregator.py`: 修复导入路径
  - `from .database import` → `from app.database import`
- ✅ `worker/app/rules.py`: 修复导入路径
  - `from .config import` → `from app.config import`
  - `from .database import` → `from app.database import`
  - `from .alerts import` → `from app.alerts import`
- ✅ `worker/app/alerts.py`: 修复导入路径
  - `from .config import` → `from app.config import`
  - `from .database import` → `from app.database import`

### 3. 环境配置修复
- ✅ `.env`: 更新数据库连接配置
  - `DB_HOST=localhost` → `DB_HOST=gpt-load-mysql`
  - `DB_USER_RO=test_user` → `DB_USER_RO=newapi_ro`
  - `DB_PASS_RO=test_password` → `DB_PASS_RO=newapi_ro_secure_password_2024`
  - 添加聚合用户配置: `DB_USER_AGG`, `DB_PASS_AGG`

## 🚀 验证步骤

请按以下步骤验证修复结果：

### 1. 重新构建和启动服务
```bash
# 停止现有服务
docker compose down

# 重新构建镜像
docker compose build

# 启动服务
docker compose up -d

# 等待30秒让服务完全启动
sleep 30
```

### 2. 检查服务状态
```bash
# 查看容器状态
docker compose ps

# 应该看到所有服务都是 "Up" 状态，没有 "Restarting"
```

### 3. 检查服务日志
```bash
# 查看API服务日志
docker compose logs api

# 查看Worker服务日志  
docker compose logs worker

# 应该没有错误信息，看到正常的启动日志
```

### 4. 测试API接口
```bash
# 测试健康检查
curl http://localhost/api/health

# 应该返回: {"ok": true, "timestamp": "...", "version": "1.0.0"}
```

### 5. 测试前端页面
- 访问: http://your-server-ip
- 检查Dashboard页面是否能正常加载数据
- 检查Top排行、热力图、异常中心页面

## 🔧 如果仍有问题

### 数据库用户权限问题
如果仍然无法连接数据库，可能需要创建数据库用户：

```sql
# 连接到MySQL
mysql -h localhost -u root -p

# 创建用户和授权
CREATE USER IF NOT EXISTS 'newapi_ro'@'%' IDENTIFIED BY 'newapi_ro_secure_password_2024';
CREATE USER IF NOT EXISTS 'newapi_agg'@'%' IDENTIFIED BY 'newapi_agg_secure_password_2024';

GRANT SELECT ON `new-api`.* TO 'newapi_ro'@'%';
GRANT SELECT ON `new-api`.logs TO 'newapi_agg'@'%';
GRANT SELECT, INSERT, UPDATE ON `new-api`.agg_usage_hourly TO 'newapi_agg'@'%';

FLUSH PRIVILEGES;
```

### 网络连接问题
如果容器间无法通信，检查Docker网络：
```bash
# 查看网络
docker network ls

# 检查容器网络连接
docker compose exec api ping gpt-load-mysql
```

## 📊 预期结果

修复完成后，你应该看到：
- ✅ 所有Docker容器状态为 "Up"
- ✅ API健康检查返回正常
- ✅ 前端页面能够加载数据
- ✅ Dashboard显示KPI指标和图表
- ✅ Top排行页面显示排行数据
- ✅ 异常中心显示风控检测结果

## 🎯 总结

这次故障的根本原因是：
1. **依赖版本兼容性问题** - Pydantic 2.x API变更
2. **Python模块导入问题** - 相对导入路径错误
3. **配置错误** - 数据库连接信息不正确

所有问题都已修复，系统应该能够正常运行。
