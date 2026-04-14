// API断言 API - 配合后端简化同步执行优化
import apiClient from './axios';

// API断言相关的 API 接口
export const apiAssertionAPI = {
  // 获取API请求的断言列表
  getByApiRequest: (apiRequestId, params = {}) => {
    const queryParams = new URLSearchParams(params);
    queryParams.append('api_request', apiRequestId);
    const queryString = queryParams.toString();
    return apiClient.get(`/api-assertions/${queryString ? `?${queryString}` : ''}`);
  },
  
  // 创建API断言
  create: (data) => {
    return apiClient.post('/api-assertions/', data);
  },
  
  // 更新API断言
  update: (assertionId, data) => {
    return apiClient.put(`/api-assertions/${assertionId}/`, data);
  },
  
  // 部分更新API断言
  patch: (assertionId, data) => {
    return apiClient.patch(`/api-assertions/${assertionId}/`, data);
  },
  
  // 删除API断言
  delete: (assertionId) => {
    return apiClient.delete(`/api-assertions/${assertionId}/`);
  },
  
  // 批量删除断言
  deleteBatch: (assertionIds) => {
    return apiClient.post('/api-assertions/delete-batch/', { ids: assertionIds });
  },
  
  // 获取所有断言类型
  getAssertionTypes: () => {
    return apiClient.get('/api-assertions/types/');
  },
  
  // 验证断言配置
  validate: (data) => {
    return apiClient.post('/api-assertions/validate/', data);
  },
  
  // 批量断言配置
  bulkCreate: (assertionsData) => {
    return apiClient.post('/api-assertions/bulk-create/', { assertions: assertionsData });
  }
};

export default apiAssertionAPI;