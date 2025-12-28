import apiClient from './axios';

export const requestCollectionsAPI = {
  // 获取所有请求集合
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/request-collections/${queryString ? `?${queryString}` : ''}`);
  },

  // 获取单个请求集合
  getById: (id) => apiClient.get(`/request-collections/${id}/`),

  // 创建请求集合
  create: (data) => apiClient.post('/request-collections/', data),

  // 更新请求集合
  update: (id, data) => apiClient.put(`/request-collections/${id}/`, data),

  // 部分更新请求集合
  patch: (id, data) => apiClient.patch(`/request-collections/${id}/`, data),

  // 删除请求集合
  delete: (id) => apiClient.delete(`/request-collections/${id}/`),

  // 执行请求集合
  execute: (id) => apiClient.post(`/request-collections/${id}/execute/`),

  // YAML配置相关
  yamlToCollection: (projectId, data) => apiClient.post(`/projects/${projectId}/yaml-to-collection/`, data),

  validateYaml: (projectId, data) => apiClient.post(`/projects/${projectId}/yaml/validate/`, data),
};
