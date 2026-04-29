/**
 * 会话管理 Hook
 */
import { useState, useCallback } from 'react';
import { message } from 'antd';
import { chatbotAPI } from '../../../api';
import { handleApiError } from '../../../utils/errorHandler';

export const useConversations = (projectContext) => {
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [maxAllowed, setMaxAllowed] = useState(30);

  const loadConversations = useCallback(async () => {
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
  }, []);

  const createNewConversation = useCallback(async () => {
    if (conversations.length >= maxAllowed) {
      message.warning(`会话数量已达上限（${maxAllowed}个），请删除部分会话后再创建`);
      return null;
    }
    try {
      const response = await chatbotAPI.createConversation({ project_id: projectContext?.id });
      if (response.data.success) {
        const newConvId = response.data.conversation_id;
        setConversationId(newConvId);
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
  }, [conversations.length, maxAllowed, projectContext?.id, loadConversations]);

  const switchConversation = useCallback(async (convId, onLoadMessages) => {
    if (!convId || convId === conversationId) return;
    
    try {
      const response = await chatbotAPI.getConversation(convId);
      if (response.data.success) {
        const conv = response.data.conversation;
        setConversationId(convId);
        
        if (onLoadMessages && conv.messages && conv.messages.length > 0) {
          const formattedMessages = conv.messages.map((msg, index) => ({
            id: `${convId}-${index}`,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString()
          }));
          onLoadMessages(formattedMessages);
        } else if (onLoadMessages) {
          onLoadMessages([]);
        }
      }
    } catch (error) {
      handleApiError(error, '加载会话失败');
    }
  }, [conversationId]);

  const deleteConversation = useCallback(async (convId, onSwitchAfterDelete) => {
    try {
      const response = await chatbotAPI.deleteConversation(convId);
      if (response.data.success) {
        message.success('会话已删除');
        await loadConversations();
        
        if (convId === conversationId && onSwitchAfterDelete) {
          onSwitchAfterDelete();
        }
      } else {
        message.error(response.data.error || '删除会话失败');
      }
    } catch (error) {
      handleApiError(error, '删除会话失败');
    }
  }, [conversationId, loadConversations]);

  const clearConversation = useCallback(async (convId) => {
    if (!convId) {
      return { success: true, clearedByLocal: true };
    }
    
    try {
      const response = await chatbotAPI.clearConversation(convId);
      if (response.data.success) {
        return { success: true };
      } else {
        message.error(response.data.error || '清空失败');
        return { success: false };
      }
    } catch (error) {
      handleApiError(error, '清空对话失败');
      return { success: false };
    }
  }, []);

  return {
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
  };
};

export default useConversations;