import React from 'react';
import { Tag, Spin } from 'antd';
import {
  BulbOutlined,
  BookOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import './ChatBotProgressRenderer.css';

const logTypeConfig = {
  info: { icon: null, color: 'blue', text: '信息' },
  intent: { icon: <BulbOutlined />, color: 'purple', text: '意图' },
  knowledge: { icon: <BookOutlined />, color: 'cyan', text: '知识' },
  tool: { icon: <ToolOutlined />, color: 'orange', text: '工具' },
  user: { icon: null, color: 'default', text: '用户' },
  success: { icon: <CheckCircleOutlined />, color: 'green', text: '完成' },
  error: { icon: <CloseCircleOutlined />, color: 'red', text: '错误' }
};

const ProgressStep = ({ log, isLast, isActive }) => {
  const config = logTypeConfig[log.type] || logTypeConfig.info;
  
  return (
    <div className={`progress-step ${isLast && isActive ? 'active' : ''} ${log.type}`}>
      <div className="step-indicator">
        {isLast && isActive ? (
          <LoadingOutlined className="loading-icon" />
        ) : log.type === 'success' ? (
          <CheckCircleOutlined className="success-icon" />
        ) : log.type === 'error' ? (
          <CloseCircleOutlined className="error-icon" />
        ) : (
          <div className="step-dot" />
        )}
      </div>
      <div className="step-content">
        <div className="step-header">
          <Tag color={config.color} className="step-tag">
            {config.icon} {config.text}
          </Tag>
          <span className="step-message">{log.message}</span>
        </div>
        {log.intent && (
          <div className="step-detail">
            <span className="detail-label">意图:</span>
            <Tag color="purple">{log.intent}</Tag>
            {log.confidence && (
              <span className="confidence">
                {(log.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        )}
        {log.tool && (
          <div className="step-detail">
            <span className="detail-label">工具:</span>
            <Tag color="orange">{log.tool}</Tag>
            {log.step && <span className="step-name">{log.step}</span>}
          </div>
        )}
        {log.count !== undefined && (
          <div className="step-detail">
            <span className="detail-label">数量:</span>
            <span className="count-value">{log.count} 条</span>
          </div>
        )}
        {log.knowledge_summary && log.knowledge_summary.length > 0 && (
          <div className="knowledge-summary">
            {log.knowledge_summary.map((s, i) => (
              <span key={i} className="summary-item">• {s}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ChatBotProgressRenderer = ({ logs, processing = true, result = null }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="progress-container empty">
        <Spin indicator={<LoadingOutlined spin />} />
        <span className="empty-text">准备中...</span>
      </div>
    );
  }

  const nonUserLogs = logs.filter(l => l.type !== 'user');
  const isComplete = !processing;
  const hasResult = result !== null;

  const renderHeader = () => {
    if (isComplete) {
      return (
        <>
          <CheckCircleOutlined className="header-icon success" />
          <span className="header-text">思考过程</span>
        </>
      );
    }
    return (
      <>
        <LoadingOutlined spin className="header-icon" />
        <span className="header-text">AI 正在处理</span>
      </>
    );
  };
  
  return (
    <div className="progress-container">
      <div className="progress-header">
        {renderHeader()}
      </div>
      <div className="progress-steps">
        {nonUserLogs.map((log, index) => (
          <ProgressStep
            key={index}
            log={log}
            isLast={index === nonUserLogs.length - 1}
            isActive={processing && index === nonUserLogs.length - 1}
          />
        ))}
      </div>
      {isComplete && !hasResult && (
        <div className="waiting-result">
          <Spin size="small" />
          <span>等待响应...</span>
        </div>
      )}
    </div>
  );
};

export default ChatBotProgressRenderer;