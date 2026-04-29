/**
 * 单条消息组件
 */
import React from 'react';
import { Button, Tooltip } from 'antd';
import { UserOutlined, RobotOutlined, CopyOutlined, CheckOutlined } from '@ant-design/icons';
import ChatBotMessageRenderer from '../ChatBotMessageRenderer';
import '../../styles/message-item.css';

const MessageItem = ({ message, onCopy, isCopied, onSendMessage }) => {
  const isUser = message.role === 'user';

  const getCopyText = (content) => {
    if (typeof content === 'string') return content;
    if (content?.message) return content.message;
    if (content?.response) return content.response;
    if (content?.tool_result?.data?.result) return content.tool_result.data.result;
    return JSON.stringify(content, null, 2);
  };

  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-header">
        <span className="message-role">
          {isUser ? (
            <><UserOutlined /> 您</>
          ) : (
            <><RobotOutlined /> AI</>
          )}
        </span>
        <span className="message-time">
          {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </span>
      </div>
      <div className="message-content">
        {isUser ? (
          message.content
        ) : (
          <ChatBotMessageRenderer 
            content={message.content} 
            onSendMessage={onSendMessage}
          />
        )}
      </div>
      <div className="message-actions">
        <Tooltip title="复制">
          <Button
            type="text"
            size="small"
            icon={isCopied ? <CheckOutlined /> : <CopyOutlined />}
            onClick={() => onCopy(getCopyText(message.content), message.id)}
          />
        </Tooltip>
      </div>
    </div>
  );
};

export default React.memo(MessageItem);