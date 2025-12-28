import apiClient from './axios';

export const testCasesAPI = {
  // 获取所有测试用例
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/testcases/${queryString ? `?${queryString}` : ''}`);
  },

  // 获取单个测试用例
  getById: (id) => apiClient.get(`/testcases/${id}/`),

  // 创建测试用例
  create: (data) => apiClient.post('/testcases/', data),

  // 更新测试用例
  update: (id, data) => apiClient.put(`/testcases/${id}/`, data),

  // 部分更新测试用例
  patch: (id, data) => apiClient.patch(`/testcases/${id}/`, data),

  // 删除测试用例
  delete: (id) => apiClient.delete(`/testcases/${id}/`),
};
