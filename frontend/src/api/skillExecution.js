/**
 * Skill Execution API 调用模块
 * 提供与 Skill 执行服务交互的 API 接口
 * 
 * [MCP Migration] 2024: 搜索和安装已迁移到 MCP Skill Manager Server
 */
import apiClient from './axios';

/**
 * 搜索远程 Skill - MCP Server 代理版本
 * [Migration] 从 GET /skills/remote-search/ 改为 POST /skills/search/
 * @param {string} keyword - 搜索关键词
 * @returns {Promise} API响应
 */
export const searchSkills = async (keyword) => {
  return await apiClient.post('/skills/search/', { keyword });
};

/**
 * 安装远程 Skill 到本地 - MCP Server 代理版本
 * [Migration] 接口保持不变，内部改为调用 MCP Server
 * @param {string} skillName - Skill 名称（格式：owner/repo@skill）
 * @returns {Promise} API响应
 */
export const installSkill = async (skillName) => {
  return await apiClient.post('/skills/install/', { skill_id: skillName });
};

/**
 * 获取本地已安装 Skill 列表 - MCP Server 代理版本（可选）
 * [Migration] 从 GET /skills/local/ 改为调用 MCP Server
 * @returns {Promise} API响应
 */
export const getLocalSkills = async () => {
  return await apiClient.get('/skills/local/');
};

/**
 * 执行 Skill
 * @param {Object} data - 请求数据
 * @param {string} data.skill_name - Skill 名称
 * @param {string} data.user_input - 用户自然语言输入
 * @param {string} [data.provider] - LLM 提供商（默认 qwen）
 * @param {string} [data.conversation_id] - 会话 ID
 * @returns {Promise} API响应
 */
export const executeSkill = async (data) => {
  return await apiClient.post('/skills/execute/', data);
};

/**
 * Skill Execution API 集合
 */
export const skillExecutionAPI = {
  searchSkills,
  installSkill,
  getLocalSkills,
  executeSkill
};

export default skillExecutionAPI;
