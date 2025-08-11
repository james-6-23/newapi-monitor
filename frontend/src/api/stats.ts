/**
 * 统计API接口和类型定义
 */
import api from './client';

// ============ 类型定义 ============

export interface SeriesDataPoint {
  bucket: string;
  reqs: number;
  tokens: number;
  users: number;
  tokens_cnt: number;
}

export interface SeriesResponse {
  data: SeriesDataPoint[];
  total_points: number;
}

export interface TopUserItem {
  user_id: number;
  username?: string;
  tokens: number;
  reqs: number;
  quota_sum: number;
}

export interface TopTokenItem {
  token_id: number;
  token_name?: string;
  tokens: number;
  reqs: number;
  quota_sum: number;
}

export interface TopModelItem {
  model_name: string;
  tokens: number;
  reqs: number;
  quota_sum: number;
}

export interface TopChannelItem {
  channel_id: number;
  channel_name?: string;
  tokens: number;
  reqs: number;
  quota_sum: number;
}

export type TopBy = 'user' | 'token' | 'model' | 'channel';
export type Metric = 'tokens' | 'reqs' | 'quota_sum';

export interface TopResponse {
  data: (TopUserItem | TopTokenItem | TopModelItem | TopChannelItem)[];
  by: TopBy;
  metric: Metric;
  limit: number;
}

export interface BurstAnomalyItem {
  token_id: number;
  token_name?: string;
  request_count: number;
  window_sec: number;
  threshold: number;
  first_request: string;
  last_request: string;
}

export interface MultiUserTokenAnomalyItem {
  token_id: number;
  token_name?: string;
  user_count: number;
  threshold: number;
  users?: string;
  total_requests: number;
}

export interface IpManyUsersAnomalyItem {
  ip: string;
  user_count: number;
  threshold: number;
  users?: string;
  total_requests: number;
}

export interface BigRequestAnomalyItem {
  token_id: number;
  token_name?: string;
  user_id: number;
  username?: string;
  token_count: number;
  created_at: string;
  mean_tokens: number;
  std_tokens: number;
  threshold: number;
  sigma: number;
}

export type Rule = 'burst' | 'multi_user_token' | 'ip_many_users' | 'big_request';

export interface AnomalyResponse {
  data: (BurstAnomalyItem | MultiUserTokenAnomalyItem | IpManyUsersAnomalyItem | BigRequestAnomalyItem)[];
  rule: Rule;
  total_count: number;
}

export interface HealthResponse {
  ok: boolean;
  timestamp: string;
  version: string;
}

// ============ API接口函数 ============

/**
 * 获取健康状态
 */
export const getHealth = (): Promise<HealthResponse> => {
  return api.get<HealthResponse>('/health');
};

/**
 * 获取时序统计数据
 */
export const getSeries = (params: {
  start_ms: number;
  end_ms: number;
  slot_sec?: number;
}): Promise<SeriesResponse> => {
  return api.get<SeriesResponse>('/stats/series', params);
};

/**
 * 获取TopN排行数据
 */
export const getTop = (params: {
  start_ms: number;
  end_ms: number;
  by: TopBy;
  metric: Metric;
  limit?: number;
}): Promise<TopResponse> => {
  return api.get<TopResponse>('/stats/top', params);
};

/**
 * 获取异常检测数据
 */
export const getAnomalies = (params: {
  start_ms: number;
  end_ms: number;
  rule: Rule;
  window_sec?: number;
  users_threshold?: number;
  sigma?: number;
  limit_per_token?: number;
}): Promise<AnomalyResponse> => {
  return api.get<AnomalyResponse>('/stats/anomalies', params);
};

/**
 * 导出CSV数据
 */
export const exportCsv = (params: {
  query_type: 'series' | 'top' | 'anomalies';
  start_ms: number;
  end_ms: number;
  [key: string]: any;
}): Promise<Blob> => {
  return api.download('/export/csv', params);
};

// ============ 工具函数 ============

/**
 * 格式化数字显示
 */
export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

/**
 * 格式化配额显示
 */
export const formatQuota = (quota: number): string => {
  return quota.toFixed(2);
};

/**
 * 获取指标显示名称
 */
export const getMetricLabel = (metric: Metric): string => {
  const labels: Record<Metric, string> = {
    tokens: 'Token数',
    reqs: '请求数',
    quota_sum: '配额消耗',
  };
  return labels[metric];
};

/**
 * 获取维度显示名称
 */
export const getByLabel = (by: TopBy): string => {
  const labels: Record<TopBy, string> = {
    user: '用户',
    token: 'Token',
    model: '模型',
    channel: '通道',
  };
  return labels[by];
};

/**
 * 获取规则显示名称
 */
export const getRuleLabel = (rule: Rule): string => {
  const labels: Record<Rule, string> = {
    burst: '突发频率',
    multi_user_token: '共享Token',
    ip_many_users: '同IP多账号',
    big_request: '超大请求',
  };
  return labels[rule];
};
