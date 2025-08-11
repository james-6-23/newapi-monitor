"""数据库连接管理模块"""
import aiomysql
import redis.asyncio as redis
from typing import Optional, List, Dict, Any
import structlog

from .config import settings

logger = structlog.get_logger()

# 全局连接池实例
_mysql_pool_ro: Optional[aiomysql.Pool] = None
_mysql_pool_agg: Optional[aiomysql.Pool] = None
_redis_client: Optional[redis.Redis] = None


async def get_mysql_pool_ro() -> aiomysql.Pool:
    """获取只读MySQL连接池"""
    global _mysql_pool_ro
    
    if _mysql_pool_ro is None:
        try:
            _mysql_pool_ro = await aiomysql.create_pool(
                minsize=1,
                maxsize=5,
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user_ro,
                password=settings.db_pass_ro,
                db=settings.db_name,
                autocommit=True,
                charset='utf8mb4',
                connect_timeout=30,
            )
            logger.info("只读MySQL连接池创建成功")
        except Exception as e:
            logger.error("只读MySQL连接池创建失败", error=str(e))
            raise
    
    return _mysql_pool_ro


async def get_mysql_pool_agg() -> aiomysql.Pool:
    """获取聚合MySQL连接池（有写权限）"""
    global _mysql_pool_agg
    
    if _mysql_pool_agg is None:
        try:
            _mysql_pool_agg = await aiomysql.create_pool(
                minsize=1,
                maxsize=3,
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user_agg,
                password=settings.db_pass_agg,
                db=settings.db_name,
                autocommit=True,
                charset='utf8mb4',
                connect_timeout=30,
            )
            logger.info("聚合MySQL连接池创建成功")
        except Exception as e:
            logger.error("聚合MySQL连接池创建失败", error=str(e))
            raise
    
    return _mysql_pool_agg


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
            )
            await _redis_client.ping()
            logger.info("Redis连接创建成功")
        except Exception as e:
            logger.error("Redis连接创建失败", error=str(e))
            raise
    
    return _redis_client


async def close_connections():
    """关闭所有连接"""
    global _mysql_pool_ro, _mysql_pool_agg, _redis_client
    
    if _mysql_pool_ro:
        _mysql_pool_ro.close()
        await _mysql_pool_ro.wait_closed()
        _mysql_pool_ro = None
        logger.info("只读MySQL连接池已关闭")
    
    if _mysql_pool_agg:
        _mysql_pool_agg.close()
        await _mysql_pool_agg.wait_closed()
        _mysql_pool_agg = None
        logger.info("聚合MySQL连接池已关闭")
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis连接已关闭")


async def execute_query_ro(sql: str, params: dict = None) -> List[Dict[str, Any]]:
    """执行只读查询"""
    pool = await get_mysql_pool_ro()
    
    try:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params or {})
                result = await cursor.fetchall()
                return [dict(row) for row in result]
                
    except Exception as e:
        logger.error("只读查询执行失败", sql=sql[:100], error=str(e))
        raise


async def execute_query_agg(sql: str, params: dict = None) -> int:
    """执行聚合查询（有写权限）"""
    pool = await get_mysql_pool_agg()
    
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params or {})
                return cursor.rowcount
                
    except Exception as e:
        logger.error("聚合查询执行失败", sql=sql[:100], error=str(e))
        raise


async def batch_insert_agg(sql: str, data_list: List[Dict[str, Any]]) -> int:
    """批量插入聚合数据"""
    if not data_list:
        return 0
    
    pool = await get_mysql_pool_agg()
    
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 使用executemany进行批量插入
                await cursor.executemany(sql, data_list)
                return cursor.rowcount
                
    except Exception as e:
        logger.error("批量插入失败", sql=sql[:100], error=str(e))
        raise


async def get_last_aggregation_time() -> Optional[str]:
    """获取最后一次聚合时间"""
    redis_client = await get_redis_client()
    
    try:
        return await redis_client.get("last_aggregation_time")
    except Exception as e:
        logger.warning("获取最后聚合时间失败", error=str(e))
        return None


async def set_last_aggregation_time(timestamp: str):
    """设置最后一次聚合时间"""
    redis_client = await get_redis_client()
    
    try:
        await redis_client.set("last_aggregation_time", timestamp)
    except Exception as e:
        logger.warning("设置最后聚合时间失败", error=str(e))
