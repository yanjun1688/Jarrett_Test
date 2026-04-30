/**
 * Agent API调用模块
 * 提供与Agentic X Agent交互的API接口
 * 
 * 路由统一规范：所有 API 都在 /api/ 下
 */
import apiClient from './axios';

/**
 * 统一规划测试流程 API
 * @param {Object} data - 请求数据
 * @param {string} data.scenario - 场景描述
 * @param {number} data.project_id - 项目ID
 * @param {string} [data.test_type='auto'] - 测试类型（ui/api/auto）
 * @param {string} [data.context] - 可选上下文
 * @param {boolean} [data.use_rag=true] - 是否使用RAG
 * @param {boolean} [data.validate=true] - 是否验证
 * @returns {Promise<{success: boolean, flow_ir: Object, steps: Array, validation: Object, statistics: Object}>} API响应
 */
export const planTestFlow = async (data) => {
  const response = await apiClient.post('/planning/plan/', {
    description: data.scenario || data.description,
    project_id: data.project_id,
    test_type: data.test_type || 'auto',
    additional_context: data.additional_context || data.context,
    use_rag: data.use_rag ?? true,
    validate: data.validate ?? true
  });
  return response.data;
};

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
 * 查询知识库
 * @param {Object} data - 请求数据
 * @param {string} data.query - 查询内容
 * @param {number} data.project_id - 项目ID
 * @param {number} [data.top_k=5] - 返回结果数量
 * @param {boolean} [data.use_llm=true] - 是否使用LLM生成答案
 * @returns {Promise} API响应
 */
export const queryKnowledgeBase = async (data) => {
  return await apiClient.post('/knowledge/query/', data);
};

/**
 * 构建知识库
 * @param {Object} data - 请求数据
 * @param {number} data.project_id - 项目ID
 * @param {string} [data.name] - 知识库名称
 * @param {string} [data.description] - 知识库描述
 * @returns {Promise} API响应
 */
export const buildKnowledgeBase = async (data) => {
  return await apiClient.post('/knowledge/build/', data);
};

/**
 * 列出所有知识库
 * @returns {Promise} API响应
 */
export const listKnowledgeBases = async () => {
  return await apiClient.get('/knowledge/list/');
};

/**
 * 获取最佳实践建议
 * @param {Object} data - 请求数据
 * @param {string} [data.context='general'] - 上下文（general, ui, api, performance）
 * @param {number} [data.project_id] - 项目ID
 * @returns {Promise} API响应
 */
export const getBestPractices = async (data = {}) => {
  return await apiClient.post('/knowledge/best-practices/', data);
};

/**
 * 上传文档到知识库
 * @param {FormData} formData - 表单数据
 * @param {number} formData.get('project_id') - 项目ID
 * @param {string} formData.get('doc_type') - 文档类型 (prd, api_doc)
 * @param {string} formData.get('title') - 文档标题
 * @param {File} formData.get('file') - 文件对象 (可选)
 * @param {string} formData.get('content') - 文档内容 (可选, 纯文本时使用)
 * @returns {Promise} API响应
 */
export const uploadDocument = async (formData) => {
  return await apiClient.post('/knowledge/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * 删除知识库文档
 * @param {number} documentId - 文档ID
 * @returns {Promise} API响应
 */
export const deleteKnowledgeDocument = async (documentId) => {
  return await apiClient.delete(`/knowledge/documents/${documentId}/`);
};

/**
 * 同步知识库文档到向量库
 * 优先尝试Celery，失败则降级同步执行
 * @param {number} documentId - 文档ID
 * @returns {Promise} API响应
 */
export const syncDocument = async (documentId) => {
  return await apiClient.post(`/knowledge/documents/${documentId}/sync/`);
};

/**
 * 获取知识库文档列表
 * @param {Object} params - 查询参数
 * @param {number} [params.knowledge_base_id] - 知识库ID
 * @param {number} [params.project_id] - 项目ID
 * @returns {Promise} API响应
 */
export const listKnowledgeDocuments = async (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return await apiClient.get(`/knowledge/documents/${queryString ? `?${queryString}` : ''}`);
};

/**
 * Agent API集合
 */
export const agentAPI = {
  planTestFlow,
  executeFlowIR,
  queryKnowledgeBase,
  buildKnowledgeBase,
  listKnowledgeBases,
  getBestPractices,
  uploadDocument,
  deleteKnowledgeDocument,
  syncDocument,
  listKnowledgeDocuments
};

export default agentAPI;