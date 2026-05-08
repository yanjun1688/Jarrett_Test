/**
 * Skill Execution API 调用模块
 * 提供与 Skill 服务交互的 API 接口
 * 
 * [MCP Migration] 2024: 搜索和安装已迁移到 MCP Skill Manager Server
 */
import apiClient from './axios';

/**
 * 搜索远程 Skill - MCP Server 代理版本
 * @param {string} keyword - 搜索关键词
 * @returns {Promise} API响应
 */
export const searchSkills = async (keyword) => {
  return await apiClient.post('/skills/search/', { keyword });
};

/**
 * 安装远程 Skill 到本地 - MCP Server 代理版本
 * @param {string} skillName - Skill 名称（格式：owner/repo@skill）
 * @returns {Promise} API响应
 */
export const installSkill = async (skillName) => {
  return await apiClient.post('/skills/install/', { skill_id: skillName });
};

/**
 * 获取本地已安装 Skill 列表 - MCP Server 代理版本
 * @returns {Promise} API响应
 */
export const getLocalSkills = async () => {
  return await apiClient.get('/skills/local/');
};

/**
 * Skill Execution API 集合
 */
export const skillExecutionAPI = {
  searchSkills,
  installSkill,
  getLocalSkills,
};

export default skillExecutionAPI;
