/**
 * 统一的数据加载Hook
 * 提供通用的数据加载、错误处理、加载状态管理
 */
import { useState, useCallback } from 'react';
import { handleApiError } from '../utils/errorHandler';

/**
 * @param {Function} apiFunction - API调用函数
 * @param {object} options - 选项
 * @param {boolean} options.autoLoad - 是否自动加载（需要提供初始参数）
 * @param {boolean} options.showErrorNotification - 是否显示错误通知
 * @returns {object} { data, loading, error, load, setData, reset }
 */
function useDataLoader(apiFunction, options = {}) {
  const {
    showErrorNotification = true,
    initialData = null,
  } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...args);
      // 处理响应数据格式（支持results数组或直接数据）
      const responseData = result?.data?.results || result?.data || result;
      setData(responseData);
      setError(null);
      return responseData;
    } catch (err) {
      const errorMessage = handleApiError(
        err,
        '加载数据失败',
        { showNotification: showErrorNotification }
      );
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction, showErrorNotification]);

  const reset = useCallback(() => {
    setData(initialData);
    setLoading(false);
    setError(null);
  }, [initialData]);

  return {
    data,
    loading,
    error,
    load,
    setData,
    reset,
  };
}

export default useDataLoader;
