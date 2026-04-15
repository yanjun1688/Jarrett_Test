import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/axios';
import { Table, Input, Button, Space, Typography, Tag, notification, Modal, Form, Select, Tabs } from 'antd';
import { handleApiError } from '../utils/errorHandler';
import FeatureTestCaseManager from './FeatureTestCaseManager';

const { Title } = Typography;
const { TabPane } = Tabs;

/**
 * 解析并校验 headers 输入 - 只接受标准 JSON 格式
 * @param {string} input - 用户输入的 headers
 * @returns {object} - 解析后的 headers 对象
 * @throws {Error} - 如果不是标准 JSON 格式
 */
function parseHeadersInput(input) {
  if (!input || typeof input !== 'string') return {};
  
  const trimmed = input.trim();
  if (!trimmed) return {};
  
  // 只接受 JSON 格式
  if (!trimmed.startsWith('{')) {
    throw new Error('请求头格式错误：请使用标准 JSON 格式，例如 {"Content-Type": "application/json"}');
  }
  
  try {
    const parsed = JSON.parse(trimmed);
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      // 校验每个键值都是字符串
      for (const [key, value] of Object.entries(parsed)) {
        if (typeof key !== 'string' || typeof value !== 'string') {
          throw new Error('请求头格式错误：键和值都必须是字符串');
        }
      }
      return parsed;
    } else {
      throw new Error('请求头格式错误：必须是 JSON 对象格式');
    }
  } catch (e) {
    if (e.message.includes('请求头格式错误')) {
      throw e;
    }
    throw new Error('请求头格式错误：JSON 解析失败，请检查格式是否正确');
  }
}

