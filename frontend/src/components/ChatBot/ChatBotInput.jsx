/**
 * ChatBot 输入组件
 * 关键优化：独立组件，最小渲染范围
 */
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Input, Button, Tooltip } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import '../../styles/chatbot-input.css';

const { TextArea } = Input;

const ChatBotInput = ({
  onSend,
  disabled = false,
  loading = false,
  placeholder = '输入您的问题... (Shift+Enter 换行)',
}) => {
  // 使用 ref 而不是 state，避免每次按键重渲染
  const inputRef = useRef(null);
  const [hasText, setHasText] = useState(false);

  // 检查是否有内容（仅在需要更新按钮状态时）
  const checkHasText = useCallback(() => {
    const text = inputRef.current?.resizableTextArea?.textArea?.value || '';
    setHasText(text.trim().length > 0);
  }, []);

  // 监听输入变化
  const handleInputChange = useCallback(() => {
    checkHasText();
  }, [checkHasText]);

  // 发送消息
  const handleSend = useCallback(() => {
    const textarea = inputRef.current?.resizableTextArea?.textArea;
    const text = textarea?.value?.trim() || '';
    if (text && !disabled && !loading) {
      onSend(text);
      // 清空输入框
      if (textarea) {
        textarea.value = '';
        setHasText(false);
      }
    }
  }, [onSend, disabled, loading]);

  // Enter 发送，Shift+Enter 换行
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // 按钮点击
  const handleButtonClick = useCallback(() => {
    handleSend();
  }, [handleSend]);

  // 初始化后检查
  useEffect(() => {
    checkHasText();
  }, [checkHasText]);

  return (
    <div className="chatbot-input-container">
      <TextArea
        ref={inputRef}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoSize={{ minRows: 1, maxRows: 6 }}
        disabled={disabled || loading}
        className="chatbot-textarea"
      />
      <Tooltip title={loading ? '发送中...' : '发送消息'}>
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleButtonClick}
          loading={loading}
          disabled={!hasText || disabled}
          className="chatbot-send-btn"
        >
          发送
        </Button>
      </Tooltip>
    </div>
  );
};

export default React.memo(ChatBotInput);