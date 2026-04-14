/**
 * ChatBot API 调用模块
 * 提供与 AI ChatBot 交互的 API 接口
 * 
 * 注意：axios.js 的 baseURL 已经包含 /api，所以这里只需要 /chatbot/ 路径
 */
import apiClient from './axios';

/**
 * 发送消息到 ChatBot
 * @param {Object} data - 请求数据
 * @param {string} data.message - 用户消息
 * @param {string} [data.conversation_id] - 会话ID（可选，不传则创建新会话）
 * @param {string} [data.provider='qwen'] - LLM 提供商 (openai/anthropic/deepseek/zhipu/qwen)
 * @param {string} [data.model] - 模型名称
 * @param {boolean} [data.use_tools=true] - 是否启用工具增强模式
 * @param {boolean} [data.stream=false] - 是否流式输出
 * @returns {Promise} API响应
 */
export const sendMessage = async (data) => {
  return await apiClient.post('/chatbot/chat/', data);
};

/**
 * 获取可用模型列表
 * @returns {Promise} API响应
 */
export const getModels = async () => {
  return await apiClient.get('/chatbot/models/');
};

/**
 * 清空对话历史（保留会话，清空消息）
 * @param {string} conversationId - 会话ID
 * @returns {Promise} API响应
 */
export const clearConversation = async (conversationId) => {
  return await apiClient.post('/chatbot/clear/', { conversation_id: conversationId });
};

/**
 * 获取会话列表
 * @returns {Promise} API响应
 */
export const getConversations = async () => {
  return await apiClient.get('/chatbot/conversations/');
};

/**
 * 创建新会话
 * @param {Object} [data={}] - 请求数据
 * @param {number} [data.project_id] - 项目ID（可选）
 * @returns {Promise} API响应
 */
export const createConversation = async (data = {}) => {
  return await apiClient.post('/chatbot/conversations/', data);
};

/**
 * 获取会话详情
 * @param {string} conversationId - 会话ID
 * @returns {Promise} API响应
 */
export const getConversation = async (conversationId) => {
  return await apiClient.get(`/chatbot/conversations/${conversationId}/`);
};

/**
 * 删除会话
 * @param {string} conversationId - 会话ID
 * @returns {Promise} API响应
 */
export const deleteConversation = async (conversationId) => {
  return await apiClient.delete(`/chatbot/conversations/${conversationId}/`);
};

/**
 * 获取上下文缓存统计
 * @returns {Promise} API响应
 */
export const getCacheStats = async () => {
  return await apiClient.get('/chatbot/cache-stats/');
};

/**
 * 获取ChatBot执行日志列表
 * @param {Object} params - 查询参数
 * @param {string} [params.conversation_id] - 会话ID
 * @param {string} [params.log_type] - 日志类型 (skill/api_test/ui_test)
 * @param {number} [params.page=1] - 页码
 * @param {number} [params.page_size=20] - 每页数量
 * @returns {Promise} API响应
 */
export const getExecutionLogs = async (params = {}) => {
  return await apiClient.get('/chatbot/execution-logs/', { params });
};

/**
 * 获取单条执行日志详情
 * @param {number} logId - 日志ID
 * @returns {Promise} API响应
 */
export const getExecutionLogDetail = async (logId) => {
  return await apiClient.get(`/chatbot/execution-logs/${logId}/`);
};

/**
 * ChatBot API 集合
 */
export const chatbotAPI = {
  sendMessage,
  getModels,
  clearConversation,
  getConversations,
  createConversation,
  getConversation,
  deleteConversation,
  getCacheStats,
  getExecutionLogs,
  getExecutionLogDetail
};

export default chatbotAPI;

// 重新导出 Skill Execution API，方便统一导入
export { skillExecutionAPI } from './skillExecution';
