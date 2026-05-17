/**
 * 共享 API 客户端
 * 
 * 提供统一的 API 调用封装：
 * - 自动携带 Token
 * - 错误处理
 * - 请求重试
 * - 类型提示
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

export interface ApiConfig {
  baseURL: string;
  timeout?: number;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data?: T;
}

class ApiClient {
  private client: AxiosInstance;
  
  constructor(config: ApiConfig) {
    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // 请求拦截器：添加 Token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );
    
    // 响应拦截器：统一错误处理
    this.client.interceptors.response.use(
      (response) => response.data,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token 过期，尝试刷新
          const refreshed = await this.tryRefreshToken();
          if (refreshed) {
            // 重试原请求
            const config = error.config!;
            config.headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`;
            return this.client.request(config);
          }
        }
        return Promise.reject(error);
      }
    );
  }
  
  private async tryRefreshToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    
    try {
      const response = await axios.post(`${this.client.defaults.baseURL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      
      if (response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token);
        return true;
      }
    } catch {
      // 刷新失败
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return false;
  }
  
  // ========== API 方法封装 ==========
  
  async get<T = any>(url: string, params?: any): Promise<T> {
    const response = await this.client.get<ApiResponse<T>>(url, { params });
    return response.data;
  }
  
  async post<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<ApiResponse<T>>(url, data);
    return response.data;
  }
  
  async put<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<ApiResponse<T>>(url, data);
    return response.data;
  }
  
  async delete<T = any>(url: string): Promise<T> {
    const response = await this.client.delete<ApiResponse<T>>(url);
    return response.data;
  }
  
  // ========== WebSocket ==========
  
  createWebSocket(path: string): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${this.client.defaults.baseURL}${path}`;
    return new WebSocket(wsUrl);
  }
}

// 默认实例
export const api = new ApiClient({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
});

// 导出工厂函数
export function createApiClient(config: ApiConfig): ApiClient {
  return new ApiClient(config);
}

// ========== 业务 API 模块 ==========

export const sensorApi = {
  list: (params?: any) => api.get('/sensors', params),
  data: (id: string) => api.get(`/sensors/${id}/data`),
  streams: () => api.get('/sensors/streams'),
};

export const alertApi = {
  list: (params?: any) => api.get('/alerts', params),
  create: (data: any) => api.post('/alerts', data),
  update: (id: string, data: any) => api.patch(`/alerts/${id}`, data),
  subscribe: () => api.createWebSocket('/ws/alerts'),
};

export const visionApi = {
  detect: (data: any) => api.post('/vision/detect', data),
};

export const expertApi = {
  query: (question: string) => api.post('/expert/query', { question }),
  generateForm: (context: any) => api.post('/expert/forms/generate', context),
};

export { ApiClient, ApiConfig, ApiResponse };
