# 0. 目标与范围

面向你的 AI 中转站（`newapi`），提供一套可落地的 **观测 + 可视化 + 风控** 方案：

- **后端**：Python FastAPI（统计 API） + Worker（定时聚合与告警），只读连接 MySQL 8.2 的 `new-api` 数据库；Redis 做缓存。
- **前端**：React + TypeScript + Ant Design + ECharts + TanStack Query/Table，提供时序趋势、Top 排行、热力图、异常中心与详情。
- **部署**：Docker Compose 一键起（api、worker、redis、frontend、可选 superset），同网段对接现有 `newapi` MySQL。
- **风控**：突发频率、共享 Token、同 IP 多账号、超大请求（3σ）等可配置规则，Webhook 告警。

> 说明：本开发文档与之前给到的「MVP 可跑版」保持一致，并在此基础上给出**完整的前后端实现细节、接口契约、代码骨架、构建发布与运维指南**。

---

# 1. 架构与技术栈

```text
[Browser]
  React + TS + AntD + ECharts + TanStack Query
        │  REST (JSON)
        ▼
[FastAPI 统计 API]  ——  [Redis 缓存]
        │  RO 连接
        ▼
[MySQL 8.2: new-api]

[Worker 定时任务] → 聚合(agg_usage_hourly) & 规则检测 → Webhook 告警

[Docker Compose]：frontend / api / worker / redis / (optional superset)
```

**选型**

- 后端：FastAPI、aiomysql、APScheduler、redis-py；（可选）prometheus-client 暴露 /metrics。
- 前端：Vite、React 18、TypeScript、Ant Design、ECharts、TanStack Query & Table。
- 可视化备选：Apache Superset（可选，用于快速 BI 看板）。

---

# 2. 数据模型要点（与 DDL 对应）

- 明细：`logs`（请求级，含 user\_id/token\_id/model/channel/tokens/ip/时间）
- 聚合：`quota_data`（用户名/模型/时间粒度聚合，辅助统计）、`agg_usage_hourly`（我们新增的小时级预汇总表）
- 维度：`users`、`tokens`、`channels`、`models`、`vendors`、`abilities`
- 计费/安全：`top_ups`、`redemptions`、`two_fas`、`two_fa_backup_codes`

**关键关系**（逻辑外键）：

- `users.id → logs.user_id / tokens.user_id / quota_data.user_id / ...`
- `tokens.id → logs.token_id`
- `channels.id → logs.channel_id`
- `models.model_name → logs.model_name`
- `vendors.id → models.vendor_id`

---

# 3. 性能与索引

> 在大多数查询中，条件是 **等值 + 时间范围**。MySQL 8.2 支持窗口函数，CTE 可配递归深度。

建议索引与生成列（一次性）：

```sql
CREATE INDEX idx_logs_user_time  ON `new-api`.logs(user_id, created_at);
CREATE INDEX idx_logs_token_time ON `new-api`.logs(token_id, created_at);
CREATE INDEX idx_logs_model_time ON `new-api`.logs(model_name, created_at);
CREATE INDEX idx_logs_ip_time    ON `new-api`.logs(ip, created_at);

ALTER TABLE `new-api`.logs
  ADD COLUMN total_tokens BIGINT AS (prompt_tokens + completion_tokens) STORED,
  ADD INDEX idx_logs_total_tokens (total_tokens);
```

> 超大表再考虑 RANGE 分区（按月）；统计大盘尽量走 `agg_usage_hourly`。

---

# 4. 接口设计（FastAPI）

## 4.1 统一约定

- 基础路径：`/api`（通过 Nginx 反代映射到 FastAPI 8080）
- 时间：毫秒时间戳 `start_ms/end_ms`；粒度 `slot_sec`（60=1分，3600=1小时）。
- 成功返回：HTTP 200 JSON；失败返回：`{"error":"...","code":...}`。
- CORS：推荐同域反代；若跨域需在 FastAPI 开 CORS。

## 4.2 Endpoints

### GET `/api/health`

- 用途：健康检查
- 响应：`{"ok": true}`

### GET `/api/stats/series`

- 参数：`start_ms`(req) `end_ms`(req) `slot_sec`(opt, 默认60)
- 返回：

```json
[
  {"bucket": "2025-08-11T10:00:00", "reqs": 123, "tokens": 4567, "users": 8, "tokens_cnt": 9},
  ...
]
```

