/**
 * ChatBotDrawer 主组件 - 重构版
 * 精简代码，使用子组件和 hooks
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Drawer, Button, Space, Tag, Tooltip, message } from 'antd';
import {
  ThunderboltOutlined,
  ClearOutlined,
  SettingOutlined,
  ToolOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DatabaseOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { chatbotAPI } from '../../api';
import { handleApiError } from '../../utils/errorHandler';
import './ChatBot.css';

import { useChatResize } from './hooks/useChatResize';
import { useConversations } from './hooks/useConversations';
import ChatBotInput from './ChatBotInput';
import ChatBotSidebar from './ChatBotSidebar';
import ChatBotMessages from './ChatBotMessages';
import ChatBotSettings from './ChatBotSettings';
import SkillExecutionManager from '../SkillExecutionManager';
import CacheStatsPanel from '../CacheStatsPanel';

const ChatBotDrawer = ({
  visible = false,
  onClose,
  width = 500,
  title = 'AI 智能助手',
  defaultSystemMessage = '你是一个智能助手，请用清晰、专业的语言回答问题。',
  initialMessage = '',
  projectContext = null,
}) => {
  // 状态管理
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [systemMessage, setSystemMessage] = useState(defaultSystemMessage);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState(null);
  const [skillManagerVisible, setSkillManagerVisible] = useState(false);
  const [cacheStatsVisible, setCacheStatsVisible] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  // Hooks
  const { drawerWidth, handleResizeMouseDown } = useChatResize(width);
  const {
    conversationId,
    setConversationId,
    conversations,
    loadingConversations,
    maxAllowed,
    loadConversations,
    createNewConversation,
    switchConversation,
    deleteConversation,
    clearConversation,
  } = useConversations(projectContext);

  // 加载模型
  const loadModels = useCallback(async () => {
    try {
      const response = await chatbotAPI.getModels();
      if (response.data.models?.length > 0) {
        setModels(response.data.models);
        const defaultModel = response.data.models.find(m => m.default === true);
        const qwenModel = response.data.models.find(m => m.provider === 'qwen');
        setSelectedModel(defaultModel || qwenModel || response.data.models[0]);
      } else {
        message.warning('未配置可用的 AI 模型');
      }
    } catch (error) {
      handleApiError(error, '加载模型失败');
    }
  }, []);

  // 初始化
  useEffect(() => {
    if (visible) {
      loadModels();
      loadConversations();
    }
  }, [visible, loadModels, loadConversations]);

  // 自动选择/创建会话
  useEffect(() => {
    if (visible && conversations.length > 0 && !conversationId) {
      const lastConversation = conversations[conversations.length - 1];
      if (lastConversation?.id) {
        switchConversation(lastConversation.id, setMessages);
      }
    } else if (visible && !conversationId && conversations.length === 0 && !loadingConversations) {
      createNewConversation();
    }
  }, [visible, conversations, conversationId, loadingConversations, switchConversation, createNewConversation]);

  // 发送消息
  const handleSendMessage = useCallback(async (text) => {
    if (!selectedModel) {
      message.warning('正在加载模型，请稍候');
      return;
    }

    let currentConvId = conversationId;
    if (!currentConvId) {
      currentConvId = await createNewConversation();
      if (!currentConvId) return;
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatbotAPI.sendMessage({
        message: text,
        conversation_id: currentConvId,
        provider: selectedModel.provider,
        model: selectedModel.name,
        system_message: systemMessage,
        temperature: 0.7,
        max_tokens: 2048,
        stream: false,
      });

      if (!response.data.success) {
        message.error(response.data.error || '发送失败');
        setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      } else {
        const finalContent = response.data.response || response.data.message || '处理完成';
        const responseLogs = response.data.logs || [];

        const hasOptions = response.data.options && response.data.options.length > 0;
        const aiMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: (responseLogs.length > 0 || hasOptions) ? {
            type: 'progress',
            logs: responseLogs,
            processing: false,
            result: {
              message: finalContent,
              response: finalContent,
              tool_result: response.data.tool_result,
              options: response.data.options,
            },
          } : finalContent,
          timestamp: new Date().toISOString(),
        };

        setMessages(prev => [...prev, aiMessage]);

        if (response.data.conversation_id && response.data.conversation_id !== conversationId) {
          setConversationId(response.data.conversation_id);
          loadConversations();
        }
      }
    } catch (error) {
      handleApiError(error, '发送消息失败');
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  }, [selectedModel, conversationId, messages, systemMessage, createNewConversation, loadConversations, setConversationId]);

  // 清空对话
  const handleClear = useCallback(async () => {
    const result = await clearConversation(conversationId);
    if (result.success) {
      setMessages([]);
      if (!result.clearedByLocal) {
        message.success('对话已清空');
      }
    }
  }, [conversationId, clearConversation]);

  // 复制消息
  const handleCopy = useCallback(async (text, messageId) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      message.success('已复制');
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch {
      message.error('复制失败');
    }
  }, []);

  // 删除会话后的处理
  const handleAfterDelete = useCallback(async () => {
    const remaining = conversations.filter(c => c.conversation_id !== conversationId);
    if (remaining.length > 0) {
      await switchConversation(remaining[0].conversation_id, setMessages);
    } else {
      await createNewConversation();
      setMessages([]);
    }
  }, [conversations, conversationId, switchConversation, createNewConversation]);

  // Skill 执行成功
  const handleSkillSuccess = useCallback((result) => {
    const resultMessage = {
      id: Date.now(),
      role: 'assistant',
      content: `Skill 执行成功！\n\n**执行结果：**\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, resultMessage]);
    setSkillManagerVisible(false);
    message.success('Skill 执行完成');
  }, []);

  return (
    <Drawer
      title={
        <div className="chatbot-header">
          <Space>
            <ThunderboltOutlined style={{ color: '#faad14', fontSize: 20 }} />
            <span>{title}</span>
            {selectedModel && (
              <Tag color="blue">{selectedModel.icon} {selectedModel.display_name}</Tag>
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
        padding: '16px 24px',
      }}
      bodyStyle={{ padding: 0 }}
      extra={
        <Space>
          <Tooltip title={sidebarCollapsed ? '展开会话列表' : '收起会话列表'}>
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
              onClick={() => window.location.href = '/reports'}
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
      <div className="chatbot-container">
        <div className="drawer-resize-handle" onMouseDown={handleResizeMouseDown} />

        <ChatBotSidebar
          collapsed={sidebarCollapsed}
          conversations={conversations}
          conversationId={conversationId}
          loadingConversations={loadingConversations}
          maxAllowed={maxAllowed}
          onCreateNew={createNewConversation}
          onSwitch={(id) => switchConversation(id, setMessages)}
          onDelete={(id) => deleteConversation(id, handleAfterDelete)}
        />

        <div className="chatbot-main">
          <ChatBotSettings
            visible={settingsVisible}
            models={models}
            selectedModel={selectedModel}
            systemMessage={systemMessage}
            onModelChange={setSelectedModel}
            onSystemMessageChange={setSystemMessage}
          />

          <CacheStatsPanel visible={cacheStatsVisible} />

          <ChatBotMessages
            messages={messages}
            loading={loading}
            onCopy={handleCopy}
            copiedMessageId={copiedMessageId}
            onSendMessage={handleSendMessage}
          />

          <ChatBotInput
            onSend={handleSendMessage}
            disabled={!selectedModel}
            loading={loading}
          />
        </div>
      </div>

      <SkillExecutionManager
        visible={skillManagerVisible}
        onCancel={() => setSkillManagerVisible(false)}
        onSuccess={handleSkillSuccess}
      />
    </Drawer>
  );
};

export default ChatBotDrawer;