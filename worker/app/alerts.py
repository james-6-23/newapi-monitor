"""告警模块"""
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
import requests
import structlog

from .config import settings, rules_config
from .database import get_redis_client

logger = structlog.get_logger()


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.webhook_url = settings.alert_webhook_url
        self.alert_type = settings.alert_type
        self.cooldown_seconds = rules_config.get_cooldown_seconds()
    
    async def send_alert(self, rule_name: str, data: Dict[str, Any], context: Dict[str, Any] = None):
        """发送告警"""
        if not self.webhook_url:
            logger.warning("未配置告警Webhook URL，跳过告警发送")
            return
        
        # 检查冷却时间
        if await self._is_in_cooldown(rule_name, data):
            logger.debug("告警在冷却期内，跳过发送", rule=rule_name)
            return
        
        try:
            # 生成告警消息
            message = self._generate_message(rule_name, data, context)
            
            # 根据告警类型发送
            if self.alert_type == "dingtalk":
                await self._send_dingtalk(message)
            elif self.alert_type == "feishu":
                await self._send_feishu(message)
            elif self.alert_type == "wechat_work":
                await self._send_wechat_work(message)
            else:
                logger.error("不支持的告警类型", alert_type=self.alert_type)
                return
            
            # 记录冷却时间
            await self._set_cooldown(rule_name, data)
            
            logger.info("告警发送成功", rule=rule_name, alert_type=self.alert_type)
            
        except Exception as e:
            logger.error("告警发送失败", rule=rule_name, error=str(e))
    
    async def send_batch_alert(self, rule_name: str, data_list: List[Dict[str, Any]], context: Dict[str, Any] = None):
        """发送批量告警"""
        if not data_list:
            return
        
        batch_threshold = rules_config.get_batch_threshold()
        
        if len(data_list) >= batch_threshold:
            # 发送汇总告警
            summary_data = {
                "count": len(data_list),
                "rule": rule_name,
                "sample": data_list[:3]  # 显示前3个样本
            }
            await self.send_alert(f"{rule_name}_batch", summary_data, context)
        else:
            # 逐个发送
            for data in data_list:
                await self.send_alert(rule_name, data, context)
                await asyncio.sleep(0.1)  # 避免频繁发送
    
    def _generate_message(self, rule_name: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """生成告警消息"""
        template = rules_config.get_alert_template(rule_name)
        
        try:
            # 合并数据和上下文
            format_data = {**data}
            if context:
                format_data.update(context)
            
            # 格式化消息
            message = template.format(**format_data)
            
            # 添加时间戳
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"\n\n⏰ 时间: {timestamp}"
            
            return message
            
        except Exception as e:
            logger.warning("消息格式化失败，使用默认格式", error=str(e))
            return f"🚨 {rule_name} 规则触发告警\n数据: {json.dumps(data, ensure_ascii=False, indent=2)}"
    
    async def _send_dingtalk(self, message: str):
        """发送钉钉告警"""
        payload = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
    
    async def _send_feishu(self, message: str):
        """发送飞书告警"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
    
    async def _send_wechat_work(self, message: str):
        """发送企业微信告警"""
        payload = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
    
    async def _is_in_cooldown(self, rule_name: str, data: Dict[str, Any]) -> bool:
        """检查是否在冷却期内"""
        try:
            redis_client = await get_redis_client()
            
            # 生成冷却键（基于规则和关键数据）
            key_data = self._get_cooldown_key_data(rule_name, data)
            cooldown_key = f"alert_cooldown:{rule_name}:{hash(str(key_data))}"
            
            last_alert_time = await redis_client.get(cooldown_key)
            if last_alert_time:
                elapsed = time.time() - float(last_alert_time)
                return elapsed < self.cooldown_seconds
            
            return False
            
        except Exception as e:
            logger.warning("检查冷却时间失败", error=str(e))
            return False
    
    async def _set_cooldown(self, rule_name: str, data: Dict[str, Any]):
        """设置冷却时间"""
        try:
            redis_client = await get_redis_client()
            
            key_data = self._get_cooldown_key_data(rule_name, data)
            cooldown_key = f"alert_cooldown:{rule_name}:{hash(str(key_data))}"
            
            await redis_client.setex(
                cooldown_key,
                self.cooldown_seconds,
                str(time.time())
            )
            
        except Exception as e:
            logger.warning("设置冷却时间失败", error=str(e))
    
    def _get_cooldown_key_data(self, rule_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """获取用于生成冷却键的关键数据"""
        if rule_name == "burst":
            return {"token_id": data.get("token_id")}
        elif rule_name == "multi_user_token":
            return {"token_id": data.get("token_id")}
        elif rule_name == "ip_many_users":
            return {"ip": data.get("ip")}
        elif rule_name == "big_request":
            return {"token_id": data.get("token_id"), "user_id": data.get("user_id")}
        else:
            return data


# 全局告警管理器实例
alert_manager = AlertManager()
