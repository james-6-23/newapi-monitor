"""依赖注入模块 - 数据库连接池和Redis连接管理"""
import os
import aiomysql
import redis.asyncio as redis
from typing import Optional
import structlog

from .config import settings

logger = structlog.get_logger()

# 全局连接池实例
_mysql_pool: Optional[aiomysql.Pool] = None
_redis_client: Optional[redis.Redis] = None


async def get_mysql_pool() -> aiomysql.Pool:
    """获取MySQL连接池"""
    global _mysql_pool
    
    if _mysql_pool is None:
        try:
            _mysql_pool = await aiomysql.create_pool(
                minsize=1,
                maxsize=10,
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user_ro,
                password=settings.db_pass_ro,
                db=settings.db_name,
                autocommit=True,
                charset='utf8mb4',
                # 连接超时设置
                connect_timeout=30,
                # 启用自动重连
                echo=False,
            )
            logger.info("MySQL连接池创建成功", 
                       host=settings.db_host, 
                       port=settings.db_port,
                       db=settings.db_name)
        except Exception as e:
            logger.error("MySQL连接池创建失败", error=str(e))
            raise
    
    return _mysql_pool


async def get_redis_client() -> redis.Redis:
    """获取Redis客户端"""
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=30,
                socket_timeout=30,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # 测试连接
            await _redis_client.ping()
            logger.info("Redis连接创建成功", url=settings.redis_url)
        except Exception as e:
            logger.error("Redis连接创建失败", error=str(e))
            raise
    
    return _redis_client


async def close_connections():
    """关闭所有连接"""
    global _mysql_pool, _redis_client
    
    if _mysql_pool:
        _mysql_pool.close()
        await _mysql_pool.wait_closed()
        _mysql_pool = None
        logger.info("MySQL连接池已关闭")
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis连接已关闭")


async def execute_query(sql: str, params: dict = None) -> list:
    """执行SQL查询并返回结果"""
    pool = await get_mysql_pool()
    
    try:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 支持多语句执行
                statements = [stmt.strip() for stmt in sql.split(';\n') if stmt.strip()]
                
                for i, stmt in enumerate(statements):
                    await cursor.execute(stmt, params or {})
                    
                    # 只有最后一个语句返回结果
                    if i == len(statements) - 1:
                        result = await cursor.fetchall()
                        return result
                
                return []
                
    except Exception as e:
        logger.error("SQL查询执行失败", sql=sql[:100], error=str(e))
        raise


async def get_cached_result(cache_key: str, query_func, ttl: int = None) -> any:
    """获取缓存结果，如果不存在则执行查询函数并缓存"""
    redis_client = await get_redis_client()
    ttl = ttl or settings.cache_ttl_seconds
    
    try:
        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            import json
            logger.debug("缓存命中", cache_key=cache_key)
            return json.loads(cached_data)
        
        # 缓存未命中，执行查询
        logger.debug("缓存未命中，执行查询", cache_key=cache_key)
        result = await query_func()
        
        # 存储到缓存
        import json
        await redis_client.setex(
            cache_key, 
            ttl, 
            json.dumps(result, ensure_ascii=False, default=str)
        )
        
        return result
        
    except Exception as e:
        logger.warning("缓存操作失败，直接执行查询", cache_key=cache_key, error=str(e))
        # 缓存失败时直接执行查询
        return await query_func()


def generate_cache_key(endpoint: str, params: dict) -> str:
    """生成缓存键"""
    import hashlib
    import json
    
    # 对参数进行排序以确保一致性
    sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
    param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
    
    return f"newapi_monitor:{endpoint}:{param_hash}"
