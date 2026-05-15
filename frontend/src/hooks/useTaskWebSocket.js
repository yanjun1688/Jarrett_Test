/**
 * Celery 任务状态 WebSocket Hook
 *
 * 连接 ws://host/ws/celery/tasks/
 * 通过 TokenAuthMiddleware 自动认证（URL ?token=xxx）
 * 接收 task.status 事件，按 task_name 回调
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_PATH = '/ws/celery/tasks/';

/**
 * @param {Function} getToken - 获取认证 token 的函数
 * @param {Object} [options]
 * @param {Record<string, Function>} [options.onTaskStatus] - 按 task_name 注册回调
 * @param {Function} [options.onAnyTaskStatus] - 所有任务的统一回调
 */
export const useTaskWebSocket = (getToken, options = {}) => {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnectRef = useRef(false);
  const optionsRef = useRef(options);
  const maxReconnectAttempts = 3;
  const reconnectDelay = 3000;

  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    isManualDisconnectRef.current = false;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const token = typeof getToken === 'function' ? getToken() : null;
      const tokenParam = token ? `?token=${token}` : '';
      const ws = new WebSocket(`${protocol}//${window.location.host}${WS_PATH}${tokenParam}`);

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'task.status') {
            const { onTaskStatus, onAnyTaskStatus } = optionsRef.current;

            if (onTaskStatus && onTaskStatus[data.task_name]) {
              onTaskStatus[data.task_name](data);
            }

            if (onAnyTaskStatus) {
              onAnyTaskStatus(data);
            }
          }
        } catch (e) {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        setError('WebSocket 连接错误');
      };

      ws.onclose = (event) => {
        setConnected(false);
        wsRef.current = null;

        if (event.code === 4001) {
          return;
        }

        if (!isManualDisconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      setError(err.message);
    }
  }, [getToken]);

  const disconnect = useCallback(() => {
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

  return { connected, error, connect, disconnect };
};

export default useTaskWebSocket;
