import apiClient from './axios';

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

  // 执行单个 API 请求
  execute: (id) => apiClient.post(`/api-requests/${id}/execute/`),

  // 批量执行 API 请求
  executeBatch: (data) => apiClient.post('/api-requests/execute-batch/', data),
};
