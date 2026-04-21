/**
 * 统一执行记录 API 模块
 * 查询所有类型的执行日志（API测试、压测、高级压测、UI测试、脚本、ChatBot）
 */
import apiClient from './axios';

export const unifiedExecutionsAPI = {
  /**
   * 获取统一执行记录列表
   * @param {Object} params - 查询参数
   * @param {string} [params.script_type] - 脚本类型过滤: api/ui/pressure/advanced_pressure/script/chatbot
   * @param {string} [params.status] - 状态过滤: pending/running/passed/failed/stopped
   * @param {number} [params.project] - 项目ID过滤
   * @param {number} [params.unified_script] - 统一脚本ID过滤
   * @param {number} [params.executed_by] - 执行人ID过滤
   * @param {string} [params.start_date] - 开始时间过滤
   * @param {string} [params.end_date] - 结束时间过滤
   * @returns {Promise}
   */
  getAll: (params = {}) => apiClient.get('/unified/executions/', { params }),

  /**
   * 获取单条执行记录详情（含 logs）
   * @param {number} id - 执行记录ID
   * @returns {Promise}
   */
  getById: (id) => apiClient.get(`/unified/executions/${id}/`),

  /**
   * 获取执行统计
   * @param {Object} params - 查询参数
   * @returns {Promise}
   */
  getStatistics: (params = {}) => apiClient.get('/unified/executions/statistics/', { params }),
};

export default unifiedExecutionsAPI;
