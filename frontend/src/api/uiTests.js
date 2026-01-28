import apiClient from './axios';

// UI 测试相关 API
export const uiTestsAPI = {
  // UI 脚本列表 / 详情
  getScripts: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/ui-test/ui-scripts/${queryString ? `?${queryString}` : ''}`);
  },
  getScriptById: (id) => apiClient.get(`/ui-test/ui-scripts/${id}/`),

  // 录制/可视化配置模式创建脚本
  createScriptFromRecording: (data) =>
    apiClient.post('/ui-test/ui-scripts/record/', data),

  // 直接创建/更新脚本（不带 steps，也可用）
  createScript: (data) => apiClient.post('/ui-test/ui-scripts/', data),
  updateScript: (id, data) => apiClient.put(`/ui-test/ui-scripts/${id}/`, data),

  // 执行脚本
  executeScript: (id) =>
    apiClient.post(`/ui-test/ui-scripts/${id}/execute/`),

  // 同步录制（阻塞式）
  syncRecord: (data) =>
    apiClient.post('/ui-test/ui-scripts/sync_record/', data, {
      timeout: 300000, // 增加超时到5分钟，因为是阻塞式录制
    }),

  // 录制完成后的脚本质量检查
  qualityCheck: (data) =>
    apiClient.post('/ui-test/ui-scripts/quality_check/', data),

  // 获取页面预览和元素选择
  previewPage: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/ui-test/ui-scripts/preview_page/${queryString ? `?${queryString}` : ''}`);
  },
  selectElement: (data) =>
    apiClient.post('/ui-test/ui-scripts/select_element/', data),

  // 执行记录
  getExecutions: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return apiClient.get(`/ui-test/ui-executions/${queryString ? `?${queryString}` : ''}`);
  },
  getExecutionById: (id) =>
    apiClient.get(`/ui-test/ui-executions/${id}/`),
  // 获取执行日志详情
  getExecutionLogs: (id) =>
    apiClient.get(`/ui-test/ui-executions/${id}/logs/`),

};


