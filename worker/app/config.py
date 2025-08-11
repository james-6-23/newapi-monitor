"""Worker配置管理模块"""
import os
import yaml
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Worker配置"""
    
    # 数据库配置
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_name: str = os.getenv("DB_NAME", "new-api")
    db_user_ro: str = os.getenv("DB_USER_RO", "newapi_ro")
    db_pass_ro: str = os.getenv("DB_PASS_RO", "")
    db_user_agg: str = os.getenv("DB_USER_AGG", "newapi_agg")
    db_pass_agg: str = os.getenv("DB_PASS_AGG", "")
    
    # Redis 配置
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 风控规则默认配置
    burst_window_sec: int = int(os.getenv("BURST_WINDOW_SEC", "60"))
    burst_limit_per_token: int = int(os.getenv("BURST_LIMIT_PER_TOKEN", "120"))
    ip_users_threshold: int = int(os.getenv("IP_USERS_THRESHOLD", "5"))
    token_multi_user_threshold: int = int(os.getenv("TOKEN_MULTI_USER_THRESHOLD", "2"))
    big_request_sigma: float = float(os.getenv("BIG_REQUEST_SIGMA", "3.0"))
    
    # 告警配置
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")
    alert_type: str = os.getenv("ALERT_TYPE", "dingtalk")  # dingtalk, feishu, wechat_work
    alert_cooldown_seconds: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))
    
    # 任务调度配置
    aggregation_interval_minutes: int = int(os.getenv("AGGREGATION_INTERVAL_MINUTES", "5"))
    burst_check_interval_minutes: int = int(os.getenv("BURST_CHECK_INTERVAL_MINUTES", "1"))
    multi_user_token_check_interval_minutes: int = int(os.getenv("MULTI_USER_TOKEN_CHECK_INTERVAL_MINUTES", "5"))
    ip_many_users_check_interval_minutes: int = int(os.getenv("IP_MANY_USERS_CHECK_INTERVAL_MINUTES", "5"))
    big_request_check_interval_minutes: int = int(os.getenv("BIG_REQUEST_CHECK_INTERVAL_MINUTES", "10"))
    
    class Config:
        env_file = ".env"


class RulesConfig:
    """风控规则配置管理"""
    
    def __init__(self, rules_file: str = "rules.yaml"):
        self.rules_file = rules_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载规则配置文件"""
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            print(f"加载规则配置文件失败: {e}")
            return {}
    
    def get_rule_config(self, rule_name: str) -> Dict[str, Any]:
        """获取特定规则的配置"""
        return self.config.get("rules", {}).get(rule_name, {})
    
    def is_rule_enabled(self, rule_name: str) -> bool:
        """检查规则是否启用"""
        rule_config = self.get_rule_config(rule_name)
        return rule_config.get("enabled", True)
    
    def get_whitelist(self, whitelist_type: str) -> List[str]:
        """获取白名单"""
        return self.config.get("whitelist", {}).get(whitelist_type, [])
    
    def get_alert_config(self) -> Dict[str, Any]:
        """获取告警配置"""
        return self.config.get("alerts", {})
    
    def get_alert_template(self, rule_name: str) -> str:
        """获取告警模板"""
        templates = self.get_alert_config().get("templates", {})
        return templates.get(rule_name, f"🚨 {rule_name} 规则触发告警")
    
    def get_cooldown_seconds(self) -> int:
        """获取告警冷却时间"""
        return self.get_alert_config().get("cooldown_seconds", 300)
    
    def get_batch_threshold(self) -> int:
        """获取批量告警阈值"""
        return self.get_alert_config().get("batch_threshold", 10)


# 全局配置实例
settings = Settings()
rules_config = RulesConfig()
