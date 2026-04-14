import React from 'react';
import { Drawer, Card, Row, Col, Typography, Tag, Progress, Space, Button } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import ExecutionTimeline from './shared/ExecutionTimeline';

const { Title, Text } = Typography;

const ExecutionResultDrawer = ({
  visible,
  execution,
  onClose,
  onReExecute,
}) => {
  if (!execution) return null;

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff', fontSize: 24 }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#faad14', fontSize: 24 }} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'green';
      case 'failed':
        return 'red';
      case 'running':
        return 'processing';
      default:
        return 'default';
    }
  };

  const formatDuration = (duration) => {
    if (!duration) return '-';
    if (typeof duration === 'number') {
      return `${duration.toFixed(2)}秒`;
    }
    return duration;
  };

  const passRate = execution.total_requests > 0
    ? Math.round((execution.passed_requests / execution.total_requests) * 100)
    : 0;

  return (
    <Drawer
      title={
        <Space>
          {getStatusIcon(execution.status)}
          <span>执行结果 - {execution.collection_name || '请求集合'}</span>
        </Space>
      }
      placement="right"
      width={700}
      open={visible}
      onClose={onClose}
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={onClose}>关闭</Button>
          {onReExecute && (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={onReExecute}>
              重新执行
            </Button>
          )}
        </Space>
      }
    >
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={4}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">状态</Text>
              <Tag icon={getStatusIcon(execution.status)} color={getStatusColor(execution.status)}>
                {execution.status === 'success' ? '成功' : 
                 execution.status === 'failed' ? '失败' : 
                 execution.status === 'running' ? '执行中' : '待执行'}
              </Tag>
            </Space>
          </Col>
          <Col span={4}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">总数</Text>
              <Text strong style={{ fontSize: 16 }}>{execution.total_requests}</Text>
            </Space>
          </Col>
          <Col span={4}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">通过</Text>
              <Text style={{ color: '#52c41a', fontWeight: 'bold', fontSize: 16 }}>
                {execution.passed_requests}
              </Text>
            </Space>
          </Col>
          <Col span={4}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">失败</Text>
              <Text style={{ color: '#ff4d4f', fontWeight: 'bold', fontSize: 16 }}>
                {execution.failed_requests}
              </Text>
            </Space>
          </Col>
          <Col span={4}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">耗时</Text>
              <Text strong>{formatDuration(execution.duration)}</Text>
            </Space>
          </Col>
          <Col span={4}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">通过率</Text>
              <Text strong>{passRate}%</Text>
            </Space>
          </Col>
        </Row>
        
        <Progress
          percent={passRate}
          status={execution.status === 'success' ? 'success' : execution.status === 'failed' ? 'exception' : 'active'}
          style={{ marginTop: 12 }}
        />
      </Card>

      <Title level={5}>执行步骤</Title>
      
      <ExecutionTimeline
        stepResults={execution.step_results || []}
        executionStatus={execution.status}
      />

      {execution.output && (
        <Card size="small" style={{ marginTop: 16 }} title="执行日志">
          <pre style={{
            margin: 0,
            fontSize: 12,
            maxHeight: 200,
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            backgroundColor: '#f5f5f5',
            padding: 8,
            borderRadius: 4,
          }}>
            {execution.output}
          </pre>
        </Card>
      )}
    </Drawer>
  );
};

export default ExecutionResultDrawer;