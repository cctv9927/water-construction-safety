import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  timeout: 30000, // RAG 查询可能较长
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;

export const expertApi = {
  // 知识库问答
  query: (question: string, siteId?: string) =>
    api.post('/api/expert/query', { question, site_id: siteId }),

  // 表格生成
  generateForm: (formType: string, context: string) =>
    api.post('/api/expert/forms/generate', { form_type: formType, context }),

  // 智慧填报
  fillForm: (formType: string, partialData: Record<string, any>, description: string) =>
    api.post('/api/expert/forms/fill', { form_type: formType, partial_data: partialData, description }),
};

// 质量问答 API（知识库检索 + LLM 生成回答）
export const qaApi = {
  ask: (question: string) => api.post('/qa/ask', { question }),
};

// 表单生成 & 填报 API
export const formApi = {
  generate: (desc: string) => api.post('/form/generate', { description: desc }),
  submit: (data: any) => api.post('/form/submit', data),
};
