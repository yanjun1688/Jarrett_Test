import React from 'react';
import { Steps, Tag, Collapse, Typography, Space, Descriptions, Badge } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

const REQUEST_TYPE_COLORS = {
  setup: 'orange',
  normal: 'blue',
  teardown: 'purple',
};

const REQUEST_TYPE_LABELS = {
  setup: 'Setup',
  normal: 'Normal',
  teardown: 'Teardown',
};

const ExecutionTimeline = ({ stepResults = [], executionStatus }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'passed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'skipped':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed':
        return '#52c41a';
      case 'failed':
        return '#ff4d4f';
      case 'running':
        return '#1890ff';
      case 'skipped':
        return '#faad14';
      default:
        return '#8c8c8c';
    }
  };

  const renderStepDetail = (result) => (
    <Descriptions size="small" column={2} style={{ marginTop: 8 }}>
      <Descriptions.Item label="状态码">
        <Tag color={result.status_code >= 200 && result.status_code < 300 ? 'green' : 'red'}>
          {result.status_code || '-'}
        </Tag>
      </Descriptions.Item>
      <Descriptions.Item label="响应时间">
        {result.response_time ? `${result.response_time.toFixed(2)}ms` : '-'}
      </Descriptions.Item>
      
      {result.extracted_vars && Object.keys(result.extracted_vars).length > 0 && (
        <Descriptions.Item label="提取变量" span={2}>
          <Space direction="vertical" size={4}>
            {Object.entries(result.extracted_vars).map(([key, value]) => (
              <Text key={key}>
                <Tag color="processing">{key}</Tag>
                <Text type="secondary">= {String(value).substring(0, 30)}</Text>
              </Text>
            ))}
          </Space>
        </Descriptions.Item>
      )}
      
      {result.assertion_results && result.assertion_results.length > 0 && (
        <Descriptions.Item label="断言结果" span={2}>
          <Space direction="vertical" size={4}>
            {result.assertion_results.map((assertion, idx) => (
              <Text key={idx}>
                <Badge status={assertion.passed ? 'success' : 'error'} />
                <Text>{assertion.type}: {assertion.passed ? '通过' : '失败'}</Text>
                {!assertion.passed && <Text type="danger">({assertion.message || '不匹配'})</Text>}
              </Text>
            ))}
          </Space>
        </Descriptions.Item>
      )}
      
      {result.error_message && (
        <Descriptions.Item label="错误信息" span={2}>
          <Text type="danger">{result.error_message}</Text>
        </Descriptions.Item>
      )}
    </Descriptions>
  );

  const steps = stepResults.map((result, index) => ({
    title: (
      <Space>
        <Tag color={REQUEST_TYPE_COLORS[result.request_type || 'normal']}>
          {REQUEST_TYPE_LABELS[result.request_type || 'normal']}
        </Tag>
        <span>{result.step_name || `步骤 ${index + 1}`}</span>
      </Space>
    ),
    description: (
      <Space direction="vertical" size={4}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {result.method} {result.url?.substring(0, 40)}
        </Text>
        <Tag color={getStatusColor(result.status)}>
          {getStatusIcon(result.status)} {result.status}
        </Tag>
        {result.status !== 'skipped' && (
          <Collapse
            size="small"
            ghost
            items={[
              {
                key: '1',
                label: '详情',
                children: renderStepDetail(result),
              },
            ]}
          />
        )}
      </Space>
    ),
    status: result.status === 'passed' ? 'finish' : result.status === 'failed' ? 'error' : 'wait',
    icon: getStatusIcon(result.status),
  }));

  return (
    <Steps
      direction="vertical"
      size="small"
      current={executionStatus === 'running' ? stepResults.filter(r => r.status !== 'pending').length : stepResults.length}
      items={steps}
      style={{ marginTop: 16 }}
    />
  );
};

export default ExecutionTimeline;