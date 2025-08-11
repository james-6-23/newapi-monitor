/**
 * API客户端 - 统一的HTTP请求封装
 */

export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export interface ApiError {
  error: string;
  code: number;
  timestamp: string;
}

export class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    params?: Record<string, any>
  ): Promise<T> {
    // 构建URL
    const url = new URL(this.baseURL + path, window.location.origin);
    
    // 添加查询参数
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    // 默认请求配置
    const config: RequestInit = {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url.toString(), config);
      
      // 检查响应状态
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorData: ApiError = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch {
          // 如果无法解析错误响应，使用默认错误消息
        }
        
        throw new Error(errorMessage);
      }

      // 解析响应
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return response as unknown as T;
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('网络请求失败');
    }
  }

  async get<T>(path: string, params?: Record<string, any>): Promise<T> {
    return this.request<T>(path, { method: 'GET' }, params);
  }

  async post<T>(path: string, data?: any, params?: Record<string, any>): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'POST',
        body: data ? JSON.stringify(data) : undefined,
      },
      params
    );
  }

  async put<T>(path: string, data?: any, params?: Record<string, any>): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'PUT',
        body: data ? JSON.stringify(data) : undefined,
      },
      params
    );
  }

  async delete<T>(path: string, params?: Record<string, any>): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' }, params);
  }

  // 下载文件
  async download(path: string, params?: Record<string, any>): Promise<Blob> {
    const url = new URL(this.baseURL + path, window.location.origin);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString());
    
    if (!response.ok) {
      throw new Error(`下载失败: ${response.statusText}`);
    }

    return response.blob();
  }
}

// 默认API客户端实例
export const apiClient = new ApiClient();

// 便捷方法
export default {
  get: <T>(path: string, params?: Record<string, any>) => apiClient.get<T>(path, params),
  post: <T>(path: string, data?: any, params?: Record<string, any>) => apiClient.post<T>(path, data, params),
  put: <T>(path: string, data?: any, params?: Record<string, any>) => apiClient.put<T>(path, data, params),
  delete: <T>(path: string, params?: Record<string, any>) => apiClient.delete<T>(path, params),
  download: (path: string, params?: Record<string, any>) => apiClient.download(path, params),
};
