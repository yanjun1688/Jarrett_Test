import apiClient from './axios';

// 简化版 API 请求接口 - 配合后端同步执行优化
// 所有 API 现在都直接返回执行结果，无需复杂的异步处理
export const apiRequestsAPI = {
  // 获取所有 API 请求
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/api-requests/${queryString ? `?${queryString}` : ''}`);
  },

  // 获取单个 API 请求
  getById: (id) => apiClient.get(`/api-requests/${id}/`),

  // 创建 API 请求
  create: (data) => apiClient.post('/api-requests/', data),

  // 更新 API 请求
  update: (id, data) => apiClient.put(`/api-requests/${id}/`, data),

  // 部分更新 API 请求  
  patch: (id, data) => apiClient.patch(`/api-requests/${id}/`, data),

  // 删除 API 请求
  delete: (id) => apiClient.delete(`/api-requests/${id}/`),

  // 执行单个 API 请求 - 直接同步执行，返回执行结果
  // 与旧版本相比，此接口现在会同步返回执行结果，包括响应数据和断言验证结果
  execute: (id) => apiClient.post(`/api-requests/${id}/execute/`),

  // 执行多个 API 请求 - 顺序执行，返回批量结果，无需复杂异步调度  
  executeBatch: (data) => apiClient.post('/api-requests/execute-batch/', data),
};

// API断言接口 - 保持原有结构不变
export const apiAssertionsAPI = {
  // 获取所有断言
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/api-assertions/${queryString ? `?${queryString}` : ''}`);
  },

  // 按API请求获取断言
  getByApiRequest: (apiRequestId, params = {}) => {
    const queryParams = { ...params, api_request: apiRequestId };
    const queryString = new URLSearchParams(queryParams).toString();
    return apiClient.get(`/api-assertions/${queryString ? `?${queryString}` : ''}`);
  },

  // 创建断言
  create: (data) => apiClient.post('/api-assertions/', data),

  // 更新断言
  update: (id, data) => apiClient.put(`/api-assertions/${id}/`, data),

  // 部分更新断言
  patch: (id, data) => apiClient.patch(`/api-assertions/${id}/`, data),

  // 删除断言
  delete: (id) => apiClient.delete(`/api-assertions/${id}/`),
};
