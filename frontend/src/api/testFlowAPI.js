/**
 * 测试流程编排 API 模块
 * 提供测试流程生成、执行和管理的 API 接口
 * 
 * 路由统一规范：所有 API 都在 /api/ 下
 */
import apiClient from './axios';

/**
 * 执行FlowIR API
 * @param {Object} data - 请求数据
 * @param {Object} data.flow_ir - FlowIR对象
 * @param {Object} [data.context={}] - 上下文
 * @param {number} [data.timeout=600] - 超时时间（秒）
 * @param {boolean} [data.save_result=true] - 是否保存执行记录
 * @returns {Promise} API响应
 */
export const executeFlowIR = async (data) => {
  const response = await apiClient.post('/execution/execute/', {
    flow_ir: data.flow_ir,
    context: data.context || {},
    timeout: data.timeout || 600,
    save_result: data.save_result ?? true
  });
  return response.data;
};

/**
 * 获取测试流程详情
 * @param {number} flowId - 流程 ID
 * @returns {Promise} API 响应
 */
export const getTestFlow = async (flowId) => {
  const response = await apiClient.get(`/flows/${flowId}/`);
  return response.data;
};

/**
 * 获取测试流程执行记录
 * @param {number} executionId - 执行记录 ID
 * @returns {Promise} API 响应
 */
export const getFlowExecution = async (executionId) => {
  const response = await apiClient.get(`/flows/execution/${executionId}/`);
  return response.data;
};

/**
 * 列出测试流程列表
 * @param {Object} params - 查询参数
 * @param {number} params.project_id - 项目 ID（可选）
 * @param {number} params.page - 页码（可选）
 * @param {number} params.page_size - 每页大小（可选）
 * @returns {Promise} API 响应
 */
export const listTestFlows = async (params = {}) => {
  const response = await apiClient.get('/flows/list/', { params });
  return response.data;
};

/**
 * 列出测试流程执行记录
 * @param {Object} params - 查询参数
 * @param {number} params.flow_id - 流程 ID（可选）
 * @param {number} params.project_id - 项目 ID（可选）
 * @param {number} params.page - 页码（可选）
 * @param {number} params.page_size - 每页大小（可选）
 * @returns {Promise} API 响应
 */
export const listFlowExecutions = async (params = {}) => {
  const response = await apiClient.get('/flows/executions/', { params });
  return response.data;
};

/**
 * 获取可用节点类型列表
 * @returns {Promise} API 响应
 */
export const getAvailableNodeTypes = async () => {
  const response = await apiClient.get('/planning/node-types/');
  return response.data;
};

/**
 * 保存/更新测试流程
 * @param {Object} data - 请求数据
 * @param {number} data.flow_id - 流程 ID
 * @param {Object} data.flow_data - 流程数据
 * @returns {Promise} API 响应
 */
export const saveTestFlow = async (data) => {
  const response = await apiClient.put(`/flows/${data.flow_id}/`, data);
  return response.data;
};

/**
 * 删除测试流程
 * @param {number} flowId - 流程 ID
 * @returns {Promise} API 响应
 */
export const deleteTestFlow = async (flowId) => {
  const response = await apiClient.delete(`/flows/${flowId}/`);
  return response.data;
};

/**
 * 测试流程 API 集合
 */
export const testFlowAPI = {
  executeFlowIR,
  getTestFlow,
  getFlowExecution,
  listTestFlows,
  listFlowExecutions,
  getAvailableNodeTypes,
  saveTestFlow,
  deleteTestFlow
};

export default testFlowAPI;