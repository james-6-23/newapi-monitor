"""配置管理模块"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_name: str = os.getenv("DB_NAME", "new-api")
    db_user_ro: str = os.getenv("DB_USER_RO", "newapi_ro")
    db_pass_ro: str = os.getenv("DB_PASS_RO", "")
    
    # Redis 配置
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # API 配置
    api_port: int = int(os.getenv("API_PORT", "8080"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 监控配置
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "false").lower() == "true"
    
    # CORS 配置
    cors_origins: list = ["*"]  # 生产环境应该限制具体域名
    
    class Config:
        env_file = ".env"


# 全局配置实例
settings = Settings()
