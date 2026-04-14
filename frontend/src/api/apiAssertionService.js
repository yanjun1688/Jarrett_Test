// API断言 API 服务 - 匹配后端同步执行优化
import apiClient from './axios';

// API断言相关的 API 服务
export const apiAssertionService = {
  // 根据API请求获取断言列表
  getByApiRequest: (apiRequestId, params = {}) => {
    const queryString = new URLSearchParams(params);
    queryString.append('api_request', apiRequestId);
    return apiClient.get(`/api-assertions/?${queryString.toString()}`);
  },
  
  // 创建API断言
  create: (assertionData) => {
    return apiClient.post('/api-assertions/', assertionData);
  },
  
  // 更新API断言
  update: (assertionId, assertionData) => {
    return apiClient.put(`/api-assertions/${assertionId}/`, assertionData);
  },
  
  // 部分更新API断言
  patch: (assertionId, assertionData) => {
    return apiClient.patch(`/api-assertions/${assertionId}/`, assertionData);
  },
  
  // 删除API断言
  delete: (assertionId) => {
    return apiClient.delete(`/api-assertions/${assertionId}/`);
  },
  
  // 批量删除断言
  deleteBatch: (assertionIds) => {
    return apiClient.post('/api-assertions/delete-batch/', { ids: assertionIds });
  },
  
  // 验证断言配置
  validate: (assertionData) => {
    return apiClient.post('/api-assertions/validate/', assertionData);
  },
  
  // 获取可用断言类型
  getAssertionTypes: () => {
    return apiClient.get('/api-assertions/types/');
  },
  
  // 批量创建断言
  bulkCreate: (assertions) => {
    return apiClient.post('/api-assertions/bulk-create/', { assertions });
  }
};

export default apiAssertionService;