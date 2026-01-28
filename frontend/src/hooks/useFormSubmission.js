/**
 * 表单提交Hook
 * 统一处理表单提交逻辑，包括验证、提交、错误处理
 */
import { useState, useCallback } from 'react';
import { notification } from 'antd';
import { handleApiError, handleFormError } from '../utils/errorHandler';

/**
 * @param {Function} submitFunction - 提交函数
 * @param {object} options - 选项
 * @returns {object} { submitting, submit, reset }
 */
function useFormSubmission(submitFunction, options = {}) {
  const {
    successMessage = '操作成功',
    onSuccess,
    onError,
    showSuccessNotification = true,
  } = options;

  const [submitting, setSubmitting] = useState(false);

  const submit = useCallback(async (values, form) => {
    setSubmitting(true);

    try {
      const result = await submitFunction(values);
      
      if (showSuccessNotification) {
        notification.success({
          message: successMessage,
          duration: 2,
        });
      }

      if (onSuccess) {
        onSuccess(result, values);
      }

      // 如果提供了form，重置表单
      if (form) {
        form.resetFields();
      }

      return result;
    } catch (err) {
      // 如果是表单验证错误，特殊处理
      if (err?.errorFields) {
        handleFormError(err.errorFields);
        if (form) {
          form.setFields(err.errorFields);
        }
      } else {
        handleApiError(err, '操作失败');
      }

      if (onError) {
        onError(err, values);
      }

      throw err;
    } finally {
      setSubmitting(false);
    }
  }, [submitFunction, successMessage, onSuccess, onError, showSuccessNotification]);

  const reset = useCallback(() => {
    setSubmitting(false);
  }, []);

  return {
    submitting,
    submit,
    reset,
  };
}

export default useFormSubmission;
