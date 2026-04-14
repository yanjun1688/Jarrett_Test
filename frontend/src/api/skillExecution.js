/**
 * Skill Execution API 调用模块
 * 提供与 Skill 执行服务交互的 API 接口
 */
import apiClient from './axios';

/**
 * 搜索 Skill
 * @param {string} site - Skill 站点 URL
 * @param {string} keyword - 搜索关键词
 * @returns {Promise} API响应
 */
export const searchSkills = async (site, keyword = '') => {
  const params = new URLSearchParams();
  if (site) params.append('site', site);
  if (keyword) params.append('keyword', keyword);
  return await apiClient.get(`/skills/remote-search/?${params.toString()}`);
};

/**
 * 获取 Skill 执行记录列表
 * TODO: Backend API not implemented - /skills/executions/ endpoint missing
 * @param {Object} params - 查询参数
 * @param {string} [params.status] - 状态过滤 (pending/running/success/failed)
 * @param {string} [params.skill_name] - Skill 名称过滤
 * @param {string} [params.created_at_from] - 创建时间开始
 * @param {string} [params.created_at_to] - 创建时间结束
 * @param {number} [params.page] - 页码
 * @returns {Promise} API响应
 */
/*
export const getSkillExecutions = async (params = {}) => {
  const queryParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      queryParams.append(key, value);
    }
  });
  const queryString = queryParams.toString();
  return await apiClient.get(`/skills/executions/${queryString ? '?' + queryString : ''}`);
};
*/
const getSkillExecutions = async () => {
  throw new Error('Backend API not implemented: /skills/executions/');
};

/**
 * 获取单个 Skill 执行记录详情
 * TODO: Backend API not implemented - /skills/executions/{id}/ endpoint missing
 * @param {number} id - 执行记录 ID
 * @returns {Promise} API响应
 */
/*
export const getSkillExecutionDetail = async (id) => {
  return await apiClient.get(`/skills/executions/${id}/`);
};
*/
const getSkillExecutionDetail = async () => {
  throw new Error('Backend API not implemented: /skills/executions/{id}/');
};

/**
 * 创建并执行 Skill
 * TODO: Backend API not implemented - POST /skills/executions/ endpoint missing
 * @param {Object} data - 请求数据
 * @param {string} data.skill_name - Skill 名称
 * @param {string} data.skill_site - Skill 站点 URL
 * @param {string} data.natural_language_input - 用户自然语言输入
 * @param {Object} [data.execution_params] - 执行参数
 * @returns {Promise} API响应
 */
/*
export const createSkillExecution = async (data) => {
  return await apiClient.post('/skills/executions/', data);
};
*/
const createSkillExecution = async () => {
  throw new Error('Backend API not implemented: POST /skills/executions/');
};

/**
 * 更新 Skill 执行记录
 * TODO: Backend API not implemented - PUT /skills/executions/{id}/ endpoint missing
 * @param {number} id - 执行记录 ID
 * @param {Object} data - 更新数据
 * @returns {Promise} API响应
 */
/*
export const updateSkillExecution = async (id, data) => {
  return await apiClient.put(`/skills/executions/${id}/`, data);
};
*/
const updateSkillExecution = async () => {
  throw new Error('Backend API not implemented: PUT /skills/executions/{id}/');
};

/**
 * 删除 Skill 执行记录
 * TODO: Backend API not implemented - DELETE /skills/executions/{id}/ endpoint missing
 * @param {number} id - 执行记录 ID
 * @returns {Promise} API响应
 */
/*
export const deleteSkillExecution = async (id) => {
  return await apiClient.delete(`/skills/executions/${id}/`);
};
*/
const deleteSkillExecution = async () => {
  throw new Error('Backend API not implemented: DELETE /skills/executions/{id}/');
};

/**
 * Skill Execution API 集合
 */
export const skillExecutionAPI = {
  searchSkills,
  getSkillExecutions,
  getSkillExecutionDetail,
  createSkillExecution,
  updateSkillExecution,
  deleteSkillExecution
};

export default skillExecutionAPI;
