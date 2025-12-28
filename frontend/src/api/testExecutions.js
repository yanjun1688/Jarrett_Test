import apiClient from './axios';

export const testExecutionsAPI = {
  // 获取所有测试执行记录
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/executions/${queryString ? `?${queryString}` : ''}`);
  },

  // 获取单个执行记录
  getById: (id) => apiClient.get(`/executions/${id}/`),

  // 创建执行记录
  create: (data) => apiClient.post('/executions/', data),

  // 更新执行记录
  update: (id, data) => apiClient.put(`/executions/${id}/`, data),

  // 部分更新执行记录（状态更新）
  patch: (id, data) => apiClient.patch(`/executions/${id}/`, data),

  // 删除执行记录
  delete: (id) => apiClient.delete(`/executions/${id}/`),

  // 执行动作（如 execute, logs）
  postAction: (id, action) => apiClient.post(`/executions/${id}/${action}/`),
  getAction: (id, action) => apiClient.get(`/executions/${id}/${action}/`),
  
  // 获取API测试日志列表（分页）
  getApiTestLogs: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/reports/api-test-logs/${queryString ? `?${queryString}` : ''}`);
  },
};
