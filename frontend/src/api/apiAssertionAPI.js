// API断言接口服务 - 匹配后端同步执行架构优化
import apiClient from './axios';

// API断言相关的服务接口
const apiAssertionAPI = {
  // 获取API请求相关断言
  getByApiRequest: (apiRequestId, params = {}) => {
    const queryString = new URLSearchParams(params);
    queryString.append('api_request', apiRequestId);
    return apiClient.get(`/api-assertions/${queryString.toString() ? `?${queryString.toString()}` : ''}`);
  },

  // 创建断言
  create: (assertionData) => {
    return apiClient.post('/api-assertions/', assertionData);
  },

  // 更新断言
  update: (assertionId, assertionData) => {
    return apiClient.put(`/api-assertions/${assertionId}/`, assertionData);
  },

  // 部分更新断言
  patch: (assertionId, assertionData) => {
    return apiClient.patch(`/api-assertions/${assertionId}/`, assertionData);
  },

  // 删除断言
  delete: (assertionId) => {
    return apiClient.delete(`/api-assertions/${assertionId}/`);
  },

  // 批量删除断言
  deleteBatch: (ids) => {
    return apiClient.post('/api-assertions/delete-batch/', { ids });
  },

  // 获取断言类型枚举
  getAssertionTypes: () => {
    return apiClient.get('/api-assertions/types/');
  },

  // 获取断言执行结果
  getAssertionResult: (assertionResultId) => {
    return apiClient.get(`/assertion-results/${assertionResultId}/`);
  },

  // 批量处理断言 - 适配后端同步执行优化
  batchProcess: (assertionData) => {
    return apiClient.post('/api-assertions/batch-process/', assertionData);
  },
  
  // 验证断言配置
  validateAssertion: (assertionConfig) => {
    return apiClient.post('/api-assertions/validate/', assertionConfig);
  },
  
  // 预览断言执行效果
  previewAssertion: (assertionPreviewData) => {
    return apiClient.post('/api-assertions/preview/', assertionPreviewData);
  },
  
  // 批量断言创建
  bulkCreate: (assertionList) => {
    return apiClient.post('/api-assertions/bulk-create/', { assertions: assertionList });
  },
  
  // 获取断言执行历史
  getAssertionHistory: (assertionId, params = {}) => {
    const queryString = new URLSearchParams(params);
    queryString.append('assertion', assertionId);
    return apiClient.get(`/assertion-executions/${queryString.toString() ? `?${queryString.toString()}` : ''}`);
  },
  
  // 获取断言结果统计
  getAssertionStats: (apiRequestId) => {
    return apiClient.get(`/api-requests/${apiRequestId}/assertion-stats/`);
  }
};

export default apiAssertionAPI;