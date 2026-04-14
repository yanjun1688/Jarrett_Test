/**
 * ChatBot 悬浮按钮组件
 * 在页面右下角显示一个悬浮按钮，点击打开 ChatBot 抽屉
 */
import React, { useState } from 'react';
import { Button, Badge } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
import ChatBotDrawer from './ChatBotDrawer';
import './ChatBotFloatButton.css';
import './ChatBotFloatButton.css';

const ChatBotFloatButton = ({
  title = 'AI 智能助手',
  drawerWidth = 500,
  defaultSystemMessage,
  projectContext
}) => {
  const [visible, setVisible] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const handleOpen = () => {
    setVisible(true);
    setUnreadCount(0);
  };

  const handleClose = () => {
    setVisible(false);
  };

  return (
    <>
      {/* 悬浮按钮 */}
      <div className="chatbot-float-button-container">
        <Badge count={unreadCount} size="small">
          <Button
            type="primary"
            shape="circle"
            size="large"
            icon={<MessageOutlined />}
            onClick={handleOpen}
            className="chatbot-float-button"
          />
        </Badge>
      </div>

      {/* ChatBot 抽屉 */}
      <ChatBotDrawer
        visible={visible}
        onClose={handleClose}
        width={drawerWidth}
        title={title}
        defaultSystemMessage={defaultSystemMessage}
        projectContext={projectContext}
      />
    </>
  );
};

export default ChatBotFloatButton;
