"""FastAPI主应用模块"""
import os
import json
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .deps import (
    get_mysql_pool, get_redis_client, close_connections,
    execute_query, get_cached_result, generate_cache_key
)
from .queries import (
    SERIES_QUERY, get_top_query, get_anomaly_query
)
from .schemas import (
    HealthResponse, ErrorResponse, SeriesResponse, TopResponse, 
    AnomalyResponse, StatsQueryParams, TopQueryParams, AnomalyQueryParams
)

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化连接
    logger.info("正在启动NewAPI监控API服务...")
    try:
        await get_mysql_pool()
        await get_redis_client()
        logger.info("服务启动成功")
    except Exception as e:
        logger.error("服务启动失败", error=str(e))
        raise
    
    yield
    
    # 关闭时清理连接
    logger.info("正在关闭服务...")
    await close_connections()
    logger.info("服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="NewAPI Monitor API",
    description="NewAPI监控与风控系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 可选：添加Prometheus监控
if settings.enable_metrics:
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error("未处理的异常", 
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="内部服务器错误",
            code=500
        ).dict()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    try:
        # 检查数据库连接
        pool = await get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
        
        # 检查Redis连接
        redis_client = await get_redis_client()
        await redis_client.ping()
        
        return HealthResponse()
        
    except Exception as e:
        logger.error("健康检查失败", error=str(e))
        raise HTTPException(status_code=503, detail="服务不可用")


@app.get("/stats/series")
async def get_series_data(
    start_ms: int = Query(description="开始时间戳(毫秒)"),
    end_ms: int = Query(description="结束时间戳(毫秒)"),
    slot_sec: int = Query(default=60, description="时间粒度(秒)")
):
    """获取时序统计数据"""
    try:
        # 参数验证
        if start_ms >= end_ms:
            raise HTTPException(status_code=400, detail="开始时间必须小于结束时间")
        
        if slot_sec not in [60, 300, 900, 1800, 3600]:  # 1分钟到1小时
            raise HTTPException(status_code=400, detail="不支持的时间粒度")
        
        # 生成缓存键
        cache_key = generate_cache_key("series", {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "slot_sec": slot_sec
        })
        
        # 查询函数
        async def query_func():
            params = {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "slot_sec": slot_sec
            }
            result = await execute_query(SERIES_QUERY, params)
            return [dict(row) for row in result]
        
        # 获取缓存结果
        data = await get_cached_result(cache_key, query_func)
        
        logger.info("时序数据查询成功", 
                   start_ms=start_ms, 
                   end_ms=end_ms, 
                   slot_sec=slot_sec,
                   data_points=len(data))
        
        return {"data": data, "total_points": len(data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("时序数据查询失败", error=str(e))
        raise HTTPException(status_code=500, detail="查询失败")


@app.get("/stats/top")
async def get_top_data(
    start_ms: int = Query(description="开始时间戳(毫秒)"),
    end_ms: int = Query(description="结束时间戳(毫秒)"),
    by: str = Query(description="排序维度", regex="^(user|token|model|channel)$"),
    metric: str = Query(description="排序指标", regex="^(tokens|reqs|quota_sum)$"),
    limit: int = Query(default=50, ge=1, le=1000, description="限制数量")
):
    """获取TopN排行数据"""
    try:
        # 参数验证
        if start_ms >= end_ms:
            raise HTTPException(status_code=400, detail="开始时间必须小于结束时间")

        # 生成缓存键
        cache_key = generate_cache_key("top", {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "by": by,
            "metric": metric,
            "limit": limit
        })

        # 查询函数
        async def query_func():
            sql = get_top_query(by, metric)
            params = {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "limit": limit
            }
            result = await execute_query(sql, params)
            return [dict(row) for row in result]

        # 获取缓存结果
        data = await get_cached_result(cache_key, query_func)

        logger.info("TopN数据查询成功",
                   start_ms=start_ms,
                   end_ms=end_ms,
                   by=by,
                   metric=metric,
                   limit=limit,
                   result_count=len(data))

        return {
            "data": data,
            "by": by,
            "metric": metric,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TopN数据查询失败", error=str(e))
        raise HTTPException(status_code=500, detail="查询失败")


@app.get("/stats/anomalies")
async def get_anomalies_data(
    start_ms: int = Query(description="开始时间戳(毫秒)"),
    end_ms: int = Query(description="结束时间戳(毫秒)"),
    rule: str = Query(description="规则名称", regex="^(burst|multi_user_token|ip_many_users|big_request)$"),
    window_sec: Optional[int] = Query(default=60, description="时间窗口(秒)"),
    users_threshold: Optional[int] = Query(default=5, description="用户数阈值"),
    sigma: Optional[float] = Query(default=3.0, description="标准差倍数"),
    limit_per_token: Optional[int] = Query(default=120, description="Token请求数阈值")
):
    """获取异常检测数据"""
    try:
        # 参数验证
        if start_ms >= end_ms:
            raise HTTPException(status_code=400, detail="开始时间必须小于结束时间")

        # 生成缓存键
        cache_key = generate_cache_key("anomalies", {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "rule": rule,
            "window_sec": window_sec,
            "users_threshold": users_threshold,
            "sigma": sigma,
            "limit_per_token": limit_per_token
        })

        # 查询函数
        async def query_func():
            sql = get_anomaly_query(rule)
            params = {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "window_sec": window_sec,
                "users_threshold": users_threshold,
                "sigma": sigma,
                "limit_per_token": limit_per_token
            }
            result = await execute_query(sql, params)
            return [dict(row) for row in result]

        # 获取缓存结果
        data = await get_cached_result(cache_key, query_func)

        logger.info("异常检测数据查询成功",
                   start_ms=start_ms,
                   end_ms=end_ms,
                   rule=rule,
                   anomaly_count=len(data))

        return {
            "data": data,
            "rule": rule,
            "total_count": len(data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("异常检测数据查询失败", error=str(e))
        raise HTTPException(status_code=500, detail="查询失败")


@app.get("/export/csv")
async def export_csv(
    query_type: str = Query(description="查询类型", regex="^(series|top|anomalies)$"),
    start_ms: int = Query(description="开始时间戳(毫秒)"),
    end_ms: int = Query(description="结束时间戳(毫秒)"),
    # 其他参数根据query_type动态处理
):
    """导出CSV数据"""
    try:
        from fastapi.responses import StreamingResponse
        import csv
        import io

        # 根据查询类型获取数据
        if query_type == "series":
            slot_sec = 300  # 默认5分钟粒度
            data_response = await get_series_data(start_ms, end_ms, slot_sec)
            data = data_response["data"]
            filename = f"series_data_{start_ms}_{end_ms}.csv"

        elif query_type == "top":
            # 这里简化处理，实际应该从query参数获取
            by = "user"
            metric = "tokens"
            limit = 100
            data_response = await get_top_data(start_ms, end_ms, by, metric, limit)
            data = data_response["data"]
            filename = f"top_{by}_{metric}_{start_ms}_{end_ms}.csv"

        else:
            raise HTTPException(status_code=400, detail="暂不支持该查询类型的导出")

        # 生成CSV
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        # 返回流式响应
        response = StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

        logger.info("CSV导出成功", query_type=query_type, rows=len(data))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("CSV导出失败", error=str(e))
        raise HTTPException(status_code=500, detail="导出失败")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False
    )
