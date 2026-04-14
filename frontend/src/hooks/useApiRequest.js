import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';
import logger from '../utils/logger';

const useApiRequest = (apiFunction) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const execute = useCallback(async (params = {}) => {
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // 创建新的 AbortController
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const response = await apiFunction({
        ...params,
        signal: abortControllerRef.current.signal,
      });
      setData(response.data);
      setError(null);
      return response.data;
    } catch (err) {
      if (err.name === 'AbortError') {
        // 请求被取消了，不设置错误状态
        logger.log('Request was aborted');
      } else {
        const errorMessage = err.response?.data?.detail || err.message || '请求失败';
        setError(errorMessage);
        message.error(errorMessage);
      }
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);

  // 重置函数 - 清除状态和取消请求
  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  // 组件卸载时取消请求
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    data,
    loading,
    error,
    execute,
    setData,
    reset,
  };
};

export default useApiRequest;
