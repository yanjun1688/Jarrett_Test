import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Table, Button, Space, Typography, Tag, Dropdown, Menu, notification } from 'antd';
import { DownOutlined } from '@ant-design/icons';

const { Title } = Typography;

const getStatusTag = (status) => {
  switch (status) {
    case 'passed':
      return <Tag color="success">Passed</Tag>;
    case 'failed':
      return <Tag color="error">Failed</Tag>;
    case 'blocked':
      return <Tag color="warning">Blocked</Tag>;
    case 'skipped':
      return <Tag color="default">Skipped</Tag>;
    default:
      return <Tag>{status}</Tag>;
  }
};

function TestExecutionList({ projectId }) { // Accept projectId as a prop
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchExecutions = useCallback(async () => {
    setLoading(true);
    try {
      let url = 'http://localhost:8000/api/executions/';
      if (projectId) {
        // Assume backend supports filtering executions by project ID via testcase
        url += `?testcase__project=${projectId}`;
      }
      const response = await axios.get(url);
      setExecutions(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取执行记录失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [projectId]); // Add projectId to dependency array

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  const handleStatusChange = async (executionId, newStatus) => {
    try {
      await axios.patch(`http://localhost:8000/api/executions/${executionId}/`, {
        status: newStatus,
      });
      notification.success({ message: `状态已更新为 ${newStatus}` });
      fetchExecutions(); // Reload data
    } catch (error) {
      notification.error({ message: '更新状态失败', description: error.message });
    }
  };

  const columns = [
    { title: '测试用例', dataIndex: 'testcase_title', key: 'testcase_title' },
    { title: '执行人', dataIndex: 'executor_name', key: 'executor_name', render: (name) => name || '未知' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag,
    },
    { title: '执行时间', dataIndex: 'executed_at', key: 'executed_at', render: (text) => new Date(text).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        const menu = (
          <Menu onClick={({ key }) => handleStatusChange(record.id, key)}>
            <Menu.Item key="passed">Passed</Menu.Item>
            <Menu.Item key="failed">Failed</Menu.Item>
            <Menu.Item key="blocked">Blocked</Menu.Item>
          </Menu>
        );
        return (
          <Dropdown overlay={menu}>
            <Button>
              更新状态 <DownOutlined />
            </Button>
          </Dropdown>
        );
      },
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!projectId && <Title level={2}>测试执行记录</Title>}
      <Table
        columns={columns}
        dataSource={executions}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    </Space>
  );
}

export default TestExecutionList;