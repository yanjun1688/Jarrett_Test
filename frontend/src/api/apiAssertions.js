import apiClient from './axios';

// API断言接口 - 优化配合后端同步执行
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

  // 获取单个断言
  getById: (id) => apiClient.get(`/api-assertions/${id}/`),

  // 更新断言
  update: (id, data) => apiClient.put(`/api-assertions/${id}/`, data),

  // 部分更新断言
  patch: (id, data) => apiClient.patch(`/api-assertions/${id}/`, data),

  // 删除断言
  delete: (id) => apiClient.delete(`/api-assertions/${id}/`),
};

export default apiAssertionsAPI;