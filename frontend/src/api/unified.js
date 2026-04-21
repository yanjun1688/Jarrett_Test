import apiClient from './axios';

export const unifiedAPI = {
  getExecutions: (params) => apiClient.get('/unified/executions/', { params }),
  getExecutionById: (id) => apiClient.get(`/unified/executions/${id}/`),
  getStatistics: (params) => apiClient.get('/unified/executions/statistics/', { params }),
  getScripts: (params) => apiClient.get('/unified/scripts/', { params }),
};