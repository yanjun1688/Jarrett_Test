/**
 * 统一执行日志弹窗组件
 * 支持 API 测试、UI 测试、集合执行三种类型
 * 配合后端同步执行优化，无需复杂轮询机制
 */
import React from 'react';
import { Modal, Button, Space, Row, Col, Card, Tag, Typography, Divider, Table, Progress } from 'antd';
import { 
  SyncOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  ClockCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import '../css/UiTestManager.css';

const { Title, Text } = Typography;

/**
 * ExecutionLogModal 组件
 * 
 * @param {boolean} visible - 弹窗是否可见
 * @param {function} onClose - 关闭回调
 * @param {string} title - 弹窗标题
 * @param {string} executionType - 执行类型: 'api' | 'ui' | 'collection'
 * @param {string} status - 执行状态: 'pending' | 'running' | 'passed' | 'failed'
 * @param {number} totalCount - 总执行请求数
 * @param {number} passedCount - 通过数
 * @param {number} failedCount - 失败数
 * @param {number} executionDuration - 执行时长（秒）
 * @param {string|string[]} logs - 执行日志
 * @param {number} responseStatus - HTTP 状态码（API 测试）
 * @param {number} responseTime - 响应时间（API 测试）
 * @param {string} responseBody - 响应体（API 测试）
 * @param {Array} assertions - 断言结果（API 测试）
 * @param {Array} screenshots - 截图列表（UI 测试）
 * @param {string} errorMessage - 错误信息
 * @param {string} startTime - 开始时间
 * @param {string} endTime - 结束时间
 * @param {number} progress - 进度百分比（集合执行）
 */
const ExecutionLogModal = ({
  visible,
  onClose,
  title = '执行结果',
  executionType = 'api',
  status = 'pending',
  totalCount = 0,
  passedCount = 0,
  failedCount = 0,
  executionDuration,
  logs,
  responseStatus,
  responseTime,
  responseBody,
  assertions = [],
  screenshots = [],
  errorMessage,
  startTime,
  endTime,
  progress = 0,
}) => {
  const getStatusColor = (s) => {
    switch (s) {
      case 'passed':
      case 'success':
        return 'green';
      case 'failed':
      case 'error':
        return 'red';
      case 'running':
        return 'processing';
      case 'pending':
      default:
        return 'default';
    }
  };

  const getStatusText = (s) => {
    const statusMap = {
      'pending': '等待执行',
      'running': '执行中',
      'passed': '执行通过',
      'success': '执行成功',
      'failed': '执行失败',
      'error': '执行错误',
    };
    return statusMap[s] || s || '未知';
  };

  const getStatusIcon = (s) => {
    switch (s) {
      case 'passed':
      case 'success':
        return <CheckCircleOutlined />;
      case 'failed':
      case 'error':
        return <CloseCircleOutlined />;
      case 'running':
        return <SyncOutlined spin />;
      case 'pending':
        return <ClockCircleOutlined />;
      default:
        return null;
    }
  };

  const isRunning = status === 'running' || status === 'pending';

  // 格式化日志内容
  const formatLogs = () => {
    if (!logs) return null;
    if (Array.isArray(logs)) {
      return logs.join('\n');
    }
    return logs;
  };

  // 格式化响应体
  const formatResponseBody = () => {
    if (!responseBody) return null;
    try {
      const parsed = JSON.parse(responseBody);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return responseBody;
    }
  };

  // 断言结果表格列
  const assertionColumns = [
    {
      title: '断言类型',
      dataIndex: 'assertion_type',
      key: 'assertion_type',
      width: 120,
      render: (type) => {
        const typeMap = {
          'status_code': '状态码',
          'response_time': '响应时间',
          'response_body_field': '响应体字段',
          'response_header_field': '响应头字段',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '字段路径',
      dataIndex: 'field_path',
      key: 'field_path',
      width: 150,
      ellipsis: true,
    },
    {
      title: '比较方式',
      dataIndex: 'comparison',
      key: 'comparison',
      width: 100,
      render: (comp) => {
        const compMap = {
          'equals': '等于',
          'not_equals': '不等于',
          'contains': '包含',
          'not_contains': '不包含',
          'greater_than': '大于',
          'less_than': '小于',
          'exists': '存在',
          'not_exists': '不存在',
        };
        return compMap[comp] || comp;
      },
    },
    {
      title: '期望值',
      dataIndex: 'expected_value',
      key: 'expected_value',
      width: 120,
      ellipsis: true,
    },
    {
      title: '实际值',
      dataIndex: 'actual_value',
      key: 'actual_value',
      width: 120,
      ellipsis: true,
      render: (val) => {
        if (val === null || val === undefined) return '-';
        const str = String(val);
        return str.length > 50 ? str.substring(0, 50) + '...' : str;
      },
    },
    {
      title: '结果',
      dataIndex: 'passed',
      key: 'passed',
      width: 80,
      render: (passed) => (
        <Tag color={passed ? 'green' : 'red'}>
          {passed ? '通过' : '失败'}
        </Tag>
      ),
    },
  ];

  // 计算执行时长显示
  const getDurationDisplay = () => {
    if (executionDuration !== undefined && executionDuration !== null) {
      return `${executionDuration.toFixed(2)}秒`;
    }
    if (responseTime !== undefined && responseTime !== null) {
      return `${responseTime.toFixed(4)}秒`;
    }
    if (isRunning) {
      return '计算中...';
    }
    return '-';
  };

  // 获取总数标签
  const getTotalLabel = () => {
    switch (executionType) {
      case 'ui':
        return '总 Actions';
      case 'collection':
        return '总请求数';
      case 'api':
      default:
        return '总请求数';
    }
  };

  return (
    <Modal
      title={
        <Space>
          {isRunning ? (
            <LoadingOutlined spin style={{ color: '#1890ff' }} />
          ) : status === 'passed' || status === 'success' ? (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          ) : status === 'failed' || status === 'error' ? (
            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
          ) : (
            <ClockCircleOutlined style={{ color: '#faad14' }} />
          )}
          <span>{title}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          {isRunning ? '后台执行' : '关闭'}
        </Button>,
      ]}
      width={1000}
      destroyOnClose
    >
      <Space direction="vertical" className="ui-test-space-vertical" size="middle" style={{ width: '100%' }}>
        {/* 状态概览 */}
        <Card size="small">
          <Row gutter={16}>
            <Col span={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">状态</Text>
                <Tag 
                  icon={getStatusIcon(status)} 
                  color={getStatusColor(status)}
                  style={{ marginTop: 4 }}
                >
                  {getStatusText(status)}
                </Tag>
              </Space>
            </Col>
            <Col span={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">{getTotalLabel()}</Text>
                <Text strong style={{ fontSize: 16 }}>{totalCount}</Text>
              </Space>
            </Col>
            <Col span={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">通过 / 失败</Text>
                <Space>
                  <Text style={{ color: '#52c41a', fontWeight: 'bold' }}>{passedCount}</Text>
                  <Text>/</Text>
                  <Text style={{ color: '#ff4d4f', fontWeight: 'bold' }}>{failedCount}</Text>
                </Space>
              </Space>
            </Col>
            <Col span={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">执行时长</Text>
                <Text strong>{getDurationDisplay()}</Text>
              </Space>
            </Col>
          </Row>

          {/* API 测试特有：HTTP 状态码和响应时间 */}
          {executionType === 'api' && (responseStatus || responseTime) && (
            <Row gutter={16} style={{ marginTop: 16 }}>
              {responseStatus && (
                <Col span={6}>
                  <Space direction="vertical" size={0}>
                    <Text type="secondary">HTTP 状态码</Text>
                    <Tag color={responseStatus >= 200 && responseStatus < 300 ? 'green' : 'red'}>
                      {responseStatus}
                    </Tag>
                  </Space>
                </Col>
              )}
              {responseTime !== undefined && responseTime !== null && (
                <Col span={6}>
                  <Space direction="vertical" size={0}>
                    <Text type="secondary">响应时间</Text>
                    <Text strong>{responseTime.toFixed(4)}秒</Text>
                  </Space>
                </Col>
              )}
            </Row>
          )}

          {/* 进度条 - 适配同步执行 */}
          {isRunning && executionType === 'collection' && (
            <Progress percent={progress} status="active" style={{ marginTop: 12 }} />
          )}
          {!isRunning && status === 'passed' && (
            <Progress percent={100} status="success" style={{ marginTop: 12 }} />
          )}
          {!isRunning && (status === 'failed' || status === 'error') && (
            <Progress percent={Math.round((passedCount / Math.max(totalCount, 1)) * 100)} status="exception" style={{ marginTop: 12 }} />
          )}
        </Card>

        {/* 断言结果（API 测试） - 简化逻辑，适配后端同步结果 */}
        {executionType === 'api' && assertions && assertions.length > 0 && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>断言结果 ({passedCount}/{assertions.length} 通过)</Title>
            <Table
              columns={assertionColumns}
              dataSource={assertions.map((a, i) => ({ ...a, key: a.id || i }))}
              size="small"
              pagination={{ pageSize: 10 }}
              scroll={{ x: 700 }}
            />
          </>
        )}

        {/* 执行日志 - 改良显示 */}
        {logs && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>执行日志</Title>
            <Card 
              className="ui-test-log-card"
              bodyStyle={{ 
                maxHeight: 250,
                overflow: 'auto',
                fontSize: 12,
                backgroundColor: '#f5f5f5',
                fontFamily: 'monospace'
              }}
            >
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {formatLogs()}
              </pre>
            </Card>
          </>
        )}

        {/* 响应数据（API 测试） */}
        {executionType === 'api' && responseBody && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>响应数据</Title>
            <Card 
              size="small"
              bodyStyle={{ 
                maxHeight: 300, 
                overflow: 'auto', 
                backgroundColor: '#f0f2f5',
                padding: 12,
                fontFamily: 'monospace',
                fontSize: 12
              }}
            >
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {formatResponseBody()}
              </pre>
            </Card>
          </>
        )}

        {/* 截图列表（UI 测试） */}
        {executionType === 'ui' && screenshots && screenshots.length > 0 && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>截图 ({screenshots.length})</Title>
            <Row gutter={[16, 16]}>
              {screenshots.map((screenshot, idx) => (
                <Col span={8} key={idx}>
                  <Card
                    size="small"
                    cover={
                      <img
                        alt={`截图 ${idx + 1}`}
                        src={screenshot.startsWith('http') || screenshot.startsWith('/') ? screenshot : `/media/${screenshot}`}
                        className="ui-test-screenshot-img"
                        style={{ maxHeight: 200, objectFit: 'contain' }}
                      />
                    }
                  >
                    <Card.Meta
                      description={
                        <Text ellipsis className="ui-test-screenshot-text">
                          {screenshot.split('/').pop()}
                        </Text>
                      }
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          </>
        )}

        {/* 错误信息 */}
        {errorMessage && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>错误信息</Title>
            <Card 
              className="ui-test-error-card"
              bodyStyle={{ 
                backgroundColor: '#fff1f0',
                border: '1px solid #ffa39e',
                fontFamily: 'monospace',
                fontSize: 12 
              }}
            >
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#cf1322' }}>
                {errorMessage}
              </pre>
            </Card>
          </>
        )}

        {/* 执行时间 */}
        {(startTime || endTime) && (
          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Text type="secondary">
              {startTime && `开始时间: ${startTime}`}
              {startTime && endTime && ' | '}
              {endTime && `结束时间: ${endTime}`}
            </Text>
          </div>
        )}
      </Space>
    </Modal>
  );
};

export default React.memo(ExecutionLogModal);
