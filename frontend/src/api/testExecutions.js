import apiClient from './axios';

export const testExecutionsAPI = {
  getById: (id) => apiClient.get(`/executions/${id}/`),
};