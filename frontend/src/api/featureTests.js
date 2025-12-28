import apiClient from './axios';

export const featureTestsAPI = {
  // 获取所有功能测试
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/feature-tests/${queryString ? `?${queryString}` : ''}`);
  },

  // 获取单个功能测试
  getById: (id) => apiClient.get(`/feature-tests/${id}/`),

  // 创建功能测试
  create: (data) => apiClient.post('/feature-tests/', data),

  // 更新功能测试
  update: (id, data) => apiClient.put(`/feature-tests/${id}/`, data),

  // 部分更新功能测试
  patch: (id, data) => apiClient.patch(`/feature-tests/${id}/`, data),

  // 删除功能测试
  delete: (id) => apiClient.delete(`/feature-tests/${id}/`),
};
