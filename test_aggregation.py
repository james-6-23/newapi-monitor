#!/usr/bin/env python3
"""
手动测试聚合逻辑
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加worker模块路径
sys.path.append('worker/app')

from database import execute_query_ro, execute_query_agg, get_last_aggregation_time, set_last_aggregation_time

async def test_aggregation():
    """测试聚合逻辑"""
    print("🔍 手动测试聚合逻辑")
    print("=" * 50)
    
    try:
        # 1. 检查最后聚合时间
        print("\n📅 1. 检查最后聚合时间")
        last_time = await get_last_aggregation_time()
        print(f"最后聚合时间: {last_time}")
        
        # 2. 计算聚合时间范围
        print("\n⏰ 2. 计算聚合时间范围")
        current_time = datetime.now()
        end_time = current_time.replace(minute=0, second=0, microsecond=0)
        
        if last_time:
            start_time = datetime.fromisoformat(last_time)
        else:
            start_time = end_time - timedelta(hours=2)
            
        print(f"开始时间: {start_time}")
        print(f"结束时间: {end_time}")
        
        # 转换为时间戳
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        print(f"开始时间戳: {start_timestamp}")
        print(f"结束时间戳: {end_timestamp}")
        
        # 3. 检查原始数据
        print("\n📊 3. 检查原始数据")
        check_sql = """
            SELECT COUNT(*) as count
            FROM logs
            WHERE created_at >= %s AND created_at < %s
        """
        results = await execute_query_ro(check_sql, [start_timestamp, end_timestamp])
        print(f"时间范围内的原始记录数: {results[0]['count'] if results else 0}")
        
        if not results or results[0]['count'] == 0:
            print("❌ 没有数据可聚合")
            return
            
        # 4. 测试全局聚合SQL
        print("\n🔄 4. 测试全局聚合SQL")
        global_sql = """
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
        
        results = await execute_query_ro(global_sql, [start_timestamp, end_timestamp])
        print(f"聚合结果数量: {len(results) if results else 0}")
        
        if results:
            print("前3条聚合结果:")
            for i, row in enumerate(results[:3]):
                print(f"  {i+1}. {row}")
                
            # 5. 测试插入聚合数据
            print("\n💾 5. 测试插入聚合数据")
            insert_sql = """
                INSERT INTO agg_usage_hourly (
                    hour_bucket, user_id, model_name, channel_id,
                    request_count, total_tokens, prompt_tokens, completion_tokens,
                    quota_sum, unique_users, unique_tokens
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    request_count = VALUES(request_count),
                    total_tokens = VALUES(total_tokens),
                    prompt_tokens = VALUES(prompt_tokens),
                    completion_tokens = VALUES(completion_tokens),
                    quota_sum = VALUES(quota_sum),
                    unique_users = VALUES(unique_users),
                    unique_tokens = VALUES(unique_tokens),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 插入第一条记录作为测试
            test_row = results[0]
            test_data = [
                test_row['hour_bucket'],
                None,  # user_id (全局聚合)
                None,  # model_name (全局聚合)
                None,  # channel_id (全局聚合)
                test_row['request_count'],
                test_row['total_tokens'],
                test_row['prompt_tokens'],
                test_row['completion_tokens'],
                test_row['quota_sum'],
                test_row['unique_users'],
                test_row['unique_tokens']
            ]
            
            affected_rows = await execute_query_agg(insert_sql, test_data)
            print(f"插入结果: {affected_rows} 行受影响")
            
            # 6. 验证插入结果
            print("\n✅ 6. 验证插入结果")
            verify_sql = "SELECT COUNT(*) as count FROM agg_usage_hourly"
            verify_results = await execute_query_ro(verify_sql, [])
            print(f"聚合表总记录数: {verify_results[0]['count'] if verify_results else 0}")
            
        else:
            print("❌ 聚合查询没有返回结果")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_aggregation())
