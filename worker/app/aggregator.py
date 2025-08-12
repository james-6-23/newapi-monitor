"""数据聚合模块"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog

from app.database import execute_query_ro, execute_query_agg, get_last_aggregation_time, set_last_aggregation_time

logger = structlog.get_logger()


class DataAggregator:
    """数据聚合器"""
    
    def __init__(self):
        self.batch_size = 1000  # 批量处理大小
    
    async def aggregate_hourly_data(self, hours_back: int = 2):
        """聚合小时级数据"""
        try:
            # 获取最后聚合时间
            last_time = await get_last_aggregation_time()

            # 计算聚合时间范围
            current_time = datetime.now()
            end_time = current_time.replace(minute=0, second=0, microsecond=0)

            if last_time:
                start_time = datetime.fromisoformat(last_time)
                # 如果最后聚合时间就是当前小时，跳过
                if start_time >= end_time:
                    logger.debug("无需聚合数据", last_time=last_time, end_time=end_time.isoformat())
                    return
            else:
                # 首次运行，聚合过去几小时的数据
                start_time = end_time - timedelta(hours=hours_back)
            
            logger.info("开始聚合小时级数据", 
                       start_time=start_time.isoformat(),
                       end_time=end_time.isoformat())
            
            # 聚合全局数据
            await self._aggregate_global_hourly(start_time, end_time)
            
            # 聚合用户维度数据
            await self._aggregate_user_hourly(start_time, end_time)
            
            # 聚合模型维度数据
            await self._aggregate_model_hourly(start_time, end_time)
            
            # 聚合通道维度数据
            await self._aggregate_channel_hourly(start_time, end_time)
            
            # 更新最后聚合时间
            await set_last_aggregation_time(end_time.isoformat())
            
            logger.info("小时级数据聚合完成")
            
        except Exception as e:
            logger.error("小时级数据聚合失败", error=str(e))
            raise
    
    async def _aggregate_global_hourly(self, start_time: datetime, end_time: datetime):
        """聚合全局小时级数据"""
        # 转换为Unix时间戳
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        sql_query = """
            SELECT
                DATE_FORMAT(FROM_UNIXTIME(created_at), '%%Y-%%m-%%d %%H:00:00') AS hour_bucket,
                COUNT(*) AS request_count,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(quota), 0) AS quota_sum,
                COUNT(DISTINCT user_id) AS unique_users,
                COUNT(DISTINCT token_id) AS unique_tokens
            FROM logs
            WHERE created_at >= %s
              AND created_at < %s
            GROUP BY hour_bucket
            ORDER BY hour_bucket
        """
        
        results = await execute_query_ro(sql_query, [start_timestamp, end_timestamp])
        
        if results:
            await self._upsert_aggregation_data(results, None, None, None)
            logger.info("全局小时级数据聚合完成", records=len(results))
    
    async def _aggregate_user_hourly(self, start_time: datetime, end_time: datetime):
        """聚合用户维度小时级数据"""
        # 转换为Unix时间戳
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        sql_query = """
            SELECT
                DATE_FORMAT(FROM_UNIXTIME(created_at), '%%Y-%%m-%%d %%H:00:00') AS hour_bucket,
                user_id,
                COUNT(*) AS request_count,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(quota), 0) AS quota_sum,
                1 AS unique_users,
                COUNT(DISTINCT token_id) AS unique_tokens
            FROM logs
            WHERE created_at >= %s
              AND created_at < %s
            GROUP BY hour_bucket, user_id
            ORDER BY hour_bucket, user_id
        """
        
        results = await execute_query_ro(sql_query, [start_timestamp, end_timestamp])
        
        if results:
            await self._upsert_aggregation_data(results, "user_id", None, None)
            logger.info("用户维度小时级数据聚合完成", records=len(results))
    
    async def _aggregate_model_hourly(self, start_time: datetime, end_time: datetime):
        """聚合模型维度小时级数据"""
        # 转换为Unix时间戳
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        sql_query = """
            SELECT
                DATE_FORMAT(FROM_UNIXTIME(created_at), '%%Y-%%m-%%d %%H:00:00') AS hour_bucket,
                model_name,
                COUNT(*) AS request_count,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(quota), 0) AS quota_sum,
                COUNT(DISTINCT user_id) AS unique_users,
                COUNT(DISTINCT token_id) AS unique_tokens
            FROM logs
            WHERE created_at >= %s
              AND created_at < %s
            GROUP BY hour_bucket, model_name
            ORDER BY hour_bucket, model_name
        """
        
        results = await execute_query_ro(sql_query, [start_timestamp, end_timestamp])
        
        if results:
            await self._upsert_aggregation_data(results, None, "model_name", None)
            logger.info("模型维度小时级数据聚合完成", records=len(results))
    
    async def _aggregate_channel_hourly(self, start_time: datetime, end_time: datetime):
        """聚合通道维度小时级数据"""
        # 转换为Unix时间戳
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        sql_query = """
            SELECT
                DATE_FORMAT(FROM_UNIXTIME(created_at), '%%Y-%%m-%%d %%H:00:00') AS hour_bucket,
                channel_id,
                COUNT(*) AS request_count,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(quota), 0) AS quota_sum,
                COUNT(DISTINCT user_id) AS unique_users,
                COUNT(DISTINCT token_id) AS unique_tokens
            FROM logs
            WHERE created_at >= %s
              AND created_at < %s
            GROUP BY hour_bucket, channel_id
            ORDER BY hour_bucket, channel_id
        """
        
        results = await execute_query_ro(sql_query, [start_timestamp, end_timestamp])
        
        if results:
            await self._upsert_aggregation_data(results, None, None, "channel_id")
            logger.info("通道维度小时级数据聚合完成", records=len(results))
    
    async def _upsert_aggregation_data(self, 
                                     results: List[Dict[str, Any]], 
                                     user_id_field: Optional[str],
                                     model_name_field: Optional[str],
                                     channel_id_field: Optional[str]):
        """插入或更新聚合数据"""
        if not results:
            return
        
        # 使用ON DUPLICATE KEY UPDATE实现幂等插入
        sql = """
            INSERT INTO agg_usage_hourly (
                hour_bucket, user_id, model_name, channel_id,
                request_count, total_tokens, prompt_tokens, completion_tokens,
                quota_sum, unique_users, unique_tokens
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                request_count = VALUES(request_count),
                total_tokens = VALUES(total_tokens),
                prompt_tokens = VALUES(prompt_tokens),
                completion_tokens = VALUES(completion_tokens),
                quota_sum = VALUES(quota_sum),
                unique_users = VALUES(unique_users),
                unique_tokens = VALUES(unique_tokens),
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 准备批量插入数据
        batch_data = []
        for result in results:
            data = [
                result["hour_bucket"],
                result.get(user_id_field) if user_id_field else None,
                result.get(model_name_field) if model_name_field else None,
                result.get(channel_id_field) if channel_id_field else None,
                result["request_count"],
                result["total_tokens"],
                result["prompt_tokens"],
                result["completion_tokens"],
                result["quota_sum"],
                result["unique_users"],
                result["unique_tokens"]
            ]
            batch_data.append(data)
        
        # 分批插入
        total_affected = 0
        for i in range(0, len(batch_data), self.batch_size):
            batch = batch_data[i:i + self.batch_size]

            # 执行批量插入
            affected_rows = await batch_insert_agg(sql, batch)
            total_affected += affected_rows

            logger.debug("批量插入聚合数据",
                        batch_size=len(batch),
                        affected_rows=affected_rows)

        logger.info("聚合数据插入完成",
                   total_records=len(batch_data),
                   total_affected=total_affected)
    
    async def cleanup_old_aggregation_data(self, days_to_keep: int = 90):
        """清理旧的聚合数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            sql = """
                DELETE FROM agg_usage_hourly 
                WHERE hour_bucket < %s
            """
            
            affected_rows = await execute_query_agg(sql, [cutoff_date])
            
            logger.info("清理旧聚合数据完成", 
                       cutoff_date=cutoff_date.isoformat(),
                       deleted_rows=affected_rows)
            
        except Exception as e:
            logger.error("清理旧聚合数据失败", error=str(e))


# 全局数据聚合器实例
data_aggregator = DataAggregator()
