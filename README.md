# NewAPI 监控与风控系统

面向 AI 中转站（`newapi`）的完整监控与风控解决方案，提供实时观测、可视化分析和智能风控功能。

## 🎯 核心功能

- **📊 实时监控**: 请求量、Token消耗、用户活跃度等关键指标
- **📈 可视化分析**: 时序趋势图、TopN排行榜、热力图等多维度展示
- **🛡️ 智能风控**: 突发频率检测、共享Token识别、异常IP监控、超大请求预警
- **🔔 实时告警**: 支持钉钉、飞书、企业微信等多平台Webhook告警
- **🚀 一键部署**: Docker Compose 快速部署，开箱即用

## 🏗️ 系统架构

```
[Browser] → [React Frontend] → [Nginx] → [FastAPI API] → [MySQL (new-api)]
                                            ↓
                                        [Redis Cache]
                                            ↓
                                        [Worker Tasks] → [Webhook Alerts]
```

## 🛠️ 技术栈

- **后端**: Python FastAPI + APScheduler + aiomysql + redis-py
- **前端**: React 18 + TypeScript + Ant Design + ECharts + TanStack Query
- **数据库**: MySQL 8.2 (只读连接现有 newapi 数据库)
- **缓存**: Redis 7
- **部署**: Docker + Docker Compose

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd newapi-monitor

# 复制环境变量配置
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，配置数据库连接信息：

```bash
# 数据库配置（连接到现有的 newapi MySQL）
DB_HOST=your-newapi-mysql-host
DB_PORT=3306
DB_NAME=new-api
DB_USER_RO=newapi_ro
DB_PASS_RO=your-password

# 告警配置
ALERT_WEBHOOK_URL=your-webhook-url
```

### 3. 数据库准备

执行数据库优化脚本（可选但推荐）：

```bash
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

### 5. 访问系统

- **监控面板**: http://localhost
- **API文档**: http://localhost/api/docs
- **健康检查**: http://localhost/api/health

## 📋 功能模块

### 监控面板
- **总览页**: 实时趋势图、关键指标统计
- **排行榜**: 用户/Token/模型/通道的TopN排行
- **热力图**: 按时间维度的请求热力分布
- **异常中心**: 风控规则触发记录与详情

### 风控规则
- **突发频率检测**: 检测Token在短时间内的异常高频请求
- **共享Token识别**: 发现被多个用户共享使用的Token
- **异常IP监控**: 监控单个IP下的多账号异常行为
- **超大请求预警**: 基于3σ原则检测异常大的Token消耗

## 🔧 配置说明

### 风控规则配置

可通过环境变量调整风控规则的敏感度：

```bash
# 突发频率检测
BURST_WINDOW_SEC=60          # 检测窗口（秒）
BURST_LIMIT_PER_TOKEN=120    # 阈值（次/窗口）

# 共享Token检测
TOKEN_MULTI_USER_THRESHOLD=2 # 用户数阈值

# 异常IP检测
IP_USERS_THRESHOLD=5         # 用户数阈值

# 超大请求检测
BIG_REQUEST_SIGMA=3          # 标准差倍数
```

### 告警配置

支持多种告警渠道：

```bash
ALERT_WEBHOOK_URL=your-webhook-url
ALERT_TYPE=dingtalk  # dingtalk, feishu, wechat_work
```

## 📊 性能优化

系统已针对大数据量场景进行优化：

- **索引优化**: 针对查询模式建立复合索引
- **缓存策略**: Redis缓存热点查询，TTL=60s
- **连接池**: 数据库连接池复用，减少连接开销
- **只读分离**: 使用只读账号，避免影响主业务

## 🔒 安全考虑

- **最小权限**: 数据库账号仅有必要的SELECT权限
- **参数化查询**: 防止SQL注入
- **白名单机制**: 支持IP/用户白名单配置
- **限流保护**: Nginx层面的API限流

## 📈 监控指标

系统提供丰富的监控指标：

- **业务指标**: 请求量、Token消耗、用户活跃度、错误率
- **系统指标**: API响应时间、数据库查询时间、缓存命中率
- **风控指标**: 规则触发次数、告警发送成功率

## 🛠️ 开发指南

### 本地开发

```bash
# 后端开发
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# 前端开发
cd frontend
npm install
npm run dev

# Worker开发
cd worker
pip install -r requirements.txt
python app/worker.py
```

### 添加新的风控规则

1. 在 `worker/app/rules.py` 中定义规则逻辑
2. 在 `worker/app/worker.py` 中注册定时任务
3. 在前端 `pages/Anomalies.tsx` 中添加展示

## 📝 更新日志

### v1.0.0
- 初始版本发布
- 基础监控与风控功能
- Docker化部署

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License