function TestCaseList({ projectId }) { // Accept projectId as a prop
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('api');
  // Local filter state, only used when projectId is not provided
  const [filter, setFilter] = useState({ project: '', module: '' });
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  const fetchTestCases = useCallback(async (searchFilter = null) => {
    setLoading(true);
    try {
      // 使用传入的searchFilter，如果没有则使用空filter（用于初始加载，显示所有数据）
      const currentFilter = searchFilter !== null ? searchFilter : { project: '', module: '' };
      
      // 根据 activeTab 决定获取哪种数据
      if (activeTab === 'api') {
        // 构建API请求查询参数
        let apiRequestUrl = '/api-requests/';
        const apiRequestParams = new URLSearchParams();
        
        if (projectId) {
          apiRequestParams.append('project', projectId);
        } else {
          if (currentFilter.project) apiRequestParams.append('project__name__icontains', currentFilter.project);
          if (currentFilter.module) apiRequestParams.append('module__name__icontains', currentFilter.module);
        }
        
        const apiRequestQueryString = apiRequestParams.toString();
        if (apiRequestQueryString) {
          apiRequestUrl += `?${apiRequestQueryString}`;
        }
        
        const apiRequestsRes = await apiClient.get(apiRequestUrl);
        
        const allTestCases = (apiRequestsRes.data.results || []).map(item => ({
          ...item,
          test_type: 'api',
          project_name: item.project_name || item.project?.name,
          module_name: item.module_name || item.module?.name,
        }));
        
        // 按创建时间倒序
        allTestCases.sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });
        
        setTestCases(allTestCases);
      } else {
        // 功能测试 - 获取 testcases
        let testcaseUrl = '/testcases/';
        const testcaseParams = new URLSearchParams();
        
        if (projectId) {
          testcaseParams.append('project', projectId);
        } else {
          if (currentFilter.project) testcaseParams.append('project__name__icontains', currentFilter.project);
          if (currentFilter.module) testcaseParams.append('module__name__icontains', currentFilter.module);
        }
        
        const testcaseQueryString = testcaseParams.toString();
        if (testcaseQueryString) {
          testcaseUrl += `?${testcaseQueryString}`;
        }
        
        const testcasesRes = await apiClient.get(testcaseUrl);
        
        const allTestCases = (testcasesRes.data.results || []).map(item => ({
          ...item,
          test_type: 'feature',
          project_name: item.project_name || item.project?.name,
          module_name: item.module_name || item.module?.name,
        }));
        
        allTestCases.sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });
        
        setTestCases(allTestCases);
      }
    } catch (error) {
      notification.error({ message: '获取测试用例失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [projectId, activeTab]);

  // 只在初始加载时调用，或者projectId/activeTab改变时调用
  useEffect(() => {
    fetchTestCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, activeTab]); // 只在projectId改变时重新加载，不依赖fetchTestCases

  // 获取项目列表
  useEffect(() => {
    const fetchProjects = async () => {
      setProjectsLoading(true);
      try {
        const response = await apiClient.get('/projects/');
        setProjects(response.data.results || []);
      } catch (error) {
        notification.error({ message: '获取项目列表失败', description: error.message });
      } finally {
        setProjectsLoading(false);
      }
    };
    fetchProjects();
  }, []);

  const handleSearch = () => {
    // 点击搜索按钮时才发起请求，使用当前的filter值
    fetchTestCases(filter);
  };

  const openCreateApiTestModal = () => {
    form.resetFields();
    // If we're in a project context, pre-select that project
    if (projectId) {
      form.setFieldsValue({ project: projectId });
    }
    setModalOpen(true);
  };

  const handleCreateApiTest = async () => {
    try {
      const values = await form.validateFields();

      // 智能解析 headers，支持 JSON 和多行文本格式
      const headers = parseHeadersInput(values.headers);

      await apiClient.post('/api-requests/', {
        name: values.name,
        url: values.url,
        method: values.method,
        headers: JSON.stringify(headers),
        body: values.body || '',
        project: values.project,
      });
      notification.success({ message: 'API测试用例创建成功' });
      setModalOpen(false);
      form.resetFields();
      fetchTestCases(filter);
    } catch (error) {
      handleApiError(error, '创建API测试用例失败');
    }
  };

  const columns = React.useMemo(() => [
    {
      title: '类型',
      dataIndex: 'test_type',
      key: 'test_type',
      width: 100,
      render: (type) => {
        if (type === 'api') {
          return <Tag color="blue">API测试</Tag>;
        }
        return <Tag color="green">功能测试</Tag>;
      },
    },
    { title: '标题', dataIndex: 'title', key: 'title', render: (text) => <strong>{text}</strong> },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '模块', dataIndex: 'module_name', key: 'module_name' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => new Date(text).toLocaleString() },
  ], []);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!projectId && <Title level={2}>测试用例列表</Title>} 
      
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="API测试用例" key="api">
          {!projectId && (
            <Space style={{ marginBottom: 16 }}>
              <Select
                placeholder="选择项目搜索"
                style={{ width: 200 }}
                allowClear
                value={filter.project || undefined}
                onChange={(value) => setFilter(prev => ({ ...prev, project: value || '' }))}
                loading={projectsLoading}
              >
                {projects.map(p => (
                  <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>
                ))}
              </Select>
              <Button onClick={handleSearch} type="primary">
                搜索
              </Button>
              <Button onClick={openCreateApiTestModal} style={{ marginLeft: 16 }}>
                新增用例
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
        </TabPane>
        
        <TabPane tab="功能测试用例" key="feature">
          <FeatureTestCaseManager />
        </TabPane>
      </Tabs>

      <Modal
        title="添加API测试用例"
        open={modalOpen}
        onOk={handleCreateApiTest}
        onCancel={() => setModalOpen(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="project"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="请选择项目"
              loading={projectsLoading}
              disabled={projectsLoading || !!projectId}
            >
              {projects.map(project => (
                <Select.Option key={project.id} value={project.id}>
                  {project.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="name" label="请求名称" rules={[{ required: true, message: '请输入请求名称' }]}>
            <Input />
          </Form.Item>

          <Form.Item name="url" label="URL" rules={[{ required: true, message: '请输入URL' }]}>
            <Input placeholder="https://api.example.com/endpoint" />
          </Form.Item>

          <Form.Item
            name="method"
            label="请求方法"
            rules={[{ required: true, message: '请选择请求方法' }]}
            initialValue="GET"
          >
            <Select>
              <Select.Option value="GET">GET</Select.Option>
              <Select.Option value="POST">POST</Select.Option>
              <Select.Option value="PUT">PUT</Select.Option>
              <Select.Option value="PATCH">PATCH</Select.Option>
              <Select.Option value="DELETE">DELETE</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="headers" label="请求头（JSON格式）">
            <Input.TextArea rows={4} placeholder='{"Content-Type": "application/json", "Authorization": "Bearer token"}' />
          </Form.Item>

          <Form.Item name="body" label="请求体">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

export default TestCaseList;