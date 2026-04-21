import apiClient from './axios';

export const testExecutionsAPI = {
  getAll: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/executions/${queryString ? `?${queryString}` : ''}`);
  },
  
  getById: (id) => apiClient.get(`/executions/${id}/`),
  
  patch: (id, data) => apiClient.patch(`/executions/${id}/`, data),
  
  getApiTestLogs: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/executions/${queryString ? `?${queryString}&test_type=api` : '?test_type=api'}`);
  },
};