### GET `/api/stats/top`

- 参数：`start_ms` `end_ms` `by` in [user, token, model, channel] `metric` in [tokens, reqs, quota\_sum] `limit` 默认50
- 返回示例（by=user）：

```json
[
  {"user_id":1, "username":"alice", "tokens":9999, "reqs":120}, ...
]
```

### GET `/api/stats/anomalies`

- 参数：`start_ms` `end_ms` `rule` in [burst, multi\_user\_token, ip\_many\_users, big\_request]
- 规则附带参数：`window_sec`（burst）`users_threshold`（ip\_many\_users）`sigma`（big\_request）
- 返回：各自 SQL 的行集（见后端实现）

### （可选）GET `/api/export/csv`

- 作用：将某个查询结果导出 CSV（分页或限制 MAX\_ROWS）

## 4.3 错误码

- `400`：参数错误；`500`：内部错误；`504`：上游（DB）超时。

---

# 5. 后端实现（FastAPI）

## 5.1 目录结构

```
api/
├─ Dockerfile
├─ requirements.txt
└─ app/
   ├─ main.py          # 路由、缓存、连接池
   ├─ queries.py       # SQL 模板
   ├─ deps.py          # 连接池/Redis 依赖
   ├─ schemas.py       # Pydantic 响应模型（可选）
   └─ config.py        # 环境变量
```

## 5.2 关键代码（摘录）

**连接池 & Redis**（长连减少握手）：

```python
# deps.py
import os, aiomysql, redis.asyncio as redis
_pool = None

async def get_pool():
    global _pool
    if not _pool:
        _pool = await aiomysql.create_pool(
            minsize=1, maxsize=10,
            host=os.getenv('DB_HOST'), port=int(os.getenv('DB_PORT',3306)),
            user=os.getenv('DB_USER_RO'), password=os.getenv('DB_PASS_RO'), db=os.getenv('DB_NAME'),
            autocommit=True, charset='utf8mb4'
        )
    return _pool

_redis = None
async def get_redis():
    global _redis
    if not _redis:
        _redis = redis.from_url(os.getenv('REDIS_URL'))
    return _redis
```

**查询执行**（多语句支持、DictCursor）：

```python
# main.py 片段
async def query(sql: str, params: dict):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            for stmt in [s for s in sql.split(';\n') if s.strip()]:
                await cur.execute(stmt, params)
            return await cur.fetchall()
```

**缓存策略**：Key 由路径 + 归一化参数组成；默认 TTL=60s，可通过 `.env` 调整。

**安全**：避免将原生入参直接拼接 SQL；仅用参数化；必要时对 `order_by` 做白名单（已在后端模板内使用 `format` 严格控制）。

## 5.3 Worker（聚合 + 告警）

- APScheduler 周期：聚合（5min）、burst（1min）、multi\_user\_token（5min）、ip\_many\_users（5min）、big\_request（10min）
- 告警：钉钉/飞书/企业微信 Webhook 文本；可扩展 email/sms
- 规则来源：ENV 默认 + `rules.yaml` 覆盖（热更新需容器重启）
- 幂等：聚合使用 `ON DUPLICATE KEY UPDATE`
- 只读/最小权限：Worker 仅对 `agg_usage_hourly` 有 INSERT 权限，其余 SELECT

## 5.4 指标与日志（可选）

- Prometheus：在 API 暴露 `/metrics`（request latency、DB RT、cache hit），用 `prometheus_fastapi_instrumentator`
- 日志：uvicorn/gunicorn 结构化日志（JSON），落到 stdout，采集到 Loki/ELK（可选）

---

# 6. 风控规则（定义与 SQL）

## 6.1 规则

1. **突发频率（burst）**：同一 Token 在 `window_sec` 内请求数 ≥ 阈值
2. **共享 Token（multi\_user\_token）**：同一 Token 在区间内被 ≥N 个用户使用
3. **同 IP 多账号（ip\_many\_users）**：同一 IP 在区间内触发 ≥N 个用户
4. **超大请求（big\_request, 3σ）**：单次 token > 均值 + σ×标准差

> 白名单：对内部 token/user/channel/ip 做豁免；在 SQL 外层过滤或命中后在代码中过滤

## 6.2 SQL 模板

- 已内置在 `api/app/queries.py` 与 `worker/app/worker.py`（见前文）。
- MySQL 8.2 注意：无 `QUALIFY` 关键字，需使用子查询过滤窗口结果。

