// API请求执行服务 - 匹配后端优化架构
import apiClient from './axios';

// API请求执行服务接口定义
const apiRequestExecutionService = {
  // 直接执行API请求 - 匹配后端同步执行优化
  execute: (apiRequestId, executionData = {}) => {
    return apiClient.post(`/api-requests/${apiRequestId}/execute/`, executionData);
  },
  
  // 批量执行API请求 - 后端已同步处理优化
  executeBatch: (requestData, options = {}) => {
    return apiClient.post('/api-requests/execute-batch/', {
      ...requestData,
      execution_options: {
        mode: 'sync',  // 使用同步执行模式匹配后端优化
        ...options
      }
    });
  },
  
  // 执行请求集合 - 配合改进执行策略
  executeCollection: (collectionId, executionData = {}) => {
    return apiClient.post(`/request-collections/${collectionId}/execute/`, executionData);
  },
  
  // 获取执行结果 - 适配后端同步返回结果
  getResult: (executionId) => {
    return apiClient.get(`/executions/${executionId}/`);
  },
  
  // 获取执行状态
  getStatus: (executionId) => {
    return apiClient.get(`/executions/${executionId}/status/`);
  },
  
  // 获取详细执行报告
  getReport: (executionId) => {
    return apiClient.get(`/executions/${executionId}/full-result/`);
  },
  
  // 获取API请求执行统计信息
  getExecutionStats: (apiRequestId) => {
    return apiClient.get(`/api-requests/${apiRequestId}/execution-stats/`);
  },
  
  // 获取最新的执行记录
  getLatestExecutions: (apiRequestId, limit = 10) => {
    const params = new URLSearchParams({ 
      api_request: apiRequestId,
      ordering: '-created_at',
      limit: limit 
    });
    return apiClient.get(`/executions/?${params.toString()}`);
  },
  
  // 获取集合执行的详细结果
  getCollectionExecutionResult: (executionId) => {
    return apiClient.get(`/collection-executions/${executionId}/detailed-result/`);
  },
  
  // 获取执行指标数据
  getMetrics: (executionId) => {
    return apiClient.get(`/executions/${executionId}/metrics/`);
  },
  
  // 重新执行（如果还支持的话）
  reExecute: (executionId) => {
    return apiClient.post(`/executions/${executionId}/re-execute/`);
  },
  
  // 高级执行选项
  advancedExecute: (apiRequestId, options) => {
    return apiClient.post(`/api-requests/${apiRequestId}/advanced-execute/`, {
      ...options,
      type: 'api'  // 定义请求类型
    });
  },
  
  // 获取执行日志
  getExecutionLogs: (executionId) => {
    return apiClient.get(`/executions/${executionId}/logs/`);
  }
};

export default apiRequestExecutionService;