/**
 * 压测功能 API 模块
 * 提供压测配置和执行记录的 API 接口
 */
import apiClient from './axios';

/**
 * 压测配置 API
 */
export const pressureTestConfigAPI = {
  /**
   * 获取压测配置列表
   * @param {Object} params - 查询参数
   * @param {number} [params.project] - 项目ID过滤
   * @param {number} [params.api_request] - API请求ID过滤
   * @param {number} [params.page] - 页码
   * @returns {Promise}
   */
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, value);
      }
    });
    const queryString = queryParams.toString();
    return apiClient.get(`/pressure-test-configs/${queryString ? `?${queryString}` : ''}`);
  },

  /**
   * 获取单个压测配置
   * @param {number} id - 配置ID
   * @returns {Promise}
   */
  getById: (id) => apiClient.get(`/pressure-test-configs/${id}/`),

  /**
   * 创建压测配置
   * @param {Object} data - 配置数据
   * @param {string} data.name - 配置名称
   * @param {number} data.project - 项目ID
   * @param {number} data.api_request - API请求ID
   * @param {string} data.pressure_mode - 压测模式 (instant/sustained/batch)
   * @param {number} [data.request_count] - 瞬时并发总请求数
   * @param {number} [data.rate_per_second] - 持续并发每秒请求数
   * @param {number} [data.duration_seconds] - 持续并发持续秒数
   * @param {number} [data.batch_size] - 分批并发每批数量
   * @param {number} [data.batch_interval] - 分批并发批次间隔(秒)
   * @param {number} [data.max_concurrent] - 最大并发数
   * @returns {Promise}
   */
  create: (data) => apiClient.post('/pressure-test-configs/', data),

  /**
   * 更新压测配置
   * @param {number} id - 配置ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  update: (id, data) => apiClient.put(`/pressure-test-configs/${id}/`, data),

  /**
   * 部分更新压测配置
   * @param {number} id - 配置ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  patch: (id, data) => apiClient.patch(`/pressure-test-configs/${id}/`, data),

  /**
   * 删除压测配置
   * @param {number} id - 配置ID
   * @returns {Promise}
   */
  delete: (id) => apiClient.delete(`/pressure-test-configs/${id}/`),

  /**
   * 执行压测 - 返回 WebSocket URL
   * @param {number} id - 配置ID
   * @returns {Promise} 返回 { execution_id, websocket_url, message }
   */
  execute: (id) => apiClient.post(`/pressure-test-configs/${id}/execute/`),

  /**
   * 获取压测历史记录
   * @param {number} id - 配置ID
   * @returns {Promise}
   */
  getHistory: (id) => apiClient.get(`/pressure-test-configs/${id}/history/`),
};

/**
 * 压测执行记录 API
 */
export const pressureTestExecutionAPI = {
  /**
   * 获取执行记录列表
   * @param {Object} params - 查询参数
   * @param {number} [params.config] - 配置ID过滤
   * @param {string} [params.status] - 状态过滤 (pending/running/completed/stopped/failed)
   * @param {number} [params.page] - 页码
   * @returns {Promise}
   */
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, value);
      }
    });
    const queryString = queryParams.toString();
    return apiClient.get(`/pressure-test-executions/${queryString ? `?${queryString}` : ''}`);
  },

  /**
   * 获取单个执行记录
   * @param {number} id - 执行记录ID
   * @returns {Promise}
   */
  getById: (id) => apiClient.get(`/pressure-test-executions/${id}/`),

  /**
   * 获取执行详细结果（分页）
   * @param {number} id - 执行记录ID
   * @param {Object} params - 分页参数
   * @param {number} [params.page] - 页码
   * @param {number} [params.page_size] - 每页数量
   * @returns {Promise} 返回 { results, count, page }
   */
  getResults: (id, params = {}) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, value);
      }
    });
    const queryString = queryParams.toString();
    return apiClient.get(`/pressure-test-executions/${id}/results/${queryString ? `?${queryString}` : ''}`);
  },
};

/**
 * 压测 API 统一导出
 */
export const pressureTestAPI = {
  config: pressureTestConfigAPI,
  execution: pressureTestExecutionAPI,
};

export default pressureTestAPI;