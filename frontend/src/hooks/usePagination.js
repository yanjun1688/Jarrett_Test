/**
 * 分页逻辑Hook
 * 统一管理分页状态和逻辑
 */
import { useState, useCallback } from 'react';

/**
 * @param {object} initialPagination - 初始分页配置
 * @returns {object} { pagination, setPagination, reset, handleTableChange }
 */
function usePagination(initialPagination = {}) {
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
    showSizeChanger: true,
    showTotal: (total) => `共 ${total} 条记录`,
    pageSizeOptions: ['10', '20', '50', '100'],
    ...initialPagination,
  });

  const handleTableChange = useCallback((newPagination) => {
    setPagination(prev => ({
      ...prev,
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    }));
  }, []);

  const reset = useCallback(() => {
    setPagination(prev => ({
      ...prev,
      current: 1,
    }));
  }, []);

  const updateTotal = useCallback((total) => {
    setPagination(prev => ({
      ...prev,
      total,
    }));
  }, []);

  return {
    pagination,
    setPagination,
    reset,
    handleTableChange,
    updateTotal,
  };
}

export default usePagination;
