/**
 * 统一执行记录 API 模块
 * 查询所有类型的执行日志（API测试、压测、高级压测、UI测试、脚本、ChatBot）
 */
import apiClient from './axios';

export const unifiedExecutionsAPI = {
  getAll: (params = {}) => apiClient.get('/unified/executions/', { params }),
};

export default unifiedExecutionsAPI;
