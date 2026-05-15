import apiClient from './axios';

export const projectsAPI = {
  // 获取所有项目
  getAll: () => apiClient.get('/projects/'),

  // 获取单个项目详情
  getById: (id) => apiClient.get(`/projects/${id}/`),

  // 获取统计（全局 + 所有/指定项目）
  getStatistics: (params) => apiClient.get('/projects/statistics/', { params }),

  // 获取全局统计（无参）
  getGlobalStatistics: () => apiClient.get('/projects/statistics/'),

  // 获取指定项目统计
  getProjectStatistics: (id) => apiClient.get('/projects/statistics/', { params: { project: id } }),

  // 创建项目
  create: (data) => apiClient.post('/projects/', data),

  // 更新项目
  update: (id, data) => apiClient.put(`/projects/${id}/`, data),

  // 部分更新项目
  patch: (id, data) => apiClient.patch(`/projects/${id}/`, data),

  // 删除项目
  delete: (id) => apiClient.delete(`/projects/${id}/`),
};
