# NewAPI 监控与风控系统 API 接口文档

## 📋 文档概览

**版本**: v1.0.0  
**基础URL**: `http://your-domain/api`  
**协议**: HTTP/HTTPS  
**数据格式**: JSON  
**字符编码**: UTF-8  

## 🔐 认证方式

当前版本暂未实现认证机制，后续版本将支持：
- API Key 认证
- JWT Token 认证
- OAuth 2.0 认证

## 📊 通用响应格式

### 成功响应
```json
{
  "data": [...],
  "total_points": 100,
  "timestamp": "2024-08-11T12:00:00Z"
}
```

### 错误响应
```json
{
  "error": "错误描述",
  "code": 400,
  "timestamp": "2024-08-11T12:00:00Z"
}
```

## 🏥 健康检查接口

### GET /health

检查系统健康状态

**请求参数**: 无

**响应示例**:
```json
{
  "ok": true,
  "timestamp": "2024-08-11T12:00:00Z",
  "version": "1.0.0"
}
```

**状态码**:
- `200`: 服务正常
- `503`: 服务不可用

---

## 📈 统计数据接口

### GET /stats/series

获取时序统计数据

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| start_ms | integer | 是 | 开始时间戳(毫秒) | 1691740800000 |
| end_ms | integer | 是 | 结束时间戳(毫秒) | 1691827200000 |
| slot_sec | integer | 否 | 时间粒度(秒) | 300 |

**时间粒度说明**:
- `60`: 1分钟
- `300`: 5分钟
- `900`: 15分钟
- `1800`: 30分钟
- `3600`: 1小时

**响应示例**:
```json
{
  "data": [
    {
      "bucket": "2024-08-11T12:00:00Z",
      "reqs": 1250,
      "tokens": 45000,
      "users": 25,
      "tokens_cnt": 8
    }
  ],
  "total_points": 24
}
```

**字段说明**:
- `bucket`: 时间桶
- `reqs`: 请求数
- `tokens`: Token总数
- `users`: 活跃用户数
- `tokens_cnt`: Token种类数

---

### GET /stats/top

获取TopN排行数据

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| start_ms | integer | 是 | 开始时间戳(毫秒) | - |
| end_ms | integer | 是 | 结束时间戳(毫秒) | - |
| by | string | 是 | 排序维度 | user, token, model, channel |
| metric | string | 是 | 排序指标 | tokens, reqs, quota_sum |
| limit | integer | 否 | 限制数量(1-1000) | 50 |

**响应示例 (by=user, metric=tokens)**:
```json
{
  "data": [
    {
      "user_id": 123,
      "username": "张三",
      "tokens": 50000,
      "reqs": 200,
      "quota_sum": 25.50
    }
  ],
  "by": "user",
  "metric": "tokens",
  "limit": 50
}
```

**不同维度的响应字段**:

#### 用户维度 (by=user)
- `user_id`: 用户ID
- `username`: 用户名
- `tokens`: Token数
- `reqs`: 请求数
- `quota_sum`: 配额消耗

#### Token维度 (by=token)
- `token_id`: Token ID
- `token_name`: Token名称
- `tokens`: Token数
- `reqs`: 请求数
- `quota_sum`: 配额消耗

#### 模型维度 (by=model)
- `model_name`: 模型名称
- `tokens`: Token数
- `reqs`: 请求数
- `quota_sum`: 配额消耗

#### 通道维度 (by=channel)
- `channel_id`: 通道ID
- `channel_name`: 通道名称
- `tokens`: Token数
- `reqs`: 请求数
- `quota_sum`: 配额消耗

---

### GET /stats/anomalies

获取异常检测数据

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| start_ms | integer | 是 | 开始时间戳(毫秒) | - |
| end_ms | integer | 是 | 结束时间戳(毫秒) | - |
| rule | string | 是 | 风控规则 | burst, multi_user_token, ip_many_users, big_request |
| window_sec | integer | 否 | 时间窗口(秒) | 60 |
| users_threshold | integer | 否 | 用户数阈值 | 5 |
| sigma | float | 否 | 标准差倍数 | 3.0 |
| limit_per_token | integer | 否 | Token请求数阈值 | 120 |

