import React, { useEffect, useRef, useState } from 'react';
import { Card } from 'antd';

/**
 * 浏览器画面显示组件
 * 
 * @param {object} props
 * @param {string} props.screenshotData - Base64编码的截图数据 (data:image/png;base64,...)
 * @param {function} props.onMouseEvent - 鼠标事件回调
 * @param {function} props.onKeyboardEvent - 键盘事件回调
 * @param {boolean} props.elementSelectMode - 元素选择模式（默认false）
 * @param {object} props.highlightRect - 高亮矩形 {x, y, width, height}（可选）
 */
const BrowserViewer = ({
  screenshotData,
  onMouseEvent,
  onKeyboardEvent,
  elementSelectMode = false,
  highlightRect = null,
}) => {
  const canvasRef = useRef(null);
  const imgRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);

  // 更新截图显示
  useEffect(() => {
    if (screenshotData && imgRef.current) {
      setIsLoading(true);
      imgRef.current.src = screenshotData;
      imgRef.current.onload = () => {
        setIsLoading(false);
        
        // 将图片绘制到Canvas（用于后续交互）
        if (canvasRef.current && imgRef.current) {
          const canvas = canvasRef.current;
          const ctx = canvas.getContext('2d');
          const img = imgRef.current;
          
          // 设置Canvas尺寸匹配图片
          canvas.width = img.width;
          canvas.height = img.height;
          
          // 绘制图片
          ctx.drawImage(img, 0, 0);
        }
      };
    }
  }, [screenshotData]);

  // 绘制高亮矩形
  useEffect(() => {
    if (highlightRect && overlayCanvasRef.current && canvasRef.current && imgRef.current) {
      const overlayCanvas = overlayCanvasRef.current;
      const mainCanvas = canvasRef.current;
      
      // 设置覆盖层Canvas尺寸与主Canvas一致
      overlayCanvas.width = mainCanvas.width;
      overlayCanvas.height = mainCanvas.height;
      
      const ctx = overlayCanvas.getContext('2d');
      
      // 清空画布
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
      
      // 绘制高亮矩形
      ctx.strokeStyle = '#1890ff';
      ctx.lineWidth = 3;
      ctx.setLineDash([]);
      ctx.strokeRect(
        highlightRect.x,
        highlightRect.y,
        highlightRect.width,
        highlightRect.height
      );
      
      // 绘制半透明背景
      ctx.fillStyle = 'rgba(24, 144, 255, 0.1)';
      ctx.fillRect(
        highlightRect.x,
        highlightRect.y,
        highlightRect.width,
        highlightRect.height
      );
    } else if (overlayCanvasRef.current) {
      // 清除高亮
      const overlayCanvas = overlayCanvasRef.current;
      const ctx = overlayCanvas.getContext('2d');
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    }
  }, [highlightRect]);

  // 处理鼠标事件
  const handleMouseEvent = (event, type) => {
    if (!canvasRef.current || !onMouseEvent) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // 计算相对于Canvas内容的坐标（考虑缩放）
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const relativeX = x * scaleX;
    const relativeY = y * scaleY;

    onMouseEvent({
      event_type: type,
      x: Math.round(relativeX),
      y: Math.round(relativeY),
      button: event.button === 2 ? 'right' : event.button === 1 ? 'middle' : 'left',
    });

    // 阻止默认行为
    if (type === 'contextmenu') {
      event.preventDefault();
    }
  };

  // 处理键盘事件
  const handleKeyboardEvent = (event, type) => {
    if (!onKeyboardEvent) return;

    onKeyboardEvent({
      event_type: type,
      key: event.key,
      code: event.code,
      ctrlKey: event.ctrlKey,
      shiftKey: event.shiftKey,
      altKey: event.altKey,
    });

    // 某些按键需要阻止默认行为
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(event.key)) {
      event.preventDefault();
    }
  };

  return (
    <Card
      title="浏览器画面"
      style={{ width: '100%' }}
      bodyStyle={{ padding: 0, position: 'relative' }}
    >
      <div style={{ position: 'relative', display: 'inline-block' }}>
        {/* 隐藏的img用于加载图片 */}
        <img
          ref={imgRef}
          alt="browser screenshot"
          style={{ display: 'none' }}
        />
        
        {/* Canvas用于显示和交互 */}
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <canvas
            ref={canvasRef}
            style={{
              display: 'block',
              maxWidth: '100%',
              height: 'auto',
              cursor: elementSelectMode ? 'crosshair' : 'pointer',
            }}
            onMouseDown={(e) => handleMouseEvent(e, 'mousedown')}
            onMouseUp={(e) => handleMouseEvent(e, 'mouseup')}
            onMouseMove={(e) => handleMouseEvent(e, 'mousemove')}
            onClick={(e) => handleMouseEvent(e, 'click')}
            onDoubleClick={(e) => handleMouseEvent(e, 'dblclick')}
            onContextMenu={(e) => handleMouseEvent(e, 'contextmenu')}
            onKeyDown={(e) => handleKeyboardEvent(e, 'keydown')}
            onKeyUp={(e) => handleKeyboardEvent(e, 'keyup')}
            tabIndex={0} // 使Canvas可以接收键盘事件
          />
          {/* 覆盖层Canvas用于绘制高亮 */}
          <canvas
            ref={overlayCanvasRef}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              pointerEvents: 'none',
              maxWidth: '100%',
              height: 'auto',
            }}
          />
        </div>
        
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
            }}
          >
            <span>加载中...</span>
          </div>
        )}
        
        {!screenshotData && (
          <div
            style={{
              minHeight: '400px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#999',
            }}
          >
            等待浏览器画面...
          </div>
        )}
      </div>
    </Card>
  );
};

export default BrowserViewer;

