import { useState, useEffect, useRef, useCallback } from 'react';
import logger from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * WebSocket录制Hook
 * 
 * @param {string} sessionId - 会话ID
 * @param {boolean} autoConnect - 是否自动连接
 * @returns {object} WebSocket状态和控制方法
 */
export const useRecordingWebSocket = (sessionId, autoConnect = false) => {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [screenshots, setScreenshots] = useState([]);
  const [recordedSteps, setRecordedSteps] = useState([]);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const heartbeatIntervalRef = useRef(null);
  const connectRef = useRef(null);
  const disconnectRef = useRef(null);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  // 停止心跳
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // 启动心跳
  const startHeartbeat = useCallback(() => {
    stopHeartbeat();
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 每30秒发送一次心跳
  }, [stopHeartbeat]);

  // 获取WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiBase = API_BASE_URL.replace(/^https?:\/\//, '');
    const wsPath = apiBase.includes('/api') 
      ? `${apiBase}/ws/recording/${sessionId}/`
      : `${apiBase}/api/ws/recording/${sessionId}/`;
    
    // 从localStorage获取token
    const token = localStorage.getItem('authToken');
    const url = `${protocol}//${wsPath}`;

    let finalUrl = url;
    if (token) {
      const separator = url.includes('?') ? '&' : '?';
      finalUrl = `${url}${separator}token=${encodeURIComponent(token)}`;
    }

    return finalUrl;
  }, [sessionId]);

  // 连接WebSocket
  const connect = useCallback(() => {
    if (!sessionId) {
      logger.error('[useRecordingWebSocket] 会话ID为空');
      setError('会话ID不能为空');
      return;
    }

    // 如果已有连接，先关闭
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        logger.warn('[useRecordingWebSocket] 关闭旧连接失败:', e);
      }
      wsRef.current = null;
    }

    try {
      const wsUrl = getWebSocketUrl();

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;

        // 启动心跳
        startHeartbeat();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // 处理不同类型的消息
          if (data.type === 'screenshot') {
            setScreenshots(prev => {
              // 只保留最近10张截图，避免内存占用过大
              const newScreenshots = [...prev, data.data];
              return newScreenshots.slice(-10);
            });
          } else if (data.type === 'step_recorded') {
            setRecordedSteps(prev => [...prev, data.step]);
          } else if (data.type === 'recording_stopped') {
            if (data.steps) {
              setRecordedSteps(data.steps);
            }
          } else if (data.type === 'recording_started') {
            if (data.status === 'success') {
              setError(null);
            } else if (data.status === 'error') {
              setError(data.error || '启动录制失败');
            }
          } else if (data.type === 'error') {
            setError(data.message || '发生错误');
          }

          setLastMessage(data);
        } catch (e) {
          logger.error('[useRecordingWebSocket] 解析消息失败:', e);
        }
      };

      ws.onerror = (error) => {
        logger.error('[useRecordingWebSocket] WebSocket错误:', error);
        setError('WebSocket连接错误');
      };

      ws.onclose = (event) => {
        setConnected(false);
        
        // 停止心跳
        stopHeartbeat();
        
        wsRef.current = null;

        // 自动重连
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        } else {
          setError('连接失败，已达最大重试次数');
        }
      };
    } catch (error) {
      logger.error('[useRecordingWebSocket] 创建WebSocket连接失败:', error);
      setError(error.message);
    }
  }, [sessionId, getWebSocketUrl, startHeartbeat, stopHeartbeat]);

  // 断开连接
  const disconnect = useCallback(() => {
    stopHeartbeat();
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnected(false);
    reconnectAttemptsRef.current = maxReconnectAttempts; // 阻止自动重连
  }, []);

  // 发送消息
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const messageStr = JSON.stringify(message);
      wsRef.current.send(messageStr);
      return true;
    } else {
      logger.warn('[useRecordingWebSocket] WebSocket未连接，无法发送消息');
      return false;
    }
  }, []);

  // 更新函数引用到ref（避免useEffect依赖问题）
  useEffect(() => {
    connectRef.current = connect;
    disconnectRef.current = disconnect;
  }, [connect, disconnect]);

  // 自动连接
  useEffect(() => {
    if (autoConnect && sessionId) {
      connectRef.current();
    }

    return () => {
      disconnectRef.current();
    };
  }, [autoConnect, sessionId]); // 只依赖 autoConnect 和 sessionId

  return {
    connected,
    error,
    lastMessage,
    screenshots,
    recordedSteps,
    connect,
    disconnect,
    sendMessage,
    readyState: wsRef.current ? wsRef.current.readyState : WebSocket.CLOSED,
  };
};
