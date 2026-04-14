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

/**
 * 处理通用错误
 * @param {Error} error - 错误对象
 * @param {string} customMessage - 自定义错误消息
 */
export const handleError = (error, customMessage) => {
  const errorMessage = customMessage || error?.message || '发生了未知错误';
  
  logger.error('Error:', error);
  
  notification.error({
    message: '错误',
    description: errorMessage,
    duration: 4,
  });
  
  return errorMessage;
};

/**
 * 处理表单验证错误
 * @param {object} errorFields - Ant Design表单错误字段
 */
export const handleFormError = (errorFields) => {
  if (errorFields && errorFields.length > 0) {
    const firstError = errorFields[0];
    notification.warning({
      message: '表单验证失败',
      description: firstError.errors?.[0] || '请检查表单填写',
      duration: 3,
    });
  }
};
