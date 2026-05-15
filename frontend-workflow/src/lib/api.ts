import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  timeout: 10000,
});

// 请求拦截：注入 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：处理 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// 告警相关 API
export const alertsApi = {
  list: (params: Record<string, any>) =>
    api.get('/api/alerts', { params }),
  get: (id: string) =>
    api.get(`/api/alerts/${id}`),
  create: (data: any) =>
    api.post('/api/alerts', data),
  update: (id: string, data: any) =>
    api.patch(`/api/alerts/${id}`, data),
  // 工作流流转
  assign: (id: string, userId: string) =>
    api.post(`/api/alerts/${id}/assign`, { user_id: userId }),
  resolve: (id: string, resolution: string) =>
    api.post(`/api/alerts/${id}/resolve`, { resolution }),
  close: (id: string) =>
    api.post(`/api/alerts/${id}/close`),
};
