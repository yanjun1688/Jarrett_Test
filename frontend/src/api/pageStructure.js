import apiClient from './axios';

/**
 * 页面结构管理API
 * 用于保存和查询页面HTML结构
 * 
 * 路由统一规范：所有 API 都在 /api/ 下
 */

export const pageStructureAPI = {
  /**
   * 保存页面结构到知识库
   * @param {Object} data
   * @param {number} data.project_id - 项目ID
   * @param {string} data.url - 页面URL
   * @param {string} data.title - 页面标题
   * @param {Array} data.elements - 页面元素列表
   * @returns {Promise}
   */
  savePageStructure: async (data) => {
    const response = await apiClient.post('/knowledge/page-structure/', data);
    return response.data;
  },

  /**
   * 根据URL查询页面结构
   * @param {string} url - 页面URL
   * @param {number} project_id - 项目ID
   * @returns {Promise}
   */
  getPageStructure: async (url, project_id) => {
    const response = await apiClient.get('/knowledge/page-structure/', {
      params: { url, project_id }
    });
    return response.data;
  },

  /**
   * 检查页面结构是否存在
   * @param {string} url - 页面URL
   * @param {number} project_id - 项目ID
   * @returns {Promise<boolean>}
   */
  checkPageStructureExists: async (url, project_id) => {
    try {
      const response = await pageStructureAPI.getPageStructure(url, project_id);
      return response.success && response.data;
    } catch (error) {
      return false;
    }
  },

  /**
   * 自动提取页面元素（使用 Playwright 渲染）
   * @param {Object} params
   * @param {string} params.url - 页面URL
   * @param {string} [params.browser='chromium'] - 浏览器类型
   * @param {boolean} [params.headless=true] - 是否无头模式
   * @param {boolean} [params.wait_for_network=true] - 等待网络空闲
   * @param {string} [params.wait_selector] - 等待特定选择器
   * @param {number} [params.wait_timeout=5000] - 等待超时(ms)
   * @returns {Promise}
   */
  extractElements: async (params) => {
    const response = await apiClient.post('/ui-test/extract-elements/', params);
    return response.data;
  },
};

export default pageStructureAPI;