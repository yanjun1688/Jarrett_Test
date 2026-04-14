// API请求执行 API 服务 - 匹配后端同步执行优化
import apiClient from './axios';

// API请求执行相关的 API 服务
export const executeApiRequest = {
  // 直接执行单个API请求 - 配合后端简化同步执行
  execute: (apiRequestId, testData = {}) => {
    return apiClient.post(`/api-requests/${apiRequestId}/execute/`, testData);
  },
  
  // 批量执行API请求 - 后端已同步处理优化
  executeBatch: (requestData) => {
    return apiClient.post('/api-requests/execute-batch/', requestData);
  },
  
  // 执行请求集合 - 同步执行并返回结果
  executeCollection: (collectionId, executionData = {}) => {
    return apiClient.post(`/request-collections/${collectionId}/execute/`, executionData);
  },
  
  // 获取执行详情 - 适配后端同步执行返回模式
  getExecutionResult: (executionId) => {
    return apiClient.get(`/executions/${executionId}/`);
  },
  
  // 检查执行状态
  getExecutionStatus: (executionId) => {
    return apiClient.get(`/executions/${executionId}/status/`);
  },
  
  // 获取执行日志
  getExecutionLogs: (executionId) => {
    return apiClient.get(`/executions/${executionId}/logs/`);
  },
  
  // 重新执行上次失败的请求
  retryFailedRequest: (executionId) => {
    return apiClient.post(`/executions/${executionId}/retry/`);
  }
};

export default executeApiRequest;