"""风控规则检测模块"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog

from .config import settings, rules_config
from .database import execute_query_ro
from .alerts import alert_manager

logger = structlog.get_logger()


class RuleEngine:
    """风控规则引擎"""
    
    def __init__(self):
        self.whitelist_ips = rules_config.get_whitelist("ips")
        self.whitelist_users = rules_config.get_whitelist("users")
        self.whitelist_tokens = rules_config.get_whitelist("tokens")
    
    async def check_burst_rule(self, window_minutes: int = 5):
        """检查突发频率规则"""
        if not rules_config.is_rule_enabled("burst"):
            logger.debug("突发频率规则已禁用")
            return
        
        try:
            # 获取规则配置
            rule_config = rules_config.get_rule_config("burst")
            window_sec = rule_config.get("window_sec", settings.burst_window_sec)
            limit_per_token = rule_config.get("limit_per_token", settings.burst_limit_per_token)
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=window_minutes)
            
            # 查询SQL
            sql = """
                SELECT 
                    l.token_id,
                    t.name AS token_name,
                    COUNT(*) AS request_count,
                    %s AS window_sec,
                    %s AS threshold,
                    MIN(l.created_at) AS first_request,
                    MAX(l.created_at) AS last_request
                FROM logs l
                LEFT JOIN tokens t ON l.token_id = t.id
                WHERE l.created_at >= %s
                  AND l.created_at < %s
                GROUP BY l.token_id, t.name
                HAVING COUNT(*) >= %s
                   AND TIMESTAMPDIFF(SECOND, MIN(l.created_at), MAX(l.created_at)) <= %s
                ORDER BY request_count DESC
                LIMIT 100
            """
            
            params = [
                window_sec, limit_per_token,
                start_time, end_time,
                limit_per_token, window_sec
            ]
            
            results = await execute_query_ro(sql, params)
            
            # 过滤白名单
            filtered_results = self._filter_whitelist_tokens(results)
            
            if filtered_results:
                logger.warning("检测到突发频率异常", count=len(filtered_results))
                await alert_manager.send_batch_alert("burst", filtered_results)
            
            logger.info("突发频率规则检查完成", 
                       anomalies=len(filtered_results),
                       window_minutes=window_minutes)
            
        except Exception as e:
            logger.error("突发频率规则检查失败", error=str(e))
    
    async def check_multi_user_token_rule(self, window_hours: int = 1):
        """检查共享Token规则"""
        if not rules_config.is_rule_enabled("multi_user_token"):
            logger.debug("共享Token规则已禁用")
            return
        
        try:
            # 获取规则配置
            rule_config = rules_config.get_rule_config("multi_user_token")
            users_threshold = rule_config.get("users_threshold", settings.token_multi_user_threshold)
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=window_hours)
            
            # 查询SQL
            sql = """
                SELECT 
                    l.token_id,
                    t.name AS token_name,
                    COUNT(DISTINCT l.user_id) AS user_count,
                    %s AS threshold,
                    GROUP_CONCAT(DISTINCT u.username ORDER BY u.username) AS users,
                    COUNT(*) AS total_requests
                FROM logs l
                LEFT JOIN tokens t ON l.token_id = t.id
                LEFT JOIN users u ON l.user_id = u.id
                WHERE l.created_at >= %s
                  AND l.created_at < %s
                GROUP BY l.token_id, t.name
                HAVING COUNT(DISTINCT l.user_id) >= %s
                ORDER BY user_count DESC
                LIMIT 100
            """
            
            params = [users_threshold, start_time, end_time, users_threshold]
            results = await execute_query_ro(sql, params)
            
            # 过滤白名单
            filtered_results = self._filter_whitelist_tokens(results)
            
            if filtered_results:
                logger.warning("检测到共享Token异常", count=len(filtered_results))
                await alert_manager.send_batch_alert("multi_user_token", filtered_results)
            
            logger.info("共享Token规则检查完成", 
                       anomalies=len(filtered_results),
                       window_hours=window_hours)
            
        except Exception as e:
            logger.error("共享Token规则检查失败", error=str(e))
    
    async def check_ip_many_users_rule(self, window_hours: int = 1):
        """检查同IP多账号规则"""
        if not rules_config.is_rule_enabled("ip_many_users"):
            logger.debug("同IP多账号规则已禁用")
            return
        
        try:
            # 获取规则配置
            rule_config = rules_config.get_rule_config("ip_many_users")
            users_threshold = rule_config.get("users_threshold", settings.ip_users_threshold)
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=window_hours)
            
            # 查询SQL
            sql = """
                SELECT 
                    l.ip,
                    COUNT(DISTINCT l.user_id) AS user_count,
                    %s AS threshold,
                    GROUP_CONCAT(DISTINCT u.username ORDER BY u.username) AS users,
                    COUNT(*) AS total_requests
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE l.created_at >= %s
                  AND l.created_at < %s
                  AND l.ip IS NOT NULL
                  AND l.ip != ''
                GROUP BY l.ip
                HAVING COUNT(DISTINCT l.user_id) >= %s
                ORDER BY user_count DESC
                LIMIT 100
            """
            
            params = [users_threshold, start_time, end_time, users_threshold]
            results = await execute_query_ro(sql, params)
            
            # 过滤白名单IP
            filtered_results = self._filter_whitelist_ips(results)
            
            if filtered_results:
                logger.warning("检测到同IP多账号异常", count=len(filtered_results))
                await alert_manager.send_batch_alert("ip_many_users", filtered_results)
            
            logger.info("同IP多账号规则检查完成", 
                       anomalies=len(filtered_results),
                       window_hours=window_hours)
            
        except Exception as e:
            logger.error("同IP多账号规则检查失败", error=str(e))
    
    async def check_big_request_rule(self, window_hours: int = 2):
        """检查超大请求规则（3σ原则）"""
        if not rules_config.is_rule_enabled("big_request"):
            logger.debug("超大请求规则已禁用")
            return
        
        try:
            # 获取规则配置
            rule_config = rules_config.get_rule_config("big_request")
            sigma = rule_config.get("sigma", settings.big_request_sigma)
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=window_hours)
            
            # 查询SQL（使用3σ原则）
            sql = """
                WITH stats AS (
                    SELECT 
                        AVG(prompt_tokens + completion_tokens) AS mean_tokens,
                        STDDEV(prompt_tokens + completion_tokens) AS std_tokens
                    FROM logs
                    WHERE created_at >= %s
                      AND created_at < %s
                      AND (prompt_tokens + completion_tokens) > 0
                ),
                big_requests AS (
                    SELECT 
                        l.id,
                        l.token_id,
                        t.name AS token_name,
                        l.user_id,
                        u.username,
                        (l.prompt_tokens + l.completion_tokens) AS token_count,
                        l.created_at,
                        s.mean_tokens,
                        s.std_tokens,
                        (s.mean_tokens + %s * s.std_tokens) AS threshold
                    FROM logs l
                    LEFT JOIN tokens t ON l.token_id = t.id
                    LEFT JOIN users u ON l.user_id = u.id
                    CROSS JOIN stats s
                    WHERE l.created_at >= %s
                      AND l.created_at < %s
                      AND (l.prompt_tokens + l.completion_tokens) > (s.mean_tokens + %s * s.std_tokens)
                )
                SELECT 
                    token_id,
                    token_name,
                    user_id,
                    username,
                    token_count,
                    created_at,
                    ROUND(mean_tokens, 2) AS mean_tokens,
                    ROUND(std_tokens, 2) AS std_tokens,
                    ROUND(threshold, 2) AS threshold,
                    %s AS sigma
                FROM big_requests
                ORDER BY token_count DESC
                LIMIT 100
            """
            
            params = [
                start_time, end_time, sigma,
                start_time, end_time, sigma, sigma
            ]
            
            results = await execute_query_ro(sql, params)
            
            # 过滤白名单
            filtered_results = self._filter_whitelist_tokens(results)
            filtered_results = self._filter_whitelist_users(filtered_results)
            
            if filtered_results:
                logger.warning("检测到超大请求异常", count=len(filtered_results))
                await alert_manager.send_batch_alert("big_request", filtered_results)
            
            logger.info("超大请求规则检查完成", 
                       anomalies=len(filtered_results),
                       window_hours=window_hours)
            
        except Exception as e:
            logger.error("超大请求规则检查失败", error=str(e))
    
    def _filter_whitelist_tokens(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤白名单Token"""
        if not self.whitelist_tokens:
            return results
        
        return [r for r in results if r.get("token_id") not in self.whitelist_tokens]
    
    def _filter_whitelist_users(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤白名单用户"""
        if not self.whitelist_users:
            return results
        
        return [r for r in results if r.get("username") not in self.whitelist_users]
    
    def _filter_whitelist_ips(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤白名单IP"""
        if not self.whitelist_ips:
            return results
        
        filtered = []
        for result in results:
            ip = result.get("ip", "")
            is_whitelisted = False
            
            for whitelist_ip in self.whitelist_ips:
                if "/" in whitelist_ip:
                    # CIDR格式
                    import ipaddress
                    try:
                        if ipaddress.ip_address(ip) in ipaddress.ip_network(whitelist_ip):
                            is_whitelisted = True
                            break
                    except:
                        pass
                else:
                    # 精确匹配
                    if ip == whitelist_ip:
                        is_whitelisted = True
                        break
            
            if not is_whitelisted:
                filtered.append(result)
        
        return filtered


# 全局规则引擎实例
rule_engine = RuleEngine()
