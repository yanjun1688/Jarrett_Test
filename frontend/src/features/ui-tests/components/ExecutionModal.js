/**
 * 执行结果弹窗组件
 */
import React from 'react';
import { Modal, Button, Space, Row, Col, Card, Tag, Typography, Divider, Spin } from 'antd';
import { SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { EXECUTION_STATUS, EXECUTION_STATUS_LABELS } from '../../../constants';
import '../../../css/UiTestManager.css';

const { Title, Text } = Typography;

const ExecutionModal = ({ visible, executionDetail, onClose }) => {
  if (!executionDetail) {
    return null;
  }

  const getStatusColor = (status) => {
    switch (status) {
      case EXECUTION_STATUS.PASSED:
      case 'passed':
        return 'green';
      case EXECUTION_STATUS.FAILED:
      case 'failed':
        return 'red';
      case EXECUTION_STATUS.RUNNING:
      case 'running':
        return 'processing';
      case 'pending':
        return 'default';
      default:
        return 'default';
    }
  };

  const getStatusText = (status) => {
    const statusMap = {
      'pending': '等待执行',
      'running': '执行中',
      'passed': '执行通过',
      'failed': '执行失败',
    };
    return EXECUTION_STATUS_LABELS[status] || statusMap[status] || status || '未知';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'passed':
      case EXECUTION_STATUS.PASSED:
        return <CheckCircleOutlined />;
      case 'failed':
      case EXECUTION_STATUS.FAILED:
        return <CloseCircleOutlined />;
      case 'running':
      case EXECUTION_STATUS.RUNNING:
        return <SyncOutlined spin />;
      case 'pending':
        return <ClockCircleOutlined />;
      default:
        return null;
    }
  };

  const isRunning = executionDetail.status === 'running' || executionDetail.status === 'pending';

  return (
    <Modal
      title={
        <Space>
          <span>UI 测试执行结果</span>
          {isRunning && <Spin size="small" />}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          {isRunning ? '后台执行' : '关闭'}
        </Button>,
      ]}
      width={900}
    >
      <Space direction="vertical" className="ui-test-space-vertical" size="middle" style={{ width: '100%' }}>
        {/* 状态和执行时长 */}
        <Space size="large">
          <Space>
            <Text strong>状态：</Text>
            <Tag 
              icon={getStatusIcon(executionDetail.status)} 
              color={getStatusColor(executionDetail.status)}
            >
              {getStatusText(executionDetail.status)}
            </Tag>
          </Space>
          <Space>
            <Text strong>执行时长：</Text>
            <Text>
              {executionDetail.execution_duration_ms
                ? `${(executionDetail.execution_duration_ms / 1000).toFixed(2)}秒`
                : executionDetail.duration
                ? `${executionDetail.duration.toFixed(2)}秒`
                : isRunning
                ? '计算中...'
                : '-'}
            </Text>
          </Space>
        </Space>

        {/* 进度显示 */}
        {isRunning && (
          <Card size="small" className="ui-test-running-card">
            <Text>执行中，请稍候...</Text>
          </Card>
        )}

        {/* 执行日志 */}
        {executionDetail.logs && executionDetail.logs.length > 0 && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>执行日志</Title>
            <Card className="ui-test-log-card">
              <pre className="ui-test-log-pre">
                {executionDetail.logs.join('\n')}
              </pre>
            </Card>
          </>
        )}

        {/* 截图列表 */}
        {executionDetail.screenshots && executionDetail.screenshots.length > 0 && (
          <>
            <Divider />
            <Title level={5}>截图 ({executionDetail.screenshots.length})</Title>
            <Row gutter={[16, 16]}>
              {executionDetail.screenshots.map((screenshot, idx) => (
                <Col span={8} key={idx}>
                  <Card
                    size="small"
                    cover={
                      <img
                        alt={`截图 ${idx + 1}`}
                        src={screenshot.startsWith('http') || screenshot.startsWith('/') ? screenshot : `/media/${screenshot}`}
                        className="ui-test-screenshot-img"
                      />
                    }
                  >
                    <Card.Meta
                      description={
                        <Text ellipsis className="ui-test-screenshot-text">
                          {screenshot}
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
        {executionDetail.error_message && (
          <>
            <Divider />
            <Title level={5}>错误信息</Title>
            <Card className="ui-test-error-card">
              <pre className="ui-test-error-pre">
                {executionDetail.error_message}
              </pre>
            </Card>
          </>
        )}
      </Space>
    </Modal>
  );
};

export default React.memo(ExecutionModal);
