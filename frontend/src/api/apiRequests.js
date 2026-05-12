import apiClient from './axios';

// 简化版 API 请求接口 - 配合后端同步执行优化
// 所有 API 现在都直接返回执行结果，无需复杂的异步处理
export const apiRequestsAPI = {
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/api-requests/${queryString ? `?${queryString}` : ''}`);
  },
};
