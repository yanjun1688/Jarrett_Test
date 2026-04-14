// API请求执行 API - 配合后端简化同步执行优化
import apiClient from './axios';

// API请求执行相关的 API 接口
export const apiRequestExecutionAPI = {
  // 执行单个API请求 - 直接同步返回结果
  execute: (apiRequestId) => {
    return apiClient.post(`/api-requests/${apiRequestId}/execute/`);
  },
  
  // 批量执行API请求 - 后端已在同步处理中完成批量操作
  executeBatch: (requestData) => {
    return apiClient.post('/api-requests/execute-batch/', requestData);
  },
  
  // 执行请求集合 - 配合同步执行优化
  executeCollection: (collectionId, executionData = {}) => {
    return apiClient.post(`/request-collections/${collectionId}/execute/`, executionData);
  },
  
  // 获取执行结果 - 由于后端已优化为直接返回，此接口主要用于兼容  
  getExecutionResult: (executionId) => {
    return apiClient.get(`/executions/${executionId}/`);
  },
  
  // 获取集合执行状态
  getCollectionExecutionStatus: (executionId) => {
    return apiClient.get(`/collection-executions/${executionId}/status/`);
  },
  
  // 轮询执行结果（后端优化后，此 API 很可能已被弃用）
  pollExecutionResult: (taskId) => {
    return apiClient.get(`/executions/${taskId}/poll/`);
  }
};

export default apiRequestExecutionAPI;