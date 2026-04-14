// API请求执行服务 API接口 - 匹配后端同步执行优化
import apiClient from './axios';

// API请求执行相关的服务接口
export const apiExecutionService = {
  // 执行API请求相关接口
  execute: (apiRequestId, executionData = {}) => {
    return apiClient.post(`/api-requests/${apiRequestId}/execute/`, executionData);
  },
  
  // 批量执行
  executeBatch: (requestData) => {
    return apiClient.post('/api-requests/execute-batch/', {
      ...requestData,
      mode: 'sync',  // 指明使用同步模式，配合后端优化
    });
  },
  
  // 执行请求集合
  executeCollection: (collectionId, executionData = {}) => {
    return apiClient.post(`/request-collections/${collectionId}/execute/`, executionData);
  },
  
  // 获取执行结果（适配后端同步执行优化）
  getResult: (executionId) => {
    return apiClient.get(`/executions/${executionId}/`);
  },
  
  // 获取执行状态
  getStatus: (executionId) => {
    return apiClient.get(`/executions/${executionId}/status/`);
  },
  
  // 获取执行报告
  getReport: (executionId) => {
    return apiClient.get(`/executions/${executionId}/report/`);
  },
  
  // 获取执行详细信息
  getDetailedResult: (executionId) => {
    return apiClient.get(`/executions/${executionId}/detailed/`);
  },
  
  // 重新执行
  reExecute: (executionId) => {
    return apiClient.post(`/executions/${executionId}/re-execute/`);
  },
  
  // 中断执行（如果还支持的话）
  cancelExecution: (executionId) => {
    return apiClient.post(`/executions/${executionId}/cancel/`);
  },
  
  // 获取执行历史
  getExecutionHistory: (apiRequestId, params = {}) => {
    const queryString = new URLSearchParams(params);
    queryString.append('api_request', apiRequestId);
    return apiClient.get(`/executions/?${queryString.toString()}`);
  }
};

export default apiExecutionService;