/**
 * WebSocket Hook for ChatBot - DISABLED
 * 
 * 此文件已被 SSE 替代，保留用于将来可能的双向通信场景。
 * 新代码请使用 useChatBotSSE.js
 * 
 * @deprecated Use useChatBotSSE instead
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import logger from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const useChatBotWebSocket = (getToken) => {
  const [connected, setConnected] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [processing, setProcessing] = useState(false);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const messageQueueRef = useRef([]);
  const isManualDisconnectRef = useRef(false);
  const authenticatedRef = useRef(false);
  const maxReconnectAttempts = 3;
  const reconnectDelay = 3000;

  const getWebSocketUrl = useCallback(() => {
    const isHttps = API_BASE_URL.startsWith('https://') || window.location.protocol === 'https:';
    const protocol = isHttps ? 'wss:' : 'ws:';
    let apiBase = API_BASE_URL.replace(/^https?:\/\//, '');
    apiBase = apiBase.replace(/^api\/?/, '').replace(/\/api\/?$/, '');
    return `${protocol}//${apiBase}/ws/chatbot/`;
  }, []);

  const processMessageQueue = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !authenticatedRef.current) {
      return;
    }
    
    while (messageQueueRef.current.length > 0) {
      const msg = messageQueueRef.current.shift();
      wsRef.current.send(JSON.stringify({
        type: 'chat',
        message: msg
      }));
      setLogs(prev => [...prev, { type: 'user', message: msg }]);
    }
  }, []);

  useEffect(() => {
    authenticatedRef.current = authenticated;
  }, [authenticated]);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      logger.info('[useChatBotWebSocket] Already connected, skipping');
      return;
    }

    logger.info('[useChatBotWebSocket] Connecting...');
    isManualDisconnectRef.current = false;

    try {
      const wsUrl = getWebSocketUrl();
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        logger.info('[useChatBotWebSocket] WebSocket connected');
        
        const currentToken = typeof getToken === 'function' ? getToken() : null;
        if (currentToken) {
          ws.send(JSON.stringify({
            type: 'auth',
            token: currentToken
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          logger.info('[useChatBotWebSocket] Received:', data.type);

          switch (data.type) {
            case 'auth_success':
              setAuthenticated(true);
              setError(null);
              processMessageQueue();
              break;
            case 'auth_error':
              setError(data.message || 'Authentication failed');
              setAuthenticated(false);
              break;
            case 'processing':
              setProcessing(true);
              setLogs(prev => [...prev, { type: 'info', message: data.message }]);
              break;
            case 'intent_classification_start':
              setLogs(prev => [...prev, { type: 'info', message: data.message }]);
              break;
            case 'intent_classified':
              setLogs(prev => [...prev, { 
                type: 'intent', 
                intent: data.intent, 
                confidence: data.confidence,
                message: `意图识别: ${data.intent} (置信度: ${(data.confidence * 100).toFixed(0)}%)`
              }]);
              break;
            case 'knowledge_retrieval_start':
              setLogs(prev => [...prev, { type: 'info', message: data.message }]);
              break;
            case 'knowledge_retrieved':
              setLogs(prev => [...prev, { 
                type: 'knowledge', 
                count: data.count,
                message: `检索到 ${data.count} 条相关知识`
              }]);
              break;
            case 'tool_call_start':
              setLogs(prev => [...prev, { 
                type: 'tool', 
                tool: data.tool,
                message: `准备执行工具: ${data.tool}`
              }]);
              break;
            case 'tool_executing':
              setLogs(prev => [...prev, { 
                type: 'tool', 
                tool: data.tool,
                step: data.step,
                message: data.message
              }]);
              break;
            case 'tool_executed':
              setLogs(prev => [...prev, { 
                type: 'tool', 
                tool: data.tool,
                status: 'completed',
                message: `工具 ${data.tool} 执行完成`
              }]);
              break;
            case 'complete':
              setProcessing(false);
              setResult(data.result);
              setLogs(prev => [...prev, { 
                type: 'success', 
                message: data.message || '处理完成'
              }]);
              break;
            case 'error':
              logger.error('[useChatBotWebSocket] Error received:', JSON.stringify(data));
              setProcessing(false);
              setError(data.message || '发生错误');
              setLogs(prev => [...prev, { 
                type: 'error', 
                message: data.message 
              }]);
              break;
            default:
              logger.warn('[useChatBotWebSocket] Unknown message type:', data.type);
          }
        } catch (e) {
          logger.error('[useChatBotWebSocket] Parse error:', e);
        }
      };

      ws.onerror = (error) => {
        logger.error('[useChatBotWebSocket] WebSocket error:', error);
        setError('WebSocket连接错误');
      };

      ws.onclose = (event) => {
        logger.info('[useChatBotWebSocket] WebSocket closed:', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          isManual: isManualDisconnectRef.current
        });
        setConnected(false);
        setAuthenticated(false);
        wsRef.current = null;

        const currentToken = typeof getToken === 'function' ? getToken() : null;
        if (!isManualDisconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts && currentToken) {
          logger.info('[useChatBotWebSocket] Scheduling reconnect, attempt:', reconnectAttemptsRef.current + 1);
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
    } catch (error) {
      logger.error('[useChatBotWebSocket] Connect error:', error);
      setError(error.message);
    }
  }, [getToken, getWebSocketUrl, processMessageQueue]);

  const disconnect = useCallback(() => {
    logger.info('[useChatBotWebSocket] Disconnecting... isManual:', isManualDisconnectRef.current);
    isManualDisconnectRef.current = true;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnected(false);
    setAuthenticated(false);
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    isManualDisconnectRef.current = false;
    connect();
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (!message || !message.trim()) {
      return false;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && authenticated) {
      wsRef.current.send(JSON.stringify({
        type: 'chat',
        message: message
      }));
      setLogs(prev => [...prev, { 
        type: 'user', 
        message: message 
      }]);
      return true;
    } else if (connected) {
      messageQueueRef.current.push(message);
      logger.info('[useChatBotWebSocket] Message queued, waiting for authentication');
      return true;
    } else {
      logger.warn('[useChatBotWebSocket] WebSocket not connected');
      return false;
    }
  }, [authenticated, connected]);

  const clearLogs = useCallback(() => {
    setLogs([]);
    setResult(null);
    setError(null);
    setProcessing(false);
    messageQueueRef.current = [];
}, []);

  const disconnectRef = useRef(disconnect);
  useEffect(() => {
    disconnectRef.current = disconnect;
  }, [disconnect]);

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    return () => {
      disconnectRef.current();
    };
  }, []);

  return {
    connected,
    authenticated,
    error,
    logs,
    result,
    processing,
    connect,
    disconnect,
    reconnect,
    sendMessage,
    clearLogs
  };
};
