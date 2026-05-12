import axios from './axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

export const advancedPressureTestAPI = {
  config: {
    getAll: (params) => axios.get(`${API_BASE_URL}/advanced-pressure-configs/`, { params }),
    create: (data) => axios.post(`${API_BASE_URL}/advanced-pressure-configs/`, data),
    update: (id, data) => axios.put(`${API_BASE_URL}/advanced-pressure-configs/${id}/`, data),
    delete: (id) => axios.delete(`${API_BASE_URL}/advanced-pressure-configs/${id}/`),
    execute: (id) => axios.post(`${API_BASE_URL}/advanced-pressure-configs/${id}/execute/`),
    getHistory: (id) => axios.get(`${API_BASE_URL}/advanced-pressure-configs/${id}/history/`)
  },
  execution: {
    getById: (id) => axios.get(`${API_BASE_URL}/advanced-pressure-executions/${id}/`),
  }
};

export default advancedPressureTestAPI;