**风控规则说明**:
- `burst`: 突发频率检测
- `multi_user_token`: 共享Token检测
- `ip_many_users`: 同IP多账号检测
- `big_request`: 超大请求检测

**响应示例 (rule=burst)**:
```json
{
  "data": [
    {
      "token_id": 456,
      "token_name": "sk-xxx",
      "request_count": 150,
      "window_sec": 60,
      "threshold": 120,
      "first_request": "2024-08-11T12:00:00Z",
      "last_request": "2024-08-11T12:01:00Z"
    }
  ],
  "rule": "burst",
  "total_count": 5
}
```

**不同规则的响应字段**:

#### 突发频率 (rule=burst)
- `token_id`: Token ID
- `token_name`: Token名称
- `request_count`: 请求次数
- `window_sec`: 时间窗口
- `threshold`: 阈值
- `first_request`: 首次请求时间
- `last_request`: 最后请求时间

#### 共享Token (rule=multi_user_token)
- `token_id`: Token ID
- `token_name`: Token名称
- `user_count`: 用户数量
- `threshold`: 阈值
- `users`: 用户列表(逗号分隔)
- `total_requests`: 总请求数

#### 同IP多账号 (rule=ip_many_users)
- `ip`: IP地址
- `user_count`: 用户数量
- `threshold`: 阈值
- `users`: 用户列表(逗号分隔)
- `total_requests`: 总请求数

#### 超大请求 (rule=big_request)
- `token_id`: Token ID
- `token_name`: Token名称
- `user_id`: 用户ID
- `username`: 用户名
- `token_count`: Token数量
- `created_at`: 请求时间
- `mean_tokens`: 均值
- `std_tokens`: 标准差
- `threshold`: 阈值
- `sigma`: σ倍数

---

## 📥 数据导出接口

### GET /export/csv

导出CSV格式数据

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| query_type | string | 是 | 查询类型 | series, top, anomalies |
| start_ms | integer | 是 | 开始时间戳(毫秒) | - |
| end_ms | integer | 是 | 结束时间戳(毫秒) | - |
| ... | ... | 否 | 其他参数 | 根据query_type而定 |

**响应**: 
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="data.csv"`

**示例请求**:
```
GET /export/csv?query_type=series&start_ms=1691740800000&end_ms=1691827200000&slot_sec=300
```

---

## 🚨 错误码说明

| 状态码 | 错误类型 | 说明 |
|--------|----------|------|
| 200 | 成功 | 请求成功 |
| 400 | 请求错误 | 参数错误或格式不正确 |
| 404 | 未找到 | 接口不存在 |
| 500 | 服务器错误 | 内部服务器错误 |
| 503 | 服务不可用 | 数据库或Redis连接失败 |

**常见错误示例**:

```json
{
  "error": "开始时间必须小于结束时间",
  "code": 400,
  "timestamp": "2024-08-11T12:00:00Z"
}
```

```json
{
  "error": "不支持的时间粒度",
  "code": 400,
  "timestamp": "2024-08-11T12:00:00Z"
}
```

---

## 📝 请求示例

### cURL 示例

#### 获取健康状态
```bash
curl -X GET "http://localhost/api/health"
```

#### 获取时序数据
```bash
curl -X GET "http://localhost/api/stats/series?start_ms=1691740800000&end_ms=1691827200000&slot_sec=300"
```

#### 获取用户TopN
```bash
curl -X GET "http://localhost/api/stats/top?start_ms=1691740800000&end_ms=1691827200000&by=user&metric=tokens&limit=10"
```

#### 获取异常数据
```bash
curl -X GET "http://localhost/api/stats/anomalies?start_ms=1691740800000&end_ms=1691827200000&rule=burst"
```

#### 导出CSV数据
```bash
curl -X GET "http://localhost/api/export/csv?query_type=series&start_ms=1691740800000&end_ms=1691827200000" -o data.csv
```

### JavaScript 示例

```javascript
// 获取时序数据
const response = await fetch('/api/stats/series?' + new URLSearchParams({
  start_ms: Date.now() - 24 * 60 * 60 * 1000,
  end_ms: Date.now(),
  slot_sec: 300
}));
const data = await response.json();

// 获取TopN数据
const topResponse = await fetch('/api/stats/top?' + new URLSearchParams({
  start_ms: Date.now() - 24 * 60 * 60 * 1000,
  end_ms: Date.now(),
  by: 'user',
  metric: 'tokens',
  limit: 10
}));
const topData = await topResponse.json();
```

### Python 示例

```python
import requests
import time

