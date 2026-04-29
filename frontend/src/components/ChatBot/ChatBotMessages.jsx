/**
 * ChatBot 消息列表组件
 */
import React, { useRef, useEffect } from 'react';
import { Spin, Avatar } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import MessageItem from './MessageItem';
import '../../styles/chatbot-messages.css';

const ChatBotMessages = ({
  messages = [],
  loading = false,
  onCopy,
  copiedMessageId,
  onSendMessage,
}) => {
  const messagesEndRef = useRef(null);
  const prevMessagesLengthRef = useRef(0);

  // 自动滚动到底部（仅在消息数量增加时）
  useEffect(() => {
    if (messages.length > prevMessagesLengthRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevMessagesLengthRef.current = messages.length;
  }, [messages.length]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="chatbot-empty">
        <RobotOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
        <p className="empty-text">开始与 AI 对话吧</p>
        <p className="empty-hint">可以询问测试相关问题、代码审查、最佳实践等</p>
      </div>
    );
  }

  return (
    <div className="chatbot-messages">
      {messages.map((msg) => (
        <MessageItem
          key={msg.id}
          message={msg}
          onCopy={onCopy}
          isCopied={copiedMessageId === msg.id}
          onSendMessage={onSendMessage}
        />
      ))}
      {loading && (
        <div className="chatbot-message assistant loading">
          <Avatar icon={<RobotOutlined />} className="message-avatar" />
          <div className="message-content">
            <Spin />
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default React.memo(ChatBotMessages);