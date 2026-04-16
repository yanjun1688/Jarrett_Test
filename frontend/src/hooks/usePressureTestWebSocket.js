/**
 * 压测 WebSocket Hook
 * 用于实时接收压测进度和性能指标
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import logger from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * 压测 WebSocket Hook
 * @param {Function} getToken - 获取认证token的函数
 * @returns {Object} WebSocket状态和控制方法
 */
export const usePressureTestWebSocket = (getToken) => {
  const [connected, setConnected] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState(null);
  const [executionId, setExecutionId] = useState(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(null);
  const [stats, setStats] = useState(null);
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnectRef = useRef(false);
  const authenticatedRef = useRef(false);
  const executionIdRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const maxReconnectAttempts = 3;
  const reconnectDelay = 3000;
  const CONNECTION_IDLE_TIMEOUT = 60000; // 60秒无活动自动断开

  /**
   * 构建 WebSocket URL
   * @param {number} execId - 执行记录ID
   */
  const getWebSocketUrl = useCallback((execId) => {
    const isHttps = API_BASE_URL.startsWith('https://') || window.location.protocol === 'https:';
    const protocol = isHttps ? 'wss:' : 'ws:';
    let apiBase = API_BASE_URL.replace(/^https?:\/\//, '');
    apiBase = apiBase.replace(/\/api\/v1\/?$/, '').replace(/\/api\/?$/, '');
    return `${protocol}//${apiBase}/ws/pressure-test/${execId}/`;
  }, []);

  useEffect(() => {
    authenticatedRef.current = authenticated;
    executionIdRef.current = executionId;
  }, [authenticated, executionId]);

  /**
   * 连接 WebSocket
   * @param {number} execId - 执行记录ID
   */
  const connect = useCallback((execId) => {
    // 先断开旧连接（如果存在）
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }

    logger.info('[usePressureTestWS] Connecting to execution:', execId);
    isManualDisconnectRef.current = false;
    setExecutionId(execId);

    try {
      const wsUrl = getWebSocketUrl(execId);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        logger.info('[usePressureTestWS] WebSocket connected');

        // 重置空闲超时
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
        }
        connectionTimeoutRef.current = setTimeout(() => {
          logger.warn('[usePressureTestWS] Connection idle timeout, disconnecting');
          disconnect();
        }, CONNECTION_IDLE_TIMEOUT);

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
          // 重置空闲超时
          if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
          }
          connectionTimeoutRef.current = setTimeout(() => {
            logger.warn('[usePressureTestWS] Connection idle timeout, disconnecting');
            disconnect();
          }, CONNECTION_IDLE_TIMEOUT);

          const data = JSON.parse(event.data);
          logger.info('[usePressureTestWS] Received:', data.type);

          switch (data.type) {
            case 'auth_success':
              setAuthenticated(true);
              setError(null);
              break;

            case 'auth_error':
              setError(data.message || '认证失败');
              setAuthenticated(false);
              break;

            case 'started':
              setRunning(true);
              setProgress({
                executionId: data.execution_id,
                config: data.config,
                message: data.message
              });
              setResults([]);
              setSummary(null);
              break;

            case 'result':
              setResults(prev => [...prev, {
                index: data.index,
                statusCode: data.status_code,
                responseTime: data.response_time,
                success: data.success,
                timestamp: data.timestamp
              }]);
              break;

            case 'stats':
              setStats({
                completed: data.completed,
                total: data.total,
                successRate: data.success_rate,
                avgResponseTime: data.avg_response_time,
                rps: data.rps
              });
              break;

            case 'complete':
              setRunning(false);
              setSummary({
                status: data.summary?.status,
                totalRequests: data.summary?.total_requests,
                successCount: data.summary?.success_count,
                failedCount: data.summary?.failed_count,
                errorRate: data.summary?.error_rate,
                avgResponseTime: data.summary?.avg_response_time,
                minResponseTime: data.summary?.min_response_time,
                maxResponseTime: data.summary?.max_response_time,
                p50ResponseTime: data.summary?.p50_response_time,
                p90ResponseTime: data.summary?.p90_response_time,
                p95ResponseTime: data.summary?.p95_response_time,
                p99ResponseTime: data.summary?.p99_response_time,
                throughput: data.summary?.throughput,
                peakConcurrent: data.summary?.peak_concurrent,
                durationSeconds: data.summary?.duration_seconds
              });
              logger.info('[usePressureTestWS] Pressure test completed');
              // 清理空闲超时，设置自动断开超时
              if (connectionTimeoutRef.current) {
                clearTimeout(connectionTimeoutRef.current);
              }
              connectionTimeoutRef.current = setTimeout(() => {
                logger.info('[usePressureTestWS] Auto disconnecting after test completed');
                disconnect();
              }, 3000);
              break;

            case 'stopped':
              setRunning(false);
              logger.info('[usePressureTestWS] Pressure test stopped');
              // 清理空闲超时，设置自动断开超时
              if (connectionTimeoutRef.current) {
                clearTimeout(connectionTimeoutRef.current);
              }
              connectionTimeoutRef.current = setTimeout(() => {
                logger.info('[usePressureTestWS] Auto disconnecting after stopped');
                disconnect();
              }, 1000);
              break;

            case 'error':
              setError(data.message || '发生错误');
              setRunning(false);
              logger.error('[usePressureTestWS] Error:', data.message);
              break;

            default:
              logger.warn('[usePressureTestWS] Unknown message type:', data.type);
          }
        } catch (e) {
          logger.error('[usePressureTestWS] Parse error:', e);
        }
      };

      ws.onerror = (err) => {
        logger.error('[usePressureTestWS] WebSocket error:', err);
        setError('WebSocket连接错误');
      };

      ws.onclose = (event) => {
        logger.info('[usePressureTestWS] WebSocket closed:', event.code);
        setConnected(false);
        setAuthenticated(false);
        wsRef.current = null;

        // 清理空闲超时
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
          connectionTimeoutRef.current = null;
        }

        const currentToken = typeof getToken === 'function' ? getToken() : null;
        // 使用 executionIdRef 替代闭包中的 executionId，避免闭包问题
        if (!isManualDisconnectRef.current && 
            reconnectAttemptsRef.current < maxReconnectAttempts && 
            currentToken && 
            executionIdRef.current) {
          logger.info('[usePressureTestWS] Scheduling reconnect');
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect(executionIdRef.current);  // 使用最新的 executionId
          }, reconnectDelay);
        }
      };
    } catch (err) {
      logger.error('[usePressureTestWS] Connect error:', err);
      setError(err.message);
    }
  }, [getToken, getWebSocketUrl, executionId]);

  /**
   * 断开 WebSocket
   */
  const disconnect = useCallback(() => {
    logger.info('[usePressureTestWS] Disconnecting...');
    isManualDisconnectRef.current = true;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnected(false);
    setAuthenticated(false);
    setExecutionId(null);
  }, []);

  /**
   * 开始压测
   */
  const startTest = useCallback(() => {
    if (running) {
      logger.warn('[usePressureTestWS] Pressure test already running');
      return false;
    }
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      logger.warn('[usePressureTestWS] WebSocket not connected');
      return false;
    }

    if (!authenticatedRef.current) {
      logger.warn('[usePressureTestWS] Not authenticated');
      return false;
    }

    wsRef.current.send(JSON.stringify({
      type: 'start'
    }));

    setRunning(true);
    setResults([]);
    setStats(null);
    setSummary(null);
    return true;
  }, [running]);

  /**
   * 停止压测
   */
  const stopTest = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      logger.warn('[usePressureTestWS] WebSocket not connected');
      return false;
    }

    wsRef.current.send(JSON.stringify({
      type: 'stop'
    }));

    return true;
  }, []);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setRunning(false);
    setProgress(null);
    setStats(null);
    setResults([]);
    setSummary(null);
    setError(null);

    // 断开 WebSocket 连接
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }
  }, []);

  const disconnectRef = useRef(disconnect);
  useEffect(() => {
    disconnectRef.current = disconnect;
  }, [disconnect]);

  useEffect(() => {
    return () => {
      disconnectRef.current();
    };
  }, []);

  return {
    connected,
    authenticated,
    error,
    executionId,
    running,
    progress,
    stats,
    results,
    summary,
    connect,
    disconnect,
    startTest,
    stopTest,
    reset
  };
};

export default usePressureTestWebSocket;