import { useState, useEffect, useCallback, useRef } from 'react';

const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000';

export const useAdvancedPressureTestWebSocket = (token) => {
  const [connected, setConnected] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState(null);
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const executionIdRef = useRef(null);

  const connect = useCallback((executionId) => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    executionIdRef.current = executionId;
    const wsUrl = `${WS_BASE_URL}/ws/advanced-pressure-test/${executionId}/?token=${token}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'connected':
            setAuthenticated(true);
            break;
            
          case 'started':
            setRunning(true);
            setResults([]);
            setSummary(null);
            break;
            
          case 'result':
            setResults(prev => [...prev, data]);
            break;
            
          case 'stats':
            setStats(data);
            break;
          
          case 'stats_summary':
            // CSV方案的统计汇总消息
            setStats(data);
            setSummary(data);
            break;
            
          case 'complete':
            setRunning(false);
            setSummary(data.summary);
            break;
            
          case 'stopped':
            setRunning(false);
            break;
            
          case 'error':
            setError(data.message);
            setRunning(false);
            break;
            
          default:
            break;
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };
    
    ws.onclose = () => {
      setConnected(false);
      setAuthenticated(false);
    };
    
    ws.onerror = (e) => {
      setError('WebSocket error');
      setConnected(false);
    };
  }, [token]);

  const startTest = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'start' }));
    }
  }, []);

  const stopTest = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop' }));
    }
  }, []);

  const reset = useCallback(() => {
    setConnected(false);
    setAuthenticated(false);
    setRunning(false);
    setStats(null);
    setResults([]);
    setSummary(null);
    setError(null);
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    connected,
    authenticated,
    running,
    stats,
    results,
    summary,
    error,
    connect,
    startTest,
    stopTest,
    reset
  };
};

export default useAdvancedPressureTestWebSocket;