"""Pydantic响应模型定义"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    """健康检查响应"""
    ok: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    code: int = 500
    timestamp: datetime = Field(default_factory=datetime.now)


class SeriesDataPoint(BaseModel):
    """时序数据点"""
    bucket: str = Field(description="时间桶")
    reqs: int = Field(description="请求数")
    tokens: int = Field(description="Token数")
    users: int = Field(description="用户数")
    tokens_cnt: int = Field(description="Token种类数")


class SeriesResponse(BaseModel):
    """时序数据响应"""
    data: List[SeriesDataPoint]
    total_points: int = Field(description="数据点总数")


class TopUserItem(BaseModel):
    """Top用户项"""
    user_id: int
    username: Optional[str] = None
    tokens: int = 0
    reqs: int = 0
    quota_sum: float = 0.0


class TopTokenItem(BaseModel):
    """Top Token项"""
    token_id: int
    token_name: Optional[str] = None
    tokens: int = 0
    reqs: int = 0
    quota_sum: float = 0.0


class TopModelItem(BaseModel):
    """Top模型项"""
    model_name: str
    tokens: int = 0
    reqs: int = 0
    quota_sum: float = 0.0


class TopChannelItem(BaseModel):
    """Top通道项"""
    channel_id: int
    channel_name: Optional[str] = None
    tokens: int = 0
    reqs: int = 0
    quota_sum: float = 0.0


class TopResponse(BaseModel):
    """TopN响应"""
    data: List[Dict[str, Any]]
    by: str = Field(description="排序维度")
    metric: str = Field(description="排序指标")
    limit: int = Field(description="限制数量")


class BurstAnomalyItem(BaseModel):
    """突发频率异常项"""
    token_id: int
    token_name: Optional[str] = None
    request_count: int
    window_sec: int
    threshold: int
    first_request: datetime
    last_request: datetime


class MultiUserTokenAnomalyItem(BaseModel):
    """共享Token异常项"""
    token_id: int
    token_name: Optional[str] = None
    user_count: int
    threshold: int
    users: Optional[str] = None


class IpManyUsersAnomalyItem(BaseModel):
    """IP多用户异常项"""
    ip: str
    user_count: int
    threshold: int
    users: Optional[str] = None
    total_requests: int


class BigRequestAnomalyItem(BaseModel):
    """超大请求异常项"""
    token_id: int
    token_name: Optional[str] = None
    user_id: int
    username: Optional[str] = None
    token_count: int
    created_at: datetime
    mean_tokens: float
    std_tokens: float
    threshold: float
    sigma: float


class AnomalyResponse(BaseModel):
    """异常检测响应"""
    data: List[Dict[str, Any]]
    rule: str = Field(description="规则名称")
    total_count: int = Field(description="异常总数")


class StatsQueryParams(BaseModel):
    """统计查询参数"""
    start_ms: int = Field(description="开始时间戳(毫秒)")
    end_ms: int = Field(description="结束时间戳(毫秒)")
    slot_sec: int = Field(default=60, description="时间粒度(秒)")


class TopQueryParams(BaseModel):
    """TopN查询参数"""
    start_ms: int = Field(description="开始时间戳(毫秒)")
    end_ms: int = Field(description="结束时间戳(毫秒)")
    by: str = Field(description="排序维度", regex="^(user|token|model|channel)$")
    metric: str = Field(description="排序指标", regex="^(tokens|reqs|quota_sum)$")
    limit: int = Field(default=50, ge=1, le=1000, description="限制数量")


class AnomalyQueryParams(BaseModel):
    """异常检测查询参数"""
    start_ms: int = Field(description="开始时间戳(毫秒)")
    end_ms: int = Field(description="结束时间戳(毫秒)")
    rule: str = Field(description="规则名称", regex="^(burst|multi_user_token|ip_many_users|big_request)$")
    
    # 规则特定参数
    window_sec: Optional[int] = Field(default=60, description="时间窗口(秒)")
    users_threshold: Optional[int] = Field(default=5, description="用户数阈值")
    sigma: Optional[float] = Field(default=3.0, description="标准差倍数")
    limit_per_token: Optional[int] = Field(default=120, description="Token请求数阈值")


class ExportQueryParams(BaseModel):
    """导出查询参数"""
    query_type: str = Field(description="查询类型", regex="^(series|top|anomalies)$")
    format: str = Field(default="csv", description="导出格式", regex="^(csv|json)$")
    # 其他参数继承自对应的查询参数
