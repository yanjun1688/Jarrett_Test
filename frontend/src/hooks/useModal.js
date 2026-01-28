/**
 * Modal状态管理Hook
 * 简化Modal的显示/隐藏状态管理
 */
import { useState, useCallback } from 'react';

/**
 * @param {boolean} initialVisible - 初始可见状态
 * @returns {object} { visible, show, hide, toggle }
 */
function useModal(initialVisible = false) {
  const [visible, setVisible] = useState(initialVisible);

  const show = useCallback(() => {
    setVisible(true);
  }, []);

  const hide = useCallback(() => {
    setVisible(false);
  }, []);

  const toggle = useCallback(() => {
    setVisible(prev => !prev);
  }, []);

  return {
    visible,
    show,
    hide,
    toggle,
    setVisible, // 保留直接设置的能力
  };
}

export default useModal;
