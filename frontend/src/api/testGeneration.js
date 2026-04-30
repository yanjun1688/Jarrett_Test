import apiClient from './axios';

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
  generateAPITest,
  generateFromPRD,
  generateFromPRDFile,
  createAndExecuteScript,
};

export default testGenerationAPI;