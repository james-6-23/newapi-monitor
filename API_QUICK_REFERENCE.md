# NewAPI 监控系统 API 快速参考

## 🚀 基础信息

**基础URL**: `http://your-domain/api`  
**数据格式**: JSON  
**缓存时间**: 60秒  

## 📋 接口列表

### 1. 健康检查
```
GET /health
```
**响应**: `{"ok": true, "version": "1.0.0"}`

### 2. 时序数据
```
GET /stats/series?start_ms={timestamp}&end_ms={timestamp}&slot_sec={seconds}
```
**参数**:
- `start_ms`: 开始时间戳(毫秒)
- `end_ms`: 结束时间戳(毫秒)  
- `slot_sec`: 时间粒度 (60/300/900/1800/3600)

**响应**:
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

### 3. TopN排行
```
GET /stats/top?start_ms={timestamp}&end_ms={timestamp}&by={dimension}&metric={metric}&limit={number}
```
**参数**:
- `by`: 维度 (user/token/model/channel)
- `metric`: 指标 (tokens/reqs/quota_sum)
- `limit`: 数量限制 (1-1000)

**响应**:
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
  "metric": "tokens"
}
```

### 4. 异常检测
```
GET /stats/anomalies?start_ms={timestamp}&end_ms={timestamp}&rule={rule_name}
```
**参数**:
- `rule`: 规则名称 (burst/multi_user_token/ip_many_users/big_request)
- `window_sec`: 时间窗口(可选)
- `users_threshold`: 用户数阈值(可选)
- `sigma`: 标准差倍数(可选)

**响应**:
```json
{
  "data": [
    {
      "token_id": 456,
      "token_name": "sk-xxx",
      "request_count": 150,
      "threshold": 120
    }
  ],
  "rule": "burst",
  "total_count": 5
}
```

### 5. 数据导出
```
GET /export/csv?query_type={type}&start_ms={timestamp}&end_ms={timestamp}&...
```
**参数**:
- `query_type`: 查询类型 (series/top/anomalies)
- 其他参数根据类型而定

**响应**: CSV文件下载

## 🔧 快速示例

### JavaScript
```javascript
// 获取最近24小时数据
const response = await fetch('/api/stats/series?' + new URLSearchParams({
  start_ms: Date.now() - 24 * 60 * 60 * 1000,
  end_ms: Date.now(),
  slot_sec: 3600
}));
const data = await response.json();
```

### cURL
```bash
# 健康检查
curl "http://localhost/api/health"

# 获取时序数据
curl "http://localhost/api/stats/series?start_ms=1691740800000&end_ms=1691827200000&slot_sec=300"

# 获取用户排行
curl "http://localhost/api/stats/top?start_ms=1691740800000&end_ms=1691827200000&by=user&metric=tokens&limit=10"

# 检测异常
curl "http://localhost/api/stats/anomalies?start_ms=1691740800000&end_ms=1691827200000&rule=burst"
```

### Python
```python
import requests
import time

base_url = "http://localhost/api"
end_time = int(time.time() * 1000)
start_time = end_time - 24 * 60 * 60 * 1000

# 获取时序数据
response = requests.get(f"{base_url}/stats/series", params={
    'start_ms': start_time,
    'end_ms': end_time,
    'slot_sec': 3600
})
data = response.json()
```

## ⚡ 时间粒度建议

| 时间范围 | 建议粒度 | slot_sec |
|---------|---------|----------|
| < 6小时 | 5分钟 | 300 |
| 6-24小时 | 15分钟 | 900 |
| 1-7天 | 1小时 | 3600 |
| > 7天 | 4小时 | 14400 |

## 🚨 常见错误

| 状态码 | 错误信息 | 解决方案 |
|--------|----------|----------|
| 400 | 开始时间必须小于结束时间 | 检查时间戳参数 |
| 400 | 不支持的时间粒度 | 使用有效的slot_sec值 |
| 400 | 不支持的维度 | 使用有效的by参数 |
| 503 | 服务不可用 | 检查数据库连接 |

## 📊 响应字段说明

### 时序数据字段
- `bucket`: 时间桶 (ISO 8601格式)
- `reqs`: 请求数量
- `tokens`: Token总数
- `users`: 活跃用户数
- `tokens_cnt`: Token种类数

### TopN数据字段
- `tokens`: Token消耗数
- `reqs`: 请求数量
- `quota_sum`: 配额消耗总和
- 维度特定字段 (user_id, token_id, model_name等)

### 异常数据字段
根据不同规则返回不同字段，详见完整API文档。

## 🔗 相关文档

- 📖 [完整API文档](./API_DOCUMENTATION.md)
- 🚀 [部署指南](./DEPLOYMENT.md)
- ✅ [验收清单](./ACCEPTANCE_CHECKLIST.md)
- 🏠 [项目说明](./README.md)

---

**版本**: v1.0.0 | **更新**: 2024-08-11