# 基础URL
BASE_URL = "http://localhost/api"

# 获取时序数据
def get_series_data():
    end_time = int(time.time() * 1000)
    start_time = end_time - 24 * 60 * 60 * 1000
    
    params = {
        'start_ms': start_time,
        'end_ms': end_time,
        'slot_sec': 300
    }
    
    response = requests.get(f"{BASE_URL}/stats/series", params=params)
    return response.json()

# 获取TopN数据
def get_top_data(by='user', metric='tokens', limit=10):
    end_time = int(time.time() * 1000)
    start_time = end_time - 24 * 60 * 60 * 1000
    
    params = {
        'start_ms': start_time,
        'end_ms': end_time,
        'by': by,
        'metric': metric,
        'limit': limit
    }
    
    response = requests.get(f"{BASE_URL}/stats/top", params=params)
    return response.json()
```

---

## 🔄 数据更新频率

| 数据类型 | 更新频率 | 缓存时间 |
|----------|----------|----------|
| 时序数据 | 5分钟 | 60秒 |
| TopN数据 | 实时查询 | 60秒 |
| 异常数据 | 1-10分钟 | 60秒 |
| 聚合数据 | 5分钟 | 无缓存 |

---

## 📊 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| API响应时间 | < 5秒 | 95%的请求 |
| 并发处理能力 | 100 QPS | 峰值处理能力 |
| 缓存命中率 | > 80% | Redis缓存命中率 |
| 数据准确性 | 99.9% | 数据一致性保证 |

---

## 🛠️ 开发工具

### Swagger/OpenAPI

访问 `http://localhost/api/docs` 查看交互式API文档

### Postman Collection

可以导入以下Postman集合进行测试：

```json
{
  "info": {
    "name": "NewAPI Monitor API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/health",
          "host": ["{{baseUrl}}"],
          "path": ["health"]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost/api"
    }
  ]
}
```

---

## 📞 技术支持

如有API使用问题，请：

1. 查看错误响应中的详细信息
2. 检查请求参数格式和范围
3. 确认服务健康状态
4. 查看系统日志获取更多信息

**联系方式**: 
- 文档更新: 查看项目README.md
- 问题反馈: 提交GitHub Issue
- 技术讨论: 参考DEPLOYMENT.md

---

## 🧪 测试用例

### 时序数据接口测试

```bash
# 测试1: 获取最近1小时数据
curl -X GET "http://localhost/api/stats/series?start_ms=$(date -d '1 hour ago' +%s)000&end_ms=$(date +%s)000&slot_sec=300"

# 测试2: 获取最近24小时数据
curl -X GET "http://localhost/api/stats/series?start_ms=$(date -d '1 day ago' +%s)000&end_ms=$(date +%s)000&slot_sec=3600"

# 测试3: 参数错误测试
curl -X GET "http://localhost/api/stats/series?start_ms=invalid&end_ms=$(date +%s)000"
```

### TopN接口测试

```bash
# 测试1: 用户Token消耗排行
curl -X GET "http://localhost/api/stats/top?start_ms=$(date -d '1 day ago' +%s)000&end_ms=$(date +%s)000&by=user&metric=tokens&limit=10"

# 测试2: 模型请求数排行
curl -X GET "http://localhost/api/stats/top?start_ms=$(date -d '1 day ago' +%s)000&end_ms=$(date +%s)000&by=model&metric=reqs&limit=20"

# 测试3: 通道配额消耗排行
curl -X GET "http://localhost/api/stats/top?start_ms=$(date -d '1 day ago' +%s)000&end_ms=$(date +%s)000&by=channel&metric=quota_sum&limit=5"
```

### 异常检测接口测试

```bash
# 测试1: 突发频率检测
curl -X GET "http://localhost/api/stats/anomalies?start_ms=$(date -d '1 hour ago' +%s)000&end_ms=$(date +%s)000&rule=burst&window_sec=60&limit_per_token=100"

# 测试2: 共享Token检测
curl -X GET "http://localhost/api/stats/anomalies?start_ms=$(date -d '6 hours ago' +%s)000&end_ms=$(date +%s)000&rule=multi_user_token&users_threshold=3"

# 测试3: 超大请求检测
curl -X GET "http://localhost/api/stats/anomalies?start_ms=$(date -d '2 hours ago' +%s)000&end_ms=$(date +%s)000&rule=big_request&sigma=2.5"
```

## 📋 接口变更日志

### v1.0.0 (2024-08-11)
- ✅ 初始版本发布
- ✅ 实现健康检查接口
- ✅ 实现时序数据接口
- ✅ 实现TopN排行接口
- ✅ 实现异常检测接口
- ✅ 实现CSV导出接口
- ✅ 添加错误处理和缓存机制

### 计划中的功能 (v1.1.0)
- 🔄 API认证机制
- 🔄 实时WebSocket推送
- 🔄 批量查询接口
- 🔄 数据聚合配置接口
- 🔄 告警规则管理接口

## 🔧 SDK 和客户端库

### JavaScript/TypeScript SDK

```typescript
// 安装: npm install newapi-monitor-sdk
import { NewAPIMonitorClient } from 'newapi-monitor-sdk';

const client = new NewAPIMonitorClient({
  baseURL: 'http://localhost/api',
  timeout: 30000
});

// 获取时序数据
const seriesData = await client.getSeriesData({
  startMs: Date.now() - 24 * 60 * 60 * 1000,
  endMs: Date.now(),
  slotSec: 300
});

// 获取TopN数据
const topData = await client.getTopData({
  startMs: Date.now() - 24 * 60 * 60 * 1000,
  endMs: Date.now(),
  by: 'user',
  metric: 'tokens',
  limit: 10
});
```

### Python SDK

```python
# 安装: pip install newapi-monitor-sdk
from newapi_monitor import NewAPIMonitorClient
import time

client = NewAPIMonitorClient(
    base_url='http://localhost/api',
    timeout=30
)

# 获取时序数据
series_data = client.get_series_data(
    start_ms=int((time.time() - 24*3600) * 1000),
    end_ms=int(time.time() * 1000),
    slot_sec=300
)

# 获取异常数据
anomalies = client.get_anomalies(
    start_ms=int((time.time() - 3600) * 1000),
    end_ms=int(time.time() * 1000),
    rule='burst'
)
```

## 🚀 最佳实践

### 1. 时间范围选择
- **短期分析** (< 6小时): 使用300秒(5分钟)粒度
- **中期分析** (6-24小时): 使用900秒(15分钟)粒度
- **长期分析** (> 24小时): 使用3600秒(1小时)粒度

### 2. 分页和限制
- TopN查询建议limit不超过100
- 大数据量查询使用CSV导出
- 避免查询超过30天的详细数据

### 3. 缓存策略
- 相同参数的查询会被缓存60秒
- 实时性要求高的场景可以添加时间戳参数
- 使用HTTP缓存头优化客户端缓存

### 4. 错误处理
```javascript
try {
  const response = await fetch('/api/stats/series?...');
  if (!response.ok) {
    const error = await response.json();
    console.error('API Error:', error.error);
    return;
  }
  const data = await response.json();
  // 处理数据
} catch (error) {
  console.error('Network Error:', error);
}
```

### 5. 性能优化
- 使用适当的时间粒度减少数据点数量
- 避免频繁的小时间范围查询
- 合理使用limit参数控制返回数据量
- 考虑使用WebSocket获取实时数据(计划中)

## 📊 数据模型说明

### 时序数据模型
```typescript
interface SeriesDataPoint {
  bucket: string;      // ISO 8601时间格式
  reqs: number;        // 请求数量
  tokens: number;      // Token总数
  users: number;       // 活跃用户数
  tokens_cnt: number;  // Token种类数
}
```

### TopN数据模型
```typescript
interface TopItem {
  // 通用字段
  tokens: number;
  reqs: number;
  quota_sum: number;

  // 维度特定字段
  user_id?: number;
  username?: string;
  token_id?: number;
  token_name?: string;
  model_name?: string;
  channel_id?: number;
  channel_name?: string;
}
```

### 异常数据模型
```typescript
interface AnomalyItem {
  // 规则特定字段，根据rule类型不同而不同
  [key: string]: any;
}
```

**最后更新**: 2024-08-11
**文档版本**: v1.0.0
