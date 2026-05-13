/**
 * ChatBot 输入组件
 * 关键优化：独立组件，最小渲染范围
 */
import React, { useState, useCallback } from 'react';
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
  const [inputValue, setInputValue] = useState('');

  const handleInputChange = useCallback((e) => {
    setInputValue(e.target.value);
  }, []);

  const handleSend = useCallback(() => {
    const text = inputValue.trim();
    if (text && !disabled && !loading) {
      onSend(text);
      setInputValue('');
    }
  }, [inputValue, onSend, disabled, loading]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleButtonClick = useCallback(() => {
    handleSend();
  }, [handleSend]);

  return (
    <div className="chatbot-input-container">
      <TextArea
        value={inputValue}
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
          disabled={!inputValue.trim() || disabled}
          className="chatbot-send-btn"
        >
          发送
        </Button>
      </Tooltip>
    </div>
  );
};

export default React.memo(ChatBotInput);