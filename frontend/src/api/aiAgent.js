import apiClient from './axios';

/**
 * AI分析用例相关的API服务
 */

/**
 * 处理PRD文档并生成测试用例
 * @param {File} file - 上传的PRD文档文件（PDF/Word/TXT）
 * @returns {Promise} 返回生成的测试用例数据
 */
export const processPRD = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/ai-agent/process-prd/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};


