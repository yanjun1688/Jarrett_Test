/**
 * ChatBot 侧边栏组件（会话列表）
 */
import React from 'react';
import { Button, Spin, List, Popconfirm } from 'antd';
import {
  PlusOutlined,
  MessageOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import '../../styles/chatbot-sidebar.css';

const ChatBotSidebar = ({
  collapsed = true,
  conversations = [],
  conversationId,
  loadingConversations = false,
  maxAllowed = 30,
  onCreateNew,
  onSwitch,
  onDelete,
}) => {
  return (
    <div className={`chatbot-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onCreateNew}
          block
          disabled={conversations.length >= maxAllowed}
        >
          新建会话
        </Button>
      </div>
      <div className="sidebar-content">
        {loadingConversations ? (
          <div className="sidebar-loading">
            <Spin size="small" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="sidebar-empty">
            <MessageOutlined style={{ fontSize: 24, color: '#bfbfbf' }} />
            <p>暂无会话</p>
          </div>
        ) : (
          <List
            dataSource={conversations}
            renderItem={(conv) => (
              <div
                className={`sidebar-item ${conv.conversation_id === conversationId ? 'active' : ''}`}
                onClick={() => onSwitch(conv.conversation_id)}
              >
                <div className="sidebar-item-title">
                  {conv.title || '新对话'}
                </div>
                <div className="sidebar-item-meta">
                  <span>{conv.message_count || 0} 条消息</span>
                  <Popconfirm
                    title="确定删除此会话？"
                    onConfirm={(e) => {
                      e.stopPropagation();
                      onDelete(conv.conversation_id);
                    }}
                    onCancel={(e) => e.stopPropagation()}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      className="sidebar-delete-btn"
                      onClick={(e) => e.stopPropagation()}
                      danger
                    />
                  </Popconfirm>
                </div>
              </div>
            )}
          />
        )}
      </div>
    </div>
  );
};

export default React.memo(ChatBotSidebar);