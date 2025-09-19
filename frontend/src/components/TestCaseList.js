import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Table, Input, Button, Space, Typography, Tag, notification } from 'antd';

const { Title } = Typography;

function TestCaseList({ projectId }) { // Accept projectId as a prop
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  // Local filter state, only used when projectId is not provided
  const [filter, setFilter] = useState({ project: '', module: '' });

  const fetchTestCases = useCallback(async () => {
    setLoading(true);
    try {
      let url = 'http://localhost:8000/api/testcases/';
      const params = new URLSearchParams();
      
      if (projectId) {
        params.append('project', projectId);
      } else {
        if (filter.project) params.append('project__name__icontains', filter.project);
        if (filter.module) params.append('module__name__icontains', filter.module);
      }
      
      const queryString = params.toString();
      if (queryString) {
        url += `?${queryString}`;
      }

      const response = await axios.get(url);
      setTestCases(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取测试用例失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [projectId, filter]); // Depend on both projectId and local filter state

  useEffect(() => {
    fetchTestCases();
  }, [fetchTestCases]);

  const handleFilterChange = (e) => {
    setFilter({ ...filter, [e.target.name]: e.target.value });
  };

  const handleSearch = () => {
    // The fetch is already dependent on the filter state, 
    // but we call it explicitly to trigger a search on button click.
    fetchTestCases();
  };

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', render: (text) => <strong>{text}</strong> },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '模块', dataIndex: 'module_name', key: 'module_name' },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => {
        let color = 'blue';
        if (priority === 'High' || priority === 'P0') color = 'volcano';
        else if (priority === 'Medium' || priority === 'P1') color = 'orange';
        return <Tag color={color}>{priority ? priority.toUpperCase() : ''}</Tag>;
      },
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => new Date(text).toLocaleString() },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!projectId && <Title level={2}>测试用例列表</Title>} 
      
      {!projectId && (
        <Space>
          <Input
            placeholder="按项目名称搜索"
            name="project"
            value={filter.project}
            onChange={handleFilterChange}
            style={{ width: 200 }}
          />
          <Input
            placeholder="按模块名称搜索"
            name="module"
            value={filter.module}
            onChange={handleFilterChange}
            style={{ width: 200 }}
          />
          <Button onClick={handleSearch} type="primary">
            搜索
          </Button>
        </Space>
      )}

      <Table
        columns={columns}
        dataSource={testCases}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10, showSizeChanger: true }}
      />
    </Space>
  );
}

export default TestCaseList;