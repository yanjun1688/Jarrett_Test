// API执行接口服务 - 匹配后端同步执行架构优化
import apiClient from './axios';

// API执行服务接口定义
const apiExecutionAPI = {
  // 单个API请求执行接口（同步）
  execute: (apiRequestId, executionData = {}) => {
    return apiClient.post(`/api-requests/${apiRequestId}/execute/`, executionData);
  },

  // 单个API请求执行接口（异步 - Celery）
  executeAsync: (apiRequestId, executionData = {}) => {
    return apiClient.post(`/api-requests/${apiRequestId}/execute-async/`, executionData);
  },

  // 批量执行（同步）
  executeBatch: (requestData, executionOptions = {}) => {
    return apiClient.post('/api-requests/execute-batch/', {
      ...requestData,
      execution_mode: executionOptions.mode || 'sync',
      timeout: executionOptions.timeout || 30000
    });
  },

  // 链式执行API请求（支持变量传递）
  executeChain: (projectId, stopOnFailure = true) => {
    return apiClient.post('/api-requests/execute-chain/', {
      project: projectId,
      stop_on_failure: stopOnFailure
    });
  },

  // 获取执行结果 - 配合后端同步执行优化
  getResult: (executionId) => {
    return apiClient.get(`/executions/${executionId}/`);
  },

  // 获取执行状态详情
  getStatus: (executionId) => {
    return apiClient.get(`/executions/${executionId}/`);
  },

  // 获取执行统计信息
  getStatistics: (executionId) => {
    return apiClient.get(`/executions/${executionId}/statistics/`);
  },
  
  // 获取API执行日志
  getLogs: (executionId) => {
    return apiClient.get(`/executions/${executionId}/logs/`);
  },

  // 获取完整报告
  getReport: (executionId) => {
    return apiClient.get(`/executions/${executionId}/report/`);
  },
  
  // 获取断言验证结果
  getAssertionResults: (executionId) => {
    return apiClient.get(`/executions/${executionId}/assertions/`);
  },
  
  // 重新执行已失败的API请求
  reExecute: (executionId) => {
    return apiClient.post(`/executions/${executionId}/re-execute/`);
  },
  
  // 中止长时间运行的执行（如有必要）
  cancelExecution: (executionId) => {
    return apiClient.post(`/executions/${executionId}/cancel/`);
  },
  
  // 获取API请求执行历史记录
  getExecutionHistory: (apiRequestId, queryParams = {}) => {
    const params = new URLSearchParams(queryParams);
    params.append('api_request', apiRequestId);
    const queryString = params.toString();
    return apiClient.get(`/executions/${queryString ? `?${queryString}` : ''}`);
  },
  
  // 获取最近执行列表
  getRecentExecutions: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/executions/${queryString ? `?${queryString}` : ''}`);
  },
  
  // 验证执行参数
  validate: (executionData) => {
    return apiClient.post('/api-requests/execute-validate/', executionData);
  }
};

export default apiExecutionAPI;