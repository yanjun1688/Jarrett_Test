/**
 * Agent API调用模块
 * 提供与Agentic X Agent交互的API接口
 * 
 * 路由统一规范：所有 API 都在 /api/ 下
 */
import apiClient from './axios';

export const uploadDocument = async (formData) => {
  return await apiClient.post('/knowledge/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const deleteKnowledgeDocument = async (documentId) => {
  return await apiClient.delete(`/knowledge/documents/${documentId}/`);
};

export const syncDocument = async (documentId) => {
  return await apiClient.post(`/knowledge/documents/${documentId}/sync/`);
};

export const listKnowledgeDocuments = async (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return await apiClient.get(`/knowledge/documents/${queryString ? `?${queryString}` : ''}`);
};

export const agentAPI = {
  uploadDocument,
  deleteKnowledgeDocument,
  syncDocument,
  listKnowledgeDocuments
};

export default agentAPI;