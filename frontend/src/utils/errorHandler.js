/**
 * 统一错误处理工具
 */
import { notification } from 'antd';
import logger from './logger';

/**
 * 处理API错误
 * @param {Error} error - 错误对象
 * @param {string} customMessage - 自定义错误消息
 * @param {object} options - 选项
 * @returns {string} 错误消息
 */
export const handleApiError = (error, customMessage, options = {}) => {
  const {
    showNotification = true,
    duration = 4,
    logError = true,
  } = options;

  const defaultMessage = customMessage || '操作失败，请稍后重试';
  
  // 提取错误消息
  let errorMessage = defaultMessage;
  
  if (error?.response?.data) {
    const data = error.response.data;
    errorMessage = data.error || 
                   data.detail || 
                   data.message || 
                   (typeof data === 'string' ? data : defaultMessage);
  } else if (error?.message && !customMessage) {
    errorMessage = error.message;
  }

  // 记录错误日志
  if (logError) {
    logger.error('API Error:', {
      message: errorMessage,
      error,
      url: error?.config?.url,
      method: error?.config?.method,
    });
  }

  // 显示通知
  if (showNotification) {
    notification.error({
      message: '操作失败',
      description: errorMessage,
      duration,
      placement: 'topRight',
    });
  }

  return errorMessage;
};


