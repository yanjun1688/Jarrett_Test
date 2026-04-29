/**
 * 拖拽调整宽度 Hook
 * 解决事件监听泄漏问题
 */
import { useState, useCallback, useEffect, useRef } from 'react';

export const useChatResize = (initialWidth = 500) => {
  const [drawerWidth, setDrawerWidth] = useState(initialWidth);
  const isResizingRef = useRef(false);

  const handleResizeMouseDown = useCallback((e) => {
    e.preventDefault();
    isResizingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMouseMove = (moveEvent) => {
      if (!isResizingRef.current) return;
      const newWidth = window.innerWidth - moveEvent.clientX;
      const clamped = Math.max(400, Math.min(newWidth, window.innerWidth * 0.9));
      setDrawerWidth(clamped);
    };

    const onMouseUp = () => {
      isResizingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);

    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, []);

  return { drawerWidth, handleResizeMouseDown };
};

export default useChatResize;