import React, { useState, useEffect, useRef, useCallback, useDeferredValue } from 'react';
import { Drawer, Input, Button, Select, message, Space, Divider, Tag, Spin, Tooltip, List, Popconfirm, Avatar } from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  ClearOutlined,
  ThunderboltOutlined,
  UserOutlined,
  SettingOutlined,
  CopyOutlined,
  CheckOutlined,
  ToolOutlined,
  PlusOutlined,
  MessageOutlined,
  DeleteOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DatabaseOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { chatbotAPI } from '../api';
import { handleApiError } from '../utils/errorHandler';
import './ChatBotDrawer.css';
import SkillExecutionManager from './SkillExecutionManager';
import ChatBotMessageRenderer from './ChatBotMessageRenderer';
import CacheStatsPanel from './CacheStatsPanel';

const { TextArea } = Input;
const { Option } = Select;

const ChatBotDrawer = ({
  visible = false,
  onClose,
  width = 500,
  title = 'AI 智能助手',
  defaultSystemMessage = '你是一个智能助手，请用清晰、专业的语言回答问题。',
  initialMessage = '',
  projectContext = null
}) => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState(initialMessage);
  const inputTextDeferred = useDeferredValue(inputText);
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [systemMessage, setSystemMessage] = useState(defaultSystemMessage);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState(null);
  const [skillManagerVisible, setSkillManagerVisible] = useState(false);
  const [cacheStatsVisible, setCacheStatsVisible] = useState(false);
  const [drawerWidth, setDrawerWidth] = useState(width);
  const isResizingRef = useRef(false);
  
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [maxAllowed, setMaxAllowed] = useState(30);

  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  const prevMessagesLengthRef = useRef(0);

  // 拖拽调整宽度
  const handleResizeMouseDown = useCallback((e) => {
    e.preventDefault();
    isResizingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMouseMove = (moveEvent) => {
      if (!isResizingRef.current) return;
      // Drawer 从右侧弹出，宽度 = 视口宽度 - 鼠标X
      const newWidth = window.innerWidth - moveEvent.clientX;
      const clamped = Math.max(400, Math.min(newWidth, window.innerWidth * 0.9));
      setDrawerWidth(clamped);
    };

    const onMouseUp = () => {
      isResizingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, []);

  useEffect(() => {
    if (visible) {
      loadModels();
      loadConversations();
    }
  }, [visible]);

  useEffect(() => {
    if (visible && conversations.length > 0 && !conversationId) {
      const lastConversation = conversations[conversations.length - 1];
      if (lastConversation?.id) {
        switchConversation(lastConversation.id);
      }
    } else if (visible && !conversationId && conversations.length === 0 && !loadingConversations) {
      createNewConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, conversations, conversationId, loadingConversations]);

  /* eslint-disable react-hooks/exhaustive-deps */
  // 初始消息
  useEffect(() => {
    if (visible && initialMessage && messages.length === 0) {
      handleSendMessage();
    }
  }, [visible, initialMessage]);
  /* eslint-enable react-hooks/exhaustive-deps */

  // 自动滚动到底部（仅在消息数量增加时）
  useEffect(() => {
    if (messages.length > prevMessagesLengthRef.current) {
      scrollToBottom();
    }
    prevMessagesLengthRef.current = messages.length;
  }, [messages]);

const loadModels = async () => {
    try {
      const response = await chatbotAPI.getModels();
      if (response.data.models?.length > 0) {
        setModels(response.data.models);
        
        const defaultModel = response.data.models.find(model => model.default === true);
        const qwenModel = response.data.models.find(model => model.provider === 'qwen');
        setSelectedModel(defaultModel || qwenModel || response.data.models[0]);
      } else {
        message.warning('未配置可用的 AI 模型，请在环境变量中配置 API Key');
      }
    } catch (error) {
      handleApiError(error, '加载模型失败');
    }
  };

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await chatbotAPI.getConversations();
      if (response.data.success) {
        setConversations(response.data.conversations || []);
        setMaxAllowed(response.data.max_allowed || 30);
      }
    } catch (error) {
      handleApiError(error, '加载会话列表失败');
    } finally {
      setLoadingConversations(false);
    }
  };

  const createNewConversation = async () => {
    if (conversations.length >= maxAllowed) {
      message.warning(`会话数量已达上限（${maxAllowed}个），请删除部分会话后再创建`);
      return null;
    }
    try {
      const response = await chatbotAPI.createConversation({ project_id: projectContext?.id });
      if (response.data.success) {
        const newConvId = response.data.conversation_id;
        setConversationId(newConvId);
        setMessages([]);
        await loadConversations();
        return newConvId;
      } else {
        message.error(response.data.error || '创建会话失败');
        return null;
      }
    } catch (error) {
      handleApiError(error, '创建会话失败');
      return null;
    }
  };

  const switchConversation = async (convId) => {
    if (!convId || convId === conversationId) return;
    
    try {
      const response = await chatbotAPI.getConversation(convId);
      if (response.data.success) {
        const conv = response.data.conversation;
        setConversationId(convId);
        
        if (conv.messages && conv.messages.length > 0) {
          const formattedMessages = conv.messages.map((msg, index) => ({
            id: `${convId}-${index}`,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString()
          }));
          setMessages(formattedMessages);
        } else {
          setMessages([]);
        }
      }
    } catch (error) {
      handleApiError(error, '加载会话失败');
    }
  };

  const handleDeleteConversation = async (convId) => {
    try {
      const response = await chatbotAPI.deleteConversation(convId);
      if (response.data.success) {
        message.success('会话已删除');
        await loadConversations();
        
        if (convId === conversationId) {
          if (conversations.length > 1) {
            const remaining = conversations.filter(c => c.conversation_id !== convId);
            if (remaining.length > 0) {
              await switchConversation(remaining[0].conversation_id);
            } else {
              await createNewConversation();
            }
          } else {
            await createNewConversation();
          }
        }
      } else {
        message.error(response.data.error || '删除会话失败');
      }
    } catch (error) {
      handleApiError(error, '删除会话失败');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = useCallback(async () => {
    const messageText = inputText.trim();
    if (!messageText) {
      return;
    }

    if (!selectedModel) {
      message.warning('正在加载模型列表，请稍候后再发送');
      return;
    }

    let currentConversationId = conversationId;
    if (!currentConversationId) {
      currentConversationId = await createNewConversation();
      if (!currentConversationId) {
        return;
      }
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLoading(true);

    const conversationHistory = messages
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({
        role: m.role,
        content: typeof m.content === 'string' ? m.content : (m.content?.response || m.content?.message || '')
      }));

    try {
      abortControllerRef.current = new AbortController();

      const response = await chatbotAPI.sendMessage({
        message: messageText,
        conversation_id: currentConversationId,
        conversation_history: conversationHistory,
        provider: selectedModel.provider,
        model: selectedModel.name,
        system_message: systemMessage,
        temperature: 0.7,
        max_tokens: 2048,
        stream: false
      });

      if (!response.data.success) {
        message.error(response.data.error || '发送消息失败');
        setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      } else {
        const finalContent = response.data.response || response.data.message || '处理完成';
        const responseLogs = response.data.logs || [];
        
        const aiMessage = {
          id: Date.now(),
          role: 'assistant',
          content: responseLogs.length > 0 ? {
            type: 'progress',
            logs: responseLogs,
            processing: false,
            result: {
              message: finalContent,
              response: finalContent,
              tool_result: response.data.tool_result,
            }
          } : finalContent,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, aiMessage]);
        
        if (response.data.conversation_id && response.data.conversation_id !== conversationId) {
          setConversationId(response.data.conversation_id);
          loadConversations();
        }
      }
      setLoading(false);
    } catch (error) {
      handleApiError(error, '发送消息失败');
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputText, selectedModel, messages, systemMessage, conversationId]);

  const handleClear = useCallback(async () => {
    if (!conversationId) {
      setMessages([]);
      message.success('对话历史已清空');
      return;
    }
    
    try {
      const response = await chatbotAPI.clearConversation(conversationId);
      if (response.data.success) {
        setMessages([]);
        message.success('对话历史已清空');
      } else {
        message.error(response.data.error || '清空失败');
      }
    } catch (error) {
      handleApiError(error, '清空对话失败');
    }
  }, [conversationId]);

  const handleCopy = useCallback(async (text, messageId) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      message.success('已复制到剪贴板');
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (error) {
      message.error('复制失败');
    }
  }, []);


  const renderMessage = (msg) => {
    const isUser = msg.role === 'user';
    const isCopied = copiedMessageId === msg.id;
    
    const getCopyText = (content) => {
      if (typeof content === 'string') return content;
      if (content?.message) return content.message;
      if (content?.response) return content.response;
      if (content?.tool_result?.data?.result) return content.tool_result.data.result;
      return JSON.stringify(content, null, 2);
    };

    return (
      <div
        key={msg.id}
        className={`chat-message ${isUser ? 'user-message' : 'assistant-message'}`}
      >
        <div className="message-header">
          <span className="message-role">
            {isUser ? (
              <><UserOutlined /> 您</>
            ) : (
              <><RobotOutlined /> AI</>
            )}
          </span>
          <span className="message-time">
            {new Date(msg.timestamp).toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        </div>
        <div className="message-content">
          {isUser ? (
            msg.content
          ) : (
            <ChatBotMessageRenderer content={msg.content} />
          )}
        </div>
        <div className="message-actions">
          <Tooltip title="复制">
            <Button
              type="text"
              size="small"
              icon={isCopied ? <CheckOutlined /> : <CopyOutlined />}
              onClick={() => handleCopy(getCopyText(msg.content), msg.id)}
            />
          </Tooltip>
        </div>
      </div>
    );
  };

return (
    <Drawer
      title={
        <div className="chatbot-header">
          <Space>
            <ThunderboltOutlined style={{ color: '#faad14', fontSize: '20px' }} />
            <span>{title}</span>
            {selectedModel && (
              <Tag color="blue" style={{ marginLeft: 8 }}>
                {selectedModel.icon} {selectedModel.display_name}
              </Tag>
            )}
          </Space>
        </div>
      }
      placement="right"
      open={visible}
      onClose={onClose}
      width={drawerWidth + (sidebarCollapsed ? 0 : 200)}
      className="chatbot-drawer"
      headerStyle={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        padding: '16px 24px'
      }}
      bodyStyle={{ padding: 0 }}
      extra={
        <Space>
          <Tooltip title="展开会话列表">
            <Button
              type="text"
              icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              style={{ color: 'white' }}
            />
          </Tooltip>
          <Tooltip title="缓存统计">
            <Button
              type="text"
              icon={<DatabaseOutlined />}
              onClick={() => setCacheStatsVisible(!cacheStatsVisible)}
              style={{ color: cacheStatsVisible ? '#faad14' : 'white' }}
            />
          </Tooltip>
          <Tooltip title="查看执行日志">
            <Button
              type="text"
              icon={<FileTextOutlined />}
              onClick={() => {
                window.location.href = '/reports';
              }}
              style={{ color: 'white' }}
            />
          </Tooltip>
          <Tooltip title="Skill 工具">
            <Button
              type="text"
              icon={<ToolOutlined />}
              onClick={() => setSkillManagerVisible(true)}
              style={{ color: 'white' }}
            />
          </Tooltip>
          <Tooltip title="设置">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => setSettingsVisible(!settingsVisible)}
              style={{ color: 'white' }}
            />
          </Tooltip>
          <Tooltip title="清空对话">
            <Button
              type="text"
              icon={<ClearOutlined />}
              onClick={handleClear}
              style={{ color: 'white' }}
              disabled={messages.length === 0}
            />
          </Tooltip>
        </Space>
      }
    >
      <div className="chatbot-container-with-sidebar">
        {/* 左侧拖拽手柄 */}
        <div
          className="drawer-resize-handle"
          onMouseDown={handleResizeMouseDown}
        />

        {/* 左侧会话列表 */}
        <div className={`conversation-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
          <div className="sidebar-header">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={createNewConversation}
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
                    className={`conversation-item ${conv.conversation_id === conversationId ? 'active' : ''}`}
                    onClick={() => switchConversation(conv.conversation_id)}
                  >
                    <div className="conversation-title">
                      {conv.title || '新对话'}
                    </div>
                    <div className="conversation-meta">
                      <span>{conv.message_count || 0} 条消息</span>
                      <Popconfirm
                        title="确定删除此会话？"
                        onConfirm={(e) => {
                          e.stopPropagation();
                          handleDeleteConversation(conv.conversation_id);
                        }}
                        onCancel={(e) => e.stopPropagation()}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Button
                          type="text"
                          size="small"
                          icon={<DeleteOutlined />}
                          className="delete-btn"
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

        {/* 右侧主内容区 */}
        <div className="chatbot-main">
          {/* 设置面板 */}
          {settingsVisible && (
            <div className="settings-panel">
              <Divider style={{ margin: '12px 0' }}>设置</Divider>
              <div className="setting-item">
                <label>AI 模型</label>
                <Select
                  value={selectedModel?.name || undefined}
                  onChange={(value) => {
                    const model = models.find(m => m.name === value);
                    setSelectedModel(model);
                  }}
                  style={{ width: '100%' }}
                  placeholder="选择模型"
                  loading={models.length === 0}
                >
                  {models.map(model => (
                    <Option key={model.id || model.name} value={model.name}>
                      {model.name} - {model.display_name || model.id}
                    </Option>
                  ))}
                </Select>
              </div>
              <div className="setting-item">
                <label>系统提示词</label>
                <TextArea
                  value={systemMessage}
                  onChange={(e) => setSystemMessage(e.target.value)}
                  rows={3}
                  placeholder="设置 AI 的角色和行为"
                />
              </div>
            </div>
          )}

          {/* 缓存统计面板 */}
          <CacheStatsPanel visible={cacheStatsVisible} />

          {/* 消息列表 */}
          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="empty-state">
                <RobotOutlined style={{ fontSize: '64px', color: '#d9d9d9' }} />
                <p className="empty-text">开始与 AI 对话吧</p>
                <p className="empty-hint">可以询问测试相关问题、代码审查、最佳实践等</p>
              </div>
            ) : (
              <>
                {messages.map(renderMessage)}
                {loading && (
                  <div className="message assistant-message loading-message">
                    <Avatar icon={<RobotOutlined />} className="message-avatar" />
                    <div className="message-content">
                      <Spin />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* 输入区域 */}
          <div className="input-container">
            <TextArea
              value={inputTextDeferred}
              onChange={(e) => setInputText(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="输入您的问题... (Shift+Enter 换行)"
              autoSize={{ minRows: 1, maxRows: 6 }}
              disabled={loading}
              className="message-input"
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              loading={loading}
              disabled={!inputText.trim()}
              className="send-button"
            >
              发送
            </Button>
          </div>
        </div>
      </div>

      {/* Skill 执行管理器 */}
      <SkillExecutionManager
        visible={skillManagerVisible}
        onCancel={() => setSkillManagerVisible(false)}
        onSuccess={(result) => {
          const resultMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Skill 执行成功！\n\n**执行结果：**\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``,
            timestamp: new Date().toISOString()
          };
          setMessages(prev => [...prev, resultMessage]);
          setSkillManagerVisible(false);
          message.success('Skill 执行完成');
        }}
      />
    </Drawer>
  );
};

export default ChatBotDrawer;
