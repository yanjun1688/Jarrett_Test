import apiClient from './axios';

/**
 * @deprecated 描述生成功能已废弃。保留仅用于 DescriptionForm 组件。
 * 替代方案：使用 generateFromPRD / generateFromPRDFile（PRD文档）或 generateAPITest（API定义）。
 */
export const generateUITest = async (data) => {
  return await apiClient.post('/chatbot/chat/', {
    message: data.description,
    project_id: data.project_id,
    test_type: 'ui',
    source: 'generator',
    url: data.url || undefined,
  });
};

export const generateAPITest = async (data) => {
  return await apiClient.post('/chatbot/chat/', {
    message: data.description || `测试 API ${data.method || 'GET'} ${data.endpoint || ''}`,
    project_id: data.project_id,
    test_type: 'api',
    source: 'generator',
    endpoint: data.endpoint || undefined,
    method: data.method || undefined,
  });
};

export const generateFromPRD = async (data) => {
  return await apiClient.post('/chatbot/chat/', {
    message: data.description,
    project_id: data.project_id,
    test_type: 'prd',
    source: 'generator',
  });
};

export const generateFromPRDFile = async (formData) => {
  return await apiClient.post('/chatbot/chat/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const createAndExecuteScript = async (projectId, jsonContent) => {
  const scriptRes = await apiClient.post('/test-scripts/', {
    name: `AI生成测试-${Date.now()}`,
    script_type: 'api',
    content: jsonContent,
    project: projectId,
    source: 'chatbot',
  });
  
  const scriptId = scriptRes.data.id;
  
  const execRes = await apiClient.post(`/test-scripts/${scriptId}/execute/`);
  
  return execRes.data;
};

export const testGenerationAPI = {
  generateUITest,
  generateAPITest,
  generateFromPRD,
  generateFromPRDFile,
  createAndExecuteScript,
};

export default testGenerationAPI;