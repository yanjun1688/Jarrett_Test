import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Button, Space, Input, Select, Tag, Modal, message } from 'antd';
import { SearchOutlined, PlayCircleOutlined, EyeOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { testFlowAPI } from '../api';
import TestFlowBuilder from './TestFlowBuilder';

const { Search } = Input;
const { Option } = Select;

const TestFlowList = () => {
  const [flows, setFlows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'builder'

  const fetchFlows = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchText) params.search = searchText;
      if (projectFilter) params.project_id = projectFilter;

      const response = await testFlowAPI.listTestFlows(params);
      if (response.success) {
        setFlows(response.data);
      } else {
        message.error(response.message || '获取流程列表失败');
      }
    } catch (error) {
      console.error('获取流程列表失败:', error);
      message.error('获取流程列表失败');
    } finally {
      setLoading(false);
    }
  }, [searchText, projectFilter]);

  useEffect(() => {
    fetchFlows();
  }, [fetchFlows]);

  const handleDelete = async (flowId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该测试流程吗？此操作不可恢复。',
      onOk: async () => {
        try {
          // 这里可以添加删除逻辑
          console.log('Deleting flow:', flowId);
          message.success('流程删除成功');
          fetchFlows();
        } catch (error) {
          console.error('删除流程失败:', error);
          message.error('删除流程失败');
        }
      }
    });
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.scenario_description}
          </div>
        </div>
      )
    },
    {
      title: '项目',
      dataIndex: 'project',
      key: 'project',
      render: (project) => (
        <Tag color="blue">{project?.name || '未指定'}</Tag>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString()
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusMap = {
          'active': <Tag color="green">活跃</Tag>,
          'draft': <Tag color="orange">草稿</Tag>,
          'archived': <Tag color="gray">已归档</Tag>
        };
        return statusMap[status] || <Tag color="default">未知</Tag>;
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<PlayCircleOutlined />}
            onClick={() => console.log('Execute flow:', record.id)}
          >
            执行
          </Button>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => console.log('View flow:', record.id)}
          >
            查看
          </Button>
          <Button
            type="text"
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
            danger
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  if (viewMode === 'builder') {
    return (
      <div>
        <div style={{ marginBottom: 16 }}>
          <Button
            onClick={() => setViewMode('list')}
          >
            返回列表
          </Button>
        </div>
        <TestFlowBuilder />
      </div>
    );
  }

  return (
    <div>
      <Card title="测试流程管理">
        <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setViewMode('builder')}
          >
            创建流程
          </Button>
          <Search
            placeholder="搜索流程名称或场景描述"
            allowClear
            enterButton={<SearchOutlined />}
            size="middle"
            style={{ width: 300 }}
            onSearch={setSearchText}
          />
          <Select
            placeholder="选择项目"
            style={{ width: 200 }}
            allowClear
            onChange={setProjectFilter}
          >
            {/* 这里可以根据实际项目数据填充 */}
            <Option value="1">项目1</Option>
            <Option value="2">项目2</Option>
            <Option value="3">项目3</Option>
          </Select>
        </div>

        <Table
          columns={columns}
          dataSource={flows}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default TestFlowList;