---

# 7. 前端实现（React + TS + AntD + ECharts）

## 7.1 目录结构

```
frontend/
├─ Dockerfile
├─ nginx.conf
├─ package.json
├─ tsconfig.json
├─ vite.config.ts
└─ src/
   ├─ main.tsx
   ├─ app/
   │  ├─ routes.tsx
   │  └─ queryClient.ts
   ├─ api/
   │  ├─ client.ts        # fetch 封装 + 错误处理
   │  └─ stats.ts         # /stats 接口函数与 TS 类型
   ├─ components/
   │  ├─ Chart.tsx        # 通用 ECharts 容器
   │  ├─ KPICard.tsx
   │  ├─ RangeFilter.tsx  # 时间/模型/通道筛选
   │  └─ DataTable.tsx
   ├─ pages/
   │  ├─ Dashboard.tsx    # 总览（时序 + KPI）
   │  ├─ Top.tsx          # TopN 排行
   │  ├─ Heatmap.tsx      # 周×小时热力
   │  └─ Anomalies.tsx    # 异常中心
   └─ styles/
      └─ index.css
```

## 7.2 关键代码（摘录）

**统一客户端**

```ts
// src/api/client.ts
export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function request<T>(path: string, params?: Record<string, any>): Promise<T> {
  const url = new URL(API_BASE + path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString(), { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
export default { get: request };
```

**接口类型与封装**

```ts
// src/api/stats.ts
import api from './client';

export type SeriesRow = { bucket: string; reqs: number; tokens: number; users: number; tokens_cnt: number };
export const getSeries = (p:{start_ms:number; end_ms:number; slot_sec?:number;}) =>
  api.get<SeriesRow[]>('/stats/series', p);

export type TopBy = 'user'|'token'|'model'|'channel';
export type Metric = 'tokens'|'reqs'|'quota_sum';
export const getTop = (p:{start_ms:number; end_ms:number; by:TopBy; metric:Metric; limit?:number;}) =>
  api.get<any[]>('/stats/top', p);

export type Rule = 'burst'|'multi_user_token'|'ip_many_users'|'big_request';
export const getAnomalies = (p:{start_ms:number; end_ms:number; rule:Rule; window_sec?:number; users_threshold?:number; sigma?:number;}) =>
  api.get<any[]>('/stats/anomalies', p);
```

**通用图表容器（ECharts）**

```tsx
// src/components/Chart.tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export default function Chart({ option, style }:{ option:any; style?:React.CSSProperties }){
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option, true);
    const h = () => chart.resize();
    window.addEventListener('resize', h);
    return () => { window.removeEventListener('resize', h); chart.dispose(); };
  }, [option]);
  return <div ref={ref} style={{ width:'100%', height:360, ...(style||{}) }} />;
}
```

**总览页（部分）**

```tsx
// src/pages/Dashboard.tsx
import React from 'react';
import { Card, DatePicker, Space, Statistic, Row, Col } from 'antd';
import dayjs from 'dayjs';
import { useQuery } from '@tanstack/react-query';
import Chart from '../components/Chart';
import { getSeries } from '../api/stats';

export default function Dashboard(){
  const [range, setRange] = React.useState<[number, number]>([
    dayjs().subtract(24,'hour').valueOf(), dayjs().valueOf()
  ]);
  const slot_sec = 300; // 5min 粒度
  const { data } = useQuery({
    queryKey: ['series', range, slot_sec],
    queryFn: () => getSeries({ start_ms: range[0], end_ms: range[1], slot_sec })
  });

  const option = React.useMemo(() => ({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'time' },
    yAxis: [ { type: 'value', name: 'reqs' }, { type: 'value', name: 'tokens' } ],
    series: [
      { name: 'reqs', type: 'line', yAxisIndex:0, data: (data||[]).map(r=>[r.bucket, r.reqs]) },
      { name: 'tokens', type: 'line', yAxisIndex:1, data: (data||[]).map(r=>[r.bucket, r.tokens]) }
    ]
  }), [data]);

  const totals = (data||[]).reduce((a,b)=>({
    reqs: a.reqs + b.reqs,
    tokens: a.tokens + b.tokens,
    users: Math.max(a.users, b.users),
  }), {reqs:0,tokens:0,users:0});

  return (
    <Space direction="vertical" style={{width:'100%'}} size="large">
      <Card>
        <DatePicker.RangePicker showTime value={[dayjs(range[0]), dayjs(range[1])]} onChange={(v)=> v&& setRange([v[0]!.valueOf(), v[1]!.valueOf()])} />
      </Card>
      <Row gutter={16}>
        <Col span={6}><Card><Statistic title="Requests" value={totals.reqs} /></Card></Col>
        <Col span={6}><Card><Statistic title="Tokens" value={totals.tokens} /></Card></Col>
        <Col span={6}><Card><Statistic title="Peak Users (slot)" value={totals.users} /></Card></Col>
      </Row>
      <Card title="Traffic">
        <Chart option={option} />
      </Card>
    </Space>
  );
}
```

**Top 排行页（部分）**

```tsx
// src/pages/Top.tsx
import React from 'react';
import { Card, Segmented } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getTop, TopBy, Metric } from '../api/stats';
import Chart from '../components/Chart';
import dayjs from 'dayjs';

export default function Top(){
  const [by, setBy] = React.useState<TopBy>('user');
  const [metric, setMetric] = React.useState<Metric>('tokens');
  const start_ms = dayjs().subtract(24,'hour').valueOf();
  const end_ms = dayjs().valueOf();
  const { data } = useQuery({ queryKey:['top', by, metric, start_ms, end_ms], queryFn:()=> getTop({start_ms,end_ms,by,metric,limit:20}) });

  const option = React.useMemo(()=>({
    xAxis: { type:'category', data: (data||[]).map((r:any)=> r.username || r.token_name || r.model_name || r.channel_name || r[by]) },
    yAxis: { type:'value' },
    tooltip: { trigger:'axis' },
    series: [{ type:'bar', data: (data||[]).map((r:any)=> r[metric]) }]
  }), [data, by, metric]);

  return (
    <Card title="Top 排行" extra={
      <Segmented options={[{label:'User',value:'user'},{label:'Token',value:'token'},{label:'Model',value:'model'},{label:'Channel',value:'channel'}]} value={by} onChange={(v)=>setBy(v as TopBy)} />
    }>
      <Segmented options={[{label:'Tokens',value:'tokens'},{label:'Reqs',value:'reqs'},{label:'Quota',value:'quota_sum'}]} value={metric} onChange={(v)=>setMetric(v as Metric)} style={{marginBottom:16}} />
      <Chart option={option} />
    </Card>
  );
}
```

> 其余页面（Heatmap、Anomalies、详情）与上面模式一致：通过 TanStack Query 取数 → 映射 ECharts/表格。

## 7.3 构建与静态托管

**Dockerfile（多阶段构建）**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml* package-lock.json* yarn.lock* ./
RUN if [ -f pnpm-lock.yaml ]; then npm i -g pnpm && pnpm i; \
    elif [ -f yarn.lock ]; then yarn; else npm i; fi
COPY . .
RUN if [ -f pnpm-lock.yaml ]; then pnpm build; \
    elif [ -f yarn.lock ]; then yarn build; else npm run build; fi

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

**Nginx 反代（前端同域转发到 FastAPI）**

```nginx
# frontend/nginx.conf
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location /api/ {
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_pass http://api:8080/; # docker 内部服务名
  }

  location / {
    try_files $uri /index.html;
  }
}
```

**Vite 配置与环境变量**

- `.env.production`：`VITE_API_BASE=/api`
- 本地 dev：`VITE_API_BASE=http://localhost:8080`

---

# 8. Docker Compose（整合）

```yaml
version: '3.9'
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server","--appendonly","yes"]
    volumes: [redis-data:/data]

  api:
    build: ./api
    restart: unless-stopped
    env_file: [.env]
    expose: ["8080"]
    depends_on: [redis]
    healthcheck:
      test: ["CMD","curl","-fsS","http://localhost:8080/health"]
      interval: 20s
      timeout: 5s
      retries: 5

  worker:
    build: ./worker
    restart: unless-stopped
    env_file: [.env]
    depends_on: [redis]

  frontend:
    build: ./frontend
    restart: unless-stopped
    ports: ["80:80"]
    depends_on: [api]

  # 可选：superset（快速 BI）
  # superset:
  #   image: apache/superset:latest
  #   ports: ["8088:8088"]
  #   environment:
  #     - SUPERSET_SECRET_KEY=${SUPERSET_SECRET_KEY}
  #   volumes: [superset-home:/app/superset_home]

volumes:
  redis-data:
  superset-home:
```

---

# 9. 环境变量与权限

**.env（关键项）**

```
DB_HOST=your-newapi-mysql-host
DB_PORT=3306
DB_NAME=new-api
DB_USER_RO=newapi_ro
DB_PASS_RO=********
REDIS_URL=redis://redis:6379/0
API_PORT=8080
CACHE_TTL_SECONDS=60
# 风控默认
BURST_WINDOW_SEC=60
BURST_LIMIT_PER_TOKEN=120
IP_USERS_THRESHOLD=5
TOKEN_MULTI_USER_THRESHOLD=2
BIG_REQUEST_SIGMA=3
# 告警
ALERT_WEBHOOK_URL=
```

**数据库权限**

- `newapi_ro`：`SELECT` on `new-api`.\*
- `newapi_agg`（可与上面分离）：`SELECT` on `logs` + `INSERT` on `agg_usage_hourly`

---

# 10. 验收用例（手动检查）

1. **趋势**：近 24h `slot_sec=300` 折线有数据且平滑；峰值与日志量相符。
2. **TopN**：切换 `by=token/model/channel` 与 `metric=reqs/tokens` 列表变化合理。
3. **热力**：工作时间段颜色明显更深；周末变浅（样本足够时）。
4. **异常**：模拟用脚本对某 token 打压（每秒 5\~10 次），1 分钟内触发 `burst` 告警。
5. **缓存**：连续刷新同参数接口，TTL 内 RT 明显降低（可在 API 日志查看 DB 查询次数）。

---

# 11. 运维与安全

- **只读优先**：统计走 RO 账号/只读副本；避免拖慢 `newapi` 主库。
- **限流与防爆破**：Nginx 对 `/api` 增加简单限流；面向公网需加认证（Admin Token 或 OIDC）。
- **白名单/黑名单**：对内网 IP、CI 用户、巡检账号做白名单；违规 token 自动加入黑名单（回写到 `tokens.status` 或外部列表）。
- **日志**：统一 stdout；落地时用 Loki/ELK 收集；按 trace-id 串联前后端。
- **监控**：/health 与（可选）/metrics；配置容器重启策略。

---

# 12. FAQ / 排错

- **接口很慢**：检查是否命中 Redis 缓存；时间范围是否过大；索引是否已建立；必要时走 `agg_usage_hourly`。
- **递归 CTE 报深度**：调大 `cte_max_recursion_depth`（已在 SQL 设置）；或改更大 `slot_sec`。
- **窗口函数错误**：确认 MySQL 8.2；并移除示例中的 `QUALIFY`（我们代码已用子查询替代）。
- **前端跨域**：建议走 Nginx 同域反代；或 FastAPI 启动 CORS（`from fastapi.middleware.cors import CORSMiddleware`）。
- **告警未发**：检查 `ALERT_WEBHOOK_URL` 与目标平台机器人权限；容器内 `curl` 测试连通。

---

# 13. 后续迭代建议

- **失败率监控**：将错误码/状态结构化到 `logs` 或旁路表，新增“失败率突升”与“通道异常”规则。
- **自适应阈值**：以 P95/P99 为基线，动态调整 burst、3σ 的 σ 值与窗口。
- **明细回放**：异常命中后，前端详情页展示关联明细 TopN（某 token 的最近 50 次）。
- **RBAC**：前端登录与角色控制（Viewer / Analyst / Admin）。
- **CI/CD**：GitHub Actions 构建镜像，推送到私有 Registry；生产用 Compose 或 Swarm/K8s 部署。

---

# 14. 里程碑（建议）

- **M1（1\~2 天）**：建索引、起 Compose、连 MySQL、Dashboard 趋势 + TopN 可用。
- **M2（1\~2 天）**：Worker 聚合与 3 条风控规则上线，Webhook 告警通。
- **M3（2\~3 天）**：热力图、异常中心、详情页、导出；只读副本或限流；简易认证。

> 到这里，你就有一套“开箱可视化 + 基础风控 + 告警”的系统，可以平滑接入更多规则与看板。需要我把这份文档里的\*\*前端完整模板（含 package.json / vite / 页面全量代码）\*\*填充进去吗？也可以直接给你一个可下载的 zip